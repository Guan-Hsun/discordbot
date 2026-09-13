import discord
from discord.ext import commands
import random
import io
import asyncio
from PIL import Image, ImageDraw, ImageFont

from json_manager import load_json, save_json

DATA_FILE = "data.json"
JENNY_EMOJI = "<:emoji_1:1127882888508088393>"

# ==========================================
# 📊 遊戲獎勵設定
# ==========================================
ENTRY_FEE = 50
SHUFFLE_FEE = 150

REWARD_TABLE = {
    2048: 400,
    1024: 240,
    512: 150,
    256: 80,
    128: 50,
    64: 30,
    32: 20,
    16: 10
}

# ==========================================
# 🎨 Pillow 2048 繪圖引擎
# ==========================================
COLORS = {
    0: ("#cdc1b4", "#cdc1b4"),
    2: ("#eee4da", "#776e65"),
    4: ("#ede0c8", "#776e65"),
    8: ("#f2b179", "#f9f6f2"),
    16: ("#f59563", "#f9f6f2"),
    32: ("#f67c5f", "#f9f6f2"),
    64: ("#f65e3b", "#f9f6f2"),
    128: ("#edcf72", "#f9f6f2"),
    256: ("#edcc61", "#f9f6f2"),
    512: ("#edc850", "#f9f6f2"),
    1024: ("#edc53f", "#f9f6f2"),
    2048: ("#edc22e", "#f9f6f2"),
}

