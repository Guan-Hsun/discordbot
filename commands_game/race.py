import discord
from discord.ext import commands
import random
import asyncio
import datetime

from json_manager import load_json, save_json

DATA_FILE = "data.json"
JENNY_EMOJI = "<:emoji_1:1127882888508088393>"
BET_COST = 20

# ==========================================
# 📊 賽馬場：動物選手資料庫 (移除固定賠率)
# ==========================================
ANIMAL_POOL = [
    {"emoji": "🐎", "name": "烈焰馬", "speed": 2, "burst": 20, "stumble": 5},
    {"emoji": "🐕", "name": "神速犬", "speed": 2, "burst": 25, "stumble": 10},
    {"emoji": "🐅", "name": "猛老虎", "speed": 3, "burst": 15, "stumble": 15},
    {"emoji": "🐆", "name": "獵豹", "speed": 3, "burst": 30, "stumble": 25},
    {"emoji": "🐢", "name": "穩重龜", "speed": 1, "burst": 5, "stumble": 0},
    {"emoji": "🐇", "name": "傲慢兔", "speed": 4, "burst": 10, "stumble": 40},
    {"emoji": "🐘", "name": "重裝象", "speed": 1, "burst": 40, "stumble": 5},
    {"emoji": "🐪", "name": "耐力駱駝", "speed": 2, "burst": 15, "stumble": 5},
    {"emoji": "🐖", "name": "貪吃豬", "speed": 1, "burst": 10, "stumble": 30},
    {"emoji": "🐏", "name": "衝撞羊", "speed": 2, "burst": 20, "stumble": 10},
    {"emoji": "🦖", "name": "暴龍", "speed": 3, "burst": 20, "stumble": 20},
    {"emoji": "🐒", "name": "皮猴子", "speed": 2, "burst": 35, "stumble": 25},
    {"emoji": "🐧", "name": "滑行企鵝", "speed": 2, "burst": 10, "stumble": 15},
    {"emoji": "🦆", "name": "暴走鴨", "speed": 2, "burst": 25, "stumble": 15},
    {"emoji": "🐌", "name": "奇蹟蝸牛", "speed": 0, "burst": 50, "stumble": 0},
]

TRACK_LENGTH = 20

# ==========================================
# 🎮 下注控制面板 (下拉式選單)
# ==========================================
class BetSelect(discord.ui.Select):
    def __init__(self, bet_type, options, max_val=1):
        placeholders = {
            "win": "🏆 獨贏：選擇 1 隻冠軍 (賠率見各選項)",
            "place": "🥉 位置：選擇 1 隻前三名 (賠率見各選項)",
            "quinella": "🤝 連贏：選擇 2 隻包辦一二名 (賠率約兩者相乘÷2)",
            "last": "💩 倒數：選擇 1 隻最後一名 (賠率見各選項)"
        }
        super().__init__(
            placeholder=placeholders[bet_type],
            min_values=1,
            max_values=max_val,
            options=options,
            custom_id=f"bet_{bet_type}"
        )
        self.bet_type = bet_type

    async def callback(self, interaction: discord.Interaction):
        view: RaceView = self.view
        if view.is_closed:
            return await interaction.response.send_message("❌ 盤口已關閉，比賽即將開始！", ephemeral=True)

        user_id = str(interaction.user.id)
        data = load_json(DATA_FILE)

        if user_id not in data:
            return await interaction.response.send_message("⚠️ 你還沒註冊獵人執照！(請輸入 `/profile`)", ephemeral=True)
        if data[user_id].get("傑尼幣", 0) < BET_COST:
            return await interaction.response.send_message(f"⚠️ 餘額不足！一注需要 {BET_COST} {JENNY_EMOJI}。", ephemeral=True)

        if self.bet_type == "quinella" and len(self.values) != 2:
            return await interaction.response.send_message("⚠️ 連贏玩法必須剛好選擇 2 隻動物！", ephemeral=True)

        data[user_id]["傑尼幣"] -= BET_COST
        save_json(DATA_FILE, data)

        if user_id not in view.bets:
            view.bets[user_id] = {"name": interaction.user.display_name, "history": []}

        selected_names = [view.racer_names[int(idx)] for idx in self.values]
        bet_desc = " & ".join(selected_names)
        view.bets[user_id]["history"].append({"type": self.bet_type, "picks": self.values, "desc": bet_desc})

        await interaction.response.send_message(
            f"✅ 成功花費 {BET_COST} {JENNY_EMOJI} 下注！\n玩法：**{self.bet_type.upper()}**\n選擇：**{bet_desc}**", 
            ephemeral=True
        )
        await view.update_embed(interaction)


