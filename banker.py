import asyncio
import sqlite3
from telethon import TelegramClient, events
from config import TG_API_ID, TG_API_HASH,TOKEN, LOG_DIALOG
from aiogram import Bot, types
from func import main

bot = Bot(TOKEN, parse_mode=types.ParseMode.HTML)


async def get_check(message, check):
	us_id = message.from_user.id
	client = TelegramClient(session="SESSION", api_id=TG_API_ID, api_hash=TG_API_HASH, app_version="version 0.0.1", device_model="Windows Phone", system_version="Windows 8")
	conn = sqlite3.connect('db.db', check_same_thread=False)
	cursor = conn.cursor()
	try:
		await client.start()
		await client.send_message('BTC_CHANGE_BOT', f"/start {check}")
		@client.on(events.NewMessage(chats=('BTC_CHANGE_BOT')))
		async def check_info(event):
			message = event.message.text
			if 'Упс, кажется, данный чек успел обналичить кто-то другой' in message:
				await bot.send_message(chat_id = us_id, text = 'Чек уже обналичен!')
				await client.disconnect()
			if 'Вы получили' in message:
				sums = message.split('(')
				sums = sums[1].split(')')
				sums = sums[0].split(' ')
				sums = sums[0]
				cursor.execute('UPDATE users SET balance = balance + (?) WHERE user_id = (?)', (sums, us_id))
				cursor.execute('UPDATE users SET all_deposit = all_deposit + (?) WHERE user_id = (?)', (sums, us_id,))
				conn.commit()
				conn.close()			
				await bot.send_message(chat_id = us_id, text = f'Баланс пополнен на {sums} RUB!')
				await bot.send_message(chat_id = LOG_DIALOG, text=f'''
💸 <b>Новое пополнение!</b>

<i>👨‍💻 Пользователь:
	1) Юзернейм: {message.from_user.username}
	2) id: {message.from_user.id}

💰 Сумма: {sums} RUB

🤖 Способ пополнения: BTC BANKER</i>




					''')
				await client.disconnect()
			else:
				pass
		#await client.run_until_disconnected()
		#await asyncio.sleep(3)
	except:
		pass
		#await client.run_until_disconnected()
		#await asyncio.sleep(3)
	finally:
		#conn.close()
		await client.run_until_disconnected()
		#await asyncio.sleep(3)


	#asyncio.sleep(1)