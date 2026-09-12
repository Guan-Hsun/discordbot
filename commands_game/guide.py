import discord
from discord.ext import commands

# ==========================================
# 📂 下拉式選單：指令分類
# ==========================================
class GuideSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="獵人執照與經濟", description="查看面板、簽到等指令", emoji="💰", value="eco"),
            discord.SelectOption(label="獵人專屬小遊戲", description="1A2B、猜拳、礦業、骰寶等", emoji="🎮", value="game"),
            discord.SelectOption(label="日常與工具", description="筆記本、關鍵字、打招呼", emoji="📝", value="util"),
        ]
        super().__init__(placeholder="請選擇你要查詢的指令類別...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title="獵人協會指令指南", color=0x2ecc71)

        if self.values[0] == "eco":
            embed.add_field(name="💰 經濟與面板", value="`/profile` (面板) - 查看獵人執照與升級\n`/daily` (簽到) - 每日領取薪水", inline=False)
        elif self.values[0] == "game":
            embed.add_field(
                name="🎮 獵人小遊戲", 
                value="`/ab` (1a2b) - 猜數字遊戲 (30幣)\n"
                      "`/rps` (猜拳) - 猜拳對決 (10幣)\n"
                      "`/mine` (礦場) - 地下礦業掛機面板\n"
                      "`/sicbo` (骰寶) - 地下競技場骰寶\n"
                      "`/starbattle` (星之戰) - 邏輯解謎 (30幣)", 
                inline=False
            )
        elif self.values[0] == "util":
            embed.add_field(
                name="📝 日常與工具", 
                value="`/addnote` - 新增筆記\n"
                      "`/note` - 查看筆記面板\n"
                      "`/delnote` - 刪除指定筆記\n"
                      "`/addkeyword` (新增關鍵字) - 自訂觸發回覆 (200幣)\n"
                      "`/hello` - 跟機器人打招呼\n", 
                inline=False
            )

        # 編輯原本的訊息，把卡片換成對應分類的說明
        await interaction.response.edit_message(embed=embed, view=self.view)

class GuideView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(GuideSelect())

# ==========================================
# 🚀 導覽系統主程式
# ==========================================
class GuideSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 依然移除 Discord 預設的陽春 help 指令，避免衝突與混淆
        self.bot.remove_command("help")

    # 🌟 已經將 name 改為 guide，並將 "指令集" 加入 aliases
    @commands.hybrid_command(name="guide", aliases=["指令集", "指令", "指南", "幫助"], description="呼叫獵人協會指令大全")
    async def guide_cmd(self, ctx: commands.Context):
        embed = discord.Embed(
            title="📚 獵人協會 - 指令導覽中心",
            description="歡迎來到獵人協會！請透過下方的下拉式選單，尋找你需要的指令。\n(支援使用 `/guide` 或 `!指令集` 觸發喔！)",
            color=0x3498db
        )
        if self.bot.user.display_avatar:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await ctx.reply(embed=embed, view=GuideView())

    # 🌟 監聽器：當玩家只輸入單一驚嘆號時，自動呼叫導覽面板
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        # 如果訊息內容完全等於半形或全形驚嘆號
        if message.content.strip() in ["!", "！"]:
            embed = discord.Embed(
                title="📚 獵人協會 - 指令導覽中心",
                description="看來你需要一點引導！請透過下方的下拉式選單查詢所有的功能。",
                color=0x3498db
            )
            await message.channel.send(embed=embed, view=GuideView())

async def setup(bot):
    await bot.add_cog(GuideSystem(bot))