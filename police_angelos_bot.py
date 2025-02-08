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
            application_id='1337692729215291422'
        )
    
    async def setup_hook(self):
        # Global command sync
        await self.tree.sync()
        print("Commands synced globally")

# Create bot instance.
bot = Bot()

# Channel IDs.
WELCOME_CHANNEL_ID = 1337700023558864928
LEAVES_CHANNEL_ID = 1337700040709509120
INFRACTIONS_CHANNEL_ID = 1315026120520892426
PROMOTIONS_CHANNEL_ID = 1315025682652336149
SUGGEST_CHANNEL_ID =  1337700297761357835
INTERNAL_AFFAIRS_ID = 1314367534295945258
OT_ID = 1312749062247944232

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
            description=f"Welcome {member.mention} to LAPD!",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="Member Count", value=str(member.guild.member_count))
        await channel.send(embed=embed)

# When a member leaves, send a message.
@bot.event
async def on_member_remove(member):
    channel = await get_channel_by_id(member.guild, LEAVES_CHANNEL_ID)
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


@bot.tree.command(name="say", description="Make the bot say a message.")
async def say(interaction: discord.Interaction, message: str):
    role = discord.utils.get(interaction.guild.roles, id=OT_ID)
    if role in interaction.user.roles:
        await interaction.channel.send(message)
        pass
    else:
        await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)

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
        content = ""
        sent_message = await channel.send(content=content, embed=embed)
        await sent_message.add_reaction('✅')  # Upvote
        await sent_message.add_reaction('❌')  # Downvote
        await interaction.response.send_message("Suggestion submitted!", ephemeral=True)
    else:
        await interaction.response.send_message("Internal error: Channel not found.", ephemeral=True)

@bot.tree.command(name="infract", description="Infract a user.")
async def infract(interaction: discord.Interaction, user: discord.Member, punishment: str, reason: str, notes: str):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
        return

    role = discord.utils.get(interaction.guild.roles, id=INTERNAL_AFFAIRS_ID)
    if role not in interaction.user.roles:
        await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
        return

    channel = await get_channel_by_id(interaction.guild, INFRACTIONS_CHANNEL_ID)
    if channel:
        await channel.send(f"{user.mention}")
        embed = discord.Embed(
            title="Infraction",
            description=f'The high ranking team has decided to infract you! \n\n **User getting infracted**:\n {user.mention} \n\n **Punishment**:\n {punishment} \n\n **Reason**:\n {reason} \n\n **Notes**: {notes} ',
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Issued by {interaction.user.name}")
        await channel.send(embed=embed)
        await interaction.response.send_message("Infraction logged!", ephemeral=True)
    else:
        await interaction.response.send_message("Internal error: channel not found!", ephemeral=True)


@bot.tree.command(name="promote", description="Promote a user.")
async def promote(interaction: discord.Interaction, user: discord.Member, new_rank: discord.Role, reason: str):
    try:

        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
            return

        role = discord.utils.get(interaction.guild.roles, id=INTERNAL_AFFAIRS_ID)
        if role not in interaction.user.roles:
            await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
            return


        channel = await get_channel_by_id(interaction.guild, PROMOTIONS_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message("Internal error: channel not found!", ephemeral=True)
            return

        try:
            await user.add_roles(new_rank)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to add roles to this user!", ephemeral=True)
            return
        except discord.HTTPException:
            await interaction.response.send_message("Failed to add the role. Please try again.", ephemeral=True)
            return


        embed = discord.Embed(
            title="Staff Promotion!",
            description=f'The High ranking team has decided to grant you a promotion! \n\n **User getting promoted**:\n {user.mention} \n\n **New Rank**:\n {new_rank.mention} \n\n **Reason**:\n {reason}',
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Promoted by {interaction.user.name}")
        

        await channel.send(f"{user.mention}", embed=embed)
        await interaction.response.send_message("Promotion logged!", ephemeral=True)

    except Exception as e:
        print(f"Promotion error: {str(e)}") 
        await interaction.response.send_message("An error occurred while processing the promotion.", ephemeral=True)


# Error handler-
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingPermissions):
        await ctx.send("You don't have permission to use this command!")
    elif isinstance(error, commands.errors.CommandNotFound):
        await ctx.send("Command not found!")
    else:
        await ctx.send("An error occurred while processing your command.")

# Global error handler-
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    await interaction.response.send_message("An error occurred while processing your command.", ephemeral=True)

token = ""

def main():
    bot.run(token)

if __name__ == "__main__":
    main()
