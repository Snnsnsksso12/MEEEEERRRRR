from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import asyncio
import httpx
import requests
import sqlite3
import logging
import time
from config import *
from func import *
from banker import *
from rules import *
from onesec_api import Mailbox


bot = Bot(TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot,storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

line = '➖➖➖➖➖➖➖➖➖➖➖➖'

class FIND(StatesGroup):
    GET_COUNTRY = State()
    GET_SERVICE = State()
    GET_RENT_SERVICE = State()

class GET_API(StatesGroup):
    GET_KEY = State()


class get_PAYMENTS_QIWI(StatesGroup):
    GET_SUMMA = State()
    GET_METOD = State()

class GET_NACENKA(StatesGroup):
    NAME_NACENKA = State()
    NACENKA = State()
    ALL = State()

class GET_TEXT_RASSILKA(StatesGroup):
    TEXT = State()

class GET_PHOTO_RASSILKA(StatesGroup):
    PHOTO = State()
    TEXT = State()
    START = State()

class GET_USERS_BALANCE(StatesGroup):
    US_ID = State()
    SUMMA = State()

class GET_QIWI_KEY(StatesGroup):
    KEY = State()

class CREATE_PROMOCODE(StatesGroup):
    CREATE = State()

class GET_PROMOCODE(StatesGroup):
    GET = State()

@dp.callback_query_handler(text = 'menu')
async def get_menu(call):
    await main(call.from_user.id)
#Старт
@dp.message_handler(commands="start")
async def start(message: types.Message):
    conn = sqlite3.connect('db.db', check_same_thread=False)
    cursor = conn.cursor()
    in_base = cursor.execute('SELECT * FROM users WHERE user_id = (?)', (message.from_user.id,))
    if in_base.fetchone() is None:
        conn.close() 
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Далее", callback_data="Im_agree"))
        await message.answer('Привет друг, здесь будут правила', reply_markup = keyboard)
    else:
        conn.close()
        await main(message.from_user.id)

#Правила
@dp.callback_query_handler(text="Im_agree")
async def set_pravila(call: types.CallbackQuery):
    conn = sqlite3.connect('db.db', check_same_thread=False)
    cursor = conn.cursor()
    country = '0'
    cursor.execute('INSERT INTO users (user_id, country) VALUES (?, ?)', (call.from_user.id, country ))
    cursor.execute('INSERT INTO last_zakaz (user_id, country_id, service_id, operator_id) VALUES (?, ?, ?, ?)', (call.from_user.id, 'no', 'no', 'no' ))
    conn.commit()
    conn.close()
    try:
        await bot.send_message(chat_id=LOG_DIALOG, text=f'<b>👨‍💻 У нас новый пользователь @{call.message.chat.username}!</b>')
    except:
        pass
    await bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
    await main(call.from_user.id)


@dp.message_handler(text = '🛒 Номера')
async def numbers_menu(message):
    await bot.send_photo(chat_id = message.from_user.id, photo = MENU_IMAGE, caption = '<i>Выберите страну:</i>', reply_markup = await countries_menu_keyboard(message.from_user.id, 0))

@dp.message_handler(text = '🫅 Профиль')
async def get_profile(message):
    await profile(message)

@dp.message_handler(text = 'Меню')
async def get_menu(message):
    await main(message.from_user.id)

@dp.callback_query_handler(text_startswith='next_country')
async def next_country(call):
    infolist = call.data.split('|')
    i = infolist[1]
    await bot.edit_message_reply_markup(chat_id = call.from_user.id, message_id = call.message.message_id, reply_markup = await countries_menu_keyboard(call.from_user.id, int(i)))

@dp.callback_query_handler(text_startswith='set_country')
async def set_country(call):
    infolist = call.data.split('|')
    country = infolist[1]
    await bot.edit_message_caption(chat_id = call.from_user.id, message_id=call.message.message_id, caption = f'<b>🌎 Страна:</b> {await get_name_country(country)}\n{line}\n<i>👤 Выберите оператора</i>', reply_markup = await operators_menu_keyboard(0, country))#await services_menu_keyboard(0,country))


@dp.callback_query_handler(text_startswith='set_operator')
async def set_operator(call):
    infolist = call.data.split('|')
    country = infolist[2]
    operator = infolist[1]

    conn = sqlite3.connect('db.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET operator = ? WHERE user_id = ?',[operator, call.from_user.id])
    conn.commit()
    await bot.edit_message_caption(chat_id = call.from_user.id, message_id=call.message.message_id, caption = f'<b>🌎 Страна:</b> {await get_name_country(country)}\n{line}\n<b>👤 Оператор:</b> {await get_name_operator(call.from_user.id, country)}\n{line}\n<i>🧸 Выберите услугу</i>', reply_markup = await get_params_activation(country, operator))#await services_menu_keyboard(0,country))



#\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\ АЛГОРИТМ АКТИВАЦИЙ  \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

@dp.callback_query_handler(text_startswith = 'get_activation_service')
async def get_service(call):
    infolist = call.data.split('|')
    country = infolist[1]
    await bot.edit_message_caption(chat_id = call.from_user.id, message_id=call.message.message_id, caption = f'<b>🌎 Страна:</b> {await get_name_country(country)}\n{line}\n<b>👤 Оператор:</b> {await get_name_operator(call.from_user.id, country)}\n{line}\n<b>🧸 Услуга:</b> 🛡️ Активация\n{line}\n<i>🔰 Выберите сервис</i>', reply_markup = await services_menu_keyboard(0,country, call.from_user.id))


@dp.callback_query_handler(text_startswith='next_service')
async def next_country(call):
    infolist = call.data.split('|')
    country = infolist[1]
    i = infolist[2]
    await bot.edit_message_reply_markup(chat_id = call.from_user.id, message_id = call.message.message_id, reply_markup = await services_menu_keyboard(int(i),country, call.from_user.id))

@dp.callback_query_handler(text_startswith = 'set_service')
async def set_service(call):
    infolist = call.data.split('|')
    service_id = infolist[1]
    country_id = infolist[2]
    site_api = await get_better_services(call, service_id, country_id)
    if site_api !=None:
         await bot.edit_message_caption(chat_id = call.from_user.id, message_id=call.message.message_id, caption = f'<b>🌎 Страна:</b> {await get_name_country(country_id)}\n{line}\n<b>👤 Оператор:</b> {await get_name_operator(call.from_user.id, country_id)}\n{line}\n<b>🧸 Услуга:</b> Активация\n{line}\n<b>🔰 Сервис:</b> {await get_name_service(country_id, service_id, "SERVICE")}', reply_markup = await service_info(call.from_user.id, site_api, country_id, service_id))
    else:
        await call.answer('🌟 Нет доступных номеров, подождите немного')

@dp.callback_query_handler(text_startswith = 'buy_number')
async def buy_number(call):
    #print (call.data)
    await get_number(call)

@dp.callback_query_handler(text_contains='сheckSMS')
async def checkSMS_get(call):
    await checkSMS (call)

@dp.callback_query_handler(text_contains='cancelSMS')
async def cancelSMS_get(call):
    await cancelSMS(call)

@dp.callback_query_handler(text_contains='retrySMS')
async def retrySMS_get(call):
    await retrySMS(call)

@dp.callback_query_handler(text_startswith = 'сheck_retry_SMS')
async def check_retry_SMS_get(call):
    await check_retry_SMS(call)



#\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\АЛГОРИТМ АРЕНДЫ\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

@dp.callback_query_handler(text_startswith = 'get_rent_service')
async def get_rent_service(call):
    infolist = call.data.split('|')
    country = infolist[1]
    await bot.edit_message_caption(chat_id = call.from_user.id, message_id=call.message.message_id, caption = f'<b>🌎 Страна:</b> {await get_name_country(country)}\n{line}\n<b>👤 Оператор:</b> {await get_name_operator(call.from_user.id, country)}\n{line}\n<b>🧸 Услуга:</b> 🔮 Аренда\n{line}\n<i>Выберите сервис</i>', reply_markup = await rent_services_menu_keyboard(0,country, call.from_user.id))
    

@dp.callback_query_handler(text_startswith='next_rent_service')
async def next_rent_service(call):
    infolist = call.data.split('|')
    country = infolist[1]
    i = infolist[2]
    await bot.edit_message_reply_markup(chat_id = call.from_user.id, message_id = call.message.message_id, reply_markup = await rent_services_menu_keyboard(int(i),country, call.from_user.id))

@dp.callback_query_handler(text_startswith= 'set_rent_service')
async def set_rent_service(call):
    infolist = call.data.split('|')
    service_id = infolist[1]
    country_id = infolist[2]
    await bot.edit_message_caption(chat_id = call.from_user.id, message_id=call.message.message_id, caption = f'<b>🌎 Страна:</b> {await get_name_country(country_id)}\n{line}\n<b>👤 Оператор:</b> {await get_name_operator(call.from_user.id, country_id)}\n{line}\n<b>🧸 Услуга:</b> Аренда\n{line}\n<b>🔮 Сервис:</b> {await get_name_service(country_id, service_id, "RENT")}\n{line}\n<i>Выберите срок:</i>', reply_markup = await get_rent_time_keyboard(service_id, country_id))

@dp.callback_query_handler(text_startswith='timeRent')
async def get_info_rent(call):
    infolist = call.data.split('|')
    time_rent = infolist[1]
    service_id = infolist[2]
    country_id = infolist[3]
    await rent_service_info(call, time_rent, service_id, country_id)

@dp.callback_query_handler(text_startswith='buy_rent_number')
async def buy_rent_number_get(call):
    infolist = call.data.split('|')
    service_id = infolist[1]
    country_id = infolist[2]
    time_rent = infolist[3]
    await buy_rent_number(call, service_id, country_id, time_rent)

@dp.callback_query_handler(text_startswith='check_rent_sms')
async def check_rent_sms_get(call):
    infolist = call.data.split('|')
    ids = infolist[1]
    await check_rent_sms(call, ids)

@dp.callback_query_handler(text_startswith='otmena_rent_sms')
async def otmena_rent_sms_get(call):
    infolist = call.data.split('|')
    ids = infolist[1]
    await cancel_rent_sms(call, ids)


#////////////////////////////////////////////////////ПОПОЛНЕНИЕ\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

@dp.callback_query_handler(text = 'get_money')
async def get_money(call):
    await call.message.answer('<b>💸 Выберите метод оплаты:</b>', reply_markup = await payments_keyboard())


@dp.message_handler(text_contains = 'QIWI/КАРТА')
async def QIWI_CARD_METHOD(message):
    await get_PAYMENTS_QIWI.GET_SUMMA.set()
    await message.answer('Введите сумму пополнения:')

@dp.message_handler(state=get_PAYMENTS_QIWI.GET_SUMMA)
async def get_summa_qiwi(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        await QIWI_PAY(message.text, message.from_user.id)
        await state.finish()
    else:
        await state.finish()
        await main(message.from_user.id)

@dp.callback_query_handler(text_contains='CheckQiwi_')
async def check_qiwi(call):
    conn = sqlite3.connect('db.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT QIWI_KEY FROM settings')
    QIWI_KEY = cursor.fetchone()[0]
    p2p = QiwiP2P(auth_key=QIWI_KEY)
    status = p2p.check(bill_id=call.data[10:]).status
    if status == 'PAID':
        await bot.delete_message(chat_id = call.from_user.id, message_id = call.message.message_id)
        amount = p2p.check(bill_id=call.data[10:]).amount
        cursor.execute('UPDATE users SET balance = balance + (?) WHERE user_id = (?)', (amount, call.from_user.id))
        cursor.execute('UPDATE users SET all_deposit = all_deposit + (?) WHERE user_id = (?)', (amount, call.from_user.id,))
        conn.commit()
        conn.close()
        await call.message.answer(f'<b>Начислено</b> <i>{amount}</i> <b>RUB на баланс</b>')
        await main(call.from_user.id)
        await bot.send_message(chat_id = LOG_DIALOG, text=f'''
💸 <b>Новое пополнение!</b>

<i>👨‍💻 Пользователь:
    1) Юзернейм: @{call.from_user.username}
    2) id: <code>{call.from_user.id}</code>

💰 Сумма: {amount} RUB

💳 Способ пополнения: QIWI/CARD</i>




                    ''')
    else:
        conn.close()
        await call.answer(f'⛔️ Вы не оплатили заказ, либо деньги еще доходят, подождите немного!',show_alert=False)





@dp.message_handler(text_contains = 'BTC BANKER')
async def BTC_BANKER_METHOD(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn = types.KeyboardButton(text = 'Меню')
    keyboard.add(btn)
    await message.answer('<b>🤖 Отправьте чек:</b>', reply_markup= keyboard)


@dp.message_handler(text_startswith =  'https://telegram.me/BTC_CHANGE_BOT?')
async def test(message):
    try:
        check = message.text.split('=')[1]
        await get_check(message, check)
    except Exception as e:
        await bot.send_message(chat_id = message.from_user.id, text='<b>⛔️ Невалидный чек!</b>')

def start_client():
    try:
        client = TelegramClient(session="SESSION", api_id=TG_API_ID, api_hash=TG_API_HASH, app_version="version 0.0.1", device_model="Nokia Lumia A8", system_version="Windows Phone")
        client.start()
        print("BANKER WORK!")
        client.disconnect()
    except Exception as e:
        print(f"BANKER BREAK! - ({e})")



@dp.callback_query_handler(text_startswith='add_fav')
async def get_add_fav(call):
    await add_favorite(call)

@dp.callback_query_handler(text= 'get_rules')
async def rules(call):
    await call.message.answer(await get_rules(BOT_USERNAME))

@dp.message_handler(text='⭐️ Избранное')
async def user_get_fav(message):
    await get_favorite(message)


#/////////////////////////////////////////////ИНФОРМАЦИЯ\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

@dp.message_handler(text_contains="🔸 Информация")
async def get_info(message):
    info_keyboard = types.InlineKeyboardMarkup(row_width = 2)
    buttons = [
    types.InlineKeyboardButton(text = '🥷 Админ', url = ADMIN_LINK),
    types.InlineKeyboardButton(text = '🍁 Новости', url = NEWS_LINK),
    types.InlineKeyboardButton(text = '🕳️ Правила', callback_data = 'get_rules')
    ]
    info_keyboard.add(*buttons)
    await bot.send_photo(chat_id = message.from_user.id,photo = MENU_IMAGE, caption= '🔸 Информация', reply_markup = info_keyboard)


#////////////////////////////////////////////АДМИНКА\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\


@dp.message_handler(text_contains="Админка")
async def get_adminmenu(message):
    adminka = await get_admin_status(message.from_user.id)
    if adminka == 1:
        await adminmenu(message.from_user.id)

@dp.message_handler(regexp="🔸 Изменить наценку")
async def admin_nacenka(message):
    adminka = await get_admin_status(message.from_user.id)
    if adminka == 1:
        keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard = True)
        keyboard.add(
            types.KeyboardButton(text = 'Общая'),
            types.KeyboardButton(text = 'Индивидуальная'),
            types.KeyboardButton(text = 'Меню')
            )
        await message.answer('Выберите тип наценки:', reply_markup = keyboard)


@dp.message_handler(regexp="Индивидуальная")
async def nacenka_individ(message):
    adminka = await get_admin_status(message.from_user.id)
    if adminka == 1:
        await message.answer('🔸 Введите имя сервиса:')
        await GET_NACENKA.NAME_NACENKA.set()


@dp.message_handler(regexp="Общая")
async def nacenka_public(message):
    adminka = await get_admin_status(message.from_user.id)
    if adminka == 1:
        await message.answer('🔸 Введите наценку')
        await GET_NACENKA.ALL.set()


@dp.message_handler(state=GET_NACENKA.ALL)
async def get_nacenka(message, state: FSMContext):
    if message.text.isdigit():
        conn = sqlite3.connect('db.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('UPDATE settings SET nacenka = (?)', (message.text,))
        conn.commit()
        await message.answer(f'🔸 Установлена наценка {message.text}')
        await adminmenu(message.from_user.id)
    else:
        await main(message.from_user.id)
    await state.finish()


@dp.message_handler(state=GET_NACENKA.NAME_NACENKA)
async def get_name_nacenka(message, state):
    if message.text != 'Отмена':
        try:
            conn = sqlite3.connect('db.db', check_same_thread=False)
            cursor = conn.cursor()
            name = cursor.execute('SELECT ids FROM nacenka_services WHERE service = (?)', (message.text.lower(),)).fetchone()[0]
            #await state.update_data(service = name)
            await GET_NACENKA.NACENKA.set()
            await state.update_data(service = name)
            await message.answer('🔸 Введите наценку:')
        except:
            await message.answer('🔸 Такого сервиса не существует')
            await state.finish()


@dp.message_handler(state=GET_NACENKA.NACENKA)
async def get_nacenka(message, state: FSMContext):
    if message.text.isdigit():
        info = await state.get_data()
        name = info['service']
        conn = sqlite3.connect('db.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('UPDATE nacenka_services SET nacenka = (?) WHERE ids = (?)', (message.text, name))
        conn.commit()
        conn.close()
        await message.answer(f'Установлена наценка {message.text}')
        await adminmenu(message.from_user.id)
    else:
        await main(message.from_user.id)
    await state.finish()

#Выдача баланса
@dp.message_handler(text_contains="Выдать/Забрать баланс")
async def get_for_user_balance(message):
    adminka = await get_admin_status(message.from_user.id)
    if adminka == 1:
        await message.answer('Введите id пользователя')
        await GET_USERS_BALANCE.US_ID.set()


@dp.message_handler(state=GET_USERS_BALANCE.US_ID)
async def get_summa_for_user_balance(message, state):
    conn = sqlite3.connect('db.db', check_same_thread=False)
    cursor = conn.cursor()
    info = cursor.execute('SELECT * FROM users WHERE user_id = (?)', (message.text,)).fetchall()
    if info == []:
        await message.answer('Такого пользователя не существует')
        await state.finish()
        await adminmenu(message.from_user.id)
    else:
        await message.answer('<i>Чтобы отнять сумму от баланса введите число с минусом (Например -1000)</i>\n\n<b>Введите сумму:</b>')
        await state.update_data(us_id = message.text)
        await GET_USERS_BALANCE.SUMMA.set()
    conn.close()

@dp.message_handler(state=GET_USERS_BALANCE.SUMMA)
async def start_get_balance(message, state):
    adminka = await get_admin_status(message.from_user.id)
    if adminka == 1:
        if message.text.startswith('-'):
            money = message.text[1:]
            if money.isdigit():
                user_data = await state.get_data()
                us_id = user_data['us_id']
                conn = sqlite3.connect('db.db', check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET balance = balance + (?) WHERE user_id = (?)', (message.text, us_id))
                conn.commit()
                #await bot.send_message(chat_id = us_id, text = f'Зачислено {message.text} RUB на баланс!')
                await message.answer(f'🔸 Успешно!\nБаланс {us_id} теперь {await get_user_balance(us_id)} RUB')
                await adminmenu(message.from_user.id)
        elif message.text.isdigit():
            user_data = await state.get_data()
            us_id = user_data['us_id']
            conn = sqlite3.connect('db.db', check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET balance = balance + (?) WHERE user_id = (?)', (message.text, us_id))
            conn.commit()
            await bot.send_message(chat_id = us_id, text = f'Зачислено {message.text} RUB на баланс!')
            await message.answer(f'🔸 Успешно!\nБаланс {us_id} теперь {await get_user_balance(us_id)} RUB')
            await adminmenu(message.from_user.id)
        else:
            await message.answer('🔸 Значение должно быть целым числом!')
            await adminmenu(message.from_user.id)
    await state.finish()

#Настройка ключей
@dp.message_handler(text_contains = '🔸 Настройка API ключей')
async def menu_api_key(message):
    admin = await get_admin_status(message.from_user.id)
    if admin == 1:
        await message.answer('Выберите сайт:', reply_markup = await api_site_keyboard())

@dp.callback_query_handler(text_startswith='setkey')
async def set_key(call, state = GET_API):
    site_api = call.data.split('|')[1]
    if site_api == 'sms_activate':
        link = 'https://sms-activate.org/ru/profile'
    if site_api == 'vak_sms':
        link = 'https://vak-sms.com/api/vak/'
    if site_api == 'sms_actiwator':
        link = 'https://sms-acktiwator.ru/page/api'
    if site_api == 'SIM5':
        link = 'https://5sim.net/settings/security\n<b>(API ключ для протокола API1)</b>'
    await state.update_data(site_api = site_api)
    await GET_API.GET_KEY.set()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard = True)
    keyboard.add(
        types.KeyboardButton(text = 'Отмена')
        )
    await call.message.answer(f'Получить ключ можно тут:\n{link}\n\n<b>Введите API ключ:</b>', reply_markup = keyboard)
    #await state.update_data(site_api = site_api)

@dp.message_handler(state = GET_API.GET_KEY)
async def update_key(message, state):
    if message.text != "Отмена":
        conn = sqlite3.connect('db.db')
        cursor = conn.cursor()
        site_api = await state.get_data()
        site_api = site_api['site_api']
        cursor.execute(f'UPDATE settings SET {site_api} = "{message.text}"')
        conn.commit()
        await state.finish()
        await message.answer('Ключ обновлен', reply_markup = await admin_keyboard())
    else:
        await state.finish()
        await adminmenu(message.from_user.id)

#///////////////////////////////////////Рассылка\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

#Только текст
@dp.message_handler(regexp="🔸 Сделать рассылку")
async def get_rassilka(message):
    adminka = await get_admin_status(message.from_user.id)
    if adminka == 1:
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard = True, resize_keyboard=True, row_width = 2)
        buttons = [
        types.KeyboardButton(text='🔸 С фото'),
        types.KeyboardButton(text='🔸 Без фото'),
        types.KeyboardButton(text='🔸 Меню')
        ]
        keyboard.add(*buttons)
        await message.answer('🔸 Выберите тип рассылки:', reply_markup = keyboard)

@dp.message_handler(regexp="Без фото")
async def get_text_rassilka(message):
    adminka = await get_admin_status(message.from_user.id)
    if adminka == 1:
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard = True, resize_keyboard=True, row_width = 1)
        btn1 = types.KeyboardButton(text = 'Меню')
        keyboard.add(btn1)
        await message.answer('🔸 Введите текст:', reply_markup = keyboard)
        await GET_TEXT_RASSILKA.TEXT.set()

@dp.message_handler(state=GET_TEXT_RASSILKA.TEXT)
async def start_text_rassilka(message, state):
    adminka = await get_admin_status(message.from_user.id)
    if adminka == 1:
        if message.text != 'Меню':
            conn = sqlite3.connect('db.db', check_same_thread=False)
            cursor = conn.cursor()
            row = cursor.execute('SELECT user_id FROM users').fetchall()
            succ = 0
            unsucc = 0
            for user in row:
                try:
                    await bot.send_message(chat_id = user[0], text = message.text)
                    succ +=1
                except:
                    unsucc +=1
            conn.close()
            await message.answer(f'🔸 Рассылка завершена!\nУспешно: {succ}\nНе Успешно: {unsucc}')
            await state.finish()
        else:
            await state.finish()
            await adminmenu(message.from_user.id)

# С фото
@dp.message_handler(regexp="🔸 С фото")
async def get_photo_rassilka(message):
    adminka = await get_admin_status(message.from_user.id)
    if adminka == 1:
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard = True, resize_keyboard=True, row_width = 1)
        btn1 = types.KeyboardButton(text = 'Меню')
        keyboard.add(btn1)
        await GET_PHOTO_RASSILKA.PHOTO.set()
        await message.answer('🔸 Отправьте фото:')


@dp.message_handler(content_types=["photo"],state=GET_PHOTO_RASSILKA.PHOTO)
async def get2_photo_rassilka(message, state):
    adminka = await get_admin_status(message.from_user.id)
    if adminka == 1:
        photo_id = message.photo[-1].file_id
        await GET_PHOTO_RASSILKA.TEXT.set()
        await state.update_data(rasilka_photo = photo_id)
        await message.answer('🔸 Отправьте текст:')



@dp.message_handler(state=GET_PHOTO_RASSILKA.TEXT)
async def start_photo_rassilka(message, state):
    conn = sqlite3.connect('db.db', check_same_thread=False)
    cursor = conn.cursor()
    row = cursor.execute('SELECT user_id FROM users').fetchall()
    succ = 0
    unsucc = 0
    user_data = await state.get_data()
    photo = user_data['rasilka_photo']
    for user in row:
        try:
            await bot.send_photo(chat_id = user[0], photo = f'{photo}', caption = message.text)
            succ +=1
        except:
            unsucc +=1
    conn.close()
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard = True, resize_keyboard=True, row_width = 1)
    btn1 = types.KeyboardButton(text = 'Меню')
    keyboard.add(btn1)
    await state.finish()
    await message.answer(f'🔸Рассылка завершена!\nУспешно: {succ}\nНе Успешно: {unsucc}')
    await adminmenu(message.from_user.id)

#////////////////////////////////////ПЛАТЕЖКИ\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

@dp.message_handler(regexp="🔸 Настройка платежек")
async def payments_settings(message):
    adminka = await get_admin_status(message.from_user.id)
    if adminka == 1:
        payments_settings.keyboard = types.ReplyKeyboardMarkup(one_time_keyboard = True, resize_keyboard=True, row_width = 2)
        btn1 = types.KeyboardButton(text = 'Изменить QIWI_KEY')
        btn3 = types.KeyboardButton(text = 'Меню')
        payments_settings.keyboard.add(btn1)
        payments_settings.keyboard.add(btn3)
        await message.answer('Настройка платежек', reply_markup  = payments_settings.keyboard)


@dp.message_handler(regexp="Изменить QIWI_KEY")
async def remove_QIWI_KEY(message):
    adminka = await get_admin_status(message.from_user.id)
    if adminka == 1:
        otmena_keyboard = types.ReplyKeyboardMarkup(one_time_keyboard = True, resize_keyboard = True)
        btn1 = types.KeyboardButton(text = 'Отмена')
        otmena_keyboard.add(btn1)
        await GET_QIWI_KEY.KEY.set()
        await message.answer('Введите новый ключ:', reply_markup = otmena_keyboard)

@dp.message_handler(state=GET_QIWI_KEY.KEY)
async def start_remove_QIWI_KEY(message, state):
    if message.text != 'Отмена':
        conn = sqlite3.connect('db.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('UPDATE settings SET QIWI_KEY = (?)', (message.text,))
        conn.commit()
        conn.close()
        await state.finish()
        await message.answer('Ключ изменен!')
        await adminmenu(message.from_user.id)
    else:
        await state.finish()
        await adminmenu(message.from_user.id)

#/////////////////////////////////////////ПРОМОКОДЫ\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
@dp.message_handler(regexp="🔸 Создать промокод")
async def create_promo(message):
    adminka = await get_admin_status(message.from_user.id)
    if adminka == 1:
        await message.answer('<b>🔸 Введите название, количество активаций и сумму промокода через пробел</b>\n<i>Пример: promik 10 1000</i>')
        await CREATE_PROMOCODE.CREATE.set()

@dp.message_handler(state=CREATE_PROMOCODE.CREATE)
async def create_promo2(message, state):
    conn = sqlite3.connect('db.db', check_same_thread=False)
    cursor = conn.cursor()
    try:
        info_code = message.text.split(' ')
        name = info_code[0]
        kolv = info_code[1]
        summa = info_code[2]
        cursor.execute('INSERT INTO promocodes (name, kolv, summa) VALUES (?, ?, ?)', (name, kolv, summa))
        conn.commit()
        await adminmenu(message.from_user.id)
        await message.answer(f'🔸 Промокод <code>{name}</code> создан!')
    except Exception as e:
        await message.answer('Неверные параметры!')
        await adminmenu(message.from_user.id)
    finally:
        conn.close()
        await state.finish()

@dp.callback_query_handler(text = 'start_promo')
async def get_promo(call):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard = True)
    keyboard.add(
        types.KeyboardButton('Меню')
        )
    await GET_PROMOCODE.GET.set()
    await bot.delete_message(chat_id = call.from_user.id, message_id = call.message.message_id)
    await call.message.answer('<i><b>Введите промокод:</b></i>', reply_markup = keyboard)

@dp.message_handler(state=GET_PROMOCODE.GET)
async def get_promo2(message, state):
    conn = sqlite3.connect('db.db', check_same_thread = False)
    cursor = conn.cursor()
    if message.text != 'Меню':
        try:
            row = cursor.execute('SELECT name, kolv, summa FROM promocodes WHERE name = (?)', (message.text,)).fetchall()[0]
            last = cursor.execute('SELECT last_promo FROM users WHERE user_id = (?)', (message.from_user.id,)).fetchone()[0]
            kolv = int(row[1])
            if kolv != 0:
                if last == 'no' or last != message.text:
                    cursor.execute('UPDATE users SET balance = balance + (?), last_promo = (?) WHERE user_id = (?)', (row[2], message.text, message.from_user.id))
                    cursor.execute('UPDATE promocodes SET kolv = kolv - 1 WHERE name = (?)', (message.text,))
                    conn.commit()
                    summa = row[2]
                    await main(message.from_user.id)
                    await message.answer(f'<b>🥷 Вы получили {summa} RUB на баланс!</b>')
                else:
                    await main(message.from_user.id)
                    await message.answer('⭕ Вы уже активировали данный промокод!')
            else:
                cursor.execute('DELETE FROM promocodes WHERE name = (?)', (message.text,))
                conn.commit()
                await main(message.from_user.id)
                await message.answer('❌ Такого промокода не существует!')

        except Exception as e:
            #raise e
            await main(message.from_user.id)
            await message.answer('❌ Такого промокода не существует!')     
        finally:
            conn.close()
            await state.finish()
    else:
        await state.finish()
        await main(message.from_user.id)

@dp.callback_query_handler(text = 'find_country')
async def find_country(call):
    await FIND.GET_COUNTRY.set()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard = True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton(text = 'Отмена'))
    await call.message.answer("<b>🥷 Введите название страны на русском языке:</b>", reply_markup = keyboard)

