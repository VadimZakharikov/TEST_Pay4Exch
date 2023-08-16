import asyncio
from datetime import datetime

import asyncpg
import django
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.dispatcher import FSMContext
import base64

from aiogram.utils import executor
from django.conf import settings
import DJANGO_SETTING_MODULE
import config
import hashlib
import hmac
import json
import requests
import nest_asyncio
nest_asyncio.apply()
settings.configure(DJANGO_SETTING_MODULE)
django.setup()
local = json.loads(open("locale.json", "r", encoding="utf-8").read())

connection = None
async def conn():
    print("connect to db...")
    global connection
    connection = await asyncpg.connect(dsn=config.DB_URI)

bot = Bot(config.BOT_TOKEN)

dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())


def getDP():
    return dp

#Форма(хранит все данные юзера, отдельно для каждого)
class Form(StatesGroup):
    id = State()
    price = State()

#Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start(message):
    id = message.from_user.id
    username = message.from_user.username
    buttons = [local["PayButton"], local["StatusButton"]]
    try:
        result = loop.run_until_complete(connection.fetchrow(f"SELECT status, id FROM users WHERE id = {id}"))
        if result is None:
            await connection.execute("INSERT INTO users(id, username, status, comment) VALUES ($1, $2, $3, $4)",
                               id, username, None, '')

        result = loop.run_until_complete(connection.fetchrow(f"SELECT status, id FROM users WHERE id = {id}"))
        if result['status'] is None:
            await bot.send_message(id, f"Здравствуйте, {username}. {local['Check']}",
                                   reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons))
        elif result['status'] is False:
            await bot.send_message(id, local["NotAllow"])
            return
        elif result['status'] is True:
            await bot.send_message(id, local["Allow"],
                                   reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(*buttons))
            return
    except Exception as err:
        print(f"Status err: {err}")
# ==== STATUS CHECK ====
async def send_order_notification(user, response, pay_status):
    try:
        await bot.send_message(user['id'], f"Заявка {user['order_description']} на сумму {response['OrderInfo']['Amount'] / 100:.2f} RUB: {pay_status}\n{user['order_url']}")
    except Exception as err:
        print(err)
async def status(user_id):
    has_active_orders = False
    try:
        results = loop.run_until_complete(connection.fetch(f"SELECT * FROM \"orders\" where id = {user_id}"))
    except Exception as err:
        print(err)
    users = []
    for result in results:
        users.append(dict(result.items()))
    for user in users:
        if user['order_id'] != "" and user['id'] == user_id:
            parameters = dict(ExtID=user['order_id'])
            signature = hmac.new(config.API_KEY.encode(), json.dumps(parameters, ensure_ascii=False).encode('utf-8'),
                                 digestmod=hashlib.sha1).digest()
            signature_base64 = base64.b64encode(signature).decode()
            headers = {
                'TCB-Header-Login': config.LOGIN,
                'TCB-Header-Sign': signature_base64,
                "Content-Type": "application/json; charset=utf-8"
            }
            try:
                responseJSON = requests.get(f"{config.PAY_URL}api/v1/order/state",
                                            data=json.dumps(parameters, ensure_ascii=False).encode('utf-8'),
                                            headers=headers)
            except Exception as err:
                print(err)
            response_json = responseJSON.json()
            pay_status = response_json['OrderInfo']['StateDescription']
            has_active_orders = True
            await send_order_notification(user, response_json, pay_status)
            if pay_status == "Успешно" or "Время оплаты заявки истекло" in pay_status:
                loop.run_until_complete(connection.execute(f"update \"orders\" set order_id = {None} where id = {user_id} "))
    if not has_active_orders:
        await bot.send_message(user_id, local["NoOrders"])


