import discord
from discord.ext import commands
import time
import datetime
import random

from json_manager import load_json, save_json

DATA_FILE = "data.json"
MINE_FILE = "mine.json"

# ==========================================
# 📊 遊戲數值設定 (Config)
# ==========================================

# 礦工招募費用 (已 *3) 與 累計挖礦需求
# 等級：      1(免),   2,    3,     4,     5,      6,       7,       8,       9,        10
MINER_COSTS = [0, 900, 1800, 7200, 22500, 72000, 225000, 720000, 2250000, 9000000]
MINER_REQS  = [0, 50,  200,  800,  3000,  10000, 30000,  100000, 300000,  1000000]

# 礦坑升級 (新增 req_ores 指數成長)
MINE_LEVELS = {
    1: {"name": "廢棄煤礦坑", "cost": 0,      "req_ores": 0,      "probs": [100, 0, 0, 0, 0]},
    2: {"name": "堅硬鐵礦坑", "cost": 2000,   "req_ores": 100,    "probs": [75, 25, 0, 0, 0]},
    3: {"name": "閃耀銀礦坑", "cost": 12000,  "req_ores": 1000,   "probs": [50, 30, 20, 0, 0]},
    4: {"name": "璀璨金礦坑", "cost": 80000,  "req_ores": 10000,  "probs": [30, 30, 25, 15, 0]},
    5: {"name": "奇蹟星碎礦脈", "cost": 400000, "req_ores": 100000, "probs": [10, 20, 30, 30, 10]}
}

# 倉庫升級 (費用已 *2，新增 req_ores)
WH_LEVELS = {
    1: {"name": "破舊木箱", "cap": 10,   "cost": 0,       "req_ores": 0},
    2: {"name": "鐵皮貨櫃", "cap": 20,   "cost": 1200,    "req_ores": 50},
    3: {"name": "小型地下室", "cap": 40,   "cost": 4000,    "req_ores": 300},
    4: {"name": "大型集貨倉庫", "cap": 80,   "cost": 16000,   "req_ores": 2000},
    5: {"name": "工業級倉儲區", "cap": 160,  "cost": 60000,   "req_ores": 10000},
    6: {"name": "自動化物流倉", "cap": 320,  "cost": 240000,  "req_ores": 50000},
    7: {"name": "四次元空間袋", "cap": 640,  "cost": 1000000, "req_ores": 200000}
}

# 礦車升級 (新增 req_ores)
CART_LEVELS = {
    1: {"name": "破舊手推車", "tax": 0.20, "cost": 0,      "req_ores": 0},
    2: {"name": "木質軌道車", "tax": 0.15, "cost": 1500,   "req_ores": 100},
    3: {"name": "柴油動力礦車", "tax": 0.10, "cost": 6000,   "req_ores": 500},
    4: {"name": "重裝甲運鈔車", "tax": 0.05, "cost": 30000,  "req_ores": 5000},
    5: {"name": "念能力瞬間轉移", "tax": 0.02, "cost": 150000, "req_ores": 50000}
}

# 礦石市場
ORE_TYPES = ["煤礦", "鐵礦", "銀礦", "金礦", "星碎礦"]
ORE_EMOJIS = ["🪨", "🔗", "🥈", "🥇", "💎"]
PRICE_RANGE = {
    "煤礦": (6, 15),
    "鐵礦": (18, 45),
    "銀礦": (70, 160),
    "金礦": (250, 650),
    "星碎礦": (1000, 2800)
}

# 1個礦工每 10 分鐘挖出 1 顆礦石
MINE_CYCLE_SECONDS = 600

# ==========================================
# 🧠 系統核心引擎
# ==========================================

def update_market_if_needed():
    """每 2 小時 (偶數整點) 刷新一次全服礦石價格"""
    m_data = load_json(MINE_FILE)
    if "market" not in m_data:
        m_data["market"] = {"prices": {}, "last_update": 0}

    now = datetime.datetime.now()
    even_hour = now.hour if now.hour % 2 == 0 else now.hour - 1
    target_time = now.replace(hour=even_hour, minute=0, second=0, microsecond=0)
    target_ts = target_time.timestamp()

    if m_data["market"]["last_update"] != target_ts:
        m_data["market"]["last_update"] = target_ts
        for ore in ORE_TYPES:
            min_p, max_p = PRICE_RANGE[ore]
            m_data["market"]["prices"][ore] = random.randint(min_p, max_p)
        save_json(MINE_FILE, m_data)

    return m_data["market"]