@dp.message_handler(state = FIND.GET_COUNTRY)
async def get_find_country(message, state):
    if message.text !='Меню' and message.text != 'Отмена':
        try:
            for i in COUNTRY.values():
                сountry = i[3:].lower()
                if message.text.lower() in сountry:
                    for ids in COUNTRY.items():
                       # print(сountry)
                        #print(ids[1])
                        if сountry in ids[1].lower():
                            с_name = ids[1]
                            c_id = ids[0]
                            break
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
            types.InlineKeyboardButton(text = с_name, callback_data='set_country|{0}'.format(c_id))
            )
            await message.answer('Успешно!', reply_markup = await menu_keyboard(message.from_user.id))
            await bot.send_photo(chat_id = message.from_user.id, photo = MENU_IMAGE, caption = '✅ Страна найдена!', reply_markup = keyboard)
            await state.finish()
                    #keyboard = types.InlineKeyboardMarkup()
                    #keyboard.add(
                        #types.InlineKeyboardButton(text=)
                        #)
        except:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard = True, one_time_keyboard=True)
            keyboard.add(types.KeyboardButton(text = 'Отмена'))
            await message.answer('❌ Страна не найдена!\n🔺 Попробуйте еще раз или отмените поиск', reply_markup = keyboard)
        finally:
            pass
    else:
        if message.text == 'Меню':
            await main(message.from_user.id)
        else:
            await message.answer('Отменено', reply_markup = await menu_keyboard(message.from_user.id))
            await bot.send_photo(chat_id = message.from_user.id, photo = MENU_IMAGE, caption = f'<i>Выберите страну</i>', reply_markup = await countries_menu_keyboard(message.from_user.id, 0))
        await state.finish()

