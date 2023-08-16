import json

from aiogram.dispatcher.webhook import get_new_configured_app
from aiogram.types import Update

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator

from bot import getDP

dp = getDP()


class TelegramWebhookViews(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        print(request)
        json_string = request.body.decode('utf-8')
        update_data = json.loads(json_string)
        update = Update(update_data)
        dp.process_update(update)

        return HttpResponse(status=200), "!"

    def get(self, request, *args, **kwargs):
        print(request)
        return "!"
