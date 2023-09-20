import os
BOT_TOKEN = "6212783247:AAH-rrdrgpA-7x1KjAW4JXr4Z6-IOSpOJ18"
API_KEY="k6WRcPWcVCpuLPDJoJ7hYLDtsqZF6nMnD8UxKcqNCVyfkNJ1AYdbk35KCDyWZreJZc0L4g7mtvPcmxhPQ7eijKcJdj3gOCXkQZpiV66uZ1SZp2yevTf0n5zq8sHUm0GZGDvvh82SaTsr1nujVYV3w57UA8iDznh7u2sUGc5vZw0COhxW6x7wfNCLEL3iZztXMt583JMS2zeaeFfsMvFboU2RzQp5hXEzddZvmy1yUqDQHCF8FLFE3rK1zoJotQLe"
LOGIN="T3678102697ID"
APP_URL = "https://pay4exch-telegram.herokuapp.com/" + BOT_TOKEN
# DB_URI = "postgres://dsyasedeqdffle:506ea860d88423c177181b2ab6a9740f7267e22c0a4676263fab20d739494e56@ec2-23-20-211-19.compute-1.amazonaws.com:5432/dc3jofarp6a3fj"
DB_URI = "postgres://snwmefifncjzzg:d5ad22707c4ab85e4f9833054bfac587fceb3759efd38fee3e681048b41b0030@ec2-52-20-78-241.compute-1.amazonaws.com:5432/d1c16b586vnqum"
PAY_URL="https://paytest.online.tkbbank.ru/"
LIFE_TIME="4.00:00:00" #4 days
HEROKU_APP_NAME = os.getenv('HEROKU_APP_NAME')
WEBHOOK_HOST = f'https://{HEROKU_APP_NAME}.herokuapp.com'
WEBHOOK_PATH = f'/{BOT_TOKEN}'
WEBHOOK_URL = f'https://pay4exch-telegram.herokuapp.com/{BOT_TOKEN}'
