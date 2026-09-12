import discord
from discord.ext import commands
import random
import asyncio

from json_manager import load_json, save_json

DATA_FILE = "data.json"

# ==========================================
# 📊 骰寶賠率與設定 Config
# ==========================================
BET_COST = 20  # 一注 20 傑尼幣
MAX_BETS_PER_USER = 10 # 每人最多下 10 注

ODDS = {
    "大": 2,       
    "小": 2,       
    "豹子": 25,    
    "4或17": 32,   
    "5或16": 16,   
    "6或15": 10,   
    "7或14": 7,   
    "8或13": 6,    
    "9或12": 5,    
    "10或11": 4,   
}

# 🌟 改用 Discord 內建的超大型數字 Emoji，解決原版符號太小的問題
DICE_EMOJIS = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣"}
DICE_REVERSE = {"1️⃣": 1, "2️⃣": 2, "3️⃣": 3, "4️⃣": 4, "5️⃣": 5, "6️⃣": 6}

# ==========================================
# 🎮 下注按鈕與控制面板
# ==========================================
class SicBoButton(discord.ui.Button):
    def __init__(self, label, option_id, row, style=discord.ButtonStyle.secondary):
        super().__init__(label=label, custom_id=option_id, row=row, style=style)
        self.option_id = option_id

    async def callback(self, interaction: discord.Interaction):
        view: SicBoView = self.view

        if view.is_closed:
            return await interaction.response.send_message("❌ 盤口已關閉，請等待開獎！", ephemeral=True)

        user_id = str(interaction.user.id)
        data = load_json(DATA_FILE)

        if user_id not in data:
            return await interaction.response.send_message("⚠️ 你還沒註冊獵人執照！(請輸入 `/profile`)", ephemeral=True)

        # 🌟 檢查下注上限 (每人最多 10 注)
        user_data = view.bets.get(user_id, {"bets": {}})
        total_bets_count = sum(user_data["bets"].values()) // BET_COST
        if total_bets_count >= MAX_BETS_PER_USER:
            return await interaction.response.send_message(f"⚠️ 下注失敗！你已經達到每局最多 {MAX_BETS_PER_USER} 注的上限囉！", ephemeral=True)

        if data[user_id].get("傑尼幣", 0) < BET_COST:
            return await interaction.response.send_message(f"⚠️ 餘額不足！一注需要 {BET_COST} 傑尼幣。", ephemeral=True)

        # 扣款並存檔
        data[user_id]["傑尼幣"] -= BET_COST
        save_json(DATA_FILE, data)

        # 紀錄下注資訊
        if user_id not in view.bets:
            view.bets[user_id] = {"name": interaction.user.display_name, "bets": {}}

        if self.option_id not in view.bets[user_id]["bets"]:
            view.bets[user_id]["bets"][self.option_id] = 0

        view.bets[user_id]["bets"][self.option_id] += BET_COST

        # 先回覆玩家成功下注 (隱藏訊息)
        await interaction.response.send_message(
            f"✅ 成功在 **{self.option_id}** 下注 {BET_COST} 傑尼幣！", 
            ephemeral=True
        )

        # 🌟 即時更新大廳的 Embed 卡片，讓所有人看到
        await view.update_embed(interaction)

class SicBoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.bets = {}
        self.is_closed = False

        # Row 0: 大小豹子
        self.add_item(SicBoButton(" 小 ", "小", 0, discord.ButtonStyle.primary))
        self.add_item(SicBoButton(" 豹子 ", "豹子", 0, discord.ButtonStyle.danger))
        self.add_item(SicBoButton(" 大 ", "大", 0, discord.ButtonStyle.success))

        # Row 1 & 2: 單顆骰子 (改用大型數字)
        self.add_item(SicBoButton(" 1️⃣ ", "1️⃣", 1))
        self.add_item(SicBoButton(" 2️⃣ ", "2️⃣", 1))
        self.add_item(SicBoButton(" 3️⃣ ", "3️⃣", 1))
        self.add_item(SicBoButton(" 4️⃣ ", "4️⃣", 2))
        self.add_item(SicBoButton(" 5️⃣ ", "5️⃣", 2))
        self.add_item(SicBoButton(" 6️⃣ ", "6️⃣", 2))

        # Row 3 & 4: 點數總和
        self.add_item(SicBoButton("4 或 17", "4或17", 3))
        self.add_item(SicBoButton("5 或 16", "5或16", 3))
        self.add_item(SicBoButton("6 或 15", "6或15", 3))
        self.add_item(SicBoButton("7 或 14", "7或14", 3))
        self.add_item(SicBoButton("8 或 13", "8或13", 4))
        self.add_item(SicBoButton("9 或 12", "9或12", 4))
        self.add_item(SicBoButton("10 或 11", "10或11", 4))

    # 🌟 動態更新下注看板
    async def update_embed(self, interaction):
        bet_lines = []
        for uid, udata in self.bets.items():
            # 將玩家下注的項目與金額組裝起來，例如: 大(40), 1️⃣(20)
            user_bets_str = ", ".join([f"`{opt}` ({amt})" for opt, amt in udata["bets"].items()])

            # 計算該玩家總共下了幾注
            total_bets = sum(udata["bets"].values()) // BET_COST
            bet_lines.append(f"👤 **{udata['name']}** [{total_bets}/10]: {user_bets_str}")

        bet_display = "\n".join(bet_lines) if bet_lines else "👻 尚無人下注"

        embed = interaction.message.embeds[0]
        embed.description = (
            f"點擊下方按鈕下注，**一注固定為 {BET_COST} 傑尼幣** (每人最多 {MAX_BETS_PER_USER} 注)。\n"
            "所有人皆可參與，買定離手！\n\n"
            "📜 **【目前下注狀況】**\n"
            f"{bet_display}\n\n"
            "⏳ **倒數 30 秒後開獎！**"
        )

        try:
            await interaction.message.edit(embed=embed)
        except discord.errors.HTTPException:
            pass # 防止同時太多人點擊導致 API 報錯


