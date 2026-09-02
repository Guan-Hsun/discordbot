import discord
from discord.ext import commands
import random

from json_manager import load_json, save_json

DATA_FILE = "data.json"

# ==========================================
# ✌️✊🖐️ 猜拳專用互動面板 View
# ==========================================
class RPSView(discord.ui.View):
    def __init__(self, ctx, opponent, is_bot):
        super().__init__(timeout=60.0) # 60 秒沒出拳就超時取消
        self.ctx = ctx
        self.p1 = ctx.author
        self.p2 = opponent
        self.is_bot = is_bot
        self.message = None

        # 紀錄雙方的出拳 (None 代表還沒出)
        self.choices = {self.p1.id: None}

        if self.is_bot:
            # 如果對手是機器人，它一開始就先偷偷選好了
            self.choices[self.p2.id] = random.choice(["✊", "🖐️", "✌️"])
        else:
            # 如果是玩家對戰，等待對方出拳
            self.choices[self.p2.id] = None

    async def process_choice(self, interaction: discord.Interaction, choice_str: str):
        user_id = interaction.user.id

        # 1. 檢查按按鈕的人是不是參戰玩家
        if user_id not in [self.p1.id, self.p2.id]:
            return await interaction.response.send_message("❌ 你不在這場對決中，去旁邊看戲！", ephemeral=True)

        # 2. 檢查是不是已經出過拳了
        if self.choices[user_id] is not None:
            return await interaction.response.send_message("⚠️ 你已經出過拳了，請保密並耐心等待結果！", ephemeral=True)

        # 3. 紀錄出拳
        self.choices[user_id] = choice_str

        # 4. 判斷遊戲是否結束
        if None in self.choices.values():
            # 還有一個人沒出拳
            await interaction.response.send_message(f"🤫 你悄悄地出了 **{choice_str}**！請等待對手...", ephemeral=True)
        else:
            # 雙方都出拳了，準備開牌！
            await interaction.response.send_message(f"🤫 你出了 **{choice_str}**！對決結束，準備開牌！", ephemeral=True)
            await self.resolve_game()

    @discord.ui.button(label="石頭 ✊", style=discord.ButtonStyle.secondary)
    async def btn_rock(self, interaction, button):
        await self.process_choice(interaction, "✊")

    @discord.ui.button(label="布 🖐️", style=discord.ButtonStyle.secondary)
    async def btn_paper(self, interaction, button):
        await self.process_choice(interaction, "🖐️")

    @discord.ui.button(label="剪刀 ✌️", style=discord.ButtonStyle.secondary)
    async def btn_scissors(self, interaction, button):
        await self.process_choice(interaction, "✌️")

    async def resolve_game(self):
        # 鎖死所有按鈕
        for child in self.children:
            child.disabled = True

        c1 = self.choices[self.p1.id]
        c2 = self.choices[self.p2.id]

        # 勝負判定字典 (key 贏 value)
        win_map = {"✊": "✌️", "✌️": "🖐️", "🖐️": "✊"}

        if c1 == c2:
            result = 0 # 平手
        elif win_map[c1] == c2:
            result = 1 # P1 贏
        else:
            result = 2 # P2 贏

        # 處理結算與 JSON 存檔
        data = load_json(DATA_FILE)

        # ⚠️ 最終防呆：在扣錢前，再次檢查雙方餘額有沒有人在這 60 秒內把錢花光了
        if data.get(str(self.p1.id), {}).get("傑尼幣", 0) < 10:
            embed = discord.Embed(title="🛑 對決取消", description=f"{self.p1.mention} 餘額不足 10 傑尼幣，交易失敗！", color=0xe74c3c)
            return await self.message.edit(embed=embed, view=self)

        if not self.is_bot and data.get(str(self.p2.id), {}).get("傑尼幣", 0) < 10:
            embed = discord.Embed(title="🛑 對決取消", description=f"{self.p2.mention} 餘額不足 10 傑尼幣，交易失敗！", color=0xe74c3c)
            return await self.message.edit(embed=embed, view=self)

        # 分發獎勵與扣款
        if result == 1:
            data[str(self.p1.id)]["傑尼幣"] += 10
            data[str(self.p1.id)]["經驗值"] = data[str(self.p1.id)].get("經驗值", 0) + 1
            if not self.is_bot:
                data[str(self.p2.id)]["傑尼幣"] -= 10
            winner = self.p1
        elif result == 2:
            if not self.is_bot:
                data[str(self.p2.id)]["傑尼幣"] += 10
                data[str(self.p2.id)]["經驗值"] = data[str(self.p2.id)].get("經驗值", 0) + 1
            data[str(self.p1.id)]["傑尼幣"] -= 10
            winner = self.p2

        save_json(DATA_FILE, data)

        # 製作結果卡片
        embed = discord.Embed(title="⚔️ 猜拳對決結果", color=0x3498db)
        embed.add_field(name=f"{self.p1.display_name}", value=f"出拳：**{c1}**", inline=True)
        embed.add_field(name="VS", value="⚡", inline=True)
        embed.add_field(name=f"{self.p2.display_name}", value=f"出拳：**{c2}**", inline=True)

        if result == 0:
            embed.description = "🤝 **平手！** 激烈的交鋒，雙方都沒有損失傑尼幣。"
        else:
            embed.description = f"🎉 恭喜 {winner.mention} 獲勝！\n💰 贏得 **10** <:emoji_1:1127882888508088393> 並獲得 **1** 經驗值！"

        await self.message.edit(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            embed = self.message.embeds[0]
            embed.description = "⌛ 等待超時，對決已自動取消！雙方沒有損失傑尼幣。"
            try:
                await self.message.edit(embed=embed, view=self)
            except:
                pass


# ==========================================
# 🚀 猜拳系統主程式
# ==========================================
class RockPaperScissors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["rps", "猜拳"])
    async def play_rps(self, ctx, member: discord.Member):
        # 1. 不能跟自己玩
        if member == ctx.author:
            return await ctx.reply("⚠️ 你不能跟自己猜拳啦！太邊緣了吧！")

        data = load_json(DATA_FILE)
        user_id = str(ctx.author.id)
        target_id = str(member.id)

        # 2. 檢查發起人
        if user_id not in data:
            return await ctx.reply("⚠️ **你還沒註冊！** 請先輸入 `!面板` 建立獵人資料！")
        if data[user_id].get("傑尼幣", 0) < 10:
            return await ctx.reply("⚠️ **餘額不足！** 猜拳賭注需要 10 傑尼幣！")

        is_bot = (member == self.bot.user)

        # 3. 檢查對手 (如果是玩家的話)
        if not is_bot:
            if target_id not in data:
                return await ctx.reply(f"⚠️ **{member.display_name}** 還沒註冊，不能跟他玩！")
            if data[target_id].get("傑尼幣", 0) < 10:
                return await ctx.reply(f"⚠️ **{member.display_name}** 窮到連 10 傑尼幣都沒有，放過他吧！")

        # 4. 發送對決面板
        view = RPSView(ctx, member, is_bot)
        desc = f"{ctx.author.mention} 發起了猜拳挑戰！\n賭注：**10 傑尼幣**\n\n"

        if is_bot:
            desc += f"對手是本機器人 {member.mention}，請直接點擊下方按鈕出拳！"
        else:
            desc += f"對手是 {member.mention}，請雙方**悄悄地**點擊下方按鈕出拳！"

        embed = discord.Embed(title="✌️✊🖐️ 猜拳對決！", description=desc, color=0xe67e22)

        # 如果是玩家對戰，Tag 對方叫他出來應戰；如果是機器人就不需要
        mention_msg = member.mention if not is_bot else None
        view.message = await ctx.reply(content=mention_msg, embed=embed, view=view)

    @play_rps.error
    async def play_rps_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("⚠️ **格式錯誤！**\n請標記你要挑戰的對象，例如：`!猜拳 @阿勳` 或 `!猜拳 @機器人`")

async def setup(bot):
    await bot.add_cog(RockPaperScissors(bot))