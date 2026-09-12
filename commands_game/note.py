import discord
from discord.ext import commands
from json_manager import load_json, save_json

NOTES_FILE = "notes.json"

class NotePagination(discord.ui.View):
    def __init__(self, embeds, author_id):
        super().__init__(timeout=180) 
        self.embeds = embeds
        self.current_page = 0
        self.author_id = author_id

        self.update_buttons()

    def update_buttons(self):
        self.prev_btn.disabled = self.current_page == 0
        self.next_btn.disabled = self.current_page == len(self.embeds) - 1

    @discord.ui.button(label="⬅️ 上一頁", style=discord.ButtonStyle.primary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ 這是別人的筆記，你不能翻喔！", ephemeral=True)
            return

        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(label="下一頁 ➡️", style=discord.ButtonStyle.primary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ 這是別人的筆記，你不能翻喔！", ephemeral=True)
            return

        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


class Note(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="addnote", description="新增一筆內容到你的專屬筆記本中")
    async def addnote(self, ctx: commands.Context, *, content: str):
        data = load_json(NOTES_FILE)
        user_id = str(ctx.author.id) 

        if user_id not in data:
            data[user_id] = []

        data[user_id].append(content)
        save_json(NOTES_FILE, data)

        await ctx.reply(f"✅ 已為 {ctx.author.mention} 新增筆記：\n{content}")

    @commands.hybrid_command(name="note", aliases=["notes", "筆記"], description="查看你的專屬筆記本內容")
    async def note(self, ctx: commands.Context):
        data = load_json(NOTES_FILE)
        user_id = str(ctx.author.id)
        user_notes = data.get(user_id, [])

        if not user_notes:
            embed = discord.Embed(
                title="📭 筆記本空空如也", 
                description="你目前沒有任何筆記喔。快使用 `/addnote` 來新增吧！", 
                color=discord.Color.light_grey()
            )
            await ctx.reply(embed=embed)
            return

        description_chunk = ""
        embeds_to_send = [] 

        for i, note_text in enumerate(user_notes, start=1):
            formatted_text = f"**{i}.**\n```\n{note_text}\n```\n"

            if len(description_chunk) + len(formatted_text) > 3900:
                embed = discord.Embed(
                    title=f"📝 {ctx.author.name} 的專屬筆記", 
                    description=description_chunk, 
                    color=0x3498db 
                )
                if not embeds_to_send:
                    embed.set_thumbnail(url=ctx.author.display_avatar.url)
                embeds_to_send.append(embed)
                description_chunk = "" 

            description_chunk += formatted_text

        if description_chunk:
            embed = discord.Embed(
                title=f"📝 {ctx.author.name} 的專屬筆記", 
                description=description_chunk, 
                color=0x3498db
            )
            if not embeds_to_send:
                embed.set_thumbnail(url=ctx.author.display_avatar.url)
            embeds_to_send.append(embed)

        total_pages = len(embeds_to_send)
        for i, emb in enumerate(embeds_to_send):
            emb.set_footer(text=f"頁數 {i+1} / {total_pages}")

        if total_pages == 1:
            await ctx.reply(embed=embeds_to_send[0])
        else:
            view = NotePagination(embeds_to_send, ctx.author.id)
            await ctx.reply(embed=embeds_to_send[0], view=view)

    @commands.hybrid_command(name="delnote", description="刪除指定編號的筆記 (多個編號請用空格分開，例如：1 2 3)")
    async def delnote(self, ctx: commands.Context, indices: str):
        # 將字串手動轉換為整數陣列，以相容斜線指令無法傳遞 *args 的限制
        try:
            parsed_indices = [int(i.strip()) for i in indices.split()]
        except ValueError:
            await ctx.reply("⚠️ 格式錯誤！請務必輸入「數字」作為編號，並用空格隔開，例如：`/delnote indices:1 2 3`", ephemeral=True)
            return

        if not parsed_indices:
            await ctx.reply("⚠️ 請提供至少一個筆記編號來刪除。", ephemeral=True)
            return

        data = load_json(NOTES_FILE)
        user_id = str(ctx.author.id)
        user_notes = data.get(user_id, [])

        if not user_notes:
            await ctx.reply("📭 你目前沒有任何筆記可以刪除。", ephemeral=True)
            return

        sorted_indices = sorted(set(parsed_indices), reverse=True)
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

async def setup(bot):
    await bot.add_cog(Note(bot))