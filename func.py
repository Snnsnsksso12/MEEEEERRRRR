from aiogram import Bot, Dispatcher, executor, types
import asyncio
import requests
import random
from pyqiwip2p import QiwiP2P
from threading import Thread
from multiprocessing.dummy import Pool as ThreadPool
import sqlite3
from keyboards import *
from config import *

bot = Bot(TOKEN, parse_mode=types.ParseMode.HTML)

line = '➖➖➖➖➖➖➖➖➖➖➖➖'

#Прислать меню
async def main(user_id):
	await bot.send_photo(chat_id = user_id, photo = MENU_IMAGE, caption = f'<b>🎧 Добро пожаловать!</b>\n{line}\n<b>💰 Ваш баланс:</b> <i>{await get_user_balance(user_id)} RUB</i>', reply_markup = await menu_keyboard(user_id))

async def profile(message):
	conn = sqlite3.connect('db.db', check_same_thread=False)
	cursor = conn.cursor()
	balance = await get_user_balance(message.from_user.id)
	#row = cursor.execute("SELECT balance, all_buy, all_deposit FROM users WHERE user_id = ?", [message.from_user.id]).fetchmany()[0]
	keyboard = types.InlineKeyboardMarkup(row_width=1)
	keyboard.add(
		types.InlineKeyboardButton(text="💲 Пополнить баланс", callback_data="get_money"),
		types.InlineKeyboardButton(text = '📔 Активировать промокод', callback_data='start_promo')
		)
	await bot.send_photo(chat_id = message.from_user.id, photo = PROFILE_IMAGE, caption=
'''
<b>👤 Ваш ID:</b> <code>{0}</code>
<b>💰 Ваш баланс:</b> <i>{1} RUB</i>

'''.format(message.from_user.id, balance), reply_markup = keyboard)# row[1], row[2]), reply_markup = keyboard)


#Получить баланс
async def get_user_balance(user_id):
	conn = sqlite3.connect('db.db', check_same_thread=False)
	cursor = conn.cursor()
	try:
		cursor.execute('SELECT balance FROM users WHERE user_id = (?)', (user_id,))
		balance = cursor.fetchone()[0]
	except:
		balance = 0
	conn.close()
	round_balance = round(balance, 2)
	return round_balance

async def get_admin_status(user_id):
	conn = sqlite3.connect('db.db', check_same_thread=False)
	cursor = conn.cursor()
	if user_id == admin:
		return 1
	else:
		status = cursor.execute('SELECT admin FROM users WHERE user_id = (?)', (user_id,)).fetchone()[0]
		return status
	conn.close()


def get_price(i):
	try:
		conn = sqlite3.connect('db.db', check_same_thread = False)
		cursor = conn.cursor()
		print(i)
		info = i.split('|')
		service_id = info[0]
		country_id = info[1]
		site_api = info[2]
		link = info[3]
		operator = info[4]

		if site_api == 'sim5':
			if operator == 'any':
				operator = 'megafon'
			info_number = requests.get(link).json()
			for i in info_number.items():
				p = i[1].values()
				info_dict = list(p)[0].get(operator)
				if info_dict.get('count') != 0:
					price = info_dict.get('cost')
					return site_api, price
		if site_api == 'vak':
			try:
				info_number = requests.get(link).json()
				price = info_number[country_id][service_id]['cost']
				if info_number[country_id][service_id]['count'] == 0 and info_number[country_id][service_id].get('count') == None:
					print(info_number)
					return site_api, 0
				else:
					return site_api, price
			except:
				if int(country_id) == 0:
					VAK_SMS_TOKEN = cursor.execute('SELECT vak_sms FROM settings').fetchone()[0]
					info_number = requests.get(f'https://vak-sms.com/api/getCountNumber/?apiKey={VAK_SMS_TOKEN}&service={service_id}&country=ru&operator=any&price').json()
					print(info_number)
					if info_number.get(service_id) != 0 or info_number.get(service_id) != 'None':
						return 'vak', info_number['price']
		else:
			info_number = requests.get(link).json()
			price = info_number[country_id][service_id].get('cost')
			if info_number[country_id][service_id].get('count') == 0:
				return site_api, 0
			else:
				return site_api, price
	except:
		return site_api, 0

async def get_better_services(call, service_id, country_id):
	try:
		conn = sqlite3.connect('db.db', check_same_thread=False)
		cursor = conn.cursor()
		row = cursor.execute('SELECT * FROM settings').fetchall()[0]
		operator = cursor.execute('SELECT operator FROM users WHERE user_id =?',[call.from_user.id]).fetchone()[0]
		dict_prices = {}
		urls = []
		#vak-sms
		if row[2] != 0:
			key = row[2]
			urls.append(f'{service_id}|{country_id}|vak|{VAK_SMS_DOMEN}api_key={key}&action=getPrices&service={service_id}&country={country_id}|{operator}')
		if row[3] != 0:
			key = row[3]
			urls.append(f'{service_id}|{country_id}|act|{SMS_ACTIVATE_DOMEN}api_key={key}&action=getPrices&service={service_id}&country={country_id}|{operator}')
		if row[4] != 0:
			key = row[4]
			urls.append(f'{service_id}|{country_id}|aw|{SMS_ACTIWATOR_DOMEN}api_key={key}&action=getPrices&service={service_id}&country={country_id}|{operator}')
		if row[5] != 0:
			key = row[5]
			urls.append(f'{service_id}|{country_id}|sim5|{SIM5_DOMEN}api_key={key}&action=getPrices&country={country_id}&service={service_id}|{operator}')

		pos = []
		pool = ThreadPool()
		results = pool.map(get_price, urls)
		print(results)
		for i in results:
			if i[1] != 0:
				dict_prices.update({i[1]:i[0]})
		serv_list = dict_prices.keys()
		site_api = dict_prices.get(min(serv_list))
		print(site_api)
		cursor.execute('UPDATE users SET price_sms = ? WHERE user_id = ?',[min(serv_list), call.from_user.id])
		conn.commit()
		return site_api
	except:
		return None

