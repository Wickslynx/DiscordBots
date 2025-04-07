import discord
from discord import app_commands
import asyncio
from discord.ext import commands
import os


TOKEN = ""

# Define intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
intents.guilds = True

# Initialize bot with command prefix and intents
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.tree.command(name="delete", description="Delete messages containing a specific word")
@app_commands.describe(word="The word to filter and delete")
async def filter_word(interaction: discord.Interaction, word: str):
    # Defer the response as this operation might take some time
    await interaction.response.defer(ephemeral=True)
    
    deleted_count = 0
    error_count = 0
    
    # Getting all text channels the bot can access
    channels = [channel for channel in interaction.guild.channels if isinstance(channel, discord.TextChannel) and channel.permissions_for(interaction.guild.me).read_messages]
    
    for channel in channels:
        try:
            # Check if bot has permissions to manage messages in this channel
            if not channel.permissions_for(interaction.guild.me).manage_messages:
                continue
                
            async for message in channel.history(limit=10000):  # Limit to last 100 messages per channel for performance
                if word.lower() in message.content.lower():
                    try:
                        await message.delete()
                        deleted_count += 1
                        # Add a small delay to avoid rate limiting
                        await asyncio.sleep(0.5)
                    except discord.errors.Forbidden:
                        error_count += 1
                    except Exception as e:
                        print(f"Error deleting message: {e}")
                        error_count += 1
        except Exception as e:
            print(f"Error checking channel {channel.name}: {e}")
            
    # Send a follow-up message with the results
    await interaction.followup.send(f"Finished filtering! Deleted {deleted_count} messages containing '{word}'. Failed to delete {error_count} messages.", ephemeral=True)


# Run the bot
def main():
    if not TOKEN:
        print("Error: No Discord token found. Please set the DISCORD_TOKEN environment variable.")
        return
        
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
