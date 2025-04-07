import discord
from discord import app_commands
import asyncio
from discord.ext import commands
import os


TOKEN = ""
OT_ROLE_ID = 1297503537101541457

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

@@bot.tree.command(name="delete", description="Delete messages containing a specific word in this channel")
@app_commands.describe(word="The word to filter and delete")
async def delete_word(interaction: discord.Interaction, word: str):
    # Defer the response as this operation might take some time
    await interaction.response.defer(ephemeral=True)

    deleted_count = 0
    error_count = 0

    channel = interaction.channel  # Get the current channel

    ot_role = discord.utils.get(interaction.guild.roles, id=OT_ROLE_ID)
    if ot_role not in interaction.user.roles:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    if isinstance(channel, discord.TextChannel) and channel.permissions_for(interaction.guild.me).read_messages and channel.permissions_for(interaction.guild.me).manage_messages:
        try:
            async for message in channel.history(limit=10000):  # You can adjust the limit
                if word.lower() in message.content.lower():
                    try:
                        await message.delete()
                        deleted_count += 1
                        await asyncio.sleep(0.5)  # Small delay to avoid rate limiting
                    except discord.errors.Forbidden:
                        error_count += 1
                    except Exception as e:
                        print(f"Error deleting message: {e}")
                        error_count += 1
        except Exception as e:
            print(f"Error checking channel {channel.name}: {e}")
    else:
        await interaction.followup.send("Oops! I can't read messages or delete them in this channel.", ephemeral=True)
        return

    # Send a follow-up message with the results
    await interaction.followup.send(f"Finished filtering in this channel! Deleted {deleted_count} messages containing '{word}'. Failed to delete {error_count} messages.", ephemeral=True)


bot.tree.command(name="say", description="Make the bot say a message.")
async def say(interaction: discord.Interaction, message: str):
    role = discord.utils.get(interaction.guild.roles, id=OT_ID)
    if role in interaction.user.roles:
        await interaction.response.send_message("Message sent!", ephemeral=True)
        await interaction.channel.send(message)
    else:
        await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)



# Run the bot
def main():
    if not TOKEN:
        print("Error: No Discord token found. Please set the DISCORD_TOKEN environment variable.")
        return
        
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
