import base64
import hashlib

import requests
import telebot
from telebot.types import ReplyKeyboardMarkup
import config
bot = telebot.TeleBot(config.BOT_TOKEN)

def create_link(number, summ):

    parameters = dict(ExtID=number, Amount=summ, Description="test from bot", ReturnURL="http:site.ru_result",
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
    headers = {
        'TCB-Header-Login': "PAT100002257ID",
        'TCB-Header-Sign': "M2VlYjkxNzk1MDBjODdlNzA1NmUwMDRkNjM4YTc3MmYwZDRlNzM3Yw=="
    }
    responseJSON = requests.post("https://paytest.online.tkbbank.ru/api/v1/card/registered/debi", params=parameters,
                                headers=headers)
    response = responseJSON.json()
    #hello
    par = {"InputString": "Тест"}
    res = requests.post("https://paytest.online.tkbbank.ru/api/tcbpay/gate/hello", params=par, headers=headers)
    print(res.text)
    #----------------------------------------------------------------------------------------------------------
    if response['ExceptionType'] == "Error":
        return f"Произошла ошибка! Код ошибки: <b>{response['Code']}</b>"
    else:
        return f"Ссылка: {response['URL']}"


def end(message, kvatance):
    if message.text == "Да":
        buttons = ["Оплатить"]
        #bot.send_message(message.from_user.id,
        #                 f"Отлично! Ссылка: \nhttps://my-super-payment-gateway.com/pay?number={kvatance['id']}&amount={kvatance['price']}", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons))
        bot.send_message(message.from_user.id,
                          f"Отлично!\n\n<i>{create_link(int(kvatance['id']), int(kvatance['price'] * 100))}</i>",
                          parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons))
    else:
        buttons = ["Оплатить"]
        bot.send_message(message.from_user.id, "Оплата отменена!",
                         reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons))
        return


def second(message, dogovor):
    summa = message.text
    try:
        summa = float(summa)
        buttons = ["Да", "Нет"]
        kvatance = {"id": dogovor, "price": summa}
        bot.send_message(message.from_user.id,
                         f"Квитанция: <i>{dogovor}</i>\nСумма: <i>{summa} руб.</i>\n\n<b>Все верно?</b>",
                         parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons)),
        bot.register_next_step_handler_by_chat_id(message.chat.id, end, kvatance)
    except ValueError:
        bot.send_message(message.from_user.id, "Неверный формат! Попробуйте еще раз.")
        bot.register_next_step_handler_by_chat_id(message.chat.id, second, dogovor)


def first(message):
    dogovor = message.text
    bot.send_message(message.from_user.id, f"Отлично, номер договора: {dogovor}\n\nТеперь введите сумму:")
    bot.register_next_step_handler_by_chat_id(message.chat.id, second, dogovor)
   
@bot.message_handler(commands=["pay"])
def pay(message):
    bot.send_message(message.chat.id, 'Укажите номер заявки:')
    bot.register_next_step_handler(message, first)

@bot.message_handler(content_types=['text'])
def message_handler(message):
    print(message.from_user.username + " " + message.text)
    userid = message.from_user.id
    user = message.from_user.username
    if message.text == "/start":
        buttons = ["Оплатить"]
        bot.send_message(userid,
                         f"Привет, @{user}!\nДанный бот предназаначен для создания ссылок оплаты\nДля его работы "
                         f"необходимо 2 параметра: \n1. <b>Номер договора</b>\n2. <b>Сумма платежа</b>. \n\n<i>Для "
                         f"получения ссылки нажмите на кнопку ниже!</i>",
                         parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons))
    elif message.text == "Оплатить":
        bot.send_message(userid, "Введите номер договора: ")
        bot.register_next_step_handler_by_chat_id(message.chat.id, first)
    else:
        bot.send_message(userid, "Простите, но я не знаю такую команду :<")

bot.infinity_polling()
