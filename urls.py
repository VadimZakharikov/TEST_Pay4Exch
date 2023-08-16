from django.urls import path

import config
import example
from tg_views import TelegramWebhookViews

urlpatterns = [
    path(f'{config.BOT_TOKEN}', TelegramWebhookViews.as_view(), name='telegram_webhook'),
    path('asd', example.example.as_view(), name = "test")
]