import discord
from discord.ext import commands
from datetime import datetime

# Bot config.
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='/',
            intents=intents,
            application_id='1336770228134088846'  
        )
    
    async def setup_hook(self):
        await self.tree.sync()
        print("Commands synced!")

# Create bot instance.
bot = Bot()

WELCOME_CHANNEL = 'general'
ANNOUNCEMENT_CHANNEL = 'announcements'
REQUEST_CHANNEL = 'staff-requests'

#Helper function.
async def get_channel_by_name(guild, channel_name):
    return discord.utils.get(guild.text_channels, name=channel_name)

#Bot setup.
@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user}')
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="over the server"
        )
    )

#When a member joins send a message.
@bot.event
async def on_member_join(member):
    channel = await get_channel_by_name(member.guild, WELCOME_CHANNEL)
    if channel:
        embed = discord.Embed(
            title="New Member!",
            description=f"Welcome {member.mention} to the server!",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="Member Count", value=str(member.guild.member_count))
        await channel.send(embed=embed)

#When a member leaves, send a message.
@bot.event
async def on_member_remove(member):
    channel = await get_channel_by_name(member.guild, WELCOME_CHANNEL)
    if channel:
        embed = discord.Embed(
            title="Member Left",
            description=f"Goodbye {member.mention}! We'll miss you!",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="Member Count", value=str(member.guild.member_count))
        await channel.send(embed=embed)

@bot.tree.command(name="request", destription="Request more staff to the server")
async def request(interaction: discord.Interaction):
    if not interaction.user.guild_permission.manage.messages:
        await interaction.response.send_message("You don't have permissions to use this command!", ephemeral=True)
        return
    channel = await get_channel_by_name(interaction.guild, REQUEST_CHANNEL)

    if channel == await get_channel_by_name(interaction.guild, REQUEST_CHANNEL):
        embed = discord.Embed(
            title="Staff request",
            description="@ There are low staff in the server!",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Requested by {interaction.user.name}")
        content = "@here"
        await channel.send(content=content, embed=embed)
    else:
        await interaction.response.send_message("Internal error: Channel not found.")
    


    
#Announce command.
@bot.tree.command(name="announce", description="Send an announcement to the announcements channel")
async def announce(interaction: discord.Interaction, message: str, ping_everyone: bool = False):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
        return

    channel = await get_channel_by_name(interaction.guild, ANNOUNCEMENT_CHANNEL)
    if channel:
        embed = discord.Embed(
            title="📢 Announcement",
            description=message,
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Announced by {interaction.user.name}")
        content = "@everyone " if ping_everyone else ""
        await channel.send(content=content, embed=embed)
        await interaction.response.send_message("Announcement sent successfully!", ephemeral=True)
    else:
        await interaction.response.send_message("Internal error: channel not found!", ephemeral=True)

#Error handler.
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingPermissions):
        await ctx.send("You don't have permission to use this command!")
    elif isinstance(error, commands.errors.CommandNotFound):
        await ctx.send("Command not found!")
    else:
        await ctx.send("An error occurred while processing your command.")

def main():
    bot.run('***')

if __name__ == "__main__":
    main()
