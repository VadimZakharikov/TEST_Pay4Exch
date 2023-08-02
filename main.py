import os
import telebot
import logging
import psycopg2

from config import *
from flask import Flask, request
from datetime import datetime

from telebot import types
from telebot.types import ReplyKeyboardMarkup
import requests
import json

bot = telebot.TeleBot(BOT_TOKEN)
server = Flask(__name__)
logger = telebot.logger
logger.setLevel(logging.DEBUG)

db_connection = psycopg2.connect(DB_URI, sslmode="require")
db_oject = db_connection.cursor()

@bot.message_handler(commands=["start"])
def start(message):
    id = message.from_user.id
    username = message.from_user.username
    bot.reply_to(message, f"Hello, {username}!\nWe are checking your details...")

    db_oject.execute(f"SELECT id FROM users WHERE id = {id}")
    result = db_oject.fetchone()

    if not result:
        db_oject.execute("INSERT INTO users(id, username, usercontact) VALUES (%s, %s, %s)", (id, username, ''))
        db_connection.commit()
        bot.send_message(id, f"You are identified.\nAll is ready.")
    else:
        bot.send_message(id, f"Identification is not required.\nYou have already been identified.")

# ##########################################------------------------

@bot.message_handler(commands=["docnum"])
def docnum(message):

    doc_id = datetime.utcnow()
    bot.reply_to(message, ("Номер документа: " + str(doc_id)))

