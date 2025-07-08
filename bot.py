from discord.ext import commands
import discord
import os

intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 自動載入所有 commands/*.py 模組
        for filename in os.listdir("./commands"):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = f"commands.{filename[:-3]}"
                try:
                    await self.load_extension(module_name)
                    print(f"✅ 已載入模組：{module_name}")
                except Exception as e:
                    print(f"❌ 載入 {module_name} 失敗：{e}")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"✅ Bot 上線啦！帳號：{bot.user}")
