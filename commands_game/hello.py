from discord.ext import commands
import random

class Hello(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['hi', '你好'])
    async def hello(self, ctx):
        responses = [
            "Hello World！我現在醒著！",
            "hi",
            f"{ctx.author.mention} 嗨屁嗨！",
            f"Hello {ctx.author.mention}！",
            f"{ctx.author.mention} 哈囉！今天天氣如何？",
        ]

        reply = random.choice(responses)
        await ctx.reply(reply)
        # await ctx.send(reply)

async def setup(bot):
    await bot.add_cog(Hello(bot))