def render_2048_board(board):
    cell_size = 100
    padding = 15
    width = 4 * cell_size + 5 * padding

    img = Image.new('RGB', (width, width), color='#bbada0')
    draw = ImageDraw.Draw(img)

    # 🌟 修正點 1：跨平台大字型支援 (優先尋找 Replit 支援的字體)
    font = None
    target_size = 55 # 放大字體
    font_candidates = ["arial.ttf", "DejaVuSans.ttf", "FreeSans.ttf", "LiberationSans-Regular.ttf"]

    for font_name in font_candidates:
        try:
            font = ImageFont.truetype(font_name, target_size)
            break
        except IOError:
            continue

    if font is None:
        try:
            # Pillow 10+ 支援預設字體大小調整
            font = ImageFont.load_default(size=target_size)
        except TypeError:
            font = ImageFont.load_default()

    for r in range(4):
        for c in range(4):
            val = board[r][c]
            x0 = padding + c * (cell_size + padding)
            y0 = padding + r * (cell_size + padding)
            x1 = x0 + cell_size
            y1 = y0 + cell_size

            bg_color, fg_color = COLORS.get(val, ("#3c3a32", "#f9f6f2"))
            draw.rounded_rectangle([x0, y0, x1, y1], radius=10, fill=bg_color)

            if val > 0:
                text = str(val)
                # 取得文字寬高以進行置中
                bbox = draw.textbbox((0, 0), text, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                tx = x0 + (cell_size - tw) / 2
                ty = y0 + (cell_size - th) / 2 - (th / 4) # 微調 Y 軸視覺置中
                draw.text((tx, ty), text, fill=fg_color, font=font)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

# ==========================================
# 🧠 2048 核心邏輯
# ==========================================
class Board2048:
    def __init__(self):
        self.grid = [[0]*4 for _ in range(4)]
        self.add_new_tile()
        self.add_new_tile()

    def add_new_tile(self):
        empty_cells = [(r, c) for r in range(4) for c in range(4) if self.grid[r][c] == 0]
        if empty_cells:
            r, c = random.choice(empty_cells)
            self.grid[r][c] = 2 if random.random() < 0.9 else 4

    def get_max_tile(self):
        return max(max(row) for row in self.grid)

    def is_game_over(self):
        for r in range(4):
            for c in range(4):
                if self.grid[r][c] == 0: return False
                if c < 3 and self.grid[r][c] == self.grid[r][c+1]: return False
                if r < 3 and self.grid[r][c] == self.grid[r+1][c]: return False
        return True

    def slide_left(self, grid):
        new_grid = []
        changed = False
        for row in grid:
            new_row = [v for v in row if v != 0]
            merged_row = []
            skip = False
            for i in range(len(new_row)):
                if skip:
                    skip = False
                    continue
                if i < len(new_row) - 1 and new_row[i] == new_row[i+1]:
                    merged_row.append(new_row[i] * 2)
                    skip = True
                else:
                    merged_row.append(new_row[i])
            merged_row += [0] * (4 - len(merged_row))
            if merged_row != row: changed = True
            new_grid.append(merged_row)
        return new_grid, changed

    def transpose(self, grid):
        return [list(row) for row in zip(*grid)]

    def reverse(self, grid):
        return [row[::-1] for row in grid]

    def move(self, direction):
        changed = False
        if direction == 'LEFT':
            self.grid, changed = self.slide_left(self.grid)
        elif direction == 'RIGHT':
            self.grid = self.reverse(self.grid)
            self.grid, changed = self.slide_left(self.grid)
            self.grid = self.reverse(self.grid)
        elif direction == 'UP':
            self.grid = self.transpose(self.grid)
            self.grid, changed = self.slide_left(self.grid)
            self.grid = self.transpose(self.grid)
        elif direction == 'DOWN':
            self.grid = self.transpose(self.grid)
            self.grid = self.reverse(self.grid)
            self.grid, changed = self.slide_left(self.grid)
            self.grid = self.reverse(self.grid)
            self.grid = self.transpose(self.grid)

        if changed:
            self.add_new_tile()
        return changed

    def shuffle(self):
        tiles = [v for row in self.grid for v in row if v != 0]
        random.shuffle(tiles)
        tiles += [0] * (16 - len(tiles))
        self.grid = [tiles[i*4:(i+1)*4] for i in range(4)]

# ==========================================
# 🎮 控制面板 UI
# ==========================================
class Game2048View(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=90.0)
        self.ctx = ctx
        self.author_id = ctx.author.id
        self.game = Board2048()
        self.message = None
        # 🌟 修正點 2：避免與 discord.py 內建的 is_finished 方法名稱衝突
        self.has_settled = False 

    async def update_board(self, interaction, custom_msg=None):
        if self.has_settled: return

        if self.game.is_game_over() or self.game.get_max_tile() >= 2048:
            return await self.settle_game(interaction)

        img_buf = render_2048_board(self.game.grid)
        file = discord.File(img_buf, filename="2048.png")

        embed = discord.Embed(title="🧩 2048 挑戰", color=0x3498db)
        embed.set_image(url="attachment://2048.png")

        max_val = self.game.get_max_tile()
        desc = f"**目前最高分塊**：{max_val}\n"
        if custom_msg: desc += f"\n🔔 {custom_msg}"
        embed.description = desc

        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

    async def settle_game(self, interaction=None):
        if self.has_settled: return
        self.has_settled = True
        self.clear_items()

        max_val = self.game.get_max_tile()
        reward = 0
        for threshold, rwd in sorted(REWARD_TABLE.items(), reverse=True):
            if max_val >= threshold:
                reward = rwd
                break

        data = load_json(DATA_FILE)
        user_id = str(self.author_id)

        data[user_id]["傑尼幣"] = data[user_id].get("傑尼幣", 0) + reward
        if max_val >= 128:
            data[user_id]["經驗值"] = data[user_id].get("經驗值", 0) + 1

        save_json(DATA_FILE, data)

        img_buf = render_2048_board(self.game.grid)
        file = discord.File(img_buf, filename="2048.png")

        embed = discord.Embed(title="🏁 2048 結算", color=0xf1c40f)
        embed.set_image(url="attachment://2048.png")
        embed.description = f"**最終最高分塊**：{max_val}\n💰 結算獲得 **{reward}** {JENNY_EMOJI}"

        if interaction:
            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
        elif self.message:
            await self.message.edit(embed=embed, attachments=[file], view=self)
        self.stop()

    async def handle_move(self, interaction, direction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ 這不是你的遊戲！", ephemeral=True)

        changed = self.game.move(direction)
        if changed:
            await self.update_board(interaction)
        else:
            await interaction.response.defer()

    @discord.ui.button(emoji="⬆️", style=discord.ButtonStyle.primary, row=0)
    async def btn_up(self, interaction, button):
        await self.handle_move(interaction, 'UP')

    @discord.ui.button(emoji="⬇️", style=discord.ButtonStyle.primary, row=0)
    async def btn_down(self, interaction, button):
        await self.handle_move(interaction, 'DOWN')

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.primary, row=0)
    async def btn_left(self, interaction, button):
        await self.handle_move(interaction, 'LEFT')

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.primary, row=0)
    async def btn_right(self, interaction, button):
        await self.handle_move(interaction, 'RIGHT')

    @discord.ui.button(label="🔀 洗牌 (150幣)", style=discord.ButtonStyle.danger, row=1)
    async def btn_shuffle(self, interaction, button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ 這不是你的遊戲！", ephemeral=True)

        data = load_json(DATA_FILE)
        user_id = str(self.author_id)
        if data.get(user_id, {}).get("傑尼幣", 0) < SHUFFLE_FEE:
            return await interaction.response.send_message(f"⚠️ 餘額不足 {SHUFFLE_FEE} {JENNY_EMOJI}！", ephemeral=True)

        data[user_id]["傑尼幣"] -= SHUFFLE_FEE
        save_json(DATA_FILE, data)

        self.game.shuffle()
        await self.update_board(interaction, f"已花費 {SHUFFLE_FEE} {JENNY_EMOJI} 重新洗牌！")

    @discord.ui.button(label="✅ 結算離場", style=discord.ButtonStyle.success, row=1)
    async def btn_settle(self, interaction, button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ 這不是你的遊戲！", ephemeral=True)
        await self.settle_game(interaction)

    async def on_timeout(self):
        if not self.has_settled:
            await self.settle_game()

# ==========================================
# 🚀 遊戲主入口
# ==========================================
class Play2048(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_players = set()

    @commands.hybrid_command(name="2048", description=f"花費 {ENTRY_FEE} 傑尼幣遊玩 2048，最高可贏回 400 幣！")
    async def start_2048(self, ctx: commands.Context):
        user_id = str(ctx.author.id)

        if user_id in self.active_players:
            return await ctx.reply("⚠️ 你已經有一場遊戲正在進行中囉！", ephemeral=True)

        data = load_json(DATA_FILE)
        if user_id not in data:
            return await ctx.reply("⚠️ **你還沒註冊！** 請先使用 `/profile` 建立你的獵人資料！", ephemeral=True)

        if data[user_id].get("傑尼幣", 0) < ENTRY_FEE:
            return await ctx.reply(f"⚠️ **餘額不足！** 需要 {ENTRY_FEE} {JENNY_EMOJI} 入場費。", ephemeral=True)

        data[user_id]["傑尼幣"] -= ENTRY_FEE
        save_json(DATA_FILE, data)
        self.active_players.add(user_id)

        try:
            view = Game2048View(ctx)
            img_buf = render_2048_board(view.game.grid)
            file = discord.File(img_buf, filename="2048.png")

            embed = discord.Embed(title="🧩 2048 挑戰", description="**目前最高分塊**：2", color=0x3498db)
            embed.set_image(url="attachment://2048.png")

            view.message = await ctx.reply(embed=embed, file=file, view=view)

            # 等待 View 結束 (Timeout或結算) 以解鎖玩家狀態
            await view.wait()
        except Exception as e:
            await ctx.send(f"❌ 發生錯誤，已強制結束遊戲：`{e}`", ephemeral=True)
        finally:
            self.active_players.discard(user_id)

async def setup(bot):
    await bot.add_cog(Play2048(bot))