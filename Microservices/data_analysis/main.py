import cherrypy
import json
import aiohttp
import asyncio
import numpy as np
import requests

class DataAnalysis:
    exposed = True

    def __init__(self, catalog):
        self.catalog = catalog

    @cherrypy.tools.json_out()
    def GET(self, *args, **kwargs):
        if args:
            device_id = args[0].lower()
            # Since CherryPy is synchronous, we need to run the async function using an event loop.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            vase_data = loop.run_until_complete(self.get_from_thingspeak(device_id))
            return vase_data
        else:
            raise cherrypy.HTTPError(404, "Arguments missing!")

    async def get_from_thingspeak(self, device_id):
        channel = None

        # Fetch the device list and vase list asynchronously
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.catalog['services']['resource_catalog']}/device/{device_id}") as device_resp:
                dev = await device_resp.json()
            async with session.get(f"{self.catalog['services']['resource_catalog']}/vaseByDevice/{device_id}") as vase_resp:
                vase = await vase_resp.json()

        if dev:
            channel = dev['channel_id']
        
        if not channel or not vase:
            return {"error": "Device or vase not found"}

        vase_data = {
            "temperature_alert": "",
            "soil_moisture_alert": "",
            "watertank_level_alert": "",
            "light_level_alert": ""
        }

        # Fetch the latest data from ThingSpeak
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.thingspeak.com/channels/{str(channel)}/feeds.json?results=1") as resp:
                res = await resp.json()
                if len(res["feeds"]) > 0:
                    data = res['feeds'][0]
                    vase_data["temperature"] = data['field1']
                    vase_data['light_level'] = data['field3']
                    vase_data['watertank_level'] = data['field4']
                    vase_data['soil_moisture'] = data['field2']

        # Fetch the data for the last 7 days from ThingSpeak
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.thingspeak.com/channels/{str(channel)}/feeds.json?days=7") as resp:
                res = await resp.json()
                if len(res["feeds"]) > 0:
                    data = res['feeds']
                    num_feeds = int(len(data) * 0.10)  # 10% of total feeds

                    # Extract and sort data fields
                    temperature = np.sort(np.array([float(feed['field1']) for feed in data if feed['field1']]))
                    light_level = np.sort(np.array([float(feed['field3']) for feed in data if feed['field3']]))
                    watertank_level = np.sort(np.array([float(feed['field4']) for feed in data if feed['field4']]))
                    soil_moisture = np.sort(np.array([float(feed['field2']) for feed in data if feed['field2']]))

                    # Temperature alerts
                    if np.average(temperature[:num_feeds]) < int(vase["plant"]["temperature_min"]):
                        vase_data["temperature_alert"] = "low"
                    if np.average(temperature[-num_feeds:]) > int(vase["plant"]["temperature_max"]):
                        vase_data["temperature_alert"] = "high"

                    # Soil moisture alerts
                    if np.average(soil_moisture[:num_feeds]) < int(vase["plant"]["soil_moisture_min"]):
                        vase_data["soil_moisture_alert"] = "low"
                    if np.average(soil_moisture[-num_feeds:]) > int(vase["plant"]["soil_moisture_max"]):
                        vase_data["soil_moisture_alert"] = "high"

                    # Light level alerts
                    num_light = num_feeds * int(vase["plant"]["hours_sun_min"]) / 24
                    if np.average(light_level[:int(num_light)]) < 50:  # Assume less than 50 lux is "very low"
                        vase_data["light_level_alert"] = "low"
        print(vase_data)
        return vase_data


if __name__ == '__main__':
    res = requests.get("https://serviceservice.duck.pictures").json()
    dataAnalysis = DataAnalysis(res)

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }

    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 5082  # Specify your desired port here
    })

    cherrypy.tree.mount(dataAnalysis, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()