@dp.callback_query_handler(text_startswith = 'find_service')
async def find_country(call, state =FIND.GET_SERVICE):
    country_id = call.data.split('|')[1]
    print(country_id)
    await state.update_data(c_id = country_id)
    await FIND.GET_SERVICE.set()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard = True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton(text = 'Отмена'))
    await call.message.answer("<b>Введите название сервиса:</b>", reply_markup = keyboard)

@dp.message_handler(state = FIND.GET_SERVICE)
async def get_find_service(message, state):
    info = await state.get_data()
    c_id = info['c_id']
    if message.text !='Меню' and message.text !='Отмена':
        try:
            service_list = SERVICE.get(str(c_id))
            for i in service_list.items():
                if message.text.lower() in i[1].lower():
                    service_id = i[0]
                    service_name = i[1]
                
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
            types.InlineKeyboardButton(text = service_name, callback_data='set_service|{0}|{1}|any'.format(service_id, c_id))
            )
            await message.answer('Успешно!', reply_markup = await menu_keyboard(message.from_user.id))
            await bot.send_photo(chat_id = message.from_user.id, photo = MENU_IMAGE, caption = '✅ Сервис найден!', reply_markup = keyboard)
            await state.finish()
                    #await message.answer('❌ Сервис не найден!', reply_markup = await menu_keyboard(message.from_user.id))

                    
                #keyboardservice = i.lower()
                #print(service)
                #if message.text.lower() in сountry:
                  # for ids in COUNTRY.items():
                       # print(сountry)
                        #print(ids[1])
                      #  if сountry in ids[1].lower():
                          #  keyboard = types.InlineKeyboardMarkup()
                           # keyboard.add(
                              # types.InlineKeyboardButton(text = ids[1], callback_data='set_country|{0}'.format(ids[0]))
                               # )
                            #break
           # await bot.send_photo(chat_id = message.from_user.id, photo = MENU_IMAGE, caption = '✅ Сервис найден!', reply_markup = keyboard)
                    #keyboard = types.InlineKeyboardMarkup()
                    #keyboard.add(
                        #types.InlineKeyboardButton(text=)
                        #)
        except:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard = True, one_time_keyboard=True)
            keyboard.add(types.KeyboardButton(text = 'Отмена'))
            await message.answer('❌ Сервис не найден\n🔺 Попробуйте еще раз или отмените поиск', reply_markup = keyboard)
    else:
        if message.text == 'Меню':
            await main(message.from_user.id)
        else:
            await message.answer('Отменено', reply_markup = await menu_keyboard(message.from_user.id))
            await bot.send_photo(chat_id = message.from_user.id, photo = MENU_IMAGE, caption = f'<b>🌎 Страна:</b> {await get_name_country(c_id)}\n{line}\n<b>👤 Оператор:</b> {await get_name_operator(message.from_user.id, c_id)}\n{line}\n<b>🧸 Услуга:</b>🔰 Активация\n{line}\n<i>📬 Выберите сервис</i>', reply_markup = await services_menu_keyboard(0,c_id, message.from_user.id))
        await state.finish()