# ==== LINK CREATE ====
async def create_link(number, summ, desc, state, userid):
    await state.finish()
    parameters = dict(ExtID=number,
                      Amount=summ,
                      Description=desc,
                      TTl=config.LIFE_TIME,
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
        responseJSON = requests.get(f"{config.PAY_URL}api/v1/card/unregistered/debit",
                                    data=json.dumps(parameters, ensure_ascii=False).encode('utf-8'),
                                    headers=headers)
        response_json = responseJSON.json()
        async with connection.transaction():
            try:
                await connection.execute(
                    "INSERT INTO \"orders\" (order_id, id, comment, order_status, order_description, order_URL) VALUES ($1, $2, $3, $4, $5, $6)",
                    number, userid, 'test', 'проверка', desc, response_json['FormURL']
                )
            except Exception as err:
                print(err)
        await state.finish()
        return f"{local['LinkURL']}{response_json['FormURL']}"
    except TimeoutError:
        return f"Ошибка: timeout error"


# ==================================================================================
async def yes_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer(local['CallTrue'])
    async with state.proxy() as data:
        link = loop.run_until_complete(create_link(data['docnum'], float(data['price']) * 100, data['id'], state, data['user_id']))
        await bot.send_message(callback.from_user.id,
                           f"Отлично!\n\n<i>{link}</i>",
                           parse_mode="HTML",
                           reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add("Оплатить", "Статус"))
    await state.finish()
    print("asd")
    return

async def no_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer(local['CallTrue'])
    await bot.send_message(callback.from_user.id, local['Cancel'])
    await state.reset_state()


# register callbacks
dp.register_callback_query_handler(yes_callback, lambda c: c.data == "yes", state=Form.price)
dp.register_callback_query_handler(no_callback, lambda c: c.data == "no", state=Form.price)


# ==================
def docnum():
    return str(datetime.utcnow()).replace("-", "").replace(":", "").replace(" ", "").replace(".", "")
#Проверка статуса человека и возврат значения True/False в зависимости от статуса в БД. При True - доступ рарешен, при False - нет.
async def check(userid):
    res = loop.run_until_complete(connection.fetchrow(f"select status from users where id = {userid}"))
    if res['status'] == False:
        return False
    elif res['status'] == None:
        return False
    else:
        return True

#Получение order_id
@dp.message_handler(state=Form.id)
async def getID(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['id'] = message.text
    await Form.next()
    await message.reply(local['GetOrderPrice'])


voc = "абвгдийклмнопрстуфхцчшщъыьэюяabcdefghijklmnopqrstuvwxyz"

#получение стоимости заявки
@dp.message_handler(state=Form.price)
async def getPrice(message, state):
    summa = message.text
    summa = str.replace(summa, ",", ".")
    for smb in voc:
        if smb in summa.lower():
            await bot.send_message(message.from_user.id, local['Summa'])
            await Form.price.set()
            return
    try:
        summa = float(summa)
        btn1 = InlineKeyboardButton(local['Yes'], callback_data="yes")
        btn2 = InlineKeyboardButton(local['No'], callback_data="no")
        summa = round(summa, 2)
        if summa <= 0:
            await bot.send_message(message.from_user.id, local['Null'])
            await Form.price.set()
            return
        async with state.proxy() as data:
            data['docnum'] = docnum()
            data['user_id'] = message.from_user.id
            data['price'] = summa
            await bot.send_message(message.from_user.id,
                                   f"Квитанция: <i>{data['id']}</i>\nСумма: <i>{summa:.2f} руб.</i>\n\n<b>Все верно?</b>",
                                   parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(btn1, btn2))
    except ValueError:
        await Form.price.set()
        await bot.send_message(message.from_user.id, local["Format"])

#Обработчик текст. сообщений
@dp.message_handler()
async def message_handler(message):
    if message.text.lower() == "оплатить":
        if loop.run_until_complete(check(message.from_user.id)):
            await Form.id.set()
            await bot.send_message(message.from_user.id, local['PayRequest'])
        else:
            await bot.send_message(message.from_user.id, local['NotAllowed'])
    elif message.text.lower() == "статус":
        if loop.run_until_complete(check(message.from_user.id)):
            await bot.send_message(message.from_user.id, local["StatusCheck"])
            await status(message.from_user.id)
        else:
            await bot.send_message(message.from_user.id, local['NotAllowed'])


loop = asyncio.new_event_loop()
result = loop.run_until_complete(conn())
#executor.start_polling(dp, loop=loop, skip_updates=True)