class RaceView(discord.ui.View):
    def __init__(self, racers):
        super().__init__(timeout=None)
        self.racers = racers
        self.racer_names = {i: f"{r['emoji']} {r['name']}" for i, r in enumerate(racers)}
        self.bets = {}
        self.is_closed = False

        # 🌟 將動態計算出來的賠率顯示在選單選項中
        options = [
            discord.SelectOption(
                label=f"{i+1}號賽道：{r['name']}", 
                emoji=r['emoji'], 
                value=str(i), 
                description=f"獨贏:{r['win_odds']}x | 位置:{r['place_odds']}x | 倒數:{r['last_odds']}x"
            ) 
            for i, r in enumerate(racers)
        ]

        self.add_item(BetSelect("win", options, max_val=1))
        self.add_item(BetSelect("place", options, max_val=1))
        self.add_item(BetSelect("quinella", options, max_val=2))
        self.add_item(BetSelect("last", options, max_val=1))

    async def update_embed(self, interaction):
        bet_lines = []
        for uid, udata in self.bets.items():
            total_bets = len(udata["history"])
            bet_lines.append(f"👤 **{udata['name']}** 已下注 {total_bets} 筆")

        bet_display = "\n".join(bet_lines) if bet_lines else "👻 尚無人下注"

        embed = interaction.message.embeds[0]
        embed.description = (
            f"點擊下方選單進行下注，**每注固定 {BET_COST} {JENNY_EMOJI}**。\n"
            "把握時間，買定離手！\n\n"
            "📜 **【目前大廳狀況】**\n"
            f"{bet_display}\n\n"
            "⏳ **倒數 60 秒後準時開賽！**"
        )
        try:
            await interaction.message.edit(embed=embed)
        except discord.errors.HTTPException:
            pass