# ##########################################------------------------

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
    responseJSON = requests.post("https://pay.tkbbank.ru/testgate/api/tcbpay/gate/registerorderfromcardtocard", params=parameters,
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
                          f"Отлично!\n\n<i>{create_link(kvatance['id'], int(kvatance['price'] * 100))}</i>",
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


@bot.message_handler(content_types=['text'])
def message_handler(message):
    print(message.from_user.username + " " + message.text)
    userid = message.from_user.id
    user = message.from_user.username
    if message.text == "/start":
        buttons = ["Оплатить", "Номер документа"]
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


#@bot.message_handler(commands=["pay"])
#def pay(message):
#    bot.send_message(message.chat.id, 'Укажите номер заявки:')
#    bot.register_next_step_handler(message, get_number)
#
#def get_number(message):
#    number = message.text
#    bot.send_message(message.chat.id, 'Укажите сумму:')
#    bot.register_next_step_handler(message, get_summ, number)
#
#def get_summ(message, number):
#    try:
#        summ = float(message.text)
#        amount = int(summ * 100)
#        keyboard = types.InlineKeyboardMarkup()
#        keyboard.add(
#            types.InlineKeyboardButton(text='Да', callback_data='Да'),
#            types.InlineKeyboardButton(text='Нет', callback_data='Нет')
#        )
#        bot.send_message(message.chat.id, f'Подтверждаете платеж на сумму {summ} руб.?', reply_markup=keyboard)
#        bot.register_next_step_handler(message, confirm_payment, number, amount)
#    except ValueError:
#        bot.send_message(message.chat.id, 'Неверный формат суммы. Попробуйте еще раз.')
#       bot.register_next_step_handler(message, get_number)
#
#def confirm_payment(message, number, amount):
#    if message.text == 'Да':
#        bot.send_message(message.chat.id, 'Отлично!\\nСсылка на оплату:')
#        bot.send_message(message.chat.id, f'<https://my-super-payment-gateway.com/pay?number={number}&amount={amount}>')
#    else:
#        bot.send_message(message.chat.id, 'Оплата отменена.')









# # @bot.message_handler(commands=["pay"]) # Формирование онлайн оплаты
# def pay(message):
# #    doc_id = datetime.utcnow()
# #    id = message.from_user.id
#    # bot.register_next_step_handler(bot.send_message(message.chat.id, 'Укажите номер заявкиTest2:'), NUMBER = message.text)
#    # @bot.message_handler(content_types='text')
    
#        # if message.text:
#     bot.send_message(message.chat.id,"Укажите номер заявкиTest2:")
#     @bot.message_handler(content_types='text')
#     def message_reply(message):
#         if message.text:
#             bot.send_message(message.chat.id,"WORK")
#             NUMBER = str(message.text)
#             bot.send_message(message.chat.id, NUMBER)
#            # @bot.message_handler(content_types='text')
#             bot.send_message(message.chat.id, 'Укажите сумму для оплаты заявки ' + NUMBER)
#             bot.register_next_step_handler(message, sum)
#     def sum(message):
#         if message.text:
#             SUMM = str(message.text)
#             bot.send_message(message.chat.id, SUMM)
#             bot.send_message(message.chat.id, 'Сформировать ссылку для онлайн оплаты заявки' + NUMBER + 'на сумму' + SUMM)
#            # bot.register_next_step_handler(message, button)
#    # @bot.message_handler(commands=['button'])

#     def button(message):
#         #@bot.message_handler(commands=['button'])
#         keyboard = types.InlineKeyboardMarkup()
#         keyboard.add(
#             types.InlineKeyboardButton(text='Да', callback_data='Да'),
#             types.InlineKeyboardButton(text='Нет', callback_data='Нет')
#             )
#         bot.send_Message(message.chat.id, 'Сформировать ссылку для онлайн оплаты заявки' + NUMBER + 'на сумму' + SUMM)
#         #@bot.message_handler(commands=['button'])
       
#         bot.register_next_step_handler(
#             bot.send_Message(message.chat.id, 'Сформировать ссылку для онлайн оплаты заявки' + NUMBER + 'на сумму' + SUMM, reply_markup=keyboard)
#             )
#         if message.text == 'Да':
# #        Генерируем ссылку TKB-Pay
#             #response = create_link(str(NUMBER), str(SUMM));
#             bot.send_message(message.chat.id, f"Ссылка для оплаты картой:\n" + response[FormUrl])
#         elif message.text == 'Нет':
#             bot.send_message(message.chat.id, 'Отмена.')
#         else:
#             bot.send_message(message.chat.id, 'Необходимо выбрать.')

# # ##########################################-

# def create_link(number, summ):
#     parameters = {
#         "ExtID":number,
#         "Amount":summ,
#  #   "Description":"test from bot",
# #  //"ReturnURL":"http://site.ru_result",
# #  //"ClientInfo": {
# #    //             "Email":"test@test.com",
# #      //           "PhoneNumber": "+7 (911) 123-00-00"
# #        //        },
# #  //"TTL":"4.00:00:00",
# #  //"CartPositions":[{
# #    //               "Quantity":1.0,
# #      //             "Price":300000,
# #        //           "Tax":60,
# #          //         "Text":"Оплата по договору 123_test Иванова И.И.",
# #           //        "PaymentMethodType":4,
# #            //       "PaymentSubjectType":4
# #              //     }],
# # // "AdditionalParameters":{
# #   //                      "DogovorID":"12345_test"
# #     //                    }

        
#     }
#     headers = {'Authorization': 'k6WRcPWcVCpuLPDJoJ7hYLDtsqZF6nMnD8UxKcqNCVyfkNJ1AYdbk35KCDyWZreJZc0L4g7mtvPcmxhPQ7eijKcJdj3gOCXkQZpiV66uZ1SZp2yevTf0n5zq8sHUm0GZGDvvh82SaTsr1nujVYV3w57UA8iDznh7u2sUGc5vZw0COhxW6x7wfNCLEL3iZztXMt583JMS2zeaeFfsMvFboU2RzQp5hXEzddZvmy1yUqDQHCF8FLFE3rK1zoJotQLe'}
#     responseJSON = requests.get("https://paytest.online.tkbbank.ru/api/v1/card/unregistered/debit", params = parameters, headers = headers)
#     response = json.load(responseJSON)
    

#     return response
    
# # Ждём номер заявки и записываем в number
# # Ждём сумму заявки и записываем в summ
# # Кнопки подтверждения и отмемы
# # При отмене повтор, при подтверждении генерим ссылку

#     #bot.send_message(message.chat.id,"text")
      
    
#    # bot.register_next_step_handler(bot.send_message(message.chat.id, 'Укажите номер заявкиTest:'), NUMBER = message.text)
#   #  msg = bot.reply_to(message, 'Укажите номер заявкиTest:')
#    # bot.register_next_step_handler(msg, NUMBER = message.text)
    
#  #   bot.send_message(message.chat.id, "test")
#     #bot.send_message(message.chat.id, NUMBER)
#    # bot.register_next_step_handler(bot.send_message(message.chat.id, 'Укажите сумму для оплаты заявки: {NUMBER}'),  SUMM = message.text)
# #    bot.send_message(id, f"Ссылка для оплаты картой:\nHttps://www.google.com")





# # /api/v1/card/unregistered/debit

# # {
# #  "ExtID":number,
# #  "Amount":summ,
# #  "Description":"test from bot",
# #  //"ReturnURL":"http://site.ru_result",
# #  //"ClientInfo": {
# #    //             "Email":"test@test.com",
# #      //           "PhoneNumber": "+7 (911) 123-00-00"
# #        //        },
# #  //"TTL":"4.00:00:00",
# #  //"CartPositions":[{
# #    //               "Quantity":1.0,
# #      //             "Price":300000,
# #        //           "Tax":60,
# #          //         "Text":"Оплата по договору 123_test Иванова И.И.",
# #           //        "PaymentMethodType":4,
# #            //       "PaymentSubjectType":4
# #              //     }],
# # // "AdditionalParameters":{
# #   //                      "DogovorID":"12345_test"
# #     //                    }
# # //}















# ##########################################------------------------

@server.route(f"/{BOT_TOKEN}", methods=["POST"])
def redirect_message():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200


if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=APP_URL)
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
