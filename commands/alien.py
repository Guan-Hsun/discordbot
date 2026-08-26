from discord.ext import commands
import io
from PIL import Image
import math


class Alien(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def alien(self, ctx):
        if not ctx.message.attachments:
            await ctx.reply(
                "⚠️ 沒有偵測到圖片！請在「上傳圖片的同時」，在附註欄位輸入 `!alien`。"
            )
            return

        attachment = ctx.message.attachments[0]
        if not attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            await ctx.reply("⚠️ 這似乎不是支援的圖片格式喔！")
            return

        # 先發送一則處理中的訊息，稍後算出答案會直接編輯這則訊息
        processing_msg = await ctx.reply("🔍 正在解析圖片並計算外星人位置，請稍候...")

        try:
            image_bytes = await attachment.read()
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            width, height = img.size
            cell_w = width / 9
            cell_h = height / 9

            grid_array = []
            seen_colors = []

            for row in range(9):
                row_data = []
                for col in range(9):
                    start_x = col * cell_w
                    start_y = row * cell_h

                    r, g, b = self.get_dominant_color(
                        img, start_x, start_y, cell_w, cell_h
                    )
                    color_id = self.classify_color((r, g, b), seen_colors)
                    row_data.append(color_id)

                grid_array.append(row_data)

            # 在終端機印出 9x9 陣列，方便你除錯
            # print("\n✅ 圖片解析完成，產生的 9x9 陣列如下：")
            # for r in grid_array:
            #     print(r)

            # ==========================================
            # 🚀 進入解答邏輯
            # ==========================================
            solution = self.solve_alien_puzzle(grid_array)

            if solution:
                # 格式化輸出
                # row 是 0~8，轉換為 1~9
                # col 是 0~8，轉換為 A~I (ASCII 碼 65 是 'A')
                result_texts = []
                for r, c in solution:
                    col_letter = chr(c + 65)
                    row_num = r + 1
                    result_texts.append(f"**{col_letter}{row_num}**")

                # 把陣列組合成分號隔開的字串
                final_answer = "、".join(result_texts)

                # 編輯原本那則「處理中」的訊息，公布答案！
                await processing_msg.edit(
                    content=f"✅ **計算成功！** 狙擊任務座標如下：\n\n👽 外星人的位置分別在： {final_answer}"
                )
            else:
                await processing_msg.edit(
                    content="⚠️ 圖片解析成功，但**找不到符合規則的解答**。可能是圖片裁切有誤差導致顏色分類錯誤。"
                )

        except Exception as e:
            await processing_msg.edit(content=f"❌ 處理圖片時發生錯誤：`{e}`")

    def solve_alien_puzzle(self, grid):
        """使用回溯法 (Backtracking) 來找出外星人的位置"""
        alien_positions = []

        def backtrack(row, cols_used, cats_used):
            # 如果已經成功填滿 9 個 row，代表找到答案了！
            if row == 9:
                return True

            for col in range(9):
                cat = grid[row][col]

                # 規則 2 & 3：檢查這個直排 (Column) 或是這個顏色 (Category) 是不是已經有外星人了
                if col in cols_used or cat in cats_used:
                    continue

                # 規則 4：檢查周圍 8 格有沒有其他外星人
                conflict = False
                for r, c in alien_positions:
                    # 只要兩點的 X 距離與 Y 距離都在 1 以內，就是相鄰或對角線相連
                    if abs(row - r) <= 1 and abs(col - c) <= 1:
                        conflict = True
                        break
                if conflict:
                    continue

                # 所有條件都符合，把外星人暫時放在這裡
                alien_positions.append((row, col))
                cols_used.add(col)
                cats_used.add(cat)

                # 遞迴：繼續往下一列 (row + 1) 尋找
                if backtrack(row + 1, cols_used, cats_used):
                    return True

                # 如果這條路不通（底下的 row 找不到合適的位子），就把這個外星人拔掉 (回溯)，試下一個 column
                alien_positions.pop()
                cols_used.remove(col)
                cats_used.remove(cat)

            # 這一個 row 所有的 column 都試過了還是不行，回傳 False 讓上一層去換位子
            return False

        # 從第 0 列開始找，傳入空的 set 來記錄用過的 column 和顏色
        if backtrack(0, set(), set()):
            return alien_positions
        else:
            return None

    # ======= 影像處理輔助函式保持不變 =======
    def get_dominant_color(self, img, start_x, start_y, cell_w, cell_h):
        min_x = int(start_x + cell_w * 0.25)
        max_x = int(start_x + cell_w * 0.75)
        min_y = int(start_y + cell_h * 0.60)
        max_y = int(start_y + cell_h * 0.85)
        bg_color = img.getpixel(
            (int(start_x + cell_w * 0.05), int(start_y + cell_h * 0.05))
        )
        color_votes = []
        for y in range(min_y, max_y, 2):
            for x in range(min_x, max_x, 2):
                if x >= img.width or y >= img.height:
                    continue
                r, g, b = img.getpixel((x, y))
                dist_bg = math.sqrt(
                    (r - bg_color[0]) ** 2
                    + (g - bg_color[1]) ** 2
                    + (b - bg_color[2]) ** 2
                )
                if dist_bg < 50:
                    continue
                if r < 60 and g < 60 and b < 60:
                    continue
                found_group = False
                for group in color_votes:
                    ref_r, ref_g, ref_b = group[0]
                    dist = math.sqrt(
                        (r - ref_r) ** 2 + (g - ref_g) ** 2 + (b - ref_b) ** 2
                    )
                    if dist < 45:
                        group.append((r, g, b))
                        found_group = True
                        break
                if not found_group:
                    color_votes.append([(r, g, b)])
        if not color_votes:
            return (0, 0, 0)
        color_votes.sort(key=len, reverse=True)
        largest_group = color_votes[0]
        avg_r = sum(c[0] for c in largest_group) // len(largest_group)
        avg_g = sum(c[1] for c in largest_group) // len(largest_group)
        avg_b = sum(c[2] for c in largest_group) // len(largest_group)
        return (avg_r, avg_g, avg_b)

    def classify_color(self, rgb, seen_colors, threshold=30):
        for i, c in enumerate(seen_colors):
            dist = math.sqrt(
                (rgb[0] - c[0]) ** 2 + (rgb[1] - c[1]) ** 2 + (rgb[2] - c[2]) ** 2
            )
            if dist < threshold:
                return i + 1
        seen_colors.append(rgb)
        return len(seen_colors)


async def setup(bot):
    await bot.add_cog(Alien(bot))
