import asyncio
import os
from django.core.handlers.wsgi import WSGIHandler
from django.core.servers.basehttp import WSGIServer
from aiogram.utils.executor import start_webhook
import config
from bot import dp, bot, start_all

WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = int(os.getenv('PORT', 0))

async def run_django_server():
    server = WSGIServer((WEBAPP_HOST, WEBAPP_PORT), WSGIHandler())
    server.serve_forever()

async def on_startup(dispatcher):
    await bot.set_webhook(config.APP_URL, drop_pending_updates=True)
    start_all()
    print("Django server starting...")
    await asyncio.to_thread(run_django_server)

def start_aio():
    print("Starting webhook...")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        start_webhook(
            dispatcher=dp,
            webhook_path=config.WEBHOOK_PATH,
            skip_updates=True,
            on_startup=on_startup,
            host=WEBAPP_HOST,
            port=WEBAPP_PORT,
        )
    )

if __name__ == "__main__":
    start_aio()