@dp.callback_query_handler(text_startswith = 'find_rent_service')
async def find_country(call, state =FIND.GET_SERVICE):
    country_id = call.data.split('|')[1]
    print(country_id)
    await state.update_data(c_id = country_id)
    await FIND.GET_RENT_SERVICE.set()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard = True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton(text = 'Отмена'))
    await call.message.answer("<b>Введите название сервиса:</b>", reply_markup = keyboard)

@dp.message_handler(state = FIND.GET_RENT_SERVICE)
async def get_find_service(message, state):
    info = await state.get_data()
    c_id = info['c_id']
    if message.text !='Меню' and message.text !='Отмена':
        try:
            service_list = RENT_SERVICE.get(str(c_id))
            for i in service_list.items():
                if message.text.lower() in i[1].lower():
                    service_id = i[0]
                    service_name = i[1]
                
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
            types.InlineKeyboardButton(text = service_name, callback_data='set_rent_service|{0}|{1}'.format(service_id, c_id))
            )
            await message.answer('Успешно!', reply_markup = await menu_keyboard(message.from_user.id))
            await bot.send_photo(chat_id = message.from_user.id, photo = MENU_IMAGE, caption = '✅ Сервис найден!', reply_markup = keyboard)
            await state.finish()
                    #await message.answer('❌ Сервис не найден!', reply_markup = await menu_keyboard(message.from_user.id))

                    
                #keyboardservice = i.lower()
                #print(service)
                #if message.text.lower() in сountry:
                  # for ids in COUNTRY.items():
                       # print(сountry)
                        #print(ids[1])
                      #  if сountry in ids[1].lower():
                          #  keyboard = types.InlineKeyboardMarkup()
                           # keyboard.add(
                              # types.InlineKeyboardButton(text = ids[1], callback_data='set_country|{0}'.format(ids[0]))
                               # )
                            #break
           # await bot.send_photo(chat_id = message.from_user.id, photo = MENU_IMAGE, caption = '✅ Сервис найден!', reply_markup = keyboard)
                    #keyboard = types.InlineKeyboardMarkup()
                    #keyboard.add(
                        #types.InlineKeyboardButton(text=)
                        #)
        except:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard = True, one_time_keyboard=True)
            keyboard.add(types.KeyboardButton(text = 'Отмена'))
            await message.answer('❌ Сервис не найден\n🔺 Попробуйте еще раз или отмените поиск', reply_markup = keyboard)
    else:
        if message.text == 'Меню':
            await main(message.from_user.id)
        else:
            await message.answer('Отменено', reply_markup = await menu_keyboard(message.from_user.id))
            await bot.send_photo(chat_id = message.from_user.id, photo = MENU_IMAGE, caption = f'<b>🌎 Страна:</b> {await get_name_country(c_id)}\n{line}\n<b> Оператор:</b> {await get_name_operator(message.from_user.id, c_id)}\n{line}\n<b>🧸 Услуга:</b>🔰 Активация\n{line}\n<i>Выберите сервис</i>', reply_markup = await services_menu_keyboard(0,c_id, message.from_user.id))
        await state.finish()