async def get_number(call):
	infolist = call.data.split('|')
	print(infolist)
	service_id = infolist[1]
	site_api = infolist[2]
	price = float(infolist[3])
	step = int(infolist[4])
	country_id = infolist[5]
	conn = sqlite3.connect('db.db', check_same_thread=False)
	cursor = conn.cursor()
	cursor.execute('UPDATE users SET price_sms = ? WHERE user_id = ?',[price, call.from_user.id])
	conn.commit()
	keys = cursor.execute('SELECT sms_activate, vak_sms, sms_actiwator, SIM5 FROM settings').fetchall()[0]
	SMS_ACTIVATE_TOKEN =  keys[0]
	VAK_SMS_TOKEN = keys[1]
	SMS_ACTIWATOR_TOKEN = keys[2]
	SIM5_TOKEN = keys[3]
	nacenka = float(cursor.execute('SELECT nacenka FROM nacenka_services WHERE ids = (?)', (service_id,)).fetchone()[0])
	if nacenka == 0:
		nacenka = float(cursor.execute('SELECT nacenka FROM settings').fetchone()[0])
	print(nacenka)
	operator = cursor.execute('SELECT operator FROM users WHERE user_id = ?',[call.from_user.id]).fetchone()[0]
	cursor.execute('UPDATE last_zakaz SET country_id = ?, service_id = ?, operator_id = ? WHERE user_id = ?',[country_id, service_id, operator, call.from_user.id])
	conn.commit()
	balance = await get_user_balance(call.from_user.id)
	if balance >= int(price) + nacenka:
		if site_api == 'sim5':
			try:
				SIM5_TOKEN = cursor.execute('SELECT SIM5 FROM settings').fetchone()[0]
				res = requests.get(f'{SIM5_DOMEN}api_key={SIM5_TOKEN}&action=getNumber&service={service_id}&operator={operator}&country={country_id}&operator={operator}').text
				#print('aaaaaaaaa', res)
				print(res)
				number_info = res.split(':')
				number = number_info[2]
				order_id = number_info[1]
				keyboard = types.InlineKeyboardMarkup(row_width = 2)
				button_list = [
				types.InlineKeyboardButton(text = 'Проверить смс', callback_data = f'сheckSMS|{order_id}|sim5|{service_id}'),
				types.InlineKeyboardButton(text = 'Сменить номер', callback_data= f'set_service|{service_id}|{country_id}'),
				types.InlineKeyboardButton(text = 'Отменить заказ', callback_data = f'cancelSMS|{order_id}|sim5')
				]
				keyboard.add(*button_list)
				cursor.execute('UPDATE most_buy_service SET score = score + 1 WHERE ids = (?)', (service_id,))
				cursor.execute('INSERT INTO notif (ids, user_id, number_, nacenka) VALUES (?, ?, ?, ?)',[order_id, call.from_user.id, number, nacenka])
				conn.commit()
				await bot.edit_message_caption(chat_id = call.from_user.id, message_id = call.message.message_id, caption = f'<b>✅ Номер:</b> <code>{number}</code>', reply_markup = keyboard)
				#reroot_btn = types.InlineKeyboardButton(text='')

				
			except IndexError as e:
				if res == 'NO_BALANCE':
					await bot.send_message(chat_id=admin, text= '5SIM:\nНехватает средств для покупки номеров')
				else:
					if res != 'NO_NUMBERS' and 'AVAILABLE' not in res and res != 'BAD_SERVICE':
						await bot.send_message(chat_id=admin, text= f'SIM5:\nОшибка - {res}')
				keyboard = types.InlineKeyboardMarkup(row_width = 2)
				try:
					info_number_act = requests.get(f'{SMS_ACTIVATE_DOMEN}api_key={SMS_ACTIVATE_TOKEN}&action=getPrices&service={service_id}&country={country_id}').text
					price_act = info_number_act[country_id][service_id].get('cost')
					price_act = price_act*1.5
				except:
					price_act = price*2
				if step < 4:
					btnr = types.InlineKeyboardButton(text='Сменить поставщика', callback_data=f'buy_number|{service_id}|act|{price_act}|{step+1}|{country_id}')
					keyboard.add(btnr)
					print(price)
					await bot.edit_message_caption(chat_id=call.from_user.id, message_id = call.message.message_id, caption=f'<b>У текущего поставщика кончились номера данного оператора, вы можете сменить поставщика\nНовая цена: {price_act + nacenka} RUB</b>', reply_markup = keyboard)
				else:
					keyboard = types.InlineKeyboardMarkup(row_width=1)
					btn = types.InlineKeyboardButton(text='В меню', callback_data='menu')
					keyboard.add(btn)
					await bot.send_message(chat_id = call.from_user.id, text = '<b>В данный момент у всех поставщиков отсутсвует нужный вам номер\nПопробуйте позже...</b>', reply_markup = keyboard)
					await bot.delete_message(chat_id=call.from_user.id,message_id= call.message.message_id)

		if site_api == 'vak':
			try:
				VAK_SMS_TOKEN = cursor.execute('SELECT vak_sms FROM settings').fetchone()[0]
				res = requests.get(f'{VAK_SMS_DOMEN}api_key={VAK_SMS_TOKEN}&action=getNumber&service={service_id}&operator={operator}&country={country_id}&operator={operator}').text
				#print('aaaaaaaaa', res)
				print(res)
				number_info = res.split(':')
				number = number_info[2]
				order_id = number_info[1]
				keyboard = types.InlineKeyboardMarkup(row_width = 2)
				button_list = [
				types.InlineKeyboardButton(text = 'Проверить смс', callback_data = f'сheckSMS|{order_id}|vak|{service_id}'),
				types.InlineKeyboardButton(text = 'Сменить номер', callback_data= f'set_service|{service_id}|{country_id}'),
				types.InlineKeyboardButton(text = 'Отменить заказ', callback_data = f'cancelSMS|{order_id}|vak')
				]
				keyboard.add(*button_list)
				cursor.execute('UPDATE most_buy_service SET score = score + 1 WHERE ids = (?)', (service_id,))
				cursor.execute('INSERT INTO notif (ids, user_id, number_, nacenka) VALUES (?, ?, ?, ?)',[order_id, call.from_user.id, number, nacenka])
				conn.commit()
				await bot.edit_message_caption(chat_id = call.from_user.id, message_id = call.message.message_id, caption = f'<b>✅ Номер:</b> <code>{number}</code>', reply_markup = keyboard)
				#reroot_btn = types.InlineKeyboardButton(text='')

				
			except IndexError as e:
				if res == 'NO_BALANCE':
					await bot.send_message(chat_id=admin, text= 'VAK-SMS:\nНехватает средств для покупки номеров')
				else:
					if res != 'NO_NUMBERS' and 'AVAILABLE' not in res and res != 'BAD_SERVICE':
						await bot.send_message(chat_id=admin, text= f'VAK-SMS:\nОшибка - {res}')
				keyboard = types.InlineKeyboardMarkup(row_width = 2)
				try:
					info_number_act = requests.get(f'{SMS_ACTIVATE_DOMEN}api_key={SMS_ACTIVATE_TOKEN}&action=getPrices&service={service_id}&country={country_id}').text
					price_act = info_number_act[country_id][service_id].get('cost')
					price_act = price_act*1.5
				except:
					price_act = price*2
				if step < 4:
					btnr = types.InlineKeyboardButton(text='Сменить поставщика', callback_data=f'buy_number|{service_id}|act|{price_act}|{step+1}|{country_id}')
					keyboard.add(btnr)
					print(price)
					await bot.edit_message_caption(chat_id=call.from_user.id, message_id = call.message.message_id, caption=f'<b>У текущего поставщика кончились номера данного оператора, вы можете сменить поставщика\nНовая цена: {price_act + nacenka} RUB</b>', reply_markup = keyboard)
				else:
					keyboard = types.InlineKeyboardMarkup(row_width=1)
					btn = types.InlineKeyboardButton(text='В меню', callback_data='menu')
					keyboard.add(btn)
					await bot.send_message(chat_id = call.from_user.id, text = '<b>В данный момент у всех поставщиков отсутсвует нужный вам номер\nПопробуйте позже...</b>', reply_markup = keyboard)
					await bot.delete_message(chat_id=call.from_user.id,message_id= call.message.message_id)

		if site_api == 'act':
			try:
				SMS_ACTIVATE_TOKEN = cursor.execute('SELECT sms_activate FROM settings').fetchone()[0]
				res = requests.get(f'{SMS_ACTIVATE_DOMEN}api_key={SMS_ACTIVATE_TOKEN}&action=getNumber&service={service_id}&operator={operator}&country={country_id}').text
				#print('aaaaaaaaa', res)
				number_info = res.split(':')
				number = number_info[2]
				order_id = number_info[1]
				keyboard = types.InlineKeyboardMarkup(row_width = 2)
				button_list = [
				types.InlineKeyboardButton(text = 'Проверить смс', callback_data = f'сheckSMS|{order_id}|act|{service_id}'),
				types.InlineKeyboardButton(text = 'Сменить номер', callback_data= f'set_service|{service_id}|{country_id}'),
				types.InlineKeyboardButton(text = 'Отменить заказ', callback_data = f'cancelSMS|{order_id}|act')
				]
				keyboard.add(*button_list)
				cursor.execute('UPDATE most_buy_service SET score = score + 1 WHERE ids = (?)', (service_id,))
				cursor.execute('INSERT INTO notif (ids, user_id, number_, nacenka) VALUES (?, ?, ?, ?)',[order_id, call.from_user.id, number, nacenka])
				conn.commit()
				await bot.edit_message_caption(chat_id = call.from_user.id, message_id = call.message.message_id, caption = f'<b>✅ Номер:</b> <code>{number}</code>', reply_markup = keyboard)

				
			except IndexError as e:
				if res == 'NO_BALANCE':
					await bot.send_message(chat_id=admin, text= 'SMS-ACTIVATE:\nНехватает средств для покупки номеров')
				else:
					if res != 'NO_NUMBERS' and 'AVAILABLE' not in res and res != 'BAD_SERVICE':
						await bot.send_message(chat_id=admin, text= f'SMS-ACTIVATE:\nОшибка - {res}')
				keyboard = types.InlineKeyboardMarkup(row_width = 2)
				try:
					info_number_aw = requests.get(f'https://sms-acktiwator.ru/stubs/handler_api.php?api_key={SMS_ACTIWATOR_TOKEN}&action=getPrices&service={service_id}&country={country_id}').json()
					price_aw = info_number_aw[country_id][service_id].get('cost')
				except:
					price_aw = price*2
				if step < 4:
					btnr = types.InlineKeyboardButton(text='Сменить поставщика', callback_data=f'buy_number|{service_id}|aw|{price_aw}|{step+1}|{country_id}')
					keyboard.add(btnr)
					await bot.edit_message_caption(chat_id=call.from_user.id, message_id = call.message.message_id, caption=f'<b>У текущего поставщика кончились номера данного оператора, вы можете сменить поставщика\nНовая цена: {price_aw + nacenka} RUB</b>', reply_markup = keyboard)
				else:
					#await bot.delete_message(chat_id=call.from_user.id,message_id= call.message.message_id)
					keyboard = types.InlineKeyboardMarkup(row_width=1)
					btn = types.InlineKeyboardButton(text='В меню', callback_data='menu')
					keyboard.add(btn)
					await bot.send_message(chat_id = call.from_user.id, text = '<b>В данный момент у всех поставщиков отсутсвует нужный вам номер\nПопробуйте позже...</b>', reply_markup = keyboard)
					await bot.delete_message(chat_id=call.from_user.id,message_id= call.message.message_id)

		if site_api == 'aw':
			try:
				SMS_ACTIWATOR_TOKEN = cursor.execute('SELECT sms_actiwator FROM settings').fetchone()[0]
				res = requests.get(f'{SMS_ACTIWATOR_DOMEN}api_key={SMS_ACTIWATOR_TOKEN}&action=getNumber&service={service_id}&operator={operator}&country={country_id}').text
				#print('aaaaaaaaa', res)
				number_info = res.split(':')
				number = number_info[2]
				order_id = number_info[1]
				keyboard = types.InlineKeyboardMarkup(row_width = 2)
				button_list = [
				types.InlineKeyboardButton(text = 'Проверить смс', callback_data = f'сheckSMS|{order_id}|aw|{service_id}'),
				types.InlineKeyboardButton(text = 'Сменить номер', callback_data= f'set_service|{service_id}|{country_id}'),
				types.InlineKeyboardButton(text = 'Отменить заказ', callback_data = f'cancelSMS|{order_id}|aw')
				]
				keyboard.add(*button_list)
				cursor.execute('UPDATE most_buy_service SET score = score + 1 WHERE ids = (?)', (service_id,))
				cursor.execute('INSERT INTO notif (ids, user_id, number_, nacenka) VALUES (?, ?, ?, ?)',[order_id, call.from_user.id, number, nacenka])
				conn.commit()
				await bot.edit_message_caption(chat_id = call.from_user.id, message_id = call.message.message_id, caption = f'<b>✅ Номер:</b> <code>{number}</code>', reply_markup = keyboard)

				
			except IndexError as e:
				if res == 'NO_BALANCE':
					await bot.send_message(chat_id=admin, text= 'SMS-ACTIWATOR:\nНехватает средств для покупки номеров')
				else:
					if res != 'NO_NUMBERS' and 'AVAILABLE' not in res and res != 'BAD_SERVICE':
						await bot.send_message(chat_id=admin, text= f'SMS-ACTIWATOR:\nОшибка - {res}')
				keyboard = types.InlineKeyboardMarkup(row_width = 2)
				try:
					info_number_vak = requests.get(f'https://vak-sms.com/stubs/handler_api.php?api_key={VAK_SMS_TOKEN}&action=getPrices&service={service_id}&country={country_id}').json()
					price_vak = info_number_vak[country_id][service_id].get('cost')
				except:
					price_vak = price*2
				if step < 4:
					btnr = types.InlineKeyboardButton(text='Сменить поставщика', callback_data=f'buy_number|{service_id}|vak|{price_vak}|{step+1}|{country_id}')
					keyboard.add(btnr)
					await bot.edit_message_caption(chat_id=call.from_user.id, message_id = call.message.message_id, caption=f'<b>У текущего поставщика кончились номера данного оператора, вы можете сменить поставщика\nНовая цена: {price_vak + nacenka} RUB</b>', reply_markup = keyboard)
				else:
					#await bot.delete_message(chat_id=call.from_user.id,message_id= call.message.message_id)
					keyboard = types.InlineKeyboardMarkup(row_width=1)
					btn = types.InlineKeyboardButton(text='В меню', callback_data='menu')
					keyboard.add(btn)
					await bot.send_message(chat_id = call.from_user.id, text = '<b>В данный момент у всех поставщиков отсутсвует нужный вам номер\nПопробуйте позже...</b>', reply_markup = keyboard)
					await bot.delete_message(chat_id=call.from_user.id,message_id= call.message.message_id)
	else:
		await call.answer(f'⛔️ Не хватает баланса',show_alert=False)


