import random
from discord.ext import commands

class Hello(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="hello", aliases=['hi', '你好'], description="跟機器人打聲招呼！")
    async def hello(self, ctx: commands.Context):
        responses = [
            "Hello World！我現在醒著！",
            "hi",
            f"{ctx.author.mention} 嗨屁嗨！",
            f"Hello {ctx.author.mention}！",
            f"{ctx.author.mention} 哈囉！今天天氣如何？",
        ]

        reply = random.choice(responses)
        await ctx.reply(reply)

async def setup(bot):
    await bot.add_cog(Hello(bot))