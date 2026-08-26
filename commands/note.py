from discord.ext import commands
import json
import os

NOTES_FILE = "notes.json"

class Note(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def read_notes(self):
        # 如果檔案不存在，回傳一個空的字典
        if not os.path.exists(NOTES_FILE):
            return {}
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def write_notes(self, data):
        # ensure_ascii=False 確保中文字能正常顯示，不會變成亂碼
        # indent=4 讓 JSON 檔案有縮排，方便人類閱讀
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    @commands.command()
    async def addnote(self, ctx, *, content: str):
        data = self.read_notes()
        user_id = str(ctx.author.id) # 取得使用者的唯一 ID 轉成字串

        # 如果這個使用者還沒有建過筆記，先給他一個空的列表
        if user_id not in data:
            data[user_id] = []

        data[user_id].append(content)
        self.write_notes(data)

        await ctx.reply(f"✅ 已為 {ctx.author.mention} 新增筆記：\n{content}")

    @commands.command()
    async def notes(self, ctx):
        data = self.read_notes()
        user_id = str(ctx.author.id)
        user_notes = data.get(user_id, [])

        if not user_notes:
            await ctx.reply("📭 你目前沒有任何筆記喔。")
            return

        # 這裡開始處理 2000 字元限制的問題
        message_chunk = f"📝 **{ctx.author.name} 的專屬筆記**：\n"
        messages_to_send = [] # 用來裝切割好的訊息

        for i, note in enumerate(user_notes, start=1):
            note_text = f"{i}.\n```\n{note}\n```\n"

            # 檢查加上這筆筆記後，長度是否會逼近 2000 (這裡設定 1900 比較安全)
            if len(message_chunk) + len(note_text) > 1900:
                # 塞滿了，先把這包收起來
                messages_to_send.append(message_chunk)
                # 清空，準備裝下一包
                message_chunk = "" 

            message_chunk += note_text

        # 把迴圈結束後，還沒送出去的最後一包收起來
        if message_chunk:
            messages_to_send.append(message_chunk)

        # 依序發送切割好的訊息
        for msg in messages_to_send:
            await ctx.send(msg)

    @commands.command()
    async def delnote(self, ctx, *indices: int):
        if not indices:
            await ctx.reply("⚠️ 請提供至少一個筆記編號來刪除。")
            return

        data = self.read_notes()
        user_id = str(ctx.author.id)
        user_notes = data.get(user_id, [])

        if not user_notes:
            await ctx.reply("📭 你目前沒有任何筆記可以刪除。")
            return

        # 同樣採用你原本優秀的防呆設計，由大到小排序
        sorted_indices = sorted(set(indices), reverse=True)
        success_deleted = []
        failed_indices = []

        for idx in sorted_indices:
            if 1 <= idx <= len(user_notes):
                user_notes.pop(idx - 1)
                success_deleted.append(idx)
            else:
                failed_indices.append(idx)

        # 如果有成功刪除任何筆記，才執行寫入動作
        if success_deleted:
            data[user_id] = user_notes
            self.write_notes(data)

        # 準備回覆訊息
        response = ""
        if success_deleted:
            # 翻轉回來，讓顯示給使用者的編號由小到大，比較直覺
            success_deleted.reverse()
            response += f"🗑 已刪除你的筆記編號：{', '.join(map(str, success_deleted))}\n"
        if failed_indices:
            response += f"⚠️ 以下編號無效，請確認：{', '.join(map(str, failed_indices))}"

        await ctx.reply(response)

    @delnote.error
    async def delnote_error(self, ctx, error):
        # 當發生傳入參數型態錯誤 (BadArgument) 時
        if isinstance(error, commands.BadArgument):
            await ctx.reply("⚠️ 格式錯誤！請務必輸入「數字」作為編號，例如：`!delnote 1 2 3`")

async def setup(bot):
    await bot.add_cog(Note(bot))
