from aiogram import types
from country import COUNTRY
from services import SERVICE
from rent_services import RENT_SERVICE
from operators import OPERATORS
import sqlite3

async def menu_keyboard(user_id):
	keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width = 2)
	keyboard.add(
		types.KeyboardButton(text = '🛒 Номера'),types.KeyboardButton(text = '📬 Временная почта'),
		types.KeyboardButton(text = '🫅 Профиль'),
		types.KeyboardButton(text = ⭐ Избранное')
		)
	keyboard.add(
		types.KeyboardButton(text = 'ℹ️ Информация')
		)
	from func import get_admin_status
	adminka = await get_admin_status(user_id)
	if adminka == 1:
		keyboard.add(
			types.KeyboardButton(text = '🥷 Админка')
			)
	#adminka = await get_admin_status(user_id)
	#if adminka == 1:
		#btn2 = types.KeyboardButton(text = 'Админменю')
		#keyboard.add(btn2)

	return keyboard

async def countries_menu_keyboard(us_id, i: int):
	conn = sqlite3.connect('db.db', check_same_thread = False)
	cursor = conn.cursor()
	row = cursor.execute('SELECT country_id, service_id, operator_id FROM last_zakaz WHERE user_id = ?',[us_id]).fetchone()
	keyboard = types.InlineKeyboardMarkup(row_width=3)
	btn = []
	navigation = []
	back = i
	stop = i+12
	num = 0
	for pack in COUNTRY.items():
		num +=1
		#print(num)
		if i < num:
			if i < stop:
				btn.append(types.InlineKeyboardButton(text = pack[1], callback_data='set_country|{0}'.format(pack[0])))
				i +=1
	keyboard.add(*btn)
	try:
		if row[0] != 'no':
			service_id = row[1]
			country_id = row[0]
			data = SERVICE.get(str(country_id))
			for s_id in data.keys():
				if s_id == service_id:
					service_name = data.get(service_id)
					flag = COUNTRY.get(str(country_id))
					flag = flag[:2]
					keyboard.add(types.InlineKeyboardButton(text = f'⏳ Последний заказ({flag} | {service_name})', callback_data='set_service|{0}|{1}|{2}'.format(row[1], row[0], row[2])))
					break
	except:
		pass
		#keyboard.add(types.InlineKeyboardButton(text = 'Ласт заказ', callback_data='set_service|{0}|{1}'.format(row[1], row[0])))
	keyboard.add(
		types.InlineKeyboardButton(text = '🔎 Поиск страны', callback_data=f'find_country')
		)
	if i > 12:
		navigation.append(types.InlineKeyboardButton(text='◀️', callback_data=f'next_country|{back - 12}'))

	if len(btn) == 12:
		navigation.append(types.InlineKeyboardButton(text='➡️', callback_data=f'next_country|{i}'))
	keyboard.add(*navigation)

	return keyboard


async def operators_menu_keyboard(i: int, country_id):
	keyboard = types.InlineKeyboardMarkup(row_width=3)
	btn = []
	navigation = []
	stop = i+12
	back = i
	num = 0
	SR_KEY = OPERATORS.get(str(country_id))

	for pack in SR_KEY.items():
		num +=1
		#print(num)
		if i < num:
			if i < stop:
				btn.append(types.InlineKeyboardButton(text = pack[1], callback_data='set_operator|{0}|{1}'.format(pack[0], country_id)))
				i +=1
	keyboard.add(*btn)
	if i > 12:
		navigation.append(types.InlineKeyboardButton(text='◀️', callback_data=f'next_operator|{country_id}|{back-12}'))

	if len(btn) == 12:
		navigation.append(types.InlineKeyboardButton(text='➡️', callback_data=f'next_operator|{country_id}|{i}'))
	keyboard.add(*navigation)
	return keyboard


async def get_params_activation(i:int, operator):
	keyboard = types.InlineKeyboardMarkup(row_width = 2)
	keyboard.add(
		types.InlineKeyboardButton(text = 'Активация', callback_data=f'get_activation_service|{i}'),
		types.InlineKeyboardButton(text = 'Аренда', callback_data=f'get_rent_service|{i}'),
		types.InlineKeyboardButton(text = 'Назад', callback_data=f'set_country|{i}')
		#types.InlineKeyboardButton(text = 'Несколько сервисов', callback_data=f'get_multi_service|{i}')
		)
	return keyboard




async def services_menu_keyboard(i: int, country: int, us_id):
	conn = sqlite3.connect('db.db', check_same_thread= True)
	cursor = conn.cursor()
	row = cursor.execute('SELECT * FROM most_buy_service').fetchall()
	row.sort(key=lambda x: x[2], reverse=True)
	operator = cursor.execute('SELECT operator FROM users WHERE user_id = ?',[us_id]).fetchone()[0]
	keyboard = types.InlineKeyboardMarkup(row_width=3)
	btn = []
	navigation = []
	stop = i+12
	back = i
	num = 0
	SR_KEY = SERVICE.get(country)
	for top in row:
		if top[1] in SR_KEY.keys():
			num +=1
			#print(num)
			if i < num:
				if i < stop:
					if i < 3:
						btn.append(types.InlineKeyboardButton(text = "🔥 " + top[0], callback_data='set_service|{0}|{1}'.format(top[1], country)))
					else:
						btn.append(types.InlineKeyboardButton(text = top[0], callback_data='set_service|{0}|{1}'.format(top[1], country)))
					i +=1
	keyboard.add(*btn)
	if i > 12:
		navigation.append(types.InlineKeyboardButton(text='◀️', callback_data=f'next_service|{country}|{back-12}'))

	if len(btn) == 12:
		navigation.append(types.InlineKeyboardButton(text='➡️', callback_data=f'next_service|{country}|{i}'))
	keyboard.add(
		types.InlineKeyboardButton(text = '🔎 Поиск сервиса', callback_data=f'find_service|{country}')
		)
	keyboard.add(*navigation)
	keyboard.add(
		types.InlineKeyboardButton(text = 'Назад', callback_data=f'set_operator|{operator}|{country}')
		)
	return keyboard


async def service_info(us_id, api, country_id, service_id,):
	conn = sqlite3.connect('db.db', check_same_thread = False)
	cursor = conn.cursor()

	price = cursor.execute('SELECT price_sms FROM users WHERE user_id = ?',[us_id]).fetchone()[0]
	nacenka = cursor.execute('SELECT nacenka FROM nacenka_services WHERE ids = (?)', (service_id,)).fetchone()[0]
	if nacenka == 0:
		nacenka = cursor.execute('SELECT nacenka FROM settings').fetchone()[0]
	in_fav = cursor.execute('SELECT user_id FROM favorite_service WHERE user_id = ? AND country = ? AND service = ?',[us_id, country_id, service_id]).fetchone()
	ftext = '⭐️ В избранное' if in_fav == None else '⭐️ Удалить из избранного'
	keyboard = types.InlineKeyboardMarkup(row_width=3)
	keyboard.add(
		types.InlineKeyboardButton(text = f'Купить | {price+nacenka} RUB', callback_data = f'buy_number|{service_id}|{api}|{price}|0|{country_id}|'),
		types.InlineKeyboardButton(text = ftext, callback_data = f'add_fav|{service_id}|{country_id}')
		)
	keyboard.add(
		types.InlineKeyboardButton(text='Назад', callback_data=f'get_activation_service|{country_id}')
		)
	return keyboard


async def rent_services_menu_keyboard(i: int, country: int, us_id):
	conn = sqlite3.connect('db.db', check_same_thread= True)
	cursor = conn.cursor()
	row = cursor.execute('SELECT * FROM most_buy_service').fetchall()
	row.sort(key=lambda x: x[2], reverse=True)
	operator = cursor.execute('SELECT operator FROM users WHERE user_id = ?',[us_id]).fetchone()[0]
	keyboard = types.InlineKeyboardMarkup(row_width=3)
	btn = []
	back = i
	navigation = []
	stop = i+12
	num = 0
	SR_KEY = RENT_SERVICE.get(str(country))
	try:
		for top in row:
			if top[1] in SR_KEY.keys():
				num +=1
			#print(num)
				if i < num:
					if i < stop:
						if i < 3:
							btn.append(types.InlineKeyboardButton(text = "🔥 " + top[0], callback_data='set_rent_service|{0}|{1}'.format(top[1], country)))
						else:
							btn.append(types.InlineKeyboardButton(text = top[0], callback_data='set_rent_service|{0}|{1}'.format(top[1], country)))
						i +=1
		keyboard.add(*btn)
		if i > 12:
			navigation.append(types.InlineKeyboardButton(text='◀️', callback_data=f'next_rent_service|{country}|{back-12}'))
			#btn.append(types.InlineKeyboardButton(text = pack[1], callback_data='set_rent_service|{0}|{1}'.format(pack[0], country)))

		if len(btn) == 12:
			navigation.append(types.InlineKeyboardButton(text='➡️', callback_data=f'next_rent_service|{country}|{i}'))
		keyboard.add(*navigation)
		keyboard.add(
			types.InlineKeyboardButton(text = '🔎 Поиск сервиса', callback_data=f'find_rent_service|{country}')
			)
		return keyboard
	except:
		keyboard.add(
			types.InlineKeyboardButton(text='❌ Аренда недоступна :(', callback_data='0ew0fko')
			)
	finally:
		keyboard.add(
			types.InlineKeyboardButton(text = 'Назад', callback_data=f'set_operator|{operator}|{country}')
			)
	return keyboard

async def get_rent_time_keyboard(service_id, country_id):
	keyboard = types.InlineKeyboardMarkup(row_width = 2)
	keyboard.add(
		types.InlineKeyboardButton(text = '▪️4 часа', callback_data = f'timeRent|4|{service_id}|{country_id}'),
		types.InlineKeyboardButton(text = '▪️12 часов', callback_data = f'timeRent|12|{service_id}|{country_id}'),
		types.InlineKeyboardButton(text = '▪️1 день', callback_data = f'timeRent|24|{service_id}|{country_id}'),
		types.InlineKeyboardButton(text = '▪️3 дня', callback_data = f'timeRent|72|{service_id}|{country_id}'),
		types.InlineKeyboardButton(text = '▪️1 неделя', callback_data = f'timeRent|168|{service_id}|{country_id}'),
		types.InlineKeyboardButton(text = '▪️2 недели', callback_data = f'timeRent|336|{service_id}|{country_id}'),
		types.InlineKeyboardButton(text = '🔺Назад', callback_data= f'get_rent_service|{country_id}')
		#types.InlineKeyboardButton(text = '▪️1 месяц', callback_data = f'timeRent|730|{service_id}|{country_id}')
		)
	return keyboard

async def payments_keyboard():
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(
    	types.InlineKeyboardButton('💳 QIWI CARD'),
    	types.InlineKeyboardButton('🤖 BTC BANKER'),
    	types.InlineKeyboardButton('Меню')
    	)
    return keyboard

async def admin_keyboard():
	keyboard = types.ReplyKeyboardMarkup(one_time_keyboard = True, resize_keyboard=True, row_width = 2)
	keyboard.add(
		types.InlineKeyboardButton(text= 'Настройка API ключей')
		)
	buttons = [
	types.KeyboardButton(text='🔸Изменить наценку'),
	types.KeyboardButton(text='🔸Создать промокод'),
	types.KeyboardButton(text='🔸Сделать рассылку'),
	types.KeyboardButton(text='🔸Выдать/Забрать баланс'),
	types.KeyboardButton(text='🔸Настройка платежек'),
	types.KeyboardButton(text = '🔸Меню')
	]
	keyboard.add(*buttons)
	return keyboard

async def api_site_keyboard():
	keyboard = types.InlineKeyboardMarkup(row_width = 2)
	keyboard.add(
		types.InlineKeyboardButton(text = 'SMS-ACTIVATE', callback_data= 'setkey|sms_activate'),
		types.InlineKeyboardButton(text = 'VAK-SMS', callback_data= 'setkey|vak_sms'),
		types.InlineKeyboardButton(text = 'SMS-ACTIWATOR', callback_data= 'setkey|sms_actiwator'),
		types.InlineKeyboardButton(text = '5sim', callback_data= 'setkey|SIM5')
		)
	return keyboard
		



