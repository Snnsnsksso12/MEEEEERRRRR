from aiogram.utils import executor
from aiogram import Bot, types
from initBot import bot, dp
from data.db import db, cursor
from handlers.other import register_handlers_other
# НЕ ТРОГАТЬ ЭТОТ ФАЙЛ!!! хорошо
from handlers.searching import register_handlers_searching
from handlers.searching import register_handlers_searching
import keep_alive

register_handlers_other(dp)
register_handlers_searching(dp)

async def onStartup(_):
  cursor.execute("""CREATE TABLE IF NOT EXISTS users (
      user_id INTEGRAL
  )""")
  db.commit()
    
#keep_alive.keep_alive()
executor.start_polling(dp, skip_updates=True, on_startup=onStartup)