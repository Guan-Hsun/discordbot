from discord.ext import commands
import os

NOTES_FILE = "notes.txt"
SEP = "<!NOTE_SEP!>"  # 特殊分隔符，避免筆記換行問題

class Note(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def read_notes(self):
        if not os.path.exists(NOTES_FILE):
            return []
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            data = f.read()
            if not data:
                return []
            notes = data.split(SEP)
            return [note.strip() for note in notes if note.strip()]

    def write_notes(self, notes):
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            f.write(SEP.join(notes))

    def add_note(self, content):
        notes = self.read_notes()
        notes.append(content)
        self.write_notes(notes)

    def delete_notes(self, indices):
        notes = self.read_notes()
        # 將 indices 從大到小排序避免刪除時錯位
        indices = sorted(set(indices), reverse=True)
        success = True
        for idx in indices:
            if 1 <= idx <= len(notes):
                notes.pop(idx - 1)
            else:
                success = False  # 有一個索引無效
        self.write_notes(notes)
        return success

    @commands.command()
    async def addnote(self, ctx, *, content: str):
        self.add_note(content)
        await ctx.send(f"✅ 已新增筆記：\n{content}")

    @commands.command()
    async def notes(self, ctx):
        notes = self.read_notes()
        if not notes:
            await ctx.send("📭 目前沒有任何筆記。")
        else:
            message = "📝 現有筆記：\n"
            for i, note in enumerate(notes, start=1):
                # 顯示時用三引號包裹筆記，讓換行更清晰
                message += f"{i}.\n```\n{note}\n```\n"
            await ctx.send(message)

    @commands.command()
    async def delnote(self, ctx, *indices: int):
        if not indices:
            await ctx.send("⚠️ 請提供至少一個筆記編號來刪除。")
            return
        success = self.delete_notes(indices)
        if success:
            await ctx.send(f"🗑 已刪除筆記編號：{', '.join(map(str, indices))}")
        else:
            await ctx.send("⚠️ 有提供的編號無效，請確認後再試一次。")

async def setup(bot):
    await bot.add_cog(Note(bot))