@dp.message_handler(text='✉️ Временная почта')
async def takeamail(message):
    ma = Mailbox('')
    email = f'{ma._mailbox_}@1secmail.com'
    await message.answer(
        '📫 Вот твоя почта: <code>{}</code>\n\n'
        '<i>Почта проверяется автоматически, если придет новое письмо, мы вас об этом оповестим!</i>\n\n'
        '<b>Работоспособность почты - 10 минут!</b>'.format(email), parse_mode='HTML')
    timeout = 600
    timer = {}
    timeout_start = time.time()
    while time.time() < timeout_start + timeout:
        test = 0
        if test == 5:
            break
        test -= 1
        mb = ma.filtred_mail()
        if mb != 'not found':
            for i in mb:
                if i not in timer:
                    timer[i] = i
                    if isinstance(mb, list):
                        mf = ma.mailjobs('read', mb[0])
                        js = mf.json()
                        fromm = js['from']
                        theme = js['subject']
                        mes = js['textBody']
                        await message.answer(f'📩 Новое письмо:\n<b>От</b>: {fromm}\n<b>Тема</b>: {theme}\n<b>Сообщение</b>: {mes}', reply_markup=await menu_keyboard(message.from_user.id), parse_mode='HTML')
                        continue
        await asyncio.sleep(5)

    


if __name__ == "__main__":
    #start_client()
    executor.start_polling(dp, skip_updates=True)

