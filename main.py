import os
import telebot
import logging
import psycopg2
import base64
import hashlib
import hmac

from config import *
from flask import Flask, request
from datetime import datetime

from telebot import types
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json

bot = telebot.TeleBot(BOT_TOKEN)
server = Flask(__name__)
logger = telebot.logger
logger.setLevel(logging.DEBUG)

db_connection = psycopg2.connect(DB_URI, sslmode="require")
db_oject = db_connection.cursor()

# ##########################################------------------------
#= КОМАНДА "СТАРТ" =

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
        buttons = ["Оплатить", "Статус"]
        bot.send_message(id, f"You are identified.\nAll is ready.", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons))
    else:
        buttons = ["Оплатить", "Статус"]
        bot.send_message(id, f"Identification is not required.\nYou have already been identified.", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons))

# ##########################################------------------------
#= НОМЕР ДОКУМЕНТА =

@bot.message_handler(commands=["docnum"])
def docnum(message):
    doc_number = str(datetime.utcnow()).replace("-", "").replace(":","").replace(" ", "").replace(".", "")
    bot.send_message(message.from_user.id, f"Номер документа: {doc_number}")
def doc_nmbr():
    return  str(datetime.utcnow()).replace("-", "").replace(":","").replace(" ", "").replace(".", "")
# ##########################################------------------------
#= ПРВОЕРКА СТАТУСА ЗАЯВКИ =
def status(user_id, message):
    db_oject.execute(f"SELECT * FROM users")
    users = db_oject.fetchall()
    for user in users:
        if user[2] != None and user[0] == user_id:
            parameters = dict(ExtID=user[2])
            signature = hmac.new(API_KEY.encode(), json.dumps(parameters, ensure_ascii=False).encode('utf-8'),
                                 digestmod=hashlib.sha1).digest()
            signature_base64 = base64.b64encode(signature).decode()
            headers = {
                'TCB-Header-Login': LOGIN,
                'TCB-Header-Sign': signature_base64,
                "Content-Type": "application/json; charset=utf-8"
            }
            responseJSON = requests.get("https://paytest.online.tkbbank.ru/api/v1/order/state",
                                        data=json.dumps(parameters, ensure_ascii=False).encode('utf-8'),
                                        headers=headers)
            response = responseJSON.json()
            pay_status = response['OrderInfo']['StateDescription']
            if pay_status == "Успешно":
                print("DELETE")
                db_oject.execute(f"UPDATE users SET order_id = NULL WHERE id = {user_id}")
                db_connection.commit()
            bot.send_message(user_id, f"Статус оплаты: {pay_status}")
            return
    bot.send_message(user_id, "У вас нет активных заявок.")

#= ЗАЯВКА В ПЛАТЁЖНЫЙ ШЛЮЗ =
def create_link(number, summ, desc):
    parameters = dict(ExtID=number,
                      Amount=summ,
                      Description=desc,
                      TTl="4.00:00:00",
                      OrderId=number)
    signature = hmac.new(API_KEY.encode(), json.dumps(parameters, ensure_ascii=False).encode('utf-8'),
                         digestmod=hashlib.sha1).digest()
    signature_base64 = base64.b64encode(signature).decode()
    headers = {
        'TCB-Header-Login': LOGIN,
        'TCB-Header-Sign': signature_base64,
        "Content-Type": "application/json; charset=utf-8"
    }
    try:
        responseJSON = requests.get(PAY_URL,
                                    data=json.dumps(parameters, ensure_ascii=False).encode('utf-8'),
                                    headers=headers)
        response = responseJSON.json()
        print(kvatance)
        print(response)
        db_oject.execute(f"UPDATE users SET order_id = {kvatance['docnum']} WHERE id = {kvatance['user_id']}")
        db_connection.commit()
        return f"Ссылка: {response['FormURL']}"
    except TimeoutError:
        return f"Ошибка: timeout error"


@bot.message_handler(commands=["pay"])
def pay(message):
    bot.send_message(message.chat.id, 'Введите номер платежа:')
    bot.register_next_step_handler(message, first)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
    if call.data == 'yes':
        bot.send_message(call.from_user.id,
                         f"Отлично!\n\n<i>{create_link(kvatance['docnum'], float(kvatance['price']) * 100, kvatance['id'])}</i>",
                         parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("Оплатить", "Статус"))

        return
    elif call.data == 'no':
        buttons = ["Оплатить", "Статус"]
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
        kvatance = {"id": dogovor, "price": summa, 'user_id': message.from_user.id, "docnum": doc_nmbr()}
        bot.send_message(message.from_user.id,
                         f"Квитанция: <i>{dogovor}</i>\nСумма: <i>{summa:.2f} руб.</i>\n\n<b>Все верно?</b>",
                         parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(btn1, btn2)),
    except ValueError:
        bot.send_message(message.from_user.id, "Неверный формат! Попробуйте еще раз.")
        bot.register_next_step_handler_by_chat_id(message.chat.id, second, dogovor)

def first(message):
    dogovor = message.text
    bot.send_message(message.from_user.id, "Отлично, теперь введите сумму платежа:")
    bot.register_next_step_handler_by_chat_id(message.chat.id, second, dogovor)
def check(user_id: int):
    db_oject.execute(f"SELECT {user_id} FROM users")
    print(db_oject.fetchone(), user_id)
    return lambda x: user_id in db_oject.fetchone()
@bot.message_handler(content_types=['text'])
def message_handler(message):
    userid = message.from_user.id
    if message.text == "Оплатить":
        bot.send_message(userid, "Введите номер платежа: ")
        bot.register_next_step_handler_by_chat_id(message.chat.id, first)
    elif message.text == "Статус":
        status(userid, message)
    else:
        bot.send_message(userid, "Простите, но я не знаю такую команду :<")

# ##########################################------------------------
# ##########################################------------------------
#= ОКНО ДЛЯ КОДА =







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
