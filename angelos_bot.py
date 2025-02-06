import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'The bot has finished setting up as {bot.user}')

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name='general')
    if channel is not None:
        await channel.send(f'Hello {member.mention}, welcome to Los Angelos Roleplay!')
        
@bot.event
async def on_member_remove(member):
    channel = discord.utils.get(member.guild.text_channels, name='general')
    if channel is not None:
        await channel.send(f'{member.mention} didn\'t enjoy his stay :(')
        
@bot.command()
async def announce(ctx, *, message: str):
    channel = discord.utils.get(ctx.guild.text_channels, name='announcements')
    if channel is not None:
        await channel.send(message)



token = "****************"

bot.run(token)
