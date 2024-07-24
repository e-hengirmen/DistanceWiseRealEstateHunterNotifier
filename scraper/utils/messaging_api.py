import requests

TOKEN = '7159804806:AAFiICTIh64hq2K5jsdpZ2HY8xQQz9YkgRI'
CHAT_ID = '-1002014030805'

def send_message(message, bot_token=TOKEN, chat_id=CHAT_ID):
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    params = {
        'chat_id': chat_id,
        'text': message
    }
    requests.post(url, json=params)
    
    
