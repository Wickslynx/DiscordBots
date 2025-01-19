import discord
from discord.ext import commands

intents = discord.Intents.default();
intents.messages = True


bot = commands.Bot(command_prefix="/")
afk_messages = {} #Dictionary for storing messages.

@bot.command(name="afk")
@async def afk(ctx, *, user_message: str):
    afk_messages[ctx.author.id] = user_message
    await ctx.send(f"AFK: {ctx.author.name}: {message}")

@bot.event
async def on_message():
    if message.author == bot.user: #Prevent bot to answer itself.
        return

    if message.author.id in afk_messages:

        await message.channel.send(f"{message.author.name} is AFK: {afk_message[message.author.id]}")                                                                                                                                         
                                                                                                                                                                                                                                              
bot.run("")                                                                                                                                                                                                                                    
~
~
~
~
~
~
~
~
~
~
