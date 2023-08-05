import base64
import config
import hashlib
import hmac
import json
import requests
import telebot
from requests import ConnectTimeout
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

bot = telebot.TeleBot(config.BOT_TOKEN)
def create_link(number, summ):
    parameters = dict(ExtID=number, Amount=summ, Description="test from bot",
                      ClientInfo={
                          "Email": "test@test.com",
                          "PhoneNumber": "+7 (911) 123-00-00"
                      }, TTL="4.00:00:00", CartPositions=[{
            "Quantity": 1.0,
            "Price": 300000,
            "Tax": 60,
            "Text": "Оплата по договору 123_test Иванова И.И.",
            "PaymentMethodType": 4,
            "PaymentSubjectType": 4
        }], AdditionalParameters={
            "DogovorID": "12345_test"
        })
    signature = hmac.new(config.API_KEY.encode(), json.dumps(parameters, ensure_ascii=False).encode('utf-8'),
                         digestmod=hashlib.sha1).digest()
    signature_base64 = base64.b64encode(signature).decode()
    headers = {
        'TCB-Header-Login': config.LOGIN,
        'TCB-Header-Sign': signature_base64,
        "Content-Type": "application/json; charset=utf-8"
    }
    try:
        responseJSON = requests.get("https://paytest.online.tkbbank.ru/api/v1/card/unregistered/debit",
                                    data=json.dumps(parameters, ensure_ascii=False).encode('utf-8'),
                                    headers=headers)
        response = responseJSON.json()
        return f"Ссылка: {response['FormURL']}"
    except TimeoutError:
        return f"Ошибка: timeout error"


@bot.message_handler(commands=["pay"])
def pay(message):
    bot.send_message(message.chat.id, 'Укажите номер заявки:')
    bot.register_next_step_handler(message, first)
@bot.message_handler(commands=["start"])
def start(message):
    buttons = ["Оплатить"]
    bot.send_message(message.from_user.id,
                     f"Привет, @{message.from_user.username}!\nДанный бот предназаначен для создания ссылок оплаты\nДля его работы "
                     f"необходимо 2 параметра: \n1. <b>Номер договора</b>\n2. <b>Сумма платежа</b>. \n\n<i>Для "
                     f"получения ссылки нажмите на кнопку ниже!</i>",
                     parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons))

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
    if call.data == 'yes':
        bot.send_message(call.from_user.id,
                         f"Отлично!\n\n<i>{create_link(str(kvatance['id']), float(kvatance['price']) * 100)}</i>",
                         parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("Оплатить"))

        return
    elif call.data == 'no':
        buttons = ["Оплатить"]
        bot.send_message(call.from_user.id, "Оплата отменена!",
                         reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons))
        return
voc = "абвгдийклмнопрстуфхцчшщъыьэюяabcdefghijklmnopqrstuvwxyz"
def second(message, dogovor):
    summa = message.text
    summa = str.replace(summa, ",", ".")
    for smb in voc:
        if smb in summa.lower():
            bot.send_message(message.from_user.id, "Неверная сумма, введите ещё раз.")
            bot.register_next_step_handler_by_chat_id(message.chat.id, second, dogovor)
            return
    global kvatance
    try:
        summa = float(summa)
        btn1 = InlineKeyboardButton("Ок", callback_data="yes")
        btn2 = InlineKeyboardButton("Отмена", callback_data="no")
        summa = round(summa, 2)
        kvatance = {"id": dogovor, "price": summa}
        bot.send_message(message.from_user.id,
                         f"Квитанция: <i>{dogovor}</i>\nСумма: <i>{summa:.2f} руб.</i>\n\n<b>Все верно?</b>",
                         parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(btn1, btn2)),
    except ValueError:
        bot.send_message(message.from_user.id, "Неверный формат! Попробуйте еще раз.")
        bot.register_next_step_handler_by_chat_id(message.chat.id, second, dogovor)
def first(message):
    dogovor = message.text
    bot.send_message(message.from_user.id, f"Введите сумму платежа:")
    bot.register_next_step_handler_by_chat_id(message.chat.id, second, dogovor)


@bot.message_handler(content_types=['text'])
def message_handler(message):
    userid = message.from_user.id
    if message.text == "Оплатить":
        bot.send_message(userid, "Введите номер договора: ")
        bot.register_next_step_handler_by_chat_id(message.chat.id, first)
    else:
        bot.send_message(userid, "Простите, но я не знаю такую команду :<")


bot.infinity_polling()
