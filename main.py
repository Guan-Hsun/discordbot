import os
import time
import asyncio
from dotenv import load_dotenv
from keep_alive import keep_alive

from bot import bot
from bot_game import bot_game

os.environ["TZ"] = "Asia/Taipei"
time.tzset()

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")  # 個人伺服器
TOKEN_game = os.getenv("DISCORD_TOKEN_game")  # 朋友伺服器

START_BOT = True
START_BOT_game = True


async def run_bots():
    tasks = []

    # 檢查開關 1
    if START_BOT:
        if TOKEN:
            print("⏳ 準備在個人伺服器啟動機器人 ...")
            tasks.append(bot.start(TOKEN))

    # 檢查開關 2
    if START_BOT_game:
        if TOKEN_game:
            print("⏳ 準備在朋友伺服器啟動機器人 ...")
            tasks.append(bot_game.start(TOKEN_game))

    # 如果兩個開關都是 False
    if not tasks:
        print("🛑 沒有選擇啟動任何機器人，程式結束。")
        return

    # 使用 *tasks 將清單解包，並同時執行所有被選中的機器人
    await asyncio.gather(*tasks)


# 啟動保持喚醒的網頁
keep_alive()

# 執行非同步主程式
try:
    asyncio.run(run_bots())
except KeyboardInterrupt:
    print("\n🛑 程式已手動停止。")