# ==========================================
# 🚀 賽馬場主程式
# ==========================================
class AnimalRacing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_race_window = None
        self.game_active = False

    def get_current_window(self):
        now = datetime.datetime.now()
        minute = (now.minute // 10) * 10
        return now.replace(minute=minute, second=0, microsecond=0)

    def render_track(self, racers, positions, events):
        lines = []
        for i in range(6):
            pos = min(positions[i], TRACK_LENGTH)
            racer = racers[i]
            track_before = "." * pos
            track_after = "." * (TRACK_LENGTH - pos)
            event_text = f" ({events[i]})" if events[i] else ""
            lines.append(f"[{i+1}號]\n {track_before}{racer['emoji']}{track_after}🏁{event_text}")
        return "\n".join(lines)

    @commands.hybrid_command(name="race", aliases=["賽馬", "田徑賽"], description="開啟賽馬場大廳！每10分鐘開放一次，大家一起下注看轉播！")
    async def race(self, ctx: commands.Context):
        if self.game_active:
            return await ctx.reply("⚠️ 目前已經有一場賽事正在進行中！", ephemeral=True)

        current_window = self.get_current_window()
        if self.last_race_window == current_window:
            next_window = current_window + datetime.timedelta(minutes=10)
            time_left = int((next_window - datetime.datetime.now()).total_seconds())
            mins, secs = divmod(time_left, 60)
            return await ctx.reply(f"💤 **動物們還在休息！**\n下一場賽事將在 **{mins}分 {secs}秒** 後開放 (尾數 0 的時間)。", ephemeral=True)

        self.game_active = True
        self.last_race_window = current_window

        # 1. 隨機挑選 6 隻動物
        racers = random.sample(ANIMAL_POOL, 6)

        # 2. 動態計算 6 隻動物的期望值與權重 (85% 返還率)
        total_weight = 0
        total_inv_weight = 0
        for r in racers:
            # 期望速度 (考慮失誤與爆發)
            ev = (1 - r["stumble"]/100.0) * (r["speed"] + 3 * r["burst"]/100.0)
            weight = max(0.1, ev ** 3)
            inv_weight = 1 / weight

            r["_weight"] = weight
            r["_inv_weight"] = inv_weight
            total_weight += weight
            total_inv_weight += inv_weight

        # 3. 結算各項玩法的專屬賠率
        for r in racers:
            # 獨贏
            r["win_odds"] = max(1.2, round((total_weight / r["_weight"]) * 0.85, 1))
            # 位置 (約獨贏的 1/2.8)
            r["place_odds"] = max(1.1, round(r["win_odds"] / 2.8, 1))
            # 倒數 (反向權重)
            r["last_odds"] = max(1.2, round((total_inv_weight / r["_inv_weight"]) * 0.85, 1))

        view = RaceView(racers)

        info_lines = [f"{i+1}號賽道：{r['emoji']} **{r['name']}** (獨贏賠率: {r['win_odds']}x)" for i, r in enumerate(racers)]

        embed = discord.Embed(
            title="🏁 瘋狂動物田徑賽 - 開放下注！",
            description=(
                f"點擊下方選單進行下注，**每注固定 {BET_COST} {JENNY_EMOJI}**。\n"
                "把握時間，買定離手！\n\n"
                "📜 **【目前大廳狀況】**\n"
                "👻 尚無人下注\n\n"
                "⏳ **倒數 60 秒後準時開賽！**"
            ),
            color=0x2ecc71
        )
        embed.add_field(name="🐾 本局參賽選手與獨贏賠率", value="\n".join(info_lines), inline=False)

        msg = await ctx.send(embed=embed, view=view)

        await asyncio.sleep(60)

        view.is_closed = True
        view.clear_items()

        embed.title = "🏁 賽事即將開始..."
        embed.description = "盤口已關閉，選手就位！"
        embed.color = discord.Color.gold()
        await msg.edit(embed=embed, view=view)
        await asyncio.sleep(2)

        # 🚀 賽事迴圈
        positions = [0] * 6
        finish_order = []

        while len(finish_order) < 6:
            events = [""] * 6
            for i in range(6):
                if i in finish_order:
                    continue

                racer = racers[i]
                move = racer["speed"]

                if random.randint(1, 100) <= racer["stumble"]:
                    move = 0
                    events[i] = "💤"
                elif random.randint(1, 100) <= racer["burst"]:
                    move += 3
                    events[i] = "🔥"

                positions[i] += move
                if positions[i] >= TRACK_LENGTH:
                    finish_order.append(i)

            track_display = self.render_track(racers, positions, events)

            race_embed = discord.Embed(
                title="🔴 賽事即時轉播中！",
                description=f"```text\n{track_display}\n```",
                color=0xe74c3c
            )
            await msg.edit(embed=race_embed)
            await asyncio.sleep(2.5)

        # 🏆 賽事結算
        first, second, third, last = finish_order[0], finish_order[1], finish_order[2], finish_order[-1]

        data = load_json(DATA_FILE)
        winners_text = []

        for uid, user_data in view.bets.items():
            total_win = 0
            for bet in user_data["history"]:
                b_type = bet["type"]
                picks = [int(p) for p in bet["picks"]]

                if b_type == "win" and picks[0] == first:
                    total_win += int(BET_COST * racers[first]["win_odds"])
                elif b_type == "place" and picks[0] in [first, second, third]:
                    total_win += int(BET_COST * racers[picks[0]]["place_odds"])
                elif b_type == "quinella" and set(picks) == {first, second}:
                    # 動態連贏賠率結算：兩者獨贏相乘 ÷ 2.0 (保底 3 倍)
                    q_odds = max(3.0, round((racers[first]["win_odds"] * racers[second]["win_odds"]) / 2.0, 1))
                    total_win += int(BET_COST * q_odds)
                elif b_type == "last" and picks[0] == last:
                    total_win += int(BET_COST * racers[last]["last_odds"])

            if total_win > 0:
                data[uid]["傑尼幣"] = data[uid].get("傑尼幣", 0) + total_win
                data[uid]["經驗值"] = data[uid].get("經驗值", 0) + 2
                winners_text.append(f"🎉 **{user_data['name']}** 贏回 {total_win} {JENNY_EMOJI}")

        save_json(DATA_FILE, data)

        result_embed = discord.Embed(
            title="🏁 比賽結束！結果出爐",
            description=f"```text\n{self.render_track(racers, positions, ['']*6)}\n```",
            color=0x3498db
        )
        result_embed.add_field(
            name="🏆 名次揭曉",
            value=(
                f"🥇 第一名：{racers[first]['emoji']} {racers[first]['name']} (獨贏 {racers[first]['win_odds']}x)\n"
                f"🥈 第二名：{racers[second]['emoji']} {racers[second]['name']} (獨贏 {racers[second]['win_odds']}x)\n"
                f"🥉 第三名：{racers[third]['emoji']} {racers[third]['name']}\n"
                f"💩 最後一名：{racers[last]['emoji']} {racers[last]['name']} (倒數 {racers[last]['last_odds']}x)"
            ),
            inline=False
        )

        if winners_text:
            result_embed.add_field(name="💰 贏家榜單", value="\n".join(winners_text), inline=False)
        else:
            result_embed.add_field(name="💰 贏家榜單", value=f"💀 莊家通殺！沒有人中獎。", inline=False)

        await ctx.send(embed=result_embed)
        self.game_active = False

async def setup(bot):
    await bot.add_cog(AnimalRacing(bot))