async def checkSMS (call):
	try:
		print(call.data)
		conn = sqlite3.connect('db.db', check_same_thread = False)
		cursor = conn.cursor()
		row = cursor.execute('SELECT sms_activate, sms_actiwator, vak_sms, SIM5 FROM settings').fetchall()[0]
		SMS_ACTIVATE_TOKEN = row[0]
		SMS_ACTIWATOR_TOKEN = row[1]
		VAK_SMS_TOKEN = row[2]
		SIM5_TOKEN = row[3]
		service_info = call.data.split('|')
		order_id = service_info[1]
		service_name = service_info[2]
		service_key = service_info[3]
		#info = sa.getStatus(id = order_id)
		if service_name == 'act':
			try:
				info = requests.get(f'{SMS_ACTIVATE_DOMEN}api_key={SMS_ACTIVATE_TOKEN}&action=getStatus&id={order_id}').text
			except:
				pass
		if service_name == 'aw':
			try:
				info = requests.get(f'{SMS_ACTIWATOR_DOMEN}api_key={SMS_ACTIWATOR_TOKEN}&action=getStatus&id={order_id}').text
			except:
				pass
		if service_name == 'vak':
			info = requests.get(f'{VAK_SMS_DOMEN}api_key={VAK_SMS_TOKEN}&action=getStatus&id={order_id}').text

		if service_name == 'sim5':
			info = requests.get(f'{SIM5_DOMEN}api_key={SIM5_TOKEN}&action=getStatus&id={order_id}').text



		try:
			if info.startswith('STATUS_OK') or info.startswith('STATUS_WAIT_RETRY'):
				conn = sqlite3.connect('db.db', check_same_thread=False)
				cursor = conn.cursor()
				keyboard = types.InlineKeyboardMarkup(row_width = 2)
				buttons = [
				types.InlineKeyboardButton(text = '🔁 Повторная смс', callback_data = f'retrySMS|{order_id}|{service_name}'),
				types.InlineKeyboardButton(text = '⛔️ Завершить активацию', callback_data = f'cancelSMS|{order_id}|{service_name}'),
				]
				cursor.execute('UPDATE users SET balance = balance - price_sms WHERE user_id = (?)', (call.from_user.id,))
				cursor.execute('UPDATE users SET all_buy = all_buy + 1 WHERE user_id = (?)', (call.from_user.id,))
				prices = cursor.execute('SELECT price_sms FROM users WHERE user_id = (?)', (call.from_user.id,)).fetchone()[0]
				nacenka = cursor.execute('SELECT nacenka FROM nacenka_services WHERE ids = ?', [service_key]).fetchone()[0]
				if nacenka == 0:
					nacenka = cursor.execute('SELECT nacenka FROM settings').fetchone()[0]
				cursor.execute('UPDATE users SET price_sms = (?) WHERE user_id = (?)', (0, call.from_user.id))
				conn.commit()
				conn.close()
				keyboard.add(*buttons)
				info = info.split(':')
				code = info[1]

				await bot.edit_message_reply_markup(chat_id = call.from_user.id, message_id = call.message.message_id, reply_markup = keyboard)
				await call.message.answer(f'<b>💬 Код:</b> <i>{code}</i>')
				#await bot.edit_message_text(chat_id = call.from_user.id, message_id = call.message.message_id, text = f'Код - {code}', reply_markup = keyboard)
				if service_name  == 'aw':
					service_name = 'SMS-ACTIWATOR'
				if service_name == 'vak':
					service_name = 'VAK-SMS'
				if service_name == 'act':
					service_name = 'SMS-ACTIVATE'
				if service_name == 'sim5':
					service_name = '5sim'
				await notif_admin_activate(order_id, service_name)
				#await bot.send_message(chat_id = admin, text = f'<b>✅ Куплен номер:</b>\n\n<b>Пользователь:</b> #{call.from_user.id}\n<b>Прибыль:</b> {nacenka} RUB\n\n<b>Сайт поставщика:</b> {service_name}' )
			if info == 'STATUS_WAIT_CODE' or info == 'STATUS_WAIT_RESEND':
				await call.answer(f'🕔 Ожидаем SMS',show_alert=False)
			else:
				print(info)
		except Exception as e:
			raise e
			await call.answer(f'⛔️ Ошибка, попробуйте позже',show_alert=False)
	except:
		await call.answer(f'⛔️ Ошибка, попробуйте позже',show_alert=False)