def calculate_afk_mining(user_id):
    """計算並結算掛機挖礦"""
    m_data = load_json(MINE_FILE)
    if "players" not in m_data:
        m_data["players"] = {}

    if user_id not in m_data["players"]:
        m_data["players"][user_id] = {
            "miners": 1,
            "mine_lv": 1,
            "wh_lv": 1,
            "cart_lv": 1,
            "ores": {ore: 0 for ore in ORE_TYPES},
            "last_mine_time": time.time(),
            "total_mined": 0  # 🌟 新增累計挖礦數量，作為解鎖升級的條件
        }
        save_json(MINE_FILE, m_data)
        return m_data["players"][user_id]

    player = m_data["players"][user_id]

    # 確保舊玩家也有 total_mined 欄位
    if "total_mined" not in player:
        player["total_mined"] = 0

    current_time = time.time()
    time_passed = current_time - player["last_mine_time"]
    cycles = int(time_passed // MINE_CYCLE_SECONDS)

    if cycles > 0:
        current_ores = sum(player["ores"].values())
        max_cap = WH_LEVELS[player["wh_lv"]]["cap"]
        available_space = max_cap - current_ores

        if available_space > 0:
            mined_amount = cycles * player["miners"]
            actual_mined = min(mined_amount, available_space)

            probs = MINE_LEVELS[player["mine_lv"]]["probs"]
            weights = [p/100.0 for p in probs]

            for _ in range(actual_mined):
                ore_found = random.choices(ORE_TYPES, weights=weights, k=1)[0]
                player["ores"][ore_found] += 1

            # 🌟 增加累計挖礦次數
            player["total_mined"] += actual_mined

        player["last_mine_time"] += cycles * MINE_CYCLE_SECONDS
        save_json(MINE_FILE, m_data)

    return player

# ==========================================
# 🎮 控制面板 UI
# ==========================================

class MineControlView(discord.ui.View):
    def __init__(self, ctx, page="home"):
        super().__init__(timeout=180.0) # 3 分鐘後介面自動失效
        self.ctx = ctx
        self.user_id = str(ctx.author.id)
        self.page = page
        self.message = None

        self.market = update_market_if_needed()
        self.p_data = calculate_afk_mining(self.user_id)

        self.setup_buttons()

    # 🌟 新增：超時作廢處理機制
    async def on_timeout(self):
        self.clear_items() # 清空所有按鈕
        if self.message:
            embed = self.message.embeds[0]
            embed.color = discord.Color.dark_grey() # 變灰代表失效
            embed.set_footer(text="⚠️ 操作介面已過期，請重新輸入 !mine 喚醒。")
            try:
                await self.message.edit(embed=embed, view=self)
            except:
                pass

    def setup_buttons(self):
        self.clear_items()

        if self.page == "home":
            btn_market = discord.ui.Button(label="📦 進入倉庫與市場", style=discord.ButtonStyle.primary)
            btn_market.callback = self.go_market
            self.add_item(btn_market)

            btn_upgrade = discord.ui.Button(label="⬆️ 進入升級中心", style=discord.ButtonStyle.success)
            btn_upgrade.callback = self.go_upgrade
            self.add_item(btn_upgrade)

        elif self.page == "market":
            # 🌟 新增：分拆各種礦石的獨立賣出按鈕
            btn_coal = discord.ui.Button(label="賣煤礦", style=discord.ButtonStyle.secondary, row=0)
            btn_coal.callback = lambda i: self.sell_ores(i, "煤礦")
            self.add_item(btn_coal)

            btn_iron = discord.ui.Button(label="賣鐵礦", style=discord.ButtonStyle.secondary, row=0)
            btn_iron.callback = lambda i: self.sell_ores(i, "鐵礦")
            self.add_item(btn_iron)

            btn_silver = discord.ui.Button(label="賣銀礦", style=discord.ButtonStyle.secondary, row=0)
            btn_silver.callback = lambda i: self.sell_ores(i, "銀礦")
            self.add_item(btn_silver)

            btn_gold = discord.ui.Button(label="賣金礦", style=discord.ButtonStyle.secondary, row=1)
            btn_gold.callback = lambda i: self.sell_ores(i, "金礦")
            self.add_item(btn_gold)

            btn_star = discord.ui.Button(label="賣星碎礦", style=discord.ButtonStyle.secondary, row=1)
            btn_star.callback = lambda i: self.sell_ores(i, "星碎礦")
            self.add_item(btn_star)

            btn_sell_all = discord.ui.Button(label="💰 全部賣出", style=discord.ButtonStyle.success, row=2)
            btn_sell_all.callback = lambda i: self.sell_ores(i, "all")
            self.add_item(btn_sell_all)

            btn_home = discord.ui.Button(label="🏠 回首頁", style=discord.ButtonStyle.primary, row=2)
            btn_home.callback = self.go_home
            self.add_item(btn_home)

        elif self.page == "upgrade":
            btn_u1 = discord.ui.Button(label="招募礦工", style=discord.ButtonStyle.primary, row=0)
            btn_u1.callback = lambda i: self.do_upgrade(i, "miners")
            self.add_item(btn_u1)

            btn_u2 = discord.ui.Button(label="升級礦坑", style=discord.ButtonStyle.primary, row=0)
            btn_u2.callback = lambda i: self.do_upgrade(i, "mine_lv")
            self.add_item(btn_u2)

            btn_u3 = discord.ui.Button(label="擴建倉庫", style=discord.ButtonStyle.primary, row=0)
            btn_u3.callback = lambda i: self.do_upgrade(i, "wh_lv")
            self.add_item(btn_u3)

            btn_u4 = discord.ui.Button(label="升級礦車", style=discord.ButtonStyle.primary, row=1)
            btn_u4.callback = lambda i: self.do_upgrade(i, "cart_lv")
            self.add_item(btn_u4)

            btn_home = discord.ui.Button(label="🏠 回首頁", style=discord.ButtonStyle.secondary, row=1)
            btn_home.callback = self.go_home
            self.add_item(btn_home)

    def generate_embed(self):
        self.p_data = calculate_afk_mining(self.user_id)

        embed = discord.Embed(color=0xf1c40f)
        embed.set_author(name=f"🏭 {self.ctx.author.display_name} 的地下礦業", icon_url=self.ctx.author.display_avatar.url)

        if self.page == "home":
            embed.title = "🏠 礦場首頁"
            current_ores = sum(self.p_data["ores"].values())
            max_cap = WH_LEVELS[self.p_data["wh_lv"]]["cap"]
            perc = int((current_ores / max_cap) * 10) if max_cap > 0 else 10
            bar = "█" * perc + "░" * (10 - perc)

            mine_name = MINE_LEVELS[self.p_data['mine_lv']]['name']
            cart_name = CART_LEVELS[self.p_data['cart_lv']]['name']
            tax_rate = CART_LEVELS[self.p_data['cart_lv']]['tax'] * 100

            desc = (
                f"👷 **礦工陣容**：{self.p_data['miners']} 人 (產能: {self.p_data['miners']} 顆 / 10分鐘)\n"
                f"🕳️ **目前礦坑**：{mine_name} (Lv.{self.p_data['mine_lv']})\n"
                f"📦 **倉庫狀態**：[{bar}] {current_ores} / {max_cap}\n"
                f"🚂 **運輸稅率**：{int(tax_rate)}% ({cart_name})\n\n"
                f"⛏️ *生涯累計挖出：{self.p_data.get('total_mined', 0)} 顆礦石*"
            )
            embed.description = desc

        elif self.page == "market":
            embed.title = "📈 倉庫與浮動市場"

            now = datetime.datetime.now()
            next_even_hour = now.hour + 2 if now.hour % 2 == 0 else now.hour + 1
            if next_even_hour >= 24:
                next_time = now.replace(day=now.day+1, hour=0, minute=0, second=0) if now.day < 28 else now + datetime.timedelta(hours=2)
                next_time = next_time.replace(hour=0, minute=0, second=0)
            else:
                next_time = now.replace(hour=next_even_hour, minute=0, second=0)

            time_left = int((next_time - now).total_seconds())
            mins, secs = divmod(time_left, 60)

            desc = f"🕒 *下次價格刷新：{mins}分 {secs}秒後*\n\n"

            total_value = 0
            for i, ore in enumerate(ORE_TYPES):
                qty = self.p_data["ores"][ore]
                price = self.market["prices"].get(ore, 0)
                total_value += qty * price
                desc += f"{ORE_EMOJIS[i]} **{ore}**：{qty} 顆 (目前市價: **{price}** /顆)\n"

            tax_rate = CART_LEVELS[self.p_data['cart_lv']]['tax']
            final_value = int(total_value * (1 - tax_rate))

            desc += f"\n💰 **預估總價值**：{total_value} 傑尼幣<:emoji_1:1127882888508088393>\n"
            desc += f"🧾 **扣稅後實拿**：**{final_value}** 傑尼幣<:emoji_1:1127882888508088393> (稅率 {int(tax_rate*100)}%)"
            embed.description = desc

        elif self.page == "upgrade":
            embed.title = "⬆️ 升級中心"
            c_data = load_json(DATA_FILE)
            wallet = c_data.get(self.user_id, {}).get("傑尼幣", 0)
            total_m = self.p_data.get("total_mined", 0)

            # 準備各項目的顯示文字 (包含金錢與條件)
            m_lv = self.p_data["miners"]
            if m_lv < 10:
                cost_m = f"**{MINER_COSTS[m_lv]}**"
                req_m = MINER_REQS[m_lv]
                status_m = f"需累計挖礦 {req_m} 顆" if total_m < req_m else "✅ 條件達成"
            else:
                cost_m, status_m = "MAX", "MAX"

            mine_lv = self.p_data["mine_lv"]
            if mine_lv < 5:
                cost_mine = f"**{MINE_LEVELS[mine_lv+1]['cost']}**"
                req_mine = MINE_LEVELS[mine_lv+1]['req_ores']
                status_mine = f"需累計挖礦 {req_mine} 顆" if total_m < req_mine else "✅ 條件達成"
            else:
                cost_mine, status_mine = "MAX", "MAX"

            wh_lv = self.p_data["wh_lv"]
            if wh_lv < 7:
                cost_wh = f"**{WH_LEVELS[wh_lv+1]['cost']}**"
                req_wh = WH_LEVELS[wh_lv+1]['req_ores']
                status_wh = f"需累計挖礦 {req_wh} 顆" if total_m < req_wh else "✅ 條件達成"
            else:
                cost_wh, status_wh = "MAX", "MAX"

            cart_lv = self.p_data["cart_lv"]
            if cart_lv < 5:
                cost_cart = f"**{CART_LEVELS[cart_lv+1]['cost']}**"
                req_cart = CART_LEVELS[cart_lv+1]['req_ores']
                status_cart = f"需累計挖礦 {req_cart} 顆" if total_m < req_cart else "✅ 條件達成"
            else:
                cost_cart, status_cart = "MAX", "MAX"

            desc = f"💳 你的餘額：**{wallet}** 傑尼幣<:emoji_1:1127882888508088393>\n⛏️ 生涯累計挖出：**{total_m}** 顆\n\n"
            desc += f"1️⃣ **招募礦工** (Lv.{m_lv})\n➔ 費用: {cost_m} | {status_m}\n\n"
            desc += f"2️⃣ **升級礦坑** (Lv.{mine_lv})\n➔ 費用: {cost_mine} | {status_mine}\n\n"
            desc += f"3️⃣ **擴建倉庫** (Lv.{wh_lv})\n➔ 費用: {cost_wh} | {status_wh}\n\n"
            desc += f"4️⃣ **升級礦車** (Lv.{cart_lv})\n➔ 費用: {cost_cart} | {status_cart}\n"
            embed.description = desc

        return embed

    async def update_message(self, interaction):
        self.setup_buttons()
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

    async def go_home(self, interaction):
        if interaction.user.id != self.ctx.author.id: return
        self.page = "home"
        await self.update_message(interaction)

    async def go_market(self, interaction):
        if interaction.user.id != self.ctx.author.id: return
        self.page = "market"
        await self.update_message(interaction)

    async def go_upgrade(self, interaction):
        if interaction.user.id != self.ctx.author.id: return
        self.page = "upgrade"
        await self.update_message(interaction)

    async def sell_ores(self, interaction, target_ore):
        if interaction.user.id != self.ctx.author.id: return

        # 防呆檢查庫存
        if target_ore == "all":
            current_ores = sum(self.p_data["ores"].values())
            if current_ores == 0:
                return await interaction.response.send_message("⚠️ 你的倉庫空空如也，沒有東西可以賣！", ephemeral=True)
        else:
            if self.p_data["ores"][target_ore] == 0:
                return await interaction.response.send_message(f"⚠️ 你的倉庫裡沒有 **{target_ore}** 可以賣！", ephemeral=True)

        # 結算金額
        total_value = 0
        if target_ore == "all":
            for ore in ORE_TYPES:
                qty = self.p_data["ores"][ore]
                price = self.market["prices"].get(ore, 0)
                total_value += qty * price
        else:
            qty = self.p_data["ores"][target_ore]
            price = self.market["prices"].get(target_ore, 0)
            total_value += qty * price

        tax_rate = CART_LEVELS[self.p_data['cart_lv']]['tax']
        final_value = int(total_value * (1 - tax_rate))

        # 存入玩家錢包
        c_data = load_json(DATA_FILE)
        if self.user_id not in c_data:
            return await interaction.response.send_message("⚠️ 你還沒註冊獵人執照！(請輸入 !面板)", ephemeral=True)
        c_data[self.user_id]["傑尼幣"] = c_data[self.user_id].get("傑尼幣", 0) + final_value
        save_json(DATA_FILE, c_data)

        # 扣除被賣掉的礦石
        m_data = load_json(MINE_FILE)
        if target_ore == "all":
            for ore in ORE_TYPES:
                m_data["players"][self.user_id]["ores"][ore] = 0
        else:
            m_data["players"][self.user_id]["ores"][target_ore] = 0
        save_json(MINE_FILE, m_data)

        msg = f"✅ **交易成功！** 成功賣出礦石，實拿 **{final_value}** 傑尼幣<:emoji_1:1127882888508088393>！"
        await interaction.response.send_message(msg, ephemeral=True)
        self.p_data = calculate_afk_mining(self.user_id) 
        await self.update_message(interaction)

    async def do_upgrade(self, interaction, target):
        if interaction.user.id != self.ctx.author.id: return

        c_data = load_json(DATA_FILE)
        wallet = c_data.get(self.user_id, {}).get("傑尼幣", 0)
        total_m = self.p_data.get("total_mined", 0)

        current_lv = self.p_data[target]
        cost = 0
        req = 0
        max_lv = False

        if target == "miners":
            if current_lv >= 10: max_lv = True
            else: cost, req = MINER_COSTS[current_lv], MINER_REQS[current_lv]
        elif target == "mine_lv":
            if current_lv >= 5: max_lv = True
            else: cost, req = MINE_LEVELS[current_lv+1]["cost"], MINE_LEVELS[current_lv+1]["req_ores"]
        elif target == "wh_lv":
            if current_lv >= 7: max_lv = True
            else: cost, req = WH_LEVELS[current_lv+1]["cost"], WH_LEVELS[current_lv+1]["req_ores"]
        elif target == "cart_lv":
            if current_lv >= 5: max_lv = True
            else: cost, req = CART_LEVELS[current_lv+1]["cost"], CART_LEVELS[current_lv+1]["req_ores"]

        if max_lv:
            return await interaction.response.send_message("⚠️ 該項目已經達到最高等級！", ephemeral=True)

        # 🌟 雙重檢查：金額與挖礦數量
        if total_m < req:
            return await interaction.response.send_message(f"⚠️ **經驗不足！** 該項目需累計挖滿 {req} 顆礦石才能解鎖。", ephemeral=True)
        if wallet < cost:
            return await interaction.response.send_message(f"⚠️ **餘額不足！** 升級需要 {cost} 傑尼幣<:emoji_1:1127882888508088393>。", ephemeral=True)

        # 扣錢與升級
        c_data[self.user_id]["傑尼幣"] = max(0, wallet - cost)
        save_json(DATA_FILE, c_data)

        m_data = load_json(MINE_FILE)
        m_data["players"][self.user_id][target] += 1
        save_json(MINE_FILE, m_data)

        await interaction.response.send_message(f"✅ **升級成功！** 扣除 {cost} 傑尼幣<:emoji_1:1127882888508088393>。", ephemeral=True)
        self.p_data = calculate_afk_mining(self.user_id) 
        await self.update_message(interaction)


# ==========================================
# 🚀 遊戲主控台註冊
# ==========================================

class MiningGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["礦場", "礦坑", "礦"])
    async def mine(self, ctx):
        data = load_json(DATA_FILE)
        if str(ctx.author.id) not in data:
            return await ctx.reply("⚠️ **你還沒註冊！** 請先輸入 `!面板` 建立你的獵人資料！")

        view = MineControlView(ctx, page="home")
        # 🌟 將回覆的 message 綁定給 view，供 on_timeout 修改使用
        view.message = await ctx.reply(embed=view.generate_embed(), view=view)

