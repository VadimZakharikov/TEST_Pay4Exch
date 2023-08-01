import os
import telebot
import logging
import psycopg2

from config import *
from flask import Flask, request
from datetime import datetime

from telebot import types
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
@bot.message_handler(commands=["pay"])
def pay(message):
    bot.send_message(message.chat.id, 'Укажите номер заявки:')
    bot.register_next_step_handler(message, get_number)

def get_number(message):
    number = message.text
    bot.send_message(message.chat.id, 'Укажите сумму:')
    bot.register_next_step_handler(message, get_summ, number)

def get_summ(message, number):
    try:
        summ = float(message.text)
        amount = int(summ * 100)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(text='Да', callback_data='Да'),
            types.InlineKeyboardButton(text='Нет', callback_data='Нет')
        )
        bot.send_message(message.chat.id, f'Подтверждаете платеж на сумму {summ} руб.?', reply_markup=keyboard)
        bot.register_next_step_handler(message, confirm_payment, number, amount)
    except ValueError:
        bot.send_message(message.chat.id, 'Неверный формат суммы. Попробуйте еще раз.')
        bot.register_next_step_handler(message, get_number)

def confirm_payment(message, number, amount):
    if message.text == 'Да':
        bot.send_message(message.chat.id, 'Отлично!\\nСсылка на оплату:')
         url = f'<https://paytest.online.tkbbank.ru/payment/{number}?amount={amount}&summ={summ}>'
    else:
        bot.send_message(message.chat.id, 'Оплата отменена.')

























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