async def cancelSMS(call):
	service_info = call.data.split('|')
	order_id = service_info[1]
	service_name = service_info[2]
	try:
		conn = sqlite3.connect('db.db', check_same_thread = False)
		cursor = conn.cursor()
		row = cursor.execute('SELECT sms_activate, sms_actiwator, vak_sms, SIM5 FROM settings').fetchall()[0]
		SMS_ACTIVATE_TOKEN = row[0]
		SMS_ACTIWATOR_TOKEN = row[1]
		VAK_SMS_TOKEN = row[2]
		SIM5_TOKEN = row[3]
		if service_name == 'act':
			requests.get(f'{SMS_ACTIVATE_DOMEN}?api_key={SMS_ACTIVATE_TOKEN}&action=setStatus&status=6&id={order_id}')
		if service_name == 'aw':
			requests.get(f'{SMS_ACTIWATOR_DOMEN}?api_key={SMS_ACTIWATOR_TOKEN}&action=setStatus&status=6&id={order_id}')
		if service_name == 'vak':
			requests.get(f'{VAK_SMS_DOMEN}api_key={VAK_SMS_TOKEN}&action=setStatus&status=6&id={order_id}')
		if service_name == '5sim':
			requests.get(f'{SIM5_DOMEN}api_key={SIM5_TOKEN}&action=setStatus&status=6&id={order_id}')
		try:
			cursor.execute('DELETE FROM notif WHERE ids = ?', [order_id])
			conn.commit()
		except:
			pass
	except:
		pass
	finally:
		await bot.delete_message(chat_id = call.from_user.id, message_id = call.message.message_id)
		await main(call.from_user.id)



