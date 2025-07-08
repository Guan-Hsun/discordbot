import os
from dotenv import load_dotenv
from keep_alive import keep_alive
from bot import bot

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

keep_alive()
bot.run(TOKEN)
