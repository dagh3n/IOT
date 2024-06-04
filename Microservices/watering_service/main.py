import datetime
from MyMQTT import *
import time
import requests

class wateringSystem:
    def __init__(self,clientID,broker,port,topic_sensors, topic_actuators, topic_telegram_chat, resource_catalog):
        self.water = MyMQTT(clientID,broker,port,self)
        self.topic_sub = topic_sensors
        self.topic_pub = topic_actuators
        self.topic_telegram_chat = topic_telegram_chat
    def notify(self,topic,payload):
        data = json.loads(payload)
        # "topic_sensors": "smartplant/+/sensors",
        # "topic_actuators": "smartplant/device_id/actuators"
        device_id = topic.split('/')[1]
        publisher = self.topic_pub.replace("device_id", device_id)
        resource = requests.get(resource_catalog+'/device/'+device_id).json()
        vase = requests.get(resource_catalog+'/vase/'+resource['vase_id']).json()
        user_id = vase["vase_user"]
        user = requests.get(resource_catalog+'/user/'+user_id).json()
        telegram_chat = self.topic_pub.replace("telegram_chat_id", user["telegram_chat_id"])

        """ {
            'vase_id': vase_id,
            'bn': device_id,
            'e':
            [
                {'n': 'temperature', 'value': '', 'timestamp': '', 'unit': 'C'},
                {'n': 'soil_moisture', 'value': '', 'timestamp': '', 'unit': '%'}
                {'n': 'light_level', 'value': '', 'timestamp': '', 'unit': 'lumen'},
                {'n': 'watertank_level', 'value': '', 'timestamp': '', 'unit': '%'}
            ]
        } """
        soil_moisture = None
        watertank_level = None

        for i in data['e']:
            if i['n'] == 'soil_moisture':
                soil_moisture = i
            if i['n'] == 'watertank_level':
                watertank_level = i
            
        if soil_moisture:
            if soil_moisture['value'] < vase["plant"]["soil_moisture_min"]:
                # check from resource service if the device support watering
                if watertank_level and watertank_level['value'] > 5 and "MQTT" in resource["available_services"] and "pump" in resource["actuators"]:
                    self.water.myPublish(publisher+"/pump", {"pump_target":"1"})
                else:
                    self.water.myPublish(telegram_chat+"/alert", {"water":"low"})

            elif soil_moisture['value'] > vase["plant"]["soil_moisture_max"]:
                # check from resource service if the device support watering
                self.water.myPublish(telegram_chat+"/alert", {"water":"high"})

        if watertank_level and watertank_level['value'] < 15:
            self.water.myPublish(telegram_chat+"/alert", {"watertank":"low"})
                
        
    def startSim(self):
        self.control.start()
        self.control.mySubscribe(self.topic_sub)
    
    def stopSim(self):
        self.control.unsubscribe()
        self.control.stop()

if __name__ == "__main__":

    clientID = "watering_service"

    #get al service_catalog
    service_catalog = requests.get("http://localhost:8082/all").json()
    topicSensors = service_catalog.topics.topic_sensors
    topicActuators = service_catalog.topics.topic_actuators
    topic_telegram_chat = service_catalog.topics.topic_telegram_chat
    resource_catalog = service_catalog.reource_catalog_address
    broker = service_catalog.broker.broker_address
    port = service_catalog.broker.port

    controller = wateringSystem(clientID,broker,port,topicSensors,topicActuators,topic_telegram_chat,resource_catalog)
    controller.startSim()

    try:
        while True:        
            time.sleep(10)
    except KeyboardInterrupt:
            controller.stopSim()
    