async def setup(bot):
    await bot.add_cog(MiningGame(bot))import discord
from discord.ext import commands
import time
import datetime
import random

from json_manager import load_json, save_json

DATA_FILE = "data.json"
MINE_FILE = "mine.json"

# ==========================================
# 📊 遊戲數值設定 (Config)
# ==========================================

# 礦工招募費用 (已 *3) 與 累計挖礦需求
# 等級：      1(免),   2,    3,     4,     5,      6,       7,       8,       9,        10
MINER_COSTS = [0, 900, 1800, 7200, 22500, 72000, 225000, 720000, 2250000, 9000000]
MINER_REQS  = [0, 50,  200,  800,  3000,  10000, 30000,  100000, 300000,  1000000]

# 礦坑升級 (新增 req_ores 指數成長)
MINE_LEVELS = {
    1: {"name": "廢棄煤礦坑", "cost": 0,      "req_ores": 0,      "probs": [100, 0, 0, 0, 0]},
    2: {"name": "堅硬鐵礦坑", "cost": 2000,   "req_ores": 100,    "probs": [75, 25, 0, 0, 0]},
    3: {"name": "閃耀銀礦坑", "cost": 12000,  "req_ores": 1000,   "probs": [50, 30, 20, 0, 0]},
    4: {"name": "璀璨金礦坑", "cost": 80000,  "req_ores": 10000,  "probs": [30, 30, 25, 15, 0]},
    5: {"name": "奇蹟星碎礦脈", "cost": 400000, "req_ores": 100000, "probs": [10, 20, 30, 30, 10]}
}