async def retrySMS(call):
	try:
		conn = sqlite3.connect('db.db', check_same_thread = False)
		cursor = conn.cursor()
		row = cursor.execute('SELECT sms_activate, sms_actiwator, vak_sms, SIM5 FROM settings').fetchall()[0]
		SMS_ACTIVATE_TOKEN = row[0]
		SMS_ACTIWATOR_TOKEN = row[1]
		VAK_SMS_TOKEN = row[2]
		SIM5_TOKEN = row[3]
		service_info = call.data.split('|')
		order_id = service_info[1]
		service_name = service_info[2]
		if service_name == 'act':
			info = requests.get(f'{SMS_ACTIVATE_DOMEN}?api_key={SMS_ACTIVATE_TOKEN}&action=setStatus&status=3&id={order_id}').text
		if service_name == 'aw':
			info = requests.get(f'{SMS_ACTIWATOR_DOMEN}?api_key={SMS_ACTIWATOR_TOKEN}&action=setStatus&status=3&id={order_id}').text
		if service_name == 'vak':
			info = requests.get(f'{VAK_SMS_DOMEN}api_key={VAK_SMS_TOKEN}&action=setStatus&status=3&id={order_id}').text
		if service_name == '5sim':
			info = requests.get(f'{SIM5_DOMEN}api_key={SIM5_TOKEN}&action=setStatus&status=3&id={order_id}').text

		if info == 'ACCESS_RETRY_GET':
			keyboard = types.InlineKeyboardMarkup(row_width = 2)
			buttons = [
			types.InlineKeyboardButton(text = 'Проверить смс', callback_data = f'сheck_retry_SMS|{order_id}|{service_name}'),
			types.InlineKeyboardButton(text = 'Отменить заказ', callback_data = f'cancelSMS|{order_id}|{service_name}')
			]
			keyboard.add(*buttons)
			await bot.edit_message_caption(chat_id = call.from_user.id, message_id = call.message.message_id, caption = f'{call.message.caption}\n<b>Ожидаем повторную смс...</b>', reply_markup = keyboard)
	except:
		await bot.edit_message_caption(chat_id = call.from_user.id, message_id = call.message.message_id, caption = '<b>Не удалось запросить повторную смс...</b>', reply_markup = keyboard)


async def check_retry_SMS (call):
	print(call.message.caption)
	try:
		conn = sqlite3.connect('db.db', check_same_thread = False)
		cursor = conn.cursor()
		row = cursor.execute('SELECT sms_activate, sms_actiwator, vak_sms, SIM5 FROM settings').fetchall()[0]
		SMS_ACTIVATE_TOKEN = row[0]
		SMS_ACTIWATOR_TOKEN = row[1]
		VAK_SMS_TOKEN = row[2]
		SIM5_TOKEN = row[3]
		service_info = call.data.split('|')
		order_id = service_info[1]
		service_name = service_info[2]
		#info = sa.getStatus(id = order_id)
		if service_name == 'act':
			try:
				info = requests.get(f'{SMS_ACTIVATE_DOMEN}api_key={SMS_ACTIWATOR_TOKEN}&action=getStatus&id={order_id}').text
			except:
				pass
		if service_name == 'aw':
			try:
				info = requests.get(f'{SMS_ACTIWATOR_DOMEN}api_key={SMS_ACTIWATOR_TOKEN}&action=getStatus&id={order_id}').text
			except:
				pass
		if service_name == 'vak':
			info = requests.get(f'{VAK_SMS_DOMEN}api_key={VAK_SMS_TOKEN}&action=getStatus&id={order_id}').text

		if service_name == '5sim':
			info = requests.get(f'{SIM5_DOMEN}api_key={SIM5_TOKEN}&action=getStatus&id={order_id}').text




		try:
			if info.startswith('STATUS_OK'):
				conn = sqlite3.connect('db.db', check_same_thread=False)
				cursor = conn.cursor()
				keyboard = types.InlineKeyboardMarkup(row_width = 2)
				buttons = [
				types.InlineKeyboardButton(text = '🔁 Повторная смс', callback_data = f'retrySMS|{order_id}|{service_name}'),
				types.InlineKeyboardButton(text = '⛔️ Завершить активацию', callback_data = f'cancelSMS|{order_id}|{service_name}'),
				]
				#cursor.execute('UPDATE users SET balance = balance - price_sms WHERE user_id = (?)', (call.from_user.id,))
				#cursor.execute('UPDATE users SET all_buy = all_buy + 1 WHERE user_id = (?)', (call.from_user.id,))
				#prices = cursor.execute('SELECT price_sms FROM users WHERE user_id = (?)', (call.from_user.id,)).fetchone()[0]
				#nacenka = cursor.execute('SELECT nacenka FROM nacenka_services WHERE ids = ?', [service_key]).fetchone()[0]
				#if nacenka == 0:
					#nacenka = cursor.execute('SELECT nacenka FROM settings').fetchone()[0]
				#cursor.execute('UPDATE users SET price_sms = (?) WHERE user_id = (?)', (0, call.from_user.id))
				#conn.commit()
				#conn.close()
				keyboard.add(*buttons)
				info = info.split(':')
				code = info[1]

				await bot.edit_message_reply_markup(chat_id = call.from_user.id, message_id = call.message.message_id, reply_markup = keyboard)
				await call.message.answer(f'<b>💬 Код:</b> <i>{code}</i>')
				#await bot.edit_message_text(chat_id = call.from_user.id, message_id = call.message.message_id, text = f'Код - {code}', reply_markup = keyboard)
				#if service_name  == 'aw':
					#service_name = 'SMS-ACTIWATOR'
				#if service_name == 'vak':
				#	service_name = 'VAK-SMS'
				#if service_name == 'act':
					#service_name = 'SMS-ACTIVATE'
				#await bot.send_message(chat_id = admin, text = f'<b>✅ Куплен номер:</b>\n\n<b>Пользователь:</b> #{call.from_user.id}\n</b>Прибыль:</b> {nacenka} RUB\n\n<b>Сайт поставщика:</b> {service_name}' )
			if info == 'STATUS_WAIT_CODE' or info == 'STATUS_WAIT_RESEND':
				await call.answer(f'🕔 Ожидаем SMS',show_alert=False)
			else:
				print(info)
		except Exception as e:
			raise e
			await call.answer(f'⛔️ Ошибка, попробуйте позже',show_alert=False)
	except:
		await call.answer(f'⛔️ Ошибка, попробуйте позже',show_alert=False)
		

