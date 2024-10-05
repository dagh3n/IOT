
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext
import requests
import time
import json
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import asyncio
import aiohttp
import aiofiles

resource_catalog_address = ''
service_expose_endpoint = 'http://serviceservice.duck.pictures'
vase_list = []
device_list = []
current_context = None
welcome_message = None
no_vase_found_message = None
vase_found_message = None
global_device_id = ""


async def start(update: Update, context: CallbackContext) -> None:
    welcome_message = await update.message.reply_text(
        "Welcome to the Smart Vase bot assitance, where you can indentify your plan, get suggestions and so much more!",)
    context.user_data["vase_list"]=[]
    context.user_data["device_list"]=[]
    context.user_data["current_user"]=None
    await handle_endpoints()
    if not await is_logged_in(update, context):
        await login(update, context)
    else:
        await handle_main_actions(update)


async def is_logged_in(update: Update, context: CallbackContext):
    current_user = context.user_data.get("current_user")
    isLoggedIn = current_user != None and current_user['telegram_chat_id'] == update.message.chat_id

    print(
        f'is user logged in: {isLoggedIn} loggin_user={current_user} \n chat_id={update.message.chat_id}')
    return isLoggedIn


async def login(update: Update, context: CallbackContext):
    global resource_catalog_address
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{resource_catalog_address}/listUser') as response:
            if response.status == 200:
                
                users_list = await response.json()
                for user in users_list:
                    if user['telegram_chat_id'] == update.message.chat_id:
                        context.user_data["current_user"]=user
                        print(f'User found and logged in. User = {user}')
                        await handle_main_actions(update)
                        break
                if context.user_data["current_user"] == None:
                    print('User not found')
                    await signup(update, context)


async def handle_endpoints():
    global resource_catalog_address, service_expose_endpoint
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{service_expose_endpoint}/all') as response:
            if response.status == 200:
                json_response = await response.json()
                resource_catalog_address = json_response['services']['resource_catalog_address']


""" def remove_message(update: Update, context: CallbackContext,message, is_query: bool = False):
    context.bot.delete_message(
        chat_id=update.callback_query.message.chat_id if is_query else update.message.chat_id, message_id=message.message_id)
"""

# Signup function
async def signup(update: Update, context):
    global resource_catalog_address
    async with aiohttp.ClientSession() as session:
        async with session.post(f'{resource_catalog_address}/user', json={'telegram_chat_id': update.message.chat_id}) as response:
            if response.status == 200:
                await login(update, context)

