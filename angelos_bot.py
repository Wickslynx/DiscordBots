import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
slash = SlashCommand(bot, sync_commands=True)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name='general')
    if channel is not None:
        await channel.send(f'Hello {member.mention}, welcome to the server!')

@bot.event
async def on_member_remove(member):
    channel = discord.utils.get(member.guild.text_channels, name='general')
    if channel is not None:
        await channel.send(f'{member.mention} didn\'t enjoy his stay :(')

@slash.slash(name="announce", description="Send an announcement to the announcements channel")
async def announce(ctx: SlashContext, *, message: str):
    channel = discord.utils.get(ctx.guild.text_channels, name='announcements')
    if channel is not None:
        await channel.send(message)
    await ctx.send(f"Announcement sent: {message}")

bot.run('****************') 
