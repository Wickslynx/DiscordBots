import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.messages = True

bot = commands.Bot(command_prefix="/", intents=intents)
afk_messages = {}

@bot.command(name="afk")
async def afk(ctx, *, user_message: str):
    afk_messages[ctx.author.id] = (original_nick, user_message)
    await ctx.author.edit(nick=f"AFK | {ctx.author.display_name}")
    await ctx.send(f"AFK: {ctx.author.name}: {user_message}")

@bot.command(name="infract")
async def infract(ctx, user: discord.Member, new_rank: str, *, notes: str):
    
    await ctx.send(f"{user} The high ranking team has decided to infract you. -------- New rank: {new_rank}. Notes: {notes}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.author.id in afk_messages:
        original_nick, _ = afk_messages.pop(message.author.id)
        await message.author.edit(nick=original_nick)
        await message.channel.send(f"{message.author.name} is no longer AFK.")

    for user_id, (original_nick, afk_msg) in afk_messages.items():
        if message.mentions and any(user_id == mention.id for mention in message.mentions):
            await message.channel.send(f"{message.guild.get_member(user_id).display_name} is AFK: {afk_msg}")

    await bot.process_commands(message)

bot.run("YOUR_BOT_TOKEN")
