from datetime import datetime
import django
import psycopg2
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
import base64
from django.conf import settings
import DJANGO_SETTING_MODULE
import config
import hashlib
import hmac
import json
import requests
settings.configure(DJANGO_SETTING_MODULE)
django.setup()
local = json.loads(open("locale.json", "r", encoding="utf-8").read())

db_connection = psycopg2.connect(config.DB_URI, sslmode="require")
db_oject = db_connection.cursor()

bot = Bot(config.BOT_TOKEN)

dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

def getDP():
    return dp
class Form(StatesGroup):
    id = State()
    price = State()

@dp.message_handler(commands=['start'])
async def start(message):
    id = message.from_user.id
    username = message.from_user.username
    await bot.send_message(message.from_user.id, f"Hello, {username}!\nWe are checking your details...")

    db_oject.execute(f"SELECT id FROM users WHERE id = {id}")
    result = db_oject.fetchone()

    if not result:
        db_oject.execute("INSERT INTO users(id, username, usercontact) VALUES (%s, %s, %s)", (id, username, ''))
        db_connection.commit()
        await bot.send_message(id, f"You are identified.\nAll is ready.")
    else:
        await bot.send_message(id, f"Identification is not required.\nYou have already been identified.")
    buttons = ["Оплатить", "Статус"]
    await bot.send_message(message.from_user.id,
                     f"Привет, @{message.from_user.username}!\nДанный бот предназаначен для создания ссылок оплаты\nДля его работы "
                     f"необходимо 2 параметра: \n1. <b>Номер договора</b>\n2. <b>Сумма платежа</b>. \n\n<i>Для "
                     f"получения ссылки нажмите на кнопку ниже!</i>",
                     parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons))

#==== STATUS CHECK ====

async def status(user_id):
    print("get")
    db_oject.execute(f"SELECT * FROM users")
    users = db_oject.fetchall()
    for user in users:
        if user[2] != None and user[0] == user_id:
            parameters = dict(ExtID=user[2])
            signature = hmac.new(config.API_KEY.encode(), json.dumps(parameters, ensure_ascii=False).encode('utf-8'),
                                 digestmod=hashlib.sha1).digest()
            signature_base64 = base64.b64encode(signature).decode()
            headers = {
                'TCB-Header-Login': config.LOGIN,
                'TCB-Header-Sign': signature_base64,
                "Content-Type": "application/json; charset=utf-8"
            }
            responseJSON = requests.get(config.STAT_URL,
                                        data=json.dumps(parameters, ensure_ascii=False).encode('utf-8'),
                                        headers=headers)
            response = responseJSON.json()
            print(response)
            pay_status = response['OrderInfo']['StateDescription']
            if pay_status == "Успешно":
                print("DELETE")
                db_oject.execute(f"UPDATE users SET order_id = NULL WHERE id = {user_id}")
                db_connection.commit()
            await bot.send_message(user_id, f"Статус оплаты: {pay_status}")
            return
    await bot.send_message(user_id, "У вас нет активных заявок.")
#==== LINK CREATE ====
async def create_link(number, summ, desc, state):
    print("send")
    parameters = dict(ExtID=number,
                      Amount=summ,
                      Description=desc,
                      TTl="0.00:10:00",
                      OrderId=number)
    signature = hmac.new(config.API_KEY.encode(), json.dumps(parameters, ensure_ascii=False).encode('utf-8'),
                         digestmod=hashlib.sha1).digest()
    signature_base64 = base64.b64encode(signature).decode()
    headers = {
        'TCB-Header-Login': config.LOGIN,
        'TCB-Header-Sign': signature_base64,
        "Content-Type": "application/json; charset=utf-8"
    }
    try:
        responseJSON = requests.get(config.PAY_URL,
                                    data=json.dumps(parameters, ensure_ascii=False).encode('utf-8'),
                                    headers=headers)
        response = responseJSON.json()
        async with state.proxy() as data:
            print(data)
            db_oject.execute(f"UPDATE users SET order_id = {data['docnum']} WHERE id = {data['user_id']}")
            db_connection.commit()
        await state.finish()
        print(response)
        return f"Ссылка: {response['FormURL']}"
    except TimeoutError:
        return f"Ошибка: timeout error"

