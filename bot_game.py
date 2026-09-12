from discord.ext import commands
import discord
import os

intents = discord.Intents.default()
intents.message_content = True

class GameBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=["!", "！"], intents=intents)

    async def setup_hook(self):
        # 自動載入 commands_game 資料夾底下的所有模組
        for filename in os.listdir("./commands_game"):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = f"commands_game.{filename[:-3]}"
                try:
                    await self.load_extension(module_name)
                    print(f"🎮 已載入遊戲模組：{module_name}")
                except Exception as e:
                    print(f"❌ 載入 {module_name} 失敗：{e}")

        try:
            synced = await self.tree.sync()
            print(f"🎮 已全域同步 {len(synced)} 個斜線指令")
        except Exception as e:
            print(f"❌ 指令樹全域同步失敗：{e}")

bot_game = GameBot()

@bot_game.event
async def on_ready():
    print(f"🎮 朋友伺服器 Bot 上線啦！帳號：{bot_game.user}")