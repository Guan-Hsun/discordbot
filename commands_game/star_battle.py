import discord
from discord.ext import commands
import random
import io
import itertools
from PIL import Image, ImageDraw, ImageFont

from json_manager import load_json, save_json

DATA_FILE = "data.json"

# ==========================================
# 📊 遊戲數值設定 (Config)
# ==========================================
GAME_SIZE = 7  # 🌟 透過這個變數控制棋盤大小，目前完美支援最高 10x10

# ==========================================
# 🧠 星際之戰 核心引擎
# ==========================================
def get_valid_star_sets(size):
    """找出棋盤中，所有合法的星星配置 (每行每列1顆，且互不相鄰包含對角線)"""
    sets = []
    for p in itertools.permutations(range(size)):
        valid = True
        for r in range(size - 1):
            if abs(p[r] - p[r+1]) <= 1:
                valid = False
                break
        if valid:
            sets.append([(r, p[r]) for r in range(size)])
    return sets

def count_solutions(regions, valid_sets, size):
    """計算目前的區域劃分有幾種合法解答"""
    count = 0
    for s in valid_sets:
        region_counts = set(regions[r][c] for r, c in s)
        if len(region_counts) == size: 
            count += 1
    return count

def generate_puzzle(size):
    """生成具有唯一解的星際之戰謎題 (確保區域 >= 3格)"""
    valid_sets = get_valid_star_sets(size)

    while True:
        stars = random.choice(valid_sets)
        regions = [[-1]*size for _ in range(size)]

        for i, (r, c) in enumerate(stars):
            regions[r][c] = i

        empty_cells = [(r, c) for r in range(size) for c in range(size) if regions[r][c] == -1]
        random.shuffle(empty_cells)

        progress = True
        while empty_cells and progress:
            progress = False
            for i in range(len(empty_cells)-1, -1, -1):
                r, c = empty_cells[i]
                neighbors = []
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < size and 0 <= nc < size and regions[nr][nc] != -1:
                        neighbors.append(regions[nr][nc])
                if neighbors:
                    regions[r][c] = random.choice(neighbors)
                    empty_cells.pop(i)
                    progress = True

        if empty_cells: continue 

        region_sizes = [0] * size
        for r in range(size):
            for c in range(size):
                if regions[r][c] != -1:
                    region_sizes[regions[r][c]] += 1

        if any(sz < 3 for sz in region_sizes):
            continue

        if count_solutions(regions, valid_sets, size) == 1:
            return regions, stars

# ==========================================
# 🎨 繪圖引擎 (使用 Pillow)
# ==========================================
def draw_star(draw, cx, cy, size, color="gold"):
    import math
    points = []
    for i in range(10):
        angle = i * math.pi / 5 - math.pi / 2
        radius = size if i % 2 == 0 else size / 2.5
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=color)

def draw_cross(draw, cx, cy, size, color="red"):
    draw.line((cx-size, cy-size, cx+size, cy+size), fill=color, width=3)
    draw.line((cx-size, cy+size, cx+size, cy-size), fill=color, width=3)

def create_board_image(regions, board_state, size, selected_r=None, selected_c=None):
    cell_size = 50
    margin = 30
    width = size * cell_size + margin
    height = size * cell_size + margin

    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    cols = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:size]
    for i in range(size):
        cx = margin + i * cell_size + cell_size // 2
        draw.text((cx - 4, 8), cols[i], fill="black", font=font)
        cy = margin + i * cell_size + cell_size // 2
        draw.text((10, cy - 4), str(i+1), fill="black", font=font)

    if selected_r is not None and selected_c is not None:
        sx = margin + selected_c * cell_size
        sy = margin + selected_r * cell_size
        draw.rectangle([sx, sy, sx+cell_size, sy+cell_size], fill="#fff3cd")

    for r in range(size):
        for c in range(size):
            x = margin + c * cell_size
            y = margin + r * cell_size
            draw.rectangle([x, y, x+cell_size, y+cell_size], outline="lightgray", width=1)

            mark = board_state[r][c]
            cx, cy = x + cell_size//2, y + cell_size//2
            if mark == 'S':
                draw_star(draw, cx, cy, 15, "gold")
            elif mark == 'X':
                draw_cross(draw, cx, cy, 12, "#e74c3c")

    for r in range(size):
        for c in range(size):
            x = margin + c * cell_size
            y = margin + r * cell_size
            if r == 0 or regions[r][c] != regions[r-1][c]:
                draw.line([x, y, x+cell_size, y], fill="black", width=4)
            if c == 0 or regions[r][c] != regions[r][c-1]:
                draw.line([x, y, x, y+cell_size], fill="black", width=4)
            if r == size - 1:
                draw.line([x, y+cell_size, x+cell_size, y+cell_size], fill="black", width=4)
            if c == size - 1:
                draw.line([x+cell_size, y, x+cell_size, y+cell_size], fill="black", width=4)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

