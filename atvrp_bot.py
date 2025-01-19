import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.messages = True

bot = commands.Bot(command_prefix="/", intents=intents)
afk_messages = {}  # For storing messages.

@bot.command(name="afk")
async def afk(ctx, *, user_message: str):
    afk_messages[ctx.author.id] = user_message
    await ctx.author.edit(nick=f"AFK| {original_nick}") # Set AFK | Before the original name.

    await ctx.send(f"AFK: {ctx.author.name}: {user_message}")

@bot.event
async def on_message(message):
    if message.author == bot.user:  # Prevent bot from answering itself.
        return

    if message.author.id in afk_messages:
        del afk_messages[message.author.id]   #Delete the afk messages.
        await message.channel.send(f"{message.author.name} removed your AFK role.")

    for user_id, afk_msg in afk_messages.items():
        if message.mentions and any(user_id == mention.id for mention in message.mentions): 
            await message.channel.send(f"{message.guild.get_member(user_id).name} is AFK: {afk_msg}") #Send a warning that the user is AFK.

    await bot.process_commands(message)

bot.run("")