async def handle_main_actions(update: Update):
    keyboard = [
        [InlineKeyboardButton(
            "Add a new Smart Vase", callback_data='add_vase')],
        [InlineKeyboardButton(
            "See the list of connected Smart Vases", callback_data='vase_list')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Let's get started 🚀. How can I help you?", reply_markup=reply_markup)

async def add_vase(update: Update, context):
    current_user = context.user_data.get("current_user")
    instructions = f"""
    1. Turn on the vase and your phone's WIFI.
    2. Connect to the 'SmartVase' network and click [here](http://192.168.4.1/?user_id={current_user['user_id']})
    3. Reconnect to the internet and check your vase list.
    """
    await update.callback_query.message.reply_text(instructions, parse_mode='Markdown')

async def get_user_vase_list(update: Update, context):
    global resource_catalog_address
    current_user = context.user_data.get("current_user")
    vase_list = context.user_data.get("vase_list")
    device_list = context.user_data.get("device_list")

    async with aiohttp.ClientSession() as session:
        vase_list_response = await session.get(f'{resource_catalog_address}/listVase')
        device_list_response = await session.get(f'{resource_catalog_address}/listDevice')

        if vase_list_response.status == 200:
            global_vase_list = await vase_list_response.json()
            for vase in global_vase_list:
                if vase['user_id'] == current_user['user_id'] and vase not in vase_list:
                    vase_list.append(vase)

        if device_list_response.status == 200:
            global_device_list = await device_list_response.json()
            for device in global_device_list:
                if device['user_id'] == current_user['user_id'] and device not in device_list:
                    device_list.append(device)

        # Generate response based on the retrieved devices
        if device_list:
            keyboard_list = [[InlineKeyboardButton(f"Vase {dev['device_id']}", callback_data=f'vase_info_{dev["device_id"]}') for dev in device_list]]
            reply_markup = InlineKeyboardMarkup(keyboard_list)
            await update.callback_query.message.reply_text("Here are all your vases:", reply_markup=reply_markup)
        else:
            keyboard = [[InlineKeyboardButton("Refresh my Vase List", callback_data='vase_list')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.message.reply_text("You have no smart vases connected!", reply_markup=reply_markup)
   
# Show graph for a vase
async def show_graph(name: str, field_number: int, channel_id: str, days: int, context):
    chart_url = f"http://thingspeak.duck.pictures/{channel_id}/{field_number}?title={name}%20chart&days={str(days)}"
    live_chart = f"https://thingspeak.com/channels/{channel_id}/charts/{field_number}?dynamic=true&days={days}"

    current_user = context.user_data.get("current_user")
    chat_id = current_user['telegram_chat_id']
    bot = Bot(token="7058374905:AAFJc4qnJjW5TdDyTViyjW_R6PzcSqR22CE")

    await bot.send_message(chat_id=chat_id, text=f"Plotting the {name} chart, please wait...")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(chart_url, timeout=60) as response:
                if response.status == 200:
                    image_data = await response.read()
                    await bot.send_photo(chat_id=chat_id, photo=image_data, caption=f"{name} chart\nYou can view it [here]({live_chart})")
                else:
                    await bot.send_message(chat_id=chat_id, text=f"Failed to generate {name} chart.")
        except asyncio.TimeoutError:
            await bot.send_message(chat_id=chat_id, text="Timeout while generating chart.")

# Handle button presses
async def button(update: Update, context):
    query = update.callback_query
    await query.answer()

    if query.data.startswith('configure'):
        # Extract device_id from callback_data
        device_id = query.data.split('_')[1]
        global_device_id = device_id
        await query.edit_message_text(
            text="First, please send me an image of your plant so that I can identify it!")
    elif query.data.startswith('chart_'):
        parameter_type = query.data.split('_')[1]
        channel_id = query.data.split('_')[2]
        x = query.data.split('_')[3]
        days=1
        if x=="month":
            days=30
        if x=="year":
            days=365
        if x=="week":
            days=7

        if parameter_type == 'temperature':
            await show_graph("temperature", 1, channel_id, days, context)
        elif parameter_type == 'light':
            await show_graph("light", 3, channel_id, days, context)
        elif parameter_type == 'watertank':
            await show_graph("watertank", 4, channel_id, days, context)
        elif parameter_type == 'soil':
            await show_graph("soil_mosture", 2, channel_id, days, context)
        
            
    elif query.data.startswith('details_'):
        parameter_type = query.data.split('_')[1]
        channel_id = query.data.split('_')[2]
        keyboard = [
                [
                InlineKeyboardButton(
                    f"1 day", callback_data='chart_temperature_'+str(channel_id)+"_day"), 
                InlineKeyboardButton(
                    f"last 7 days", callback_data='chart_light_'+str(channel_id)+"_week")],   
                [InlineKeyboardButton(
                    f"last 30 days", callback_data='chart_watertank_'+str(channel_id)+"_month"), 
                InlineKeyboardButton(
                    f"last year", callback_data='chart_soil_'+str(channel_id)+"_year")
                ]
            ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.reply_text(text=f"Select the time range for the chart", reply_markup=reply_markup) 

       
    elif query.data.startswith('no_details_'):
        parameter_type = query.data.split('_')[2]
        await update.callback_query.message.reply_text(text=f"Sorry, still no data for {parameter_type}")    
    elif query.data == 'add_vase':
        global_device_id = ""
        await add_vase(update, context)
    elif query.data == 'vase_list':
        global_device_id = ""
        await get_user_vase_list(update, context)
    elif query.data.startswith('vase_info_'):
        # Extract device_id from callback_data
        device_id = query.data.split('_')[2]
        await vase_details(update, context, device_id)
      
def find_device_in_list_via_device_id(device_id, item_list):
    for item in item_list:
        if item['device_id'] == device_id:
            return item  # Restituisce l'oggetto dispositivo se trovato
    return None  # Restituisce None se non trovato

async def vase_details(update: Update, context, device_id: str):
    vase_list = context.user_data.get("vase_list")
    device_list = context.user_data.get("device_list")
    vase = find_device_in_list_via_device_id(device_id, vase_list)
    dev = find_device_in_list_via_device_id(device_id, device_list)
    channel_id = dev['channel_id']
    
    if vase:
        async with aiohttp.ClientSession() as session:
            response = await session.get(f"https://api.thingspeak.com/channels/{str(channel_id)}/feeds.json?results=1")
            res = await response.json()
            if len(res["feeds"]) > 0:
                data = res['feeds'][0]
                temperature = data['field1']
                light_level = data['field3']
                watertank_level = data['field4']
                soil_moisture = data['field2']
                keyboard = [
                    [
                    InlineKeyboardButton(f"Temperature = {temperature}", callback_data='details_temperature_'+str(channel_id)),
                    InlineKeyboardButton(f"Light = {light_level}", callback_data='details_light_'+str(channel_id))
                    ],
                    [
                    InlineKeyboardButton(f"Watertank = {watertank_level}", callback_data='details_watertank_'+str(channel_id)),
                    InlineKeyboardButton(f"Soil = {soil_moisture}", callback_data='details_soil_'+str(channel_id))
                    ],
                    [InlineKeyboardButton("Go back", callback_data='vase_list')]
                ]
            else:
                keyboard = [
                    [InlineKeyboardButton("Go back", callback_data='vase_list')]
                ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.reply_text(f"Details for Vase: {vase['vase_name']}", reply_markup=reply_markup)
     
async def handle_photo(update: Update, context):
    global global_device_id

    if not global_device_id:
        await update.message.reply_text("Make sure to select a vase before trying to upload.")
        return
    
    # Download the photo
    photo_file = await update.message.photo[-1].get_file()
    file_path = f"{photo_file.file_id}.jpg"
    await photo_file.download(file_path)

    await update.message.reply_text("Image received, let's see...")
    url = "http://recommendationservice.duck.pictures"

    try:
        async with aiohttp.ClientSession() as session:
            # Open the image file asynchronously
            async with aiofiles.open(file_path, 'rb') as file:
                form = aiohttp.FormData()
                form.add_field('images', file, filename=file_path, content_type='image/jpeg')

                # Send the request to the server
                async with session.post(url, data=form) as response:
                    if response.status == 200:
                        await update.message.reply_text('Image uploaded to server successfully!')

                        # Parse the response JSON
                        try:
                            chat_response = await response.json()
                        except json.JSONDecodeError as json_err:
                            print(f"Failed to parse JSON: {json_err}")
                            await update.message.reply_text('Failed to parse the server response.')
                            return

                        # Ensure that chat_response is a valid dictionary
                        if chat_response and isinstance(chat_response, dict):
                            print("Creating vase")
                            
                            # Check if required keys are present
                            required_keys = [
                                'plant_name', 'soil_moisture_min', 'hours_sun_suggested', 
                                'soil_moisture_max', 'temperature_min', 'temperature_max', 'description'
                            ]
                            missing_keys = [key for key in required_keys if key not in chat_response]
                            if missing_keys:
                                print(f"Missing keys in response: {missing_keys}")
                                await update.message.reply_text(f'Missing data in response: {", ".join(missing_keys)}')
                                return

                            # Construct the new vase dictionary
                            new_vase = {
                                'device_id': global_device_id,
                                'vase_name': chat_response['plant_name'],  # Using the plant name from the response
                                'user_id': context.user_data['current_user']['user_id'],
                                'vase_status': 'active',
                                'plant': {
                                    'plant_name': chat_response['plant_name'],
                                    'plant_schedule_water': chat_response['soil_moisture_min'],
                                    'plant_schedule_light_level': chat_response['hours_sun_suggested'],  # Use hours of sunlight suggestion
                                    'soil_moisture_min': chat_response['soil_moisture_min'],
                                    'soil_moisture_max': chat_response['soil_moisture_max'],
                                    'hours_sun_min': chat_response['hours_sun_suggested'],
                                    'temperature_min': chat_response['temperature_min'],
                                    'temperature_max': chat_response['temperature_max'],
                                    'description': chat_response['description']
                                }
                            }

                            # Send the new vase data to the resource catalog
                            async with session.post(f"{resource_catalog_address}/vase", json=new_vase) as res:
                                if res.status == 200:
                                    await update.message.reply_text(f"Vase with {chat_response['plant_name']} added successfully.")
                                else:
                                    await update.message.reply_text('Failed to add the vase.')

                    else:
                        print(await response.text())
                        await update.message.reply_text('Failed to upload the image.')

    except Exception as e:
        print(e)
        await update.message.reply_text('Something went wrong...')
        
def main():
    # Creiamo l'istanza dell'applicazione del bot
    application = Application.builder().token("7058374905:AAFJc4qnJjW5TdDyTViyjW_R6PzcSqR22CE").concurrent_updates(True).build()

    # Aggiungiamo i gestori per i comandi e i callback
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("vase_list", get_user_vase_list))
    application.add_handler(CommandHandler("add_vase", add_vase))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))  # Nota: filters è ora minuscolo in v20+

    # Avviamo il polling in modo asincrono
    #application.initialize()
    application.run_polling()  # Cambia rispetto alla versione sincrona
    #application.idle()

if __name__ == '__main__':
    import asyncio
    #asyncio.run(main())
    main()