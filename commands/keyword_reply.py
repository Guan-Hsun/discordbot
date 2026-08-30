import discord
from discord.ext import commands
import random

from json_manager import load_json, save_json

KEYWORDS_FILE = "keywords.json"
DATA_FILE = "data.json"

class ConfirmKeywordView(discord.ui.View):
    def __init__(self, ctx, keyword, response):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.keyword = keyword
        self.response = response

    @discord.ui.button(label="確定花費 200 傑尼幣", style=discord.ButtonStyle.success)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ 這是別人的交易，你不能按喔！", ephemeral=True)
            return

        data = load_json(DATA_FILE)
        user_id = str(self.ctx.author.id)

        if user_id not in data or data[user_id].get("傑尼幣", 0) < 200:
            await interaction.response.edit_message(content="⚠️ 交易失敗！你根本沒有 200 傑尼幣可以扣！", view=None)
            return

        # 扣款
        data[user_id]["傑尼幣"] -= 200
        save_json(DATA_FILE, data)

        # 寫入關鍵字
        kw_data = load_json(KEYWORDS_FILE)
        if self.keyword not in kw_data:
            kw_data[self.keyword] = []
        kw_data[self.keyword].append(self.response)
        save_json(KEYWORDS_FILE, kw_data)

        reply_list = "\n- ".join(kw_data[self.keyword])
        success_msg = f"✅ **扣款成功！**已花費 200 <:emoji_1:1127882888508088393> 新增關鍵字。\n當有人說到「**{self.keyword}**」時，我會隨機挑一個回覆，目前有：\n- {reply_list}"
        await interaction.response.edit_message(content=success_msg, view=None)

    @discord.ui.button(label="取消", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ 這是別人的交易，你不能按喔！", ephemeral=True)
            return

        await interaction.response.edit_message(content="❌ 已取消新增關鍵字，沒有扣除任何傑尼幣。", view=None)


class KeywordReply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        prefixes = self.bot.command_prefix
        if isinstance(prefixes, list):
            prefixes = tuple(prefixes)

        if message.content.startswith(prefixes):
            return

        data = load_json(KEYWORDS_FILE)
        for keyword, responses in data.items():
            if keyword in message.content:
                reply = random.choice(responses)
                await message.reply(reply)
                break 

    @commands.command()
    async def 新增關鍵字(self, ctx, keyword: str, *, response: str):
        data = load_json(DATA_FILE)
        user_id = str(ctx.author.id)

        if user_id not in data or data[user_id].get("傑尼幣", 0) <= 200:
            await ctx.reply("⚠️ **你根本沒有 200 傑尼幣！** 請先去多簽到賺錢再來吧！")
            return

        view = ConfirmKeywordView(ctx, keyword, response)
        await ctx.reply(
            f"🛒 新增關鍵字「**{keyword}**」需要花費 **200** <:emoji_1:1127882888508088393>。\n請問確定要購買嗎？", 
            view=view
        )

    @新增關鍵字.error
    async def 新增關鍵字_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                "⚠️ **格式錯誤或輸入不完整！**\n\n"
                "💡 **正確用法**：`!新增關鍵字 <觸發字> <要回覆的話>`\n"
                "📝 **範例**：`!新增關鍵字 阿勳 他是大帥哥`"
            )

async def setup(bot):
    await bot.add_cog(KeywordReply(bot))