# ==========================================
# 🎮 遊戲 UI 控制面板
# ==========================================
class CoordButton(discord.ui.Button):
    def __init__(self, label, custom_id, row):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, custom_id=custom_id, row=row)

    async def callback(self, interaction):
        view = self.view
        if interaction.user.id != view.author_id:
            return await interaction.response.send_message("❌ 這不是你的遊戲！", ephemeral=True)

        if self.custom_id.startswith('col_'):
            view.selected_col = int(self.custom_id.split('_')[1])
        else:
            view.selected_row = int(self.custom_id.split('_')[1])

        await view.update_display(interaction)

class ActionButton(discord.ui.Button):
    def __init__(self, label, style, custom_id, row):
        super().__init__(label=label, style=style, custom_id=custom_id, row=row)

    async def callback(self, interaction):
        view = self.view
        if interaction.user.id != view.author_id:
            return await interaction.response.send_message("❌ 這不是你的遊戲！", ephemeral=True)

        if self.custom_id == 'action_toggle':
            modes = ['S', 'X', 'C']
            labels = {'S': '模式: ⭐ (星星)', 'X': '模式: ❌ (打叉)', 'C': '模式: ⬜ (清除)'}
            idx = modes.index(view.mark_mode)
            view.mark_mode = modes[(idx + 1) % 3]
            self.label = labels[view.mark_mode]
            await view.update_display(interaction)

        elif self.custom_id == 'action_submit':
            await view.handle_submit(interaction)

class StarBattleGame(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=600.0)
        self.ctx = ctx
        self.size = GAME_SIZE
        self.author_id = ctx.author.id
        self.regions, self.secret_stars = generate_puzzle(self.size)
        self.board_state = [[' ']*self.size for _ in range(self.size)]

        self.selected_row = None
        self.selected_col = None
        self.mark_mode = 'S'
        self.mistakes = 0
        self.stars_found = 0
        self.message = None

        cols = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:self.size]

        # 動態產生英文字母按鈕 (滿 5 個自動換行)
        for i in range(self.size):
            row_idx = 0 if i < 5 else 1
            self.add_item(CoordButton(cols[i], f'col_{i}', row_idx))

        # 動態產生數字按鈕 (滿 5 個自動換行)
        for i in range(self.size):
            row_idx = 2 if i < 5 else 3
            self.add_item(CoordButton(str(i+1), f'row_{i}', row_idx))

        # 動作按鈕固定放在最後一排
        self.add_item(ActionButton('模式: ⭐ (星星)', discord.ButtonStyle.primary, 'action_toggle', 4))
        self.add_item(ActionButton('✅ 確認送出', discord.ButtonStyle.success, 'action_submit', 4))

    async def update_display(self, interaction):
        for item in self.children:
            if isinstance(item, CoordButton):
                if item.custom_id.startswith('col_'):
                    c = int(item.custom_id.split('_')[1])
                    item.style = discord.ButtonStyle.primary if self.selected_col == c else discord.ButtonStyle.secondary
                else:
                    r = int(item.custom_id.split('_')[1])
                    item.style = discord.ButtonStyle.primary if self.selected_row == r else discord.ButtonStyle.secondary

        img_buf = create_board_image(self.regions, self.board_state, self.size, self.selected_row, self.selected_col)
        file = discord.File(img_buf, filename="board.png")

        embed = discord.Embed(title=f"🌌 星際之戰 Star Battle ({self.size}x{self.size})", color=0x9b59b6)
        embed.description = f"**錯誤次數：** {self.mistakes} / 3\n**已找到星星：** {self.stars_found} / {self.size}"
        embed.set_image(url="attachment://board.png")

        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

    def auto_fill_x(self, r, c):
        region = self.regions[r][c]
        for i in range(self.size):
            for j in range(self.size):
                if (i, j) == (r, c) or self.board_state[i][j] == 'S': continue
                if self.regions[i][j] == region or i == r or j == c or (abs(i-r) <= 1 and abs(j-c) <= 1):
                    self.board_state[i][j] = 'X'

    async def handle_submit(self, interaction):
        if self.selected_row is None or self.selected_col is None:
            return await interaction.response.send_message("⚠️ 請先在上方選擇「英文字母」與「數字」座標！", ephemeral=True)

        r, c = self.selected_row, self.selected_col

        if self.mark_mode == 'S':
            if self.board_state[r][c] == 'S':
                return await interaction.response.send_message("⚠️ 這裡已經放星星了！", ephemeral=True)

            if (r, c) in self.secret_stars:
                self.board_state[r][c] = 'S'
                self.stars_found += 1
                self.auto_fill_x(r, c)

                if self.stars_found == self.size:
                    return await self.game_over(interaction, win=True)
            else:
                self.mistakes += 1
                if self.mistakes >= 3:
                    return await self.game_over(interaction, win=False)
                else:
                    await interaction.response.send_message("❌ **錯誤！** 這裡不能放星星，已增加錯誤次數！", ephemeral=True)

        elif self.mark_mode == 'X':
            self.board_state[r][c] = 'X'
        elif self.mark_mode == 'C':
            self.board_state[r][c] = ' '

        await self.update_display(interaction)

    async def game_over(self, interaction, win):
        for child in self.children:
            child.disabled = True 

        for r, c in self.secret_stars:
            self.board_state[r][c] = 'S'

        img_buf = create_board_image(self.regions, self.board_state, self.size)
        file = discord.File(img_buf, filename="board_final.png")

        embed = discord.Embed(title="🌌 星際之戰 - 遊戲結束", color=0x2ecc71 if win else 0xe74c3c)
        embed.set_image(url="attachment://board_final.png")

        if win:
            rewards = {0: 50, 1: 40, 2: 30}
            coins = rewards.get(self.mistakes, 0)

            data = load_json(DATA_FILE)
            user_id = str(self.author_id)
            data[user_id]["傑尼幣"] = data[user_id].get("傑尼幣", 0) + coins
            data[user_id]["經驗值"] = data[user_id].get("經驗值", 0) + 1
            save_json(DATA_FILE, data)

            embed.description = f"🎉 **過關！**\n你犯了 {self.mistakes} 次錯誤。\n獲得獎勵：**{coins}** 傑尼幣、**1** 🌟 經驗值！"
        else:
            embed.description = "💀 **挑戰失敗！**\n你已經標記錯誤 3 次，沒收獎勵，下次再接再厲！"

        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
        self.stop()