#//////////////////////////////////////АРЕНДА\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

async def rent_service_info(call, time_rent, service_id, country_id):
	try:
		conn = sqlite3.connect('db.db', check_same_thread=False)
		cursor = conn.cursor()
		SMS_ACTIVATE_TOKEN = cursor.execute('SELECT sms_activate FROM settings').fetchone()[0]
		nacenka = cursor.execute('SELECT nacenka FROM nacenka_services WHERE ids = (?)', (service_id,)).fetchone()[0]
		if nacenka == 0:
			nacenka = cursor.execute('SELECT nacenka FROM settings').fetchone()[0]
		service = requests.get(f'{SMS_ACTIVATE_DOMEN}api_key={SMS_ACTIVATE_TOKEN}&action=getRentServicesAndCountries&rent_time={time_rent}&country={country_id}').json()
		print(service)
		quant = service['services'][service_id]['quant']['total']
		if quant != 0:
			cost = service['services'][service_id]['retail_cost']
			price = float(cost) + nacenka
			keyboard = types.InlineKeyboardMarkup(row_width = 2)
			buy_rent = types.InlineKeyboardButton(text = f'Арендовать | {round(price, 2)} RUB', callback_data = f'buy_rent_number|{service_id}|{country_id}|{time_rent}|')
			reset_serv = types.InlineKeyboardButton(text = 'Сменить сервис', callback_data = f'get_rent_service|{country_id}')
			back = types.InlineKeyboardButton(text = 'Назад', callback_data = f'set_rent_service|{service_id}|{country_id}')
			keyboard.add(buy_rent)
			keyboard.add(reset_serv, back)
			#await bot.edit_message_caption(chat_id = call.from_user.id, message_id = call.message.message_id, caption = f'<b>💴 Стоимость:</b> {price} RUB\n🗃 <b>Доступно номеров:</b>: {quant} шт', reply_markup = keyboard )
			await bot.edit_message_caption(chat_id = call.from_user.id, message_id=call.message.message_id, caption = f'<b>🌎 Страна:</b> {await get_name_country(country_id)}\n{line}\n<b>🔎 Оператор:</b> {await get_name_operator(call.from_user.id, country_id)}\n{line}\n<b>⏳ Услуга:</b> Аренда\n{line}\n<b>⚖️ Сервис:</b> {await get_name_service(country_id, service_id, "RENT")}\n{line}\n<b>⏱ Срок:</b> {await get_time_rent_name(time_rent)}',reply_markup = keyboard)
		
		else:
			await call.answer('⛔️ Нет доступных номеров')
	except:
		await call.answer('⛔️ Аренда недоступна для этого сервиса :(')


async def buy_rent_number(call, service_id, country_id, time_rent):
	conn = sqlite3.connect('db.db', check_same_thread=False)
	cursor = conn.cursor()
	SMS_ACTIVATE_TOKEN = cursor.execute('SELECT sms_activate FROM settings').fetchone()[0]
	nacenka = cursor.execute('SELECT nacenka FROM nacenka_services WHERE ids = ?',[service_id]).fetchone()[0]
	operator = cursor.execute('SELECT operator FROM users WHERE user_id = ?',[call.from_user.id]).fetchone()[0]
	if nacenka == 0:
		nacenka = cursor.execute('SELECT nacenka FROM settings').fetchone()[0]
	service_info = requests.get(f'{SMS_ACTIVATE_DOMEN}api_key={SMS_ACTIVATE_TOKEN}&action=getRentServicesAndCountries&rent_time={time_rent}&operator={operator}&country={country_id}').json()
	quant = service_info['services'][service_id]['quant']['total']

	if quant != 0:
		cost = service_info['services'][service_id]['retail_cost']
		price = float(cost) + nacenka
		balance = await get_user_balance(call.from_user.id)
		if balance >= price:
			rent_info = requests.get(f'{SMS_ACTIVATE_DOMEN}api_key={SMS_ACTIVATE_TOKEN}&action=getRentNumber&service={service_id}&rent_time={time_rent}&operator={operator}&country={country_id}').json()
			print(rent_info)
			if rent_info['status'] != 'error':
				cursor.execute('UPDATE users SET balance = balance - (?) WHERE user_id = (?)', (price, call.from_user.id,))
				cursor.execute('UPDATE most_buy_service SET score = score + 1 WHERE ids = (?)', (service_id,))
				conn.commit()
				number = rent_info['phone']['number']
				end_date = rent_info['phone']['endDate']
				ids = rent_info['phone']['id']
				cursor.execute('INSERT INTO rent_number (ids, user_id, how_sms, numbers, price) VALUES (?, ?, ?, ?, ?)', (ids, call.from_user.id, 0, number, price))
				cursor.execute('INSERT INTO notif (ids, user_id, number_, nacenka) VALUES (?, ?, ?, ?)',[ids, call.from_user.id, number, nacenka])
				conn.commit()
				keyboard = types.InlineKeyboardMarkup(row_width = 2)
				check_smsrent = types.InlineKeyboardButton(text = 'Проверить смс', callback_data = f'check_rent_sms|{ids}')
				otmena_rent = types.InlineKeyboardButton(text = 'Отменить аренду', callback_data = f'otmena_rent_sms|{ids}')
				menu = types.InlineKeyboardButton(text = 'В меню', callback_data = 'menu')
				keyboard.add(check_smsrent, otmena_rent)
				keyboard.add(menu)
				await bot.edit_message_caption(chat_id = call.from_user.id, message_id = call.message.message_id, caption = f'<b>Номер:</b> <code>+{number}</code>\nДата окончания: {end_date}', reply_markup = keyboard)
				#await bot.send_message(chat_id = admin, text = f'<b>⏳ Арендован номер:</b>\n\n<b>Пользователь:</b> #{call.from_user.id}\n<b>Номер:</b> {number}\n<b>Прибыль:</b> {nacenka} RUB\n\n<b>Сайт поставщика:</b> SMS-ACTIVATE' )
			else:
				admin_status_error = rent_info['status']
				admin_message_error = rent_info['message']
				await bot.send_message(admin, text = f'Ошибка аренды номера:\nСтатус - {admin_status_error}\n\nТекст ошибки:\n{admin_message_error}')
				await call.answer('⛔️ Попробуйте позже')
		else:
			await call.answer('⛔️ Не хватает баланса')
	else:
		await call.answer('⛔️ Нет доступных номеров, попробуйте сменить оператора')


