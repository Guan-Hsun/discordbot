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

    @commands.hybrid_command(name="profile", aliases=["面板", "介面", "積分"], description="查看你的獵人執照，若經驗足夠將自動升級")
    async def profile(self, ctx: commands.Context):
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
            await ctx.reply(f"🎉 {ctx.author.mention} 歡迎加入 ***獵人X獵人***！已為你建立專屬執照。")
            return

        user_data = data[user_id]
        lvl = user_data.get("等級", 0)
        exp = user_data.get("經驗值", 0)

        # 🚀 升級結算邏輯
        leveled_up = False
        while True:
            cost = 32 * (2 ** lvl) # 升級所需經驗：32, 64, 128...
            if exp >= cost:
                exp -= cost
                lvl += 1
                leveled_up = True
            else:
                break

        # 如果有升級，存檔並準備恭喜訊息
        congrats_msg = ""
        if leveled_up:
            user_data["等級"] = lvl
            user_data["經驗值"] = exp
            save_json(DATA_FILE, data)
            congrats_msg = f"🎊 **恭喜 {ctx.author.mention} 升級到了 Lv.{lvl}！**\n(接下來簽到可以獲得更多獎勵囉！)\n\n"

        money = user_data.get("傑尼幣", 0)
        next_lvl_cost = 32 * (2 ** lvl)

        desc = f"**等級**：Lv.{lvl}\n**經驗值**：{exp} / {next_lvl_cost}\n**傑尼幣** <:emoji_1:1127882888508088393>：{money}"

        embed = discord.Embed(
            title=f"👤 {user_data.get('名字', ctx.author.name)} 的獵人執照",
            description=desc,
            color=0x2ECC71,  
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        # 組合訊息送出
        await ctx.reply(content=congrats_msg if congrats_msg else None, embed=embed)

    @commands.hybrid_command(name="daily", aliases=["簽到", "簽"], description="每日簽到領取薪水，等級越高領越多！")
    async def daily(self, ctx: commands.Context):
        data = load_json(DATA_FILE)
        user_id = str(ctx.author.id)
        data = self.check_and_reset_daily(data)

        if user_id not in data:
            await ctx.reply(f"{ctx.author.mention} 你還沒註冊嗎>< (請先輸入 `/profile` 建立執照)", ephemeral=True)
            return

        if user_id in data.get("今日簽到", []):
            await ctx.reply(f"{ctx.author.mention} ⚠️ 你今天已經簽到過了，明天再來吧！", ephemeral=True)
            return

        lvl = data[user_id].get("等級", 0)

        # 💰 根據等級計算倍率 (0等=1倍, 1等=2倍, 2等=4倍...)
        multiplier = 2 ** lvl
        base_coins = 50 * multiplier
        base_exp = 1 * multiplier

        data["今日簽到"].append(user_id)
        data[user_id]["經驗值"] = data[user_id].get("經驗值", 0) + base_exp
        data[user_id]["傑尼幣"] = data[user_id].get("傑尼幣", 0) + base_coins

        reply_msg = (
            f"✅ {ctx.author.mention} 簽到成功！\n"
            f"獲得了 **{base_coins}** <:emoji_1:1127882888508088393> 與 **{base_exp}** 🌟 經驗值。"
        )

        # 幸運寶貝額外加碼 (依照倍率加給)
        if random.random() < 0.1:
            data[user_id]["傑尼幣"] += base_coins
            data[user_id]["經驗值"] += base_exp
            reply_msg += f"\n✨ **你今天是幸運寶貝！額外再翻倍給你 {base_coins}** <:emoji_1:1127882888508088393>"

        save_json(DATA_FILE, data)
        await ctx.reply(reply_msg)

    # ==========================================
    # 以下為管理員專用指令 (維持傳統前綴指令)
    # ==========================================

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

        current_money = data[target_id].get("傑尼幣", 0)
        data[target_id]["傑尼幣"] = max(0, current_money + amount)
        save_json(DATA_FILE, data)

        action = "發送了" if amount >= 0 else "扣除了"
        await ctx.reply(f"💸 已成功向 {member.mention} **{action}** {abs(amount)} <:emoji_1:1127882888508088393>！")

    @傑尼傑尼.error
    async def 傑尼傑尼_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            await ctx.reply("⚠️ **格式錯誤！**\n正確用法：`!傑尼傑尼 @使用者 數量` (數量輸入負數即可扣錢)")

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
        await ctx.reply(f"🌟 已成功向 {member.mention} **{action}** {abs(amount)} 點經驗值！\n他目前的經驗值為：**{data[target_id]['經驗值']}**")

    @經驗經驗.error
    async def 經驗經驗_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            await ctx.reply("⚠️ **格式錯誤！**\n正確用法：`!經驗經驗 @使用者 數量` (數量輸入負數即可扣除)")

async def setup(bot):
    await bot.add_cog(Economy(bot))