# ==========================================
# 🚪 遊戲入口
# ==========================================
class StarBattleEntry(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60.0)
        self.ctx = ctx

    @discord.ui.button(label=f"花費 30 傑尼幣開始 ({GAME_SIZE}x{GAME_SIZE})", style=discord.ButtonStyle.success)
    async def btn_start(self, interaction, button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ 請自己輸入指令開始遊戲！", ephemeral=True)

        data = load_json(DATA_FILE)
        user_id = str(self.ctx.author.id)

        if user_id not in data or data[user_id].get("傑尼幣", 0) < 30:
            return await interaction.response.send_message("⚠️ **餘額不足！** 需要 30 傑尼幣！", ephemeral=True)

        button.disabled = True
        button.label = "⏳ 生成地圖中，請稍候..."
        button.style = discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)

        data[user_id]["傑尼幣"] -= 30
        save_json(DATA_FILE, data)

        game_view = StarBattleGame(self.ctx)
        img_buf = create_board_image(game_view.regions, game_view.board_state, game_view.size)
        file = discord.File(img_buf, filename="board.png")

        embed = discord.Embed(title=f"🌌 星際之戰 Star Battle ({GAME_SIZE}x{GAME_SIZE})", color=0x9b59b6)
        embed.description = f"**錯誤次數：** 0 / 3\n**已找到星星：** 0 / {GAME_SIZE}"
        embed.set_image(url="attachment://board.png")

        await interaction.message.edit(embed=embed, attachments=[file], view=game_view)
        game_view.message = interaction.message
        self.stop()

class StarBattle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="starbattle", aliases=["星之戰", "star", "星"], description="花費 30 傑尼幣遊玩星際之戰，動腦破解盤面獲得獎金！")
    async def starbattle(self, ctx: commands.Context):
        rules = (
            f"1. 版面被粗線劃分為 {GAME_SIZE} 個「區域」。\n"
            "2. 每個 **橫列**、**直欄** 及 **區域** 中，都必須「剛好有 1 顆星星 ⭐」。\n"
            "3. **星星絕對不能相鄰**（包含斜對角線也不能碰到！）。\n\n"
            "🎯 **遊玩方式**：\n"
            "點擊下方按鈕選擇座標 (例如 A 1)，切換模式為星星 ⭐ 或 叉叉 ❌ 後按下確認。\n"
            "你共有 3 次標記星星錯誤的機會，根據錯誤次數發放對應獎金！"
        )
        embed = discord.Embed(title="🌌 星之戰 (Star Battle)", description=rules, color=0x3498db)
        await ctx.reply(embed=embed, view=StarBattleEntry(ctx))

async def setup(bot):
    await bot.add_cog(StarBattle(bot))