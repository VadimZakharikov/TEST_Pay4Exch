import os
import telebot
import logging
import psycopg2
import base64
import hashlib
import hmac

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
    bot.reply_to(message, f"Hello, {username}!\nWe are checking your details...")

    db_oject.execute(f"SELECT id FROM users WHERE id = {id}")
    result = db_oject.fetchone()

    if not result:
        db_oject.execute("INSERT INTO users(id, username, status, comment) VALUES (%s, %s, %s, %s)", (id, username, False, ''))
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
    db_oject.execute(f"SELECT * FROM \"order\"")
    users = db_oject.fetchall()
    has_active_orders = False
    for user in users:
        print(user)
        if user[0] != None and user[1] == user_id:
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
            update_query = sql.SQL("UPDATE \"order\" SET order_status = %s WHERE id = %s")
            db_oject.execute(update_query, (pay_status, user_id))
            db_connection.commit()
            print(response)
            has_active_orders = True
            if pay_status == "Успешно" or "Время оплаты заявки истекло" in pay_status:
                print("DELETE")
                db_oject.execute(f"delete from \"order\" WHERE order_id = {user[0]}")
                db_connection.commit()
            bot.send_message(user_id, f"Статус оплаты по заявке {user[4]} на сумму {response['OrderInfo']['Amount'] / 100:.2f} RUB: {pay_status}")
    if not has_active_orders:
        bot.send_message(user_id, "У вас нет активных заявок.")
    #bot.send_message(user_id, "У вас нет активных заявок.")

#= ЗАЯВКА В ПЛАТЁЖНЫЙ ШЛЮЗ =
def create_link(number, summ, desc):
    parameters = dict(ExtID=number,
                      Amount=summ,
                      Description=desc,
                      TTl=LIFE_TIME,
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
        db_oject.execute(
            "INSERT INTO \"order\" (order_id, id, comment, order_status, order_name) VALUES (%s, %s, %s, %s, %s)",
            (kvatance['docnum'], kvatance['user_id'], "test", "проверка", kvatance['id'])
        )
        return f"Ссылка для оплаты картой онлайн: {response['FormURL']}"
    except TimeoutError:
        return f"Ошибка: timeout error"


@bot.message_handler(commands=["pay"])
def pay(message):
    if check(message.from_user.id):
        bot.send_message(message.chat.id, 'Введите номер заявки:')
        bot.register_next_step_handler(message, first)
    else:
        bot.send_message(message.from_user.id, "Доступ ограничен! /start!")
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
    print(result[0])
    return result[0][0]
@bot.message_handler(content_types=['text'])
def message_handler(message):
    userid = message.from_user.id
    print(message)
    print(f"user: {userid}")
    if message.text == "Оплатить":
        print(f"user: {userid}")
        if check(userid):
            bot.send_message(userid, "Введите номер платежа: ")
            bot.register_next_step_handler_by_chat_id(message.chat.id, first)
        else:
            bot.send_message(userid, "Доступ ограничен! /start!")
    elif message.text == "Статус":
        if check(userid):
            status(userid, message)
        else:
            bot.send_message(userid, "Доступ ограничен! /start!")
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
