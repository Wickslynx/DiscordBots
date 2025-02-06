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
        # Global command sync
        await self.tree.sync()
        print("Commands synced globally")

# Create bot instance.
bot = Bot()

# Channel IDs.
WELCOME_CHANNEL_ID = 1223929486429524078 
ANNOUNCEMENT_CHANNEL_ID = 1223929286528991253  
REQUEST_CHANNEL_ID = 1337111618517073972  
INFRACTIONS_CHANNEL_ID = 1307758472179355718
PROMOTIONS_CHANNEL_ID = 1310272690434736158 
SUGGEST_CHANNEL_ID = 1223930187868016670

# Helper function.
async def get_channel_by_id(guild, channel_id):
    return guild.get_channel(channel_id)

# Bot setup.
@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user}')
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="over the server"
        )
    )

# When a member joins send a message.
@bot.event
async def on_member_join(member):
    channel = await get_channel_by_id(member.guild, WELCOME_CHANNEL_ID)
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

# When a member leaves, send a message.
@bot.event
async def on_member_remove(member):
    channel = await get_channel_by_id(member.guild, WELCOME_CHANNEL_ID)
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

#Request command.
@bot.tree.command(name="request", description="Request more staff to the server")
async def request(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You don't have permissions to use this command!", ephemeral=True)
        return
    
    channel = await get_channel_by_id(interaction.guild, REQUEST_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="Staff request",
            description="There are low staff in the server, please join!",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Requested by {interaction.user.name}")
        content = "@Staff-team"
        await channel.send(content=content, embed=embed)
        await interaction.response.send_message("Staff request sent!", ephemeral=True)
    else:
        await interaction.response.send_message("Internal error: Channel not found.", ephemeral=True)




@bot.tree.command(name="suggest", description="Submit an suggestion to the suggest channel.")
async def suggest(interaction: discord.Interaction, suggestion: str):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You don't have permissions to use this command!", ephemeral=True)
        return
    
    channel = await get_channel_by_id(interaction.guild, SUGGEST_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="Suggestion:",
            description=suggestion,
            color=discord.Color.yellow(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Suggested by {interaction.user.name}")
        await channel.send(content=content, embed=embed)
        await interaction.response.send_message("Suggestion submitted!", ephemeral=True)
    else:
        await interaction.response.send_message("Internal error: Channel not found.", ephemeral=True)




# Infract command. Takes in user, punishment, and reason.
@bot.tree.command(name="infract", description="Infract a user.")
async def infract(interaction: discord.Interaction, user: discord.Member, punishment: str, reason: str):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
        return

    channel = await get_channel_by_id(interaction.guild, INFRACTIONS_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="Infraction",
            description=f'User getting infracted: {user.mention} \n Punishment: {punishment} \n Reason: {reason}',
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Issued by {interaction.user.name}")
        await channel.send(embed=embed)
        await interaction.response.send_message("Infraction logged!", ephemeral=True)
    else:
        await interaction.response.send_message("Internal error: channel not found!", ephemeral=True)

# Promote command.
@bot.tree.command(name="promote", description="Promote a user.")
async def promote(interaction: discord.Interaction, user: discord.Member, current_rank: str, new_rank: str, reason: str):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
        return

    channel = await get_channel_by_id(interaction.guild, PROMOTIONS_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="Promotion",
            description=f'User getting promoted: {user.mention} \n\n Current Rank: {current_rank} \n\n New Rank: {new_rank} \n\n Reason: {reason}',
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Promoted by {interaction.user.name}")
        await channel.send(embed=embed)
        await interaction.response.send_message("Promotion logged!", ephemeral=True)
    else:
        await interaction.response.send_message("Internal error: channel not found!", ephemeral=True)

# Error handler.
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingPermissions):
        await ctx.send("You don't have permission to use this command!")
    elif isinstance(error, commands.errors.CommandNotFound):
        await ctx.send("Command not found!")
    else:
        await ctx.send("An error occurred while processing your command.")

token = ""

def main():
    bot.run(token)

if __name__ == "__main__":
    main()