# 倉庫升級 (費用已 *2，新增 req_ores)
WH_LEVELS = {
    1: {"name": "破舊木箱", "cap": 10,   "cost": 0,       "req_ores": 0},
    2: {"name": "鐵皮貨櫃", "cap": 20,   "cost": 1200,    "req_ores": 50},
    3: {"name": "小型地下室", "cap": 40,   "cost": 4000,    "req_ores": 300},
    4: {"name": "大型集貨倉庫", "cap": 80,   "cost": 16000,   "req_ores": 2000},
    5: {"name": "工業級倉儲區", "cap": 160,  "cost": 60000,   "req_ores": 10000},
    6: {"name": "自動化物流倉", "cap": 320,  "cost": 240000,  "req_ores": 50000},
    7: {"name": "四次元空間袋", "cap": 640,  "cost": 1000000, "req_ores": 200000}
}

# 礦車升級 (新增 req_ores)
CART_LEVELS = {
    1: {"name": "破舊手推車", "tax": 0.20, "cost": 0,      "req_ores": 0},
    2: {"name": "木質軌道車", "tax": 0.15, "cost": 1500,   "req_ores": 100},
    3: {"name": "柴油動力礦車", "tax": 0.10, "cost": 6000,   "req_ores": 500},
    4: {"name": "重裝甲運鈔車", "tax": 0.05, "cost": 30000,  "req_ores": 5000},
    5: {"name": "念能力瞬間轉移", "tax": 0.02, "cost": 150000, "req_ores": 50000}
}

