import discord
from discord.ext import commands
from json_manager import load_json, save_json

NOTES_FILE = "notes.json"

class NotePagination(discord.ui.View):
    def __init__(self, embeds, author_id):
        # timeout=180 代表按鈕 3 分鐘後會自動失效，節省機器人效能
        super().__init__(timeout=180) 
        self.embeds = embeds
        self.current_page = 0
        self.author_id = author_id

        # 初始化時先檢查要不要把「上一頁」反白(禁用)
        self.update_buttons()

    def update_buttons(self):
        # 如果是第 0 頁，就把「上一頁」按鈕鎖起來
        self.prev_btn.disabled = self.current_page == 0
        # 如果是最後一頁，就把「下一頁」按鈕鎖起來
        self.next_btn.disabled = self.current_page == len(self.embeds) - 1

    @discord.ui.button(label="⬅️ 上一頁", style=discord.ButtonStyle.primary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 防呆：避免別人亂按你的筆記
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ 這是別人的筆記，你不能翻喔！", ephemeral=True)
            return

        self.current_page -= 1
        self.update_buttons()
        # 編輯原本的訊息，把卡片換成上一頁的卡片
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="下一頁 ➡️", style=discord.ButtonStyle.primary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ 這是別人的筆記，你不能翻喔！", ephemeral=True)
            return

        self.current_page += 1
        self.update_buttons()
        # 編輯原本的訊息，把卡片換成下一頁的卡片
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


class Note(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def addnote(self, ctx, *, content: str):
        data = load_json(NOTES_FILE)
        user_id = str(ctx.author.id) 

        if user_id not in data:
            data[user_id] = []

        data[user_id].append(content)
        save_json(NOTES_FILE, data)

        await ctx.reply(f"✅ 已為 {ctx.author.mention} 新增筆記：\n{content}")

    @commands.command(aliases=["notes", "筆記"])
    async def note(self, ctx):
        data = load_json(NOTES_FILE)
        user_id = str(ctx.author.id)
        user_notes = data.get(user_id, [])

        if not user_notes:
            embed = discord.Embed(
                title="📭 筆記本空空如也", 
                description="你目前沒有任何筆記喔。快使用 `!addnote` 來新增吧！", 
                color=discord.Color.light_grey()
            )
            await ctx.reply(embed=embed)
            return

        description_chunk = ""
        embeds_to_send = [] 

        for i, note in enumerate(user_notes, start=1):
            note_text = f"**{i}.**\n```\n{note}\n```\n"

            if len(description_chunk) + len(note_text) > 3900:
                embed = discord.Embed(
                    title=f"📝 {ctx.author.name} 的專屬筆記", 
                    description=description_chunk, 
                    color=0x3498db 
                )
                if not embeds_to_send:
                    embed.set_thumbnail(url=ctx.author.display_avatar.url)
                embeds_to_send.append(embed)
                description_chunk = "" 

            description_chunk += note_text

        if description_chunk:
            embed = discord.Embed(
                title=f"📝 {ctx.author.name} 的專屬筆記", 
                description=description_chunk, 
                color=0x3498db
            )
            if not embeds_to_send:
                embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embeds_to_send.append(embed)

        # ✨ 為每一頁補上 Footer (顯示 1/3 頁這種提示)
        total_pages = len(embeds_to_send)
        for i, emb in enumerate(embeds_to_send):
            emb.set_footer(text=f"頁數 {i+1} / {total_pages}")

        # ✨ 根據頁數決定要不要加上按鈕控制面板
        if total_pages == 1:
            # 只有一頁，直接送出，不需要按鈕
            await ctx.reply(embed=embeds_to_send[0])
        else:
            # 超過一頁，掛上我們寫好的按鈕面板 (view)
            view = NotePagination(embeds_to_send, ctx.author.id)
            await ctx.reply(embed=embeds_to_send[0], view=view)

    @commands.command()
    async def delnote(self, ctx, *indices: int):
        if not indices:
            await ctx.reply("⚠️ 請提供至少一個筆記編號來刪除。")
            return

        data = load_json(NOTES_FILE)
        user_id = str(ctx.author.id)
        user_notes = data.get(user_id, [])

        if not user_notes:
            await ctx.reply("📭 你目前沒有任何筆記可以刪除。")
            return

        sorted_indices = sorted(set(indices), reverse=True)
        success_deleted = []
        failed_indices = []

        for idx in sorted_indices:
            if 1 <= idx <= len(user_notes):
                user_notes.pop(idx - 1)
                success_deleted.append(idx)
            else:
                failed_indices.append(idx)

        if success_deleted:
            data[user_id] = user_notes
            save_json(NOTES_FILE, data)

        response = ""
        if success_deleted:
            success_deleted.reverse()
            response += f"🗑 已刪除你的筆記編號：{', '.join(map(str, success_deleted))}\n"
        if failed_indices:
            response += f"⚠️ 以下編號無效，請確認：{', '.join(map(str, failed_indices))}"

        await ctx.reply(response)

    @delnote.error
    async def delnote_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.reply("⚠️ 格式錯誤！請務必輸入「數字」作為編號，例如：`!delnote 1 2 3`")

async def setup(bot):
    await bot.add_cog(Note(bot))