async def yes_callback(callback, state):
    print(callback)
    await callback.answer("Успешно!")
    async with state.proxy() as data:
        await bot.send_message(callback.from_user.id,
                               f"Отлично!\n\n<i>{await create_link(data['docnum'], float(data['price']) * 100, data['id'], state)}</i>",
                               parse_mode="HTML",
                               reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("Оплатить", "Статус"))

async def no_callnack(callback: CallbackQuery):
    await callback.answer("Успешно!")
    await bot.send_message(callback.from_user.id, "Отменено!")

#register callbacks
dp.register_callback_query_handler(yes_callback, lambda c: c.data == "yes", state=Form.price)
dp.register_callback_query_handler(no_callnack, lambda c: c.data == "no")
#==================
def docnum():
    return str(datetime.utcnow()).replace("-", "").replace(":","").replace(" ", "").replace(".", "")

@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    id = message.from_user.id
    username = message.from_user.username
    await bot.send_message(message.from_user.id, f"Hello, {username}!\nWe are checking your details...", reply_to_message_id=message.message_id)
    db_oject.execute(f"SELECT id FROM users WHERE id = {id}")
    result = db_oject.fetchone()

    if not result:
        db_oject.execute("INSERT INTO users(id, username, usercontact) VALUES (%s, %s, %s)", (id, username, ''))
        db_connection.commit()
        await bot.send_message(id, f"You are identified.\nAll is ready.")
    else:
        await bot.send_message(id, f"Identification is not required.\nYou have already been identified.")
    buttons = ["Оплатить", "Статус"]
    await bot.send_message(message.from_user.id,
                     f"Привет, @{message.from_user.username}!\nДанный бот предназаначен для создания ссылок оплаты\nДля его работы "
                     f"необходимо 2 параметра: \n1. <b>Номер договора</b>\n2. <b>Сумма платежа</b>. \n\n<i>Для "
                     f"получения ссылки нажмите на кнопку ниже!</i>",
                     parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons))

voc = "абвгдийклмнопрстуфхцчшщъыьэюяabcdefghijklmnopqrstuvwxyz"
@dp.message_handler(state=Form.price)
async def getPrice(message, state):
    summa = message.text
    summa = str.replace(summa, ",", ".")
    for smb in voc:
        if smb in summa.lower():
            await bot.send_message(message.from_user.id, "Неверная сумма, введите ещё раз.")
            await Form.price.set()
            return
    try:
        summa = float(summa)
        btn1 = InlineKeyboardButton(local['Yes'], callback_data="yes")
        btn2 = InlineKeyboardButton(local['No'], callback_data="no")
        summa = round(summa, 2)
        async with state.proxy() as data:
            data['docnum'] = docnum()
            data['user_id'] = message.from_user.id
            data['price'] = summa
            await bot.send_message(message.from_user.id,
                             f"Квитанция: <i>{data['id']}</i>\nСумма: <i>{summa:.2f} руб.</i>\n\n<b>Все верно?</b>",
                             parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(btn1, btn2))

    except ValueError:
        await Form.price.set()
        await bot.send_message(message.from_user.id, "Неверный формат! Попробуйте еще раз.")
            #bot.register_next_step_handler_by_chat_id(message.chat.id, second, dogovor)

@dp.message_handler(state=Form.id)
async def getID(message, state):
    async with state.proxy() as data:
        data['id'] = message.text
    await Form.price.set()
    await bot.send_message(message.from_user.id, local['PriceRequest'])
@dp.message_handler()
async def message_handler(message):
    if message.text.lower() == "оплатить":
        await Form.id.set()
        await bot.send_message(message.from_user.id, local['PayRequest'])
    elif message.text.lower() == "статус":
        await status(message.from_user.id)
#executor.start_polling(dp, skip_updates=True)