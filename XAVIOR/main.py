import discord
from discord.ext import commands
import os

# Intents setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

# Create bot instance
bot = commands.Bot(
    command_prefix=';',
    intents=intents,
    application_id=1336770228134088846
)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

# Load all cogs
async def load_cogs():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')


async def main():
    async with bot:
        await load_cogs()
        await bot.start('YOUR_BOT_TOKEN_HERE')


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