async def check_rent_sms(call, ids):
	conn = sqlite3.connect('db.db', check_same_thread=False)
	cursor = conn.cursor()
	SMS_ACTIVATE_TOKEN = cursor.execute('SELECT sms_activate FROM settings').fetchone()[0]
	status = requests.get(f'{SMS_ACTIVATE_DOMEN}api_key={SMS_ACTIVATE_TOKEN}&action=getRentStatus&id={ids}').json()
	await notif_admin_rent(ids)
	if status['status'] == 'error' and status['message'] == 'STATUS_WAIT_CODE':
		await call.answer('🕔 Ожидаем код')
	if status['status'] == 'success' and int(status['quantity']) > 0:
		try:
			sms_number = cursor.execute('SELECT how_sms FROM rent_number WHERE ids = (?)', (ids,)).fetchone()[0]
			#print(status['values'][f'{sms_number}']['text'])
			await bot.edit_message_caption(chat_id = call.from_user.id, message_id = call.message.message_id, caption = status['values'][f'{sms_number}']['text'])
			cursor.execute('UPDATE rent_number SET how_sms = how_sms + 1 WHERE ids = (?)', (ids,))
			conn.commit()
			if sms_number == 0:
				cursor.execute('UPDATE users SET all_buy = all_buy + 1 WHERE user_id = (?)', (call.from_user.id,))
				conn.commit()
		except:
			await call.answer('🕔 Ожидаем код')

async def cancel_rent_sms(call, ids):
	conn = sqlite3.connect('db.db', check_same_thread=False)
	cursor = conn.cursor()
	SMS_ACTIVATE_TOKEN = cursor.execute('SELECT sms_activate FROM settings').fetchone()[0]
	status = requests.get(f'{SMS_ACTIVATE_DOMEN}api_key={SMS_ACTIVATE_TOKEN}&action=setRentStatus&id={ids}&status=2')

	print(status)
	try:
		if status['status'] == 'success':
			price = cursor.execute('SELECT price FROM rent_number WHERE ids = (?)', (ids,)).fetchone()[0]
			cursor.execute('UPDATE users SET balance = balance + (?) WHERE user_id = (?)',(price, call.from_user.id,))
			conn.commit()
			cursor.execute('DELETE FROM rent_number WHERE ids = (?)', (ids,))
			cursor.execute('DELETE FROM notif WHERE ids = ?', [int(ids)])
			conn.commit()
			keyboard = types.InlineKeyboardMarkup(row_width = 1)
			mains = types.InlineKeyboardButton(text = 'В меню', callback_data = 'menu')
			keyboard.add(main)
			await bot.edit_message_caption(chat_id = call.from_user.id, message_id = call.message.message_id, caption = '⛔️ Аренда отменена', reply_markup = keyboard)
		if status['status'] == 'error' and status['message'] == 'CANT_CANCEL':
			await call.answer('⛔️ Отмена аренды возможна в течении 20 минут после покупки!')
		else:
			pass
	except:
		await bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)
		await main(call.from_user.id)


async def get_name_country(i):
	name = COUNTRY.get(i)
	return name

async def get_name_operator(us_id, country_id):
	conn = sqlite3.connect('db.db', check_same_thread = False)
	cursor = conn.cursor()
	operator_value = cursor.execute('SELECT operator FROM users WHERE user_id = ?',[us_id]).fetchone()[0]
	OP_KEY = OPERATORS.get(str(country_id))
	name = OP_KEY.get(operator_value)
	return name

async def get_name_service(country_id, service_id, DICT_NAME):
	if DICT_NAME == 'SERVICE':
		SR_KEY = SERVICE.get(str(country_id))
	else:
		SR_KEY = RENT_SERVICE.get(str(country_id))
	name = SR_KEY.get(service_id)
	return name

async def get_time_rent_name(i):
	dict_times = {
	'4':'4 часа',
	'12':'12 часов',
	'24':'1 день',
	'72':'3 дня',
	'168':'1 неделя',
	'336':'2 недели',
	}
	name = dict_times.get(str(i))
	return name

async def notif_admin_rent(ids):
	conn = sqlite3.connect('db.db', check_same_thread = False)
	cursor = conn.cursor()
	print(ids)
	try:
		row = cursor.execute('SELECT user_id, number_, nacenka FROM notif WHERE ids = ?',[ids]).fetchone()
		print(row)
		user_id = row[0]
		number = row[1]
		nacenka = row[2]
		await bot.send_message(chat_id = LOG_DIALOG, text = f'<b>⏳ Арендован номер:</b>\n\n<b>Пользователь:</b> #{user_id}\n<b>Номер:</b> {number}\n<b>Прибыль:</b> {nacenka} RUB\n\n<b>Сайт поставщика:</b> SMS-ACTIVATE' )
		cursor.execute('UPDATE users SET all_buy = all_buy + 1 WHERE user_id = (?)', (user_id,))
		cursor.execute('DELETE FROM notif WHERE ids = ?', [ids])
		conn.commit()
	except:
		pass

async def notif_admin_activate(ids, site_api):
	conn = sqlite3.connect('db.db', check_same_thread = False)
	cursor = conn.cursor()
	print(ids)
	try:
		row = cursor.execute('SELECT user_id, number_, nacenka FROM notif WHERE ids = ?',[ids]).fetchone()
		print(row)
		user_id = row[0]
		number = row[1]
		nacenka = row[2]
		await bot.send_message(chat_id = LOG_DIALOG, text = f'<b>✅ Куплен номер:</b>\n\n<b>Пользователь:</b> #{user_id}\n<b>Номер:</b> {number}\n<b>Прибыль:</b> {nacenka} RUB\n\n<b>Сайт поставщика:</b> {site_api}' )
		cursor.execute('DELETE FROM notif WHERE ids = ?', [ids])
		conn.commit()
	except:
		pass

