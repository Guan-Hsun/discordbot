import discord
from discord.ext import commands
import random
import datetime

from json_manager import load_json, save_json

DATA_FILE = "data.json"


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def check_and_reset_daily(self, data):
        today = datetime.date.today().strftime("%Y%m%d")
        if data.get("日期") != today:
            data["日期"] = today
            data["今日簽到"] = []
        return data

    @commands.command(aliases=["介面", "積分"])
    async def 面板(self, ctx):
        data = load_json(DATA_FILE)
        user_id = str(ctx.author.id)

        if user_id not in data:
            data[user_id] = {
                "名字": str(ctx.author),
                "等級": 0,
                "經驗值": 0,
                "傑尼幣": 50,
            }
            save_json(DATA_FILE, data)
            await ctx.reply(f"🎉 {ctx.author.mention} 歡迎加入 ***獵人X獵人***！")
        else:
            user_data = data[user_id]
            lvl = user_data.get("等級", 0)
            exp = user_data.get("經驗值", 0)
            money = user_data.get("傑尼幣", 0)

            # 依照要求的順序：等級、經驗值、傑尼幣
            desc = f"**等級**：{user_data['等級']}\n**經驗值**：{user_data['經驗值']}\n**傑尼幣** <:emoji_1:1127882888508088393>：{user_data['傑尼幣']}"

            embed = discord.Embed(
                title=f"👤 {user_data.get('名字', ctx.author.name)} 的獵人執照",
                description=desc,
                color=0x2ECC71,  # 綠色
            )
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            await ctx.reply(embed=embed)

    @commands.command()
    async def 簽(self, ctx):
        data = load_json(DATA_FILE)
        user_id = str(ctx.author.id)
        data = self.check_and_reset_daily(data)

        if user_id not in data:
            await ctx.reply(f"{ctx.author.mention} 你還沒註冊嗎>< (請先輸入 `!面板`)")
            return

        if user_id in data.get("今日簽到", []):
            await ctx.reply(f"{ctx.author.mention} 你今天已經簽到過了~")
            return

        data["今日簽到"].append(user_id)
        data[user_id]["經驗值"] = data[user_id].get("經驗值", 0) + 2
        data[user_id]["傑尼幣"] = data[user_id].get("傑尼幣", 0) + 50

        reply_msg = (
            f"{ctx.author.mention} 獲得簽到獎勵 給你 50 <:emoji_1:1127882888508088393>"
        )

        if random.random() < 0.3:
            data[user_id]["傑尼幣"] += 20
            data[user_id]["經驗值"] += 1
            reply_msg += "\n✨ **你今天是幸運寶貝！額外再給你 20** <:emoji_1:1127882888508088393>"

        save_json(DATA_FILE, data)
        await ctx.reply(reply_msg)

    @commands.command()
    async def 傑尼傑尼(self, ctx, member: discord.Member, amount: int):
        if ctx.author.id != 955832536414715934:
            await ctx.reply("❌ 只有管理員可以使用此指令喔！")
            return

        data = load_json(DATA_FILE)
        target_id = str(member.id)

        if target_id not in data:
            await ctx.reply("❌ 這位使用者還沒註冊成為獵人！")
            return

        # 把原本的數值加上 amount (若是負數就會自動扣除)
        current_money = data[target_id].get("傑尼幣", 0)
        data[target_id]["傑尼幣"] = max(0, current_money + amount)
        save_json(DATA_FILE, data)

        # 根據正負數給予不同的提示文案
        action = "發送了" if amount >= 0 else "扣除了"
        await ctx.reply(
            f"💸 已成功向 {member.mention} **{action}** {abs(amount)} <:emoji_1:1127882888508088393>！"
        )

    @傑尼傑尼.error
    async def 傑尼傑尼_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(
            error, commands.BadArgument
        ):
            await ctx.reply(
                "⚠️ **格式錯誤！**\n正確用法：`!調整傑尼幣 @使用者 數量` (數量輸入負數即可扣錢)\n範例：`!調整傑尼幣 @阿勳 500` 或 `!調整傑尼幣 @阿勳 -200`"
            )

    @commands.command()
    async def 經驗經驗(self, ctx, member: discord.Member, amount: int):
        if ctx.author.id != 955832536414715934:
            await ctx.reply("❌ 只有管理員可以使用此指令喔！")
            return

        data = load_json(DATA_FILE)
        target_id = str(member.id)

        if target_id not in data:
            await ctx.reply("❌ 這位使用者還沒註冊成為獵人！")
            return

        current_exp = data[target_id].get("經驗值", 0)
        data[target_id]["經驗值"] = max(0, current_exp + amount)
        save_json(DATA_FILE, data)

        action = "增加了" if amount >= 0 else "扣除了"
        await ctx.reply(
            f"🌟 已成功向 {member.mention} **{action}** {abs(amount)} 點經驗值！\n他目前的經驗值為：**{data[target_id]['經驗值']}**"
        )

    @經驗經驗.error
    async def 經驗經驗_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(
            error, commands.BadArgument
        ):
            await ctx.reply(
                "⚠️ **格式錯誤！**\n正確用法：`!調整經驗 @使用者 數量` (數量輸入負數即可扣除)\n範例：`!調整經驗 @阿勳 100` 或 `!調整經驗 @阿勳 -50`"
            )


async def setup(bot):
    await bot.add_cog(Economy(bot))