# ==========================================
# 🚀 骰寶主程式
# ==========================================
class SicBoGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.game_active = False

    @commands.hybrid_command(name="sicbo", aliases=["sb", "骰寶"], description="開放地下競技場骰寶下注，快來試試手氣！")
    async def sicbo(self, ctx: commands.Context):
        if self.game_active:
            return await ctx.reply("⚠️ 目前已經有一場骰寶正在進行中，請趕快去下注吧！", ephemeral=True)

        self.game_active = True

        try:
            view = SicBoView()
            embed = discord.Embed(
                title="🎲 地下競技場：骰寶開放下注！", 
                description=(
                    f"點擊下方按鈕下注，**一注固定為 {BET_COST} 傑尼幣** (每人最多 {MAX_BETS_PER_USER} 注)。\n"
                    "所有人皆可參與，買定離手！\n\n"
                    "📜 **【目前下注狀況】**\n"
                    "👻 尚無人下注\n\n"
                    "⏳ **倒數 30 秒後開獎！**"
                ),
                color=0xe67e22
            )
            msg = await ctx.send(embed=embed, view=view)

            # 等待 30 秒
            await asyncio.sleep(30)

            # 🌟 關閉盤口並「徹底移除所有按鈕」
            view.is_closed = True
            view.clear_items() 

            embed.title = "🎲 骰寶：買定離手，準備開獎..."
            embed.description = "盤口已關閉，正在擲骰！"
            embed.color = discord.Color.dark_gray()
            await msg.edit(embed=embed, view=view)

            await asyncio.sleep(2)

            # 🎲 擲骰子
            dice_results = [random.randint(1, 6) for _ in range(3)]
            total = sum(dice_results)
            is_triple = (dice_results[0] == dice_results[1] == dice_results[2])

            winning_conditions = []
            if is_triple:
                winning_conditions.append("豹子")
            else:
                if 4 <= total <= 10: winning_conditions.append("小")
                if 11 <= total <= 17: winning_conditions.append("大")

            if total in [4, 17]: winning_conditions.append("4或17")
            elif total in [5, 16]: winning_conditions.append("5或16")
            elif total in [6, 15]: winning_conditions.append("6或15")
            elif total in [7, 14]: winning_conditions.append("7或14")
            elif total in [8, 13]: winning_conditions.append("8或13")
            elif total in [9, 12]: winning_conditions.append("9或12")
            elif total in [10, 11]: winning_conditions.append("10或11")

            data = load_json(DATA_FILE)
            winners_text = []

            for uid, user_data in view.bets.items():
                total_win = 0
                for option, amount in user_data["bets"].items():
                    if option in ODDS:
                        if option in winning_conditions:
                            total_win += amount * ODDS[option]
                    elif option in DICE_REVERSE:
                        target_num = DICE_REVERSE[option]
                        matches = dice_results.count(target_num)
                        if matches > 0:
                            total_win += amount * (matches + 1)

                if total_win > 0:
                    data[uid]["傑尼幣"] = data[uid].get("傑尼幣", 0) + total_win
                    data[uid]["經驗值"] = data[uid].get("經驗值", 0) + 1
                    winners_text.append(f"🎉 **{user_data['name']}** 贏得 {total_win} 傑尼幣")

            save_json(DATA_FILE, data)

            # 🌟 結算畫面：放大顯示新的 Emoji
            dice_faces = " ".join([DICE_EMOJIS[d] for d in dice_results])
            result_embed = discord.Embed(
                title="🎲 骰寶開獎結果！",
                color=0xf1c40f
            )
            result_embed.add_field(name="骰子點數", value=f" {dice_faces}", inline=False)

            if is_triple:
                result_embed.add_field(name="總和與結果", value=f"**{total}** 點 ➔ **豹子！通殺！**", inline=False)
            else:
                big_small = "大" if 11 <= total <= 17 else "小"
                result_embed.add_field(name="總和與結果", value=f"**{total}** 點 ➔ **{big_small}**\n\n", inline=False)

            if winners_text:
                result_embed.add_field(name="💰 贏家榜單", value="\n".join(winners_text), inline=False)
            else:
                if view.bets:
                    result_embed.add_field(name="💰 贏家榜單", value="💀 莊家通殺！沒有人中獎。", inline=False)
                else:
                    result_embed.add_field(name="💰 贏家榜單", value="👻 本局無人下注。", inline=False)

            await ctx.send(embed=result_embed)

        finally:
            self.game_active = False

async def setup(bot):
    await bot.add_cog(SicBoGame(bot))