#///////////////////////////////ПОПОЛНЕНИЕ\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
async def QIWI_PAY(summa, user_id):
	try:
		conn = sqlite3.connect('db.db', check_same_thread=False)
		cursor = conn.cursor()
		cursor.execute('SELECT QIWI_KEY FROM settings')
		QIWI_KEY = cursor.fetchone()[0]
		conn.close()
		qid = random.randint(1111111, 9999999)
		p2p = QiwiP2P(auth_key=QIWI_KEY)
		new_bill = p2p.bill(bill_id=qid, amount=summa, lifetime=30, comment = COMMENT_QIWI)
		keyboard = types.InlineKeyboardMarkup(row_width = 2)
		buttons = [
		types.InlineKeyboardButton(text = "🏦 Оплатить", url = new_bill.pay_url),
		types.InlineKeyboardButton(text="🔎 Проверить", callback_data=f'CheckQiwi_{qid}'),
		types.InlineKeyboardButton(text = "Меню", callback_data = 'menu')
		]
		keyboard.add(*buttons)
		await bot.send_photo(chat_id = user_id, photo=MENU_IMAGE, caption = f'<b>💴 Сумма к оплате:</b> <i>{summa}</i> <b>RUB</b>\n<i>🗽 Для оплаты нажмите кнопку "Оплатить"</i>', reply_markup = keyboard)
	except Exception as e:
		await bot.send_message(chat_id = admin, text = f'Ошибка пополнения QIWI:\n{e}')
		await bot.send_message(chat_id = user_id, text ='<b>😢 Киви кошелек сломан...</b>\nМы уже занимаемся этим вопросом')
		await main(user_id)


#///////////////////////////////////////////////ИЗБРАННОЕ\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

async def add_favorite(call):
	#print(call.message.reply_markup)
	#print(call.message.reply_markup.inline_keyboard[0][0])
	conn = sqlite3.connect('db.db', check_same_thread=False)
	cursor = conn.cursor()
	infolist = call.data.split('|')
	service_id = infolist[1]
	country_id = infolist[2]
	in_fav = cursor.execute('SELECT user_id FROM favorite_service WHERE user_id = ? AND country = ? AND service = ?',[call.from_user.id, country_id, service_id]).fetchone()
	if in_fav == None:
		cursor.execute('INSERT INTO favorite_service (user_id, service, country) VALUES (?, ?, ?)',[call.from_user.id, service_id, country_id])
		conn.commit()
		ftext = '⭐️ Удалить из избранного'
	else:
		cursor.execute('DELETE FROM favorite_service WHERE user_id = ? AND country = ? AND service = ?',[call.from_user.id, country_id, service_id])
		conn.commit()
		ftext = '⭐️ В избранное'
	keyboard = types.InlineKeyboardMarkup(row_width = 2)
	keyboard.add(
		call.message.reply_markup.inline_keyboard[0][0],
		types.InlineKeyboardButton(text = ftext, callback_data = f'add_fav|{service_id}|{country_id}'),
		)
	#keyboard.add(*call.message.reply_markup.inline_keyboard[1])
	await bot.edit_message_reply_markup(chat_id = call.from_user.id, message_id = call.message.message_id, reply_markup = keyboard)

async def get_favorite(message):
	conn = sqlite3.connect('db.db', check_same_thread = False)
	cursor = conn.cursor()
	list_serv = cursor.execute('SELECT * FROM favorite_service WHERE user_id = ?', [message.from_user.id]).fetchall()
	print(list_serv)
	keyboard = types.InlineKeyboardMarkup(row_width = 2)
	btns = []
	for s in list_serv:
		serv = s[1]
		ctr = s[2]
		s_list = SERVICE.get(str(ctr))
		service = s_list.get(serv)
		flag = COUNTRY.get(str(ctr))[:2]
		btns.append(
			types.InlineKeyboardButton(text = f'{flag} | {service}', callback_data=f'set_service|{serv}|{ctr}')
			)
	keyboard.add(*btns)
	await bot.send_photo(chat_id = message.from_user.id, photo = MENU_IMAGE, caption = '<b>Выберите сервис:</b>', reply_markup = keyboard)


#///////////////////////////////////////////////////АДМИНМЕНЮ\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
def get_site_balance(url):
	balance = requests.get(url.split('|')[1]).text
	try:
		balance = balance.split(':')[1] + ' RUB'
		if 'feedback' in balance:
			balance = '-'
		#print(balance)
	except:
		balance = '-'
	return url.split('|')[0], balance


async def adminmenu(user_id):
	conn = sqlite3.connect('db.db', check_same_thread=False)
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(1) FROM users")
	all_users = cursor.fetchone()[0]
	#b = cursor.execute('SELECT service, MAX(score) FROM most_buy_service').fetchone()
	#list_top = cursor.execute('SELECT * FROM most_buy_service ORDER BY score DESC  LIMIT 3').fetchall()
	#text_top = ''
	#for i in list_top:
		#name = i[0]
		#kolv = i[2]
		#text_top = text_top + f'<b>📀 {name}</b>: <i>{kolv} раз(а)</i>\n'	
	all_balance = cursor.execute('SELECT SUM(balance) FROM users').fetchone()[0]
	all_buy = cursor.execute('SELECT SUM(all_buy) FROM users').fetchone()[0]
	all_deposit = cursor.execute('SELECT SUM(all_deposit) FROM users').fetchone()[0]
	nacenka = cursor.execute('SELECT nacenka FROM settings').fetchone()[0]
	keys = cursor.execute('SELECT vak_sms, sms_activate, sms_actiwator, SIM5 FROM settings').fetchmany()[0]
	link_balance = [
	'act|{0}api_key={1}&action=getBalance'.format(SMS_ACTIVATE_DOMEN, keys[1]),
	'vak|{0}api_key={1}&action=getBalance'.format(VAK_SMS_DOMEN, keys[0]),
	'aw|{0}api_key={1}&action=getBalance'.format(SMS_ACTIWATOR_DOMEN, keys[2]),
	'sim5|{0}api_key={1}&action=getBalance'.format(SIM5_DOMEN, keys[3]),



	]
	conn.close()
	pool = ThreadPool()
	results = pool.map(get_site_balance, link_balance)
	dict_balance = {}
	for i in results:
		dict_balance.update({i[0]:i[1]})
	await bot.send_message(chat_id = user_id, text = 
f'''
{line}
🙆‍♂️ <b>Количество пользователей:</b> <i>{all_users} шт</i>
💸 <b>Внесено средств:</b> <i>{all_deposit} RUB</i>
🏦 <b>Общий баланс:</b> <i>{all_balance} RUB</i>
🔎 <b>Куплено номеров:</b> <i>{all_buy} шт</i>
🔗 <b>Глобальная наценка:</b> <i>{nacenka} RUB</i>
{line}
<b>🌎 Балансы сайтов:</b>
<b><i>▫️ SMS-ACTIVATE:</i></b> {dict_balance.get('act')}
<b><i>▫️ VAK-SMS:</i></b> {dict_balance.get('vak')}
<b><i>▫️ SMS-ACKTIWATOR:</i></b> {dict_balance.get('aw')}
<b><i>▫️ 5SIM:</i></b> {dict_balance.get('sim5')}
{line}


''', reply_markup = await admin_keyboard())


async def check_channel(us_id):
	in_channel = await bot.get_chat_member(chat_id = NEWS_ID, user_id=us_id)
	if in_channel["status"] != 'left':
		return True
	else:
		return False