import os
import time
from dotenv import load_dotenv
from keep_alive import keep_alive
from bot import bot

os.environ['TZ'] = 'Asia/Taipei'
time.tzset()

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

keep_alive()
bot.run(TOKEN)
