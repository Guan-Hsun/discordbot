import discord
from discord.ext import commands
import random

from json_manager import load_json, save_json

DATA_FILE = "data.json"
REWARDS = [500, 400, 200, 80, 50, 40, 30, 20, 10]

# ==========================================
# 🔢 動態數字按鈕類別 (負責 0-9)
# ==========================================
class NumButton(discord.ui.Button):
    def __init__(self, label_str, row):
        super().__init__(style=discord.ButtonStyle.secondary, label=label_str, row=row)
        self.label_str = label_str

    async def callback(self, interaction: discord.Interaction):
        view: Game1A2BView = self.view
        # 防呆：避免別人亂按
        if interaction.user.id != view.ctx.author.id:
            return await interaction.response.send_message("❌ 這是別人的遊戲喔！", ephemeral=True)

        # 如果數字還沒滿 4 個，而且輸入的數字沒有重複，就加進去
        if len(view.current_guess) < 4 and self.label_str not in view.current_guess:
            view.current_guess += self.label_str
            await view.update_embed(interaction)
        else:
            # 已經滿 4 個字或重複了，直接略過 (必須 defer 否則會跳出交互失敗)
            await interaction.response.defer()


# ==========================================
# 🎮 1A2B 遊戲主控面板 View
# ==========================================
class Game1A2BView(discord.ui.View):
    def __init__(self, ctx, cog, secret):
        super().__init__(timeout=300.0) # 5 分鐘不動就自動超時
        self.ctx = ctx
        self.cog = cog
        self.secret = secret
        self.current_guess = ""
        self.history = []
        self.guesses_taken = 0
        self.message = None

        # 運用迴圈排版虛擬鍵盤 (Row 0 和 Row 1)
        for i in range(1, 6):
            self.add_item(NumButton(str(i), row=0))
        for i in range(6, 10):
            self.add_item(NumButton(str(i), row=1))
        self.add_item(NumButton("0", row=1))

    # 更新畫面
    async def update_embed(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🎮 1A2B 猜數字", color=0xf1c40f)
        desc = ""
        if self.history:
            desc += "\n".join(self.history) + "\n\n"

        # 顯示目前的輸入進度 (未滿 4 格用 〇 補齊，增加視覺回饋)
        display_guess = self.current_guess.ljust(4, "〇")
        desc += f"**目前的輸入：** `{display_guess}`\n"

        embed.description = desc
        embed.set_footer(text=f"剩餘次數: {9 - self.guesses_taken} 次 | 入場費已扣除 30 傑尼幣")
        await interaction.response.edit_message(embed=embed, view=self)

    # 🔙 退格按鈕
    @discord.ui.button(label="🔙 退格", style=discord.ButtonStyle.primary, row=2)
    async def btn_del(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ 這是別人的遊戲喔！", ephemeral=True)

        if len(self.current_guess) > 0:
            self.current_guess = self.current_guess[:-1] # 刪除最後一個字
            await self.update_embed(interaction)
        else:
            await interaction.response.defer()

    # ✅ 確定按鈕 (核心邏輯)
    @discord.ui.button(label="✅ 確定", style=discord.ButtonStyle.success, row=2)
    async def btn_submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ 這是別人的遊戲喔！", ephemeral=True)

        if len(self.current_guess) < 4:
            return await interaction.response.send_message("⚠️ 請先輸入完整的 4 個數字再按確定！", ephemeral=True)

        # 計算 A 和 B
        guess = self.current_guess
        a = sum(1 for i in range(4) if guess[i] == self.secret[i])
        b = sum(1 for i in range(4) if guess[i] in self.secret) - a

        self.guesses_taken += 1
        self.history.append(f"`第 {self.guesses_taken} 局` | **{guess}** ➔ {a}A{b}B")
        self.current_guess = "" # 清空輸入框，準備下一次

        if a == 4:
            await self.handle_win(interaction)
        elif self.guesses_taken >= 9:
            await self.handle_lose(interaction)
        else:
            await self.update_embed(interaction)

    # ❌ 取消按鈕
    @discord.ui.button(label="❌ 取消", style=discord.ButtonStyle.danger, row=2)
    async def btn_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ 這是別人的遊戲喔！", ephemeral=True)

        self.cog.active_players.discard(str(self.ctx.author.id)) # 解除鎖定
        embed = discord.Embed(title="🛑 遊戲已取消", description=f"正確答案是：**{''.join(self.secret)}**", color=0xe74c3c)
        for child in self.children:
            child.disabled = True # 鎖死所有按鈕
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def handle_win(self, interaction):
        self.cog.active_players.discard(str(self.ctx.author.id))
        reward = REWARDS[self.guesses_taken - 1]

        # 派發獎勵
        user_id = str(self.ctx.author.id)
        data = load_json(DATA_FILE)
        data[user_id]["傑尼幣"] = data[user_id].get("傑尼幣", 0) + reward
        data[user_id]["經驗值"] = data[user_id].get("經驗值", 0) + 1
        save_json(DATA_FILE, data)

        embed = discord.Embed(title="🎉 恭喜過關！", description="\n".join(self.history), color=0x2ecc71)
        embed.add_field(name="🎯 總猜測次數", value=f"{self.guesses_taken} 次", inline=True)
        embed.add_field(name="💰 獲得獎勵", value=f"**{reward}** <:emoji_1:1127882888508088393>\n**1** 🌟 經驗值", inline=True)
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def handle_lose(self, interaction):
        self.cog.active_players.discard(str(self.ctx.author.id))
        embed = discord.Embed(
            title="💀 遊戲結束", 
            description=f"9 次機會已用盡，挑戰失敗！\n正確答案是：**{''.join(self.secret)}**", 
            color=0xe74c3c
        )
        embed.add_field(name="📜 歷史紀錄", value="\n".join(self.history))
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    # 如果玩家 5 分鐘都沒操作，自動清理釋放記憶體
    async def on_timeout(self):
        self.cog.active_players.discard(str(self.ctx.author.id))
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass


# ==========================================
# 🚀 遊戲模組註冊
# ==========================================
class AB(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_players = set()

    @commands.command(aliases=["猜數字", "1a2b"])
    async def ab(self, ctx):
        user_id = str(ctx.author.id)

        if user_id in self.active_players:
            await ctx.reply("⚠️ 你已經有一場遊戲正在進行中囉，請先猜完！")
            return

        data = load_json(DATA_FILE)

        if user_id not in data:
            await ctx.reply("⚠️ **你還沒註冊！** 請先輸入 `!面板` 建立你的獵人資料！")
            return

        if data[user_id].get("傑尼幣", 0) < 30:
            await ctx.reply("⚠️ **餘額不足！** 1A2B 的入場費需要 30 傑尼幣，你太窮了><")
            return

        # 扣錢、加進名單
        data[user_id]["傑尼幣"] -= 30
        save_json(DATA_FILE, data)
        self.active_players.add(user_id)

        secret = random.sample("0123456789", 4)

        view = Game1A2BView(ctx, self, secret)

        # 初始畫面
        embed = discord.Embed(title="🎮 1A2B 猜數字", color=0xf1c40f)
        embed.description = "**目前的輸入：** `〇〇〇〇`\n"
        embed.set_footer(text="剩餘次數: 9 次 | 入場費已扣除 30 傑尼幣")

        # 發送訊息並把 message 存進 view 裡 (提供給 timeout 修改用)
        view.message = await ctx.reply(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(AB(bot))