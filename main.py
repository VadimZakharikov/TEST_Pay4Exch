import time
import telebot
import logging
import psycopg2
import base64
import hashlib
import hmac
import os
from psycopg2 import sql

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
    #bot.reply_to(message, f"Здравствуйте, {username}!\nМы проверяем Ваши данные...", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons))

    db_oject.execute(f"SELECT status, id FROM users WHERE id = {id}")
    result = db_oject.fetchone()
    if result == None:
        db_oject.execute("INSERT INTO users(id, username, status, comment) VALUES (%s, %s, %s, %s)",
                         (id, username, None, ''))
        db_connection.commit()
    db_oject.execute(f"SELECT status, id FROM users WHERE id = {id}")
    result = db_oject.fetchone()
    buttons = ["Оплатить", "Статус"]
    print(result)
    if result[0] == None:
        print("v")
        bot.send_message(id, f"Здравствуйте, {username}. Мы все еще проверяем Ваши данные...",
                         reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons))
    elif result[0] == False:
        print("f")
        bot.send_message(id, "Доступ запрещен. Обратитесь к администратору.")
        return
    if result[0] == True:
        print("t")
        bot.send_message(id, "Данные проверены. Доступ разрешен.",
                         reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons))
        return
    #else:
        #db_oject.execute("INSERT INTO users(id, username, status, comment) VALUES (%s, %s, %s, %s)",
                        #(id, username, None, ''))
        #db_connection.commit()
        #bot.send_message(id, f"Здравствуйте, {username}. Мы все еще проверяем Ваши данные", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons))

# ##########################################------------------------
#= НОМЕР ДОКУМЕНТА =

@bot.message_handler(commands=["docnum"])
def docnum(message):
    doc_number = str(datetime.utcnow()).replace("-", "").replace(":","").replace(" ", "").replace(".", "")
    bot.send_message(message.from_user.id, f"Номер документа: {doc_number}")
def doc_nmbr():
    return  str(datetime.utcnow()).replace("-", "").replace(":","").replace(" ", "").replace(".", "")
# ##########################################------------------------
#


#= ПРВОЕРКА СТАТУСА ЗАЯВКИ =
def status(user_id):
    db_oject.execute(f"SELECT * FROM \"orders\"")
    users = db_oject.fetchall()
    has_active_orders = False
    for user in users:
        print(user)
        if user[0] != None and user[1] == user_id and user[3] != None:
            parameters = dict(ExtID=user[0])
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
            update_query = sql.SQL("UPDATE \"orders\" SET order_status = %s WHERE order_id = %s")
            db_oject.execute(update_query, (pay_status, user[0]))
            db_connection.commit()
            print(response)
            has_active_orders = True
            if pay_status == "Успешно" or "Время оплаты заявки истекло" in pay_status:
                print("DELETE")
                db_oject.execute(f"update \"orders\" set order_status = %s WHERE order_id = %s", (None, user[0]))
                db_connection.commit()
            else:
                print("do")
            bot.send_message(user_id,
                             f"Заявка {user[4]} на сумму {response['OrderInfo']['Amount'] / 100:.2f} RUB: {pay_status}\n{user[5]}")
    if not has_active_orders:
        bot.send_message(user_id, "У вас нет активных заявок.")
    #bot.send_message(user_id, "У вас нет активных заявок.")

#= ЗАЯВКА В ПЛАТЁЖНЫЙ ШЛЮЗ =
def create_link(number, summ, desc):
    parameters = dict(ExtID=number,
                      Amount=summ,
                      Description=desc,
                      TTl="0.00:01:00",
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
        responseJSON = requests.get(f"{PAY_URL}api/v1/card/unregistered/debit",
                                    data=json.dumps(parameters, ensure_ascii=False).encode('utf-8'),
                                    headers=headers)
        response = responseJSON.json()
        print(response)
        db_oject.execute(
            "INSERT INTO \"orders\" (order_id, id, comment, order_status, order_description, order_URL) VALUES (%s, %s, %s, %s, %s, %s)",
            (kvatance['docnum'], kvatance['user_id'], "test", "проверка", kvatance['id'], response['FormURL'])
        )
        db_connection.commit()
        return f"Ссылка для оплаты картой онлайн: {response['FormURL']}"
    except TimeoutError:
        return f"Ошибка: timeout error"


@bot.message_handler(commands=["pay"])
def pay(message):
    stat, mes = check(message.from_user.id, message.from_user.username)
    if check(message.from_user.id):
        bot.send_message(message.chat.id, f'Введите номер заявки:')
        bot.register_next_step_handler(message, first)
    else:
        bot.send_message(message.from_user.id, "Сервис не доступен.")
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
    if call.data == 'yes':
        bot.answer_callback_query(call.id, text="Генерируем ссылку...")
        bot.send_message(call.from_user.id,
                         f"<i>{create_link(kvatance['docnum'], float(kvatance['price']) * 100, kvatance['id'])}</i>",
                         parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("Оплатить", "Статус"))

        return
    elif call.data == 'no':
        bot.answer_callback_query(call.id, text="Отменено!")
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
                         f"Заявка: <i>{dogovor}</i>\nСумма: <i>{summa:.2f} руб.</i>\n\n<b>Верно?</b>",
                         parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(btn1, btn2)),
    except ValueError:
        bot.send_message(message.from_user.id, "Ошибка в сумме, попробуйте еще раз:")
        bot.register_next_step_handler_by_chat_id(message.chat.id, second, dogovor)
def first(message):
    dogovor = message.text
    bot.send_message(message.from_user.id, "Введите сумму платежа:")
    bot.register_next_step_handler_by_chat_id(message.chat.id, second, dogovor)
def check(user_id: int):
    print(f"check {user_id}")
    db_oject.execute(f"SELECT status FROM users where id = {user_id}")
    result = db_oject.fetchall()
    print(result[0][0])
    if result[0][0] == False:
        return False
    elif result[0][0] == None:
        return False
    else:
        return True
    return result[0][0]
@bot.message_handler(content_types=['text'])
def message_handler(message):
    userid = message.from_user.id
    print(message)
    print(f"user: {userid}")
    if message.text == "Оплатить":
        print(f"user: {userid}")
        if check(message.from_user.id):
            bot.send_message(message.chat.id, f'Введите номер заявки:')
            bot.register_next_step_handler(message, first)
        else:
            bot.send_message(message.from_user.id, "Сервис не доступен.")
    elif message.text == "Статус":
        if check(message.from_user.id):
           status(message.from_user.id)
        else:
            bot.send_message(message.from_user.id, "Сервис не доступен.")
    else:
        bot.send_message(userid, "Нет такой команды, введите команду:")

# ##########################################------------------------
# ##########################################------------------------
#= ОКНО ДЛЯ КОДА =









# ##########################################------------------------
# ##########################################------------------------

@server.route(f"/{BOT_TOKEN}", methods=["POST"])
def redirect_message():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200


if __name__ == "__main__":
    print('start!')
    bot.remove_webhook()
    bot.set_webhook(url=APP_URL)
    #bot.infinity_polling()
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