# 礦石市場
ORE_TYPES = ["煤礦", "鐵礦", "銀礦", "金礦", "星碎礦"]
ORE_EMOJIS = ["🪨", "🔗", "🥈", "🥇", "💎"]
PRICE_RANGE = {
    "煤礦": (6, 15),
    "鐵礦": (18, 45),
    "銀礦": (70, 160),
    "金礦": (250, 650),
    "星碎礦": (1000, 2800)
}

# 1個礦工每 10 分鐘挖出 1 顆礦石
MINE_CYCLE_SECONDS = 600

# ==========================================
# 🧠 系統核心引擎
# ==========================================

def update_market_if_needed():
    """每 2 小時 (偶數整點) 刷新一次全服礦石價格"""
    m_data = load_json(MINE_FILE)
    if "market" not in m_data:
        m_data["market"] = {"prices": {}, "last_update": 0}

    now = datetime.datetime.now()
    even_hour = now.hour if now.hour % 2 == 0 else now.hour - 1
    target_time = now.replace(hour=even_hour, minute=0, second=0, microsecond=0)
    target_ts = target_time.timestamp()

    if m_data["market"]["last_update"] != target_ts:
        m_data["market"]["last_update"] = target_ts
        for ore in ORE_TYPES:
            min_p, max_p = PRICE_RANGE[ore]
            m_data["market"]["prices"][ore] = random.randint(min_p, max_p)
        save_json(MINE_FILE, m_data)

    return m_data["market"]

def calculate_afk_mining(user_id):
    """計算並結算掛機挖礦"""
    m_data = load_json(MINE_FILE)
    if "players" not in m_data:
        m_data["players"] = {}

    if user_id not in m_data["players"]:
        m_data["players"][user_id] = {
            "miners": 1,
            "mine_lv": 1,
            "wh_lv": 1,
            "cart_lv": 1,
            "ores": {ore: 0 for ore in ORE_TYPES},
            "last_mine_time": time.time(),
            "total_mined": 0  # 🌟 新增累計挖礦數量，作為解鎖升級的條件
        }
        save_json(MINE_FILE, m_data)
        return m_data["players"][user_id]

    player = m_data["players"][user_id]

    # 確保舊玩家也有 total_mined 欄位
    if "total_mined" not in player:
        player["total_mined"] = 0

    current_time = time.time()
    time_passed = current_time - player["last_mine_time"]
    cycles = int(time_passed // MINE_CYCLE_SECONDS)

    if cycles > 0:
        current_ores = sum(player["ores"].values())
        max_cap = WH_LEVELS[player["wh_lv"]]["cap"]
        available_space = max_cap - current_ores

        if available_space > 0:
            mined_amount = cycles * player["miners"]
            actual_mined = min(mined_amount, available_space)

            probs = MINE_LEVELS[player["mine_lv"]]["probs"]
            weights = [p/100.0 for p in probs]

            for _ in range(actual_mined):
                ore_found = random.choices(ORE_TYPES, weights=weights, k=1)[0]
                player["ores"][ore_found] += 1

            # 🌟 增加累計挖礦次數
            player["total_mined"] += actual_mined

        player["last_mine_time"] += cycles * MINE_CYCLE_SECONDS
        save_json(MINE_FILE, m_data)

    return player

# ==========================================
# 🎮 控制面板 UI
# ==========================================

class MineControlView(discord.ui.View):
    def __init__(self, ctx, page="home"):
        super().__init__(timeout=180.0) # 3 分鐘後介面自動失效
        self.ctx = ctx
        self.user_id = str(ctx.author.id)
        self.page = page
        self.message = None

        self.market = update_market_if_needed()
        self.p_data = calculate_afk_mining(self.user_id)

        self.setup_buttons()

    # 🌟 新增：超時作廢處理機制
    async def on_timeout(self):
        self.clear_items() # 清空所有按鈕
        if self.message:
            embed = self.message.embeds[0]
            embed.color = discord.Color.dark_grey() # 變灰代表失效
            embed.set_footer(text="⚠️ 操作介面已過期，請重新輸入 !mine 喚醒。")
            try:
                await self.message.edit(embed=embed, view=self)
            except:
                pass

    def setup_buttons(self):
        self.clear_items()

        if self.page == "home":
            btn_market = discord.ui.Button(label="📦 進入倉庫與市場", style=discord.ButtonStyle.primary)
            btn_market.callback = self.go_market
            self.add_item(btn_market)

            btn_upgrade = discord.ui.Button(label="⬆️ 進入升級中心", style=discord.ButtonStyle.success)
            btn_upgrade.callback = self.go_upgrade
            self.add_item(btn_upgrade)

        elif self.page == "market":
            # 🌟 新增：分拆各種礦石的獨立賣出按鈕
            btn_coal = discord.ui.Button(label="賣煤礦", style=discord.ButtonStyle.secondary, row=0)
            btn_coal.callback = lambda i: self.sell_ores(i, "煤礦")
            self.add_item(btn_coal)

            btn_iron = discord.ui.Button(label="賣鐵礦", style=discord.ButtonStyle.secondary, row=0)
            btn_iron.callback = lambda i: self.sell_ores(i, "鐵礦")
            self.add_item(btn_iron)

            btn_silver = discord.ui.Button(label="賣銀礦", style=discord.ButtonStyle.secondary, row=0)
            btn_silver.callback = lambda i: self.sell_ores(i, "銀礦")
            self.add_item(btn_silver)

            btn_gold = discord.ui.Button(label="賣金礦", style=discord.ButtonStyle.secondary, row=1)
            btn_gold.callback = lambda i: self.sell_ores(i, "金礦")
            self.add_item(btn_gold)

            btn_star = discord.ui.Button(label="賣星碎礦", style=discord.ButtonStyle.secondary, row=1)
            btn_star.callback = lambda i: self.sell_ores(i, "星碎礦")
            self.add_item(btn_star)

            btn_sell_all = discord.ui.Button(label="💰 全部賣出", style=discord.ButtonStyle.success, row=2)
            btn_sell_all.callback = lambda i: self.sell_ores(i, "all")
            self.add_item(btn_sell_all)

            btn_home = discord.ui.Button(label="🏠 回首頁", style=discord.ButtonStyle.primary, row=2)
            btn_home.callback = self.go_home
            self.add_item(btn_home)

        elif self.page == "upgrade":
            btn_u1 = discord.ui.Button(label="招募礦工", style=discord.ButtonStyle.primary, row=0)
            btn_u1.callback = lambda i: self.do_upgrade(i, "miners")
            self.add_item(btn_u1)

            btn_u2 = discord.ui.Button(label="升級礦坑", style=discord.ButtonStyle.primary, row=0)
            btn_u2.callback = lambda i: self.do_upgrade(i, "mine_lv")
            self.add_item(btn_u2)

            btn_u3 = discord.ui.Button(label="擴建倉庫", style=discord.ButtonStyle.primary, row=0)
            btn_u3.callback = lambda i: self.do_upgrade(i, "wh_lv")
            self.add_item(btn_u3)

            btn_u4 = discord.ui.Button(label="升級礦車", style=discord.ButtonStyle.primary, row=1)
            btn_u4.callback = lambda i: self.do_upgrade(i, "cart_lv")
            self.add_item(btn_u4)

            btn_home = discord.ui.Button(label="🏠 回首頁", style=discord.ButtonStyle.secondary, row=1)
            btn_home.callback = self.go_home
            self.add_item(btn_home)

    def generate_embed(self):
        self.p_data = calculate_afk_mining(self.user_id)

        embed = discord.Embed(color=0xf1c40f)
        embed.set_author(name=f"🏭 {self.ctx.author.display_name} 的地下礦業", icon_url=self.ctx.author.display_avatar.url)

        if self.page == "home":
            embed.title = "🏠 礦場首頁"
            current_ores = sum(self.p_data["ores"].values())
            max_cap = WH_LEVELS[self.p_data["wh_lv"]]["cap"]
            perc = int((current_ores / max_cap) * 10) if max_cap > 0 else 10
            bar = "█" * perc + "░" * (10 - perc)

            mine_name = MINE_LEVELS[self.p_data['mine_lv']]['name']
            cart_name = CART_LEVELS[self.p_data['cart_lv']]['name']
            tax_rate = CART_LEVELS[self.p_data['cart_lv']]['tax'] * 100

            desc = (
                f"👷 **礦工陣容**：{self.p_data['miners']} 人 (產能: {self.p_data['miners']} 顆 / 10分鐘)\n"
                f"🕳️ **目前礦坑**：{mine_name} (Lv.{self.p_data['mine_lv']})\n"
                f"📦 **倉庫狀態**：[{bar}] {current_ores} / {max_cap}\n"
                f"🚂 **運輸稅率**：{int(tax_rate)}% ({cart_name})\n\n"
                f"⛏️ *生涯累計挖出：{self.p_data.get('total_mined', 0)} 顆礦石*"
            )
            embed.description = desc

        elif self.page == "market":
            embed.title = "📈 倉庫與浮動市場"

            now = datetime.datetime.now()
            next_even_hour = now.hour + 2 if now.hour % 2 == 0 else now.hour + 1
            if next_even_hour >= 24:
                next_time = now.replace(day=now.day+1, hour=0, minute=0, second=0) if now.day < 28 else now + datetime.timedelta(hours=2)
                next_time = next_time.replace(hour=0, minute=0, second=0)
            else:
                next_time = now.replace(hour=next_even_hour, minute=0, second=0)

            time_left = int((next_time - now).total_seconds())
            mins, secs = divmod(time_left, 60)

            desc = f"🕒 *下次價格刷新：{mins}分 {secs}秒後*\n\n"

            total_value = 0
            for i, ore in enumerate(ORE_TYPES):
                qty = self.p_data["ores"][ore]
                price = self.market["prices"].get(ore, 0)
                total_value += qty * price
                desc += f"{ORE_EMOJIS[i]} **{ore}**：{qty} 顆 (目前市價: **{price}** /顆)\n"

            tax_rate = CART_LEVELS[self.p_data['cart_lv']]['tax']
            final_value = int(total_value * (1 - tax_rate))

            desc += f"\n💰 **預估總價值**：{total_value} 傑尼幣<:emoji_1:1127882888508088393>\n"
            desc += f"🧾 **扣稅後實拿**：**{final_value}** 傑尼幣<:emoji_1:1127882888508088393> (稅率 {int(tax_rate*100)}%)"
            embed.description = desc

        elif self.page == "upgrade":
            embed.title = "⬆️ 升級中心"
            c_data = load_json(DATA_FILE)
            wallet = c_data.get(self.user_id, {}).get("傑尼幣", 0)
            total_m = self.p_data.get("total_mined", 0)

            # 準備各項目的顯示文字 (包含金錢與條件)
            m_lv = self.p_data["miners"]
            if m_lv < 10:
                cost_m = f"**{MINER_COSTS[m_lv]}**"
                req_m = MINER_REQS[m_lv]
                status_m = f"需累計挖礦 {req_m} 顆" if total_m < req_m else "✅ 條件達成"
            else:
                cost_m, status_m = "MAX", "MAX"

            mine_lv = self.p_data["mine_lv"]
            if mine_lv < 5:
                cost_mine = f"**{MINE_LEVELS[mine_lv+1]['cost']}**"
                req_mine = MINE_LEVELS[mine_lv+1]['req_ores']
                status_mine = f"需累計挖礦 {req_mine} 顆" if total_m < req_mine else "✅ 條件達成"
            else:
                cost_mine, status_mine = "MAX", "MAX"

            wh_lv = self.p_data["wh_lv"]
            if wh_lv < 7:
                cost_wh = f"**{WH_LEVELS[wh_lv+1]['cost']}**"
                req_wh = WH_LEVELS[wh_lv+1]['req_ores']
                status_wh = f"需累計挖礦 {req_wh} 顆" if total_m < req_wh else "✅ 條件達成"
            else:
                cost_wh, status_wh = "MAX", "MAX"

            cart_lv = self.p_data["cart_lv"]
            if cart_lv < 5:
                cost_cart = f"**{CART_LEVELS[cart_lv+1]['cost']}**"
                req_cart = CART_LEVELS[cart_lv+1]['req_ores']
                status_cart = f"需累計挖礦 {req_cart} 顆" if total_m < req_cart else "✅ 條件達成"
            else:
                cost_cart, status_cart = "MAX", "MAX"

            desc = f"💳 你的餘額：**{wallet}** 傑尼幣<:emoji_1:1127882888508088393>\n⛏️ 生涯累計挖出：**{total_m}** 顆\n\n"
            desc += f"1️⃣ **招募礦工** (Lv.{m_lv})\n➔ 費用: {cost_m} | {status_m}\n\n"
            desc += f"2️⃣ **升級礦坑** (Lv.{mine_lv})\n➔ 費用: {cost_mine} | {status_mine}\n\n"
            desc += f"3️⃣ **擴建倉庫** (Lv.{wh_lv})\n➔ 費用: {cost_wh} | {status_wh}\n\n"
            desc += f"4️⃣ **升級礦車** (Lv.{cart_lv})\n➔ 費用: {cost_cart} | {status_cart}\n"
            embed.description = desc

        return embed

    async def update_message(self, interaction):
        self.setup_buttons()
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

    async def go_home(self, interaction):
        if interaction.user.id != self.ctx.author.id: return
        self.page = "home"
        await self.update_message(interaction)

    async def go_market(self, interaction):
        if interaction.user.id != self.ctx.author.id: return
        self.page = "market"
        await self.update_message(interaction)

    async def go_upgrade(self, interaction):
        if interaction.user.id != self.ctx.author.id: return
        self.page = "upgrade"
        await self.update_message(interaction)

    async def sell_ores(self, interaction, target_ore):
        if interaction.user.id != self.ctx.author.id: return

        # 防呆檢查庫存
        if target_ore == "all":
            current_ores = sum(self.p_data["ores"].values())
            if current_ores == 0:
                return await interaction.response.send_message("⚠️ 你的倉庫空空如也，沒有東西可以賣！", ephemeral=True)
        else:
            if self.p_data["ores"][target_ore] == 0:
                return await interaction.response.send_message(f"⚠️ 你的倉庫裡沒有 **{target_ore}** 可以賣！", ephemeral=True)

        # 結算金額
        total_value = 0
        if target_ore == "all":
            for ore in ORE_TYPES:
                qty = self.p_data["ores"][ore]
                price = self.market["prices"].get(ore, 0)
                total_value += qty * price
        else:
            qty = self.p_data["ores"][target_ore]
            price = self.market["prices"].get(target_ore, 0)
            total_value += qty * price

        tax_rate = CART_LEVELS[self.p_data['cart_lv']]['tax']
        final_value = int(total_value * (1 - tax_rate))

        # 存入玩家錢包
        c_data = load_json(DATA_FILE)
        if self.user_id not in c_data:
            return await interaction.response.send_message("⚠️ 你還沒註冊獵人執照！(請輸入 !面板)", ephemeral=True)
        c_data[self.user_id]["傑尼幣"] = c_data[self.user_id].get("傑尼幣", 0) + final_value
        save_json(DATA_FILE, c_data)

        # 扣除被賣掉的礦石
        m_data = load_json(MINE_FILE)
        if target_ore == "all":
            for ore in ORE_TYPES:
                m_data["players"][self.user_id]["ores"][ore] = 0
        else:
            m_data["players"][self.user_id]["ores"][target_ore] = 0
        save_json(MINE_FILE, m_data)

        msg = f"✅ **交易成功！** 成功賣出礦石，實拿 **{final_value}** 傑尼幣<:emoji_1:1127882888508088393>！"
        await interaction.response.send_message(msg, ephemeral=True)
        self.p_data = calculate_afk_mining(self.user_id) 
        await self.update_message(interaction)

    async def do_upgrade(self, interaction, target):
        if interaction.user.id != self.ctx.author.id: return

        c_data = load_json(DATA_FILE)
        wallet = c_data.get(self.user_id, {}).get("傑尼幣", 0)
        total_m = self.p_data.get("total_mined", 0)

        current_lv = self.p_data[target]
        cost = 0
        req = 0
        max_lv = False

        if target == "miners":
            if current_lv >= 10: max_lv = True
            else: cost, req = MINER_COSTS[current_lv], MINER_REQS[current_lv]
        elif target == "mine_lv":
            if current_lv >= 5: max_lv = True
            else: cost, req = MINE_LEVELS[current_lv+1]["cost"], MINE_LEVELS[current_lv+1]["req_ores"]
        elif target == "wh_lv":
            if current_lv >= 7: max_lv = True
            else: cost, req = WH_LEVELS[current_lv+1]["cost"], WH_LEVELS[current_lv+1]["req_ores"]
        elif target == "cart_lv":
            if current_lv >= 5: max_lv = True
            else: cost, req = CART_LEVELS[current_lv+1]["cost"], CART_LEVELS[current_lv+1]["req_ores"]

        if max_lv:
            return await interaction.response.send_message("⚠️ 該項目已經達到最高等級！", ephemeral=True)

        # 🌟 雙重檢查：金額與挖礦數量
        if total_m < req:
            return await interaction.response.send_message(f"⚠️ **經驗不足！** 該項目需累計挖滿 {req} 顆礦石才能解鎖。", ephemeral=True)
        if wallet < cost:
            return await interaction.response.send_message(f"⚠️ **餘額不足！** 升級需要 {cost} 傑尼幣<:emoji_1:1127882888508088393>。", ephemeral=True)

        # 扣錢與升級
        c_data[self.user_id]["傑尼幣"] = max(0, wallet - cost)
        save_json(DATA_FILE, c_data)

        m_data = load_json(MINE_FILE)
        m_data["players"][self.user_id][target] += 1
        save_json(MINE_FILE, m_data)

        await interaction.response.send_message(f"✅ **升級成功！** 扣除 {cost} 傑尼幣<:emoji_1:1127882888508088393>。", ephemeral=True)
        self.p_data = calculate_afk_mining(self.user_id) 
        await self.update_message(interaction)


# ==========================================
# 🚀 遊戲主控台註冊
# ==========================================

class MiningGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["礦場", "礦坑", "礦"])
    async def mine(self, ctx):
        data = load_json(DATA_FILE)
        if str(ctx.author.id) not in data:
            return await ctx.reply("⚠️ **你還沒註冊！** 請先輸入 `!面板` 建立你的獵人資料！")

        view = MineControlView(ctx, page="home")
        # 🌟 將回覆的 message 綁定給 view，供 on_timeout 修改使用
        view.message = await ctx.reply(embed=view.generate_embed(), view=view)

async def setup(bot):
    await bot.add_cog(MiningGame(bot))