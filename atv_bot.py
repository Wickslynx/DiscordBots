import discord
from discord import app_commands
import asyncio
from discord.ext import commands
import os
import datetime
import json
import re


TOKEN = ""
OT_ROLE_ID = 1297503537101541457
MODERATOR_ROLE_ID = 1352988633489211442
INTERNAL_AFFAIRS_ID = 1352988633489211442
WICKS = 1159829981803860009


MODERATION_LOG_CHANNEL_ID = 0000000000000000 #Placeholder
INFRACTIONS_CHANNEL_ID = 1337816005581476063
PROMOTIONS_CHANNEL_ID = 1330593721720377384
WARNINGS_FILE = "storage/warnings.json"

# Define intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
intents.guilds = True

# Initialize bot with command prefix and intents
bot = commands.Bot(command_prefix='::', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")



# --- HELPERS -----

async def get_channel_by_id(guild, channel_id):
    return guild.get_channel(channel_id)


def load_warnings():
    """Load warnings from JSON file."""
    try:
        if os.path.exists(WARNINGS_FILE):
            with open(WARNINGS_FILE, 'r') as f:
                content = f.read().strip()
                if content:  # Check if file is not empty
                    return json.loads(content)
        # Return empty dict if file doesn't exist or is empty
        return {}
    except json.JSONDecodeError as e:
        print(f"Error loading warnings file: {e}")
        # If file is corrupted, return empty dict and backup the bad file
        if os.path.exists(WARNINGS_FILE):
            os.rename(WARNINGS_FILE, f"{WARNINGS_FILE}.bak")
        return {}

def save_warnings(warnings):
    """Save warnings to JSON file."""
    with open(WARNINGS_FILE, 'w') as f:
        json.dump(warnings, f, indent=4)
        

# --- REAL COMMANDS --
@bot.tree.command(name="delete", description="Delete messages containing a specific word in this channel")
@app_commands.describe(word="The word to filter and delete")
async def delete_word(interaction: discord.Interaction, word: str):
    # Defer the response as this operation might take some time
    await interaction.response.defer(ephemeral=True)

    deleted_count = 0
    error_count = 0

    channel = interaction.channel  # Get the current channel

    ot_role = discord.utils.get(interaction.guild.roles, id=OT_ROLE_ID)
    if ot_role not in interaction.user.roles and interaction.user.id != WICKS:
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



@bot.tree.command(name="say", description="Make the bot say a message.")
async def say(interaction: discord.Interaction, essage: str):
    role = discord.utils.get(interaction.guild.roles, id=OT_ROLE_ID)
    if role in interaction.user.roles and interaction.user.id != WICKS:
        await interaction.response.send_message("Message sent!", ephemeral=True)
        await interaction.channel.send(message)
    else:
        await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)



#--------------------------------------

@bot.tree.command(name="ban", description="Ban a member from the server")
async def ban(interaction: discord.Interaction, member: discord.Member, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles and interaction.user.id != WICKS:
        await interaction.response.send_message("You do not have permission to ban members.", ephemeral=True)
        return

    try:
        # Send DM to user about the ban (optional)
        try:
            await member.send(f"You have been banned from {interaction.guild.name}. Reason: {reason}")
        except:
            pass

        # Ban the member
        await member.ban(reason=reason)

        # Log the ban in a moderation log channel
        log_channel = interaction.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="Member Banned",
                description=f"**User:** {member.mention}\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        await interaction.response.send_message(f"{member.name} has been banned.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to ban this user.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)







#----------------------------


@bot.tree.command(name="unban", description="Unban a member from the server")
async def unban(interaction: discord.Interaction, user_id: str, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles and interaction.user.id != WICKS:
        await interaction.response.send_message("You do not have permission to unban members.", ephemeral=True)
        return

    try:
        # Unban the user
        await interaction.guild.unban(discord.Object(id=int(user_id)), reason=reason)

        # Log the unban in a moderation log channel
        log_channel = interaction.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="Member Unbanned",
                description=f"**User ID:** {user_id}\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        await interaction.response.send_message(f"User with ID {user_id} has been unbanned.", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("User not found in the ban list.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to unban this user.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)





#-------------------------------

@bot.tree.command(name="mute", description="Mute a member")
async def mute(interaction: discord.Interaction, member: discord.Member, duration: int = None, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles and interaction.user.id != WICKS:
        await interaction.response.send_message("You do not have permission to mute members.", ephemeral=True)
        return

    # Find or create muted role
    muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not muted_role:
        try:
            muted_role = await interaction.guild.create_role(name="Muted")
            # Optionally, set up permission overwrites to prevent speaking
            for channel in interaction.guild.channels:
                await channel.set_permissions(muted_role, send_messages=False)
        except Exception as e:
            await interaction.response.send_message(f"Failed to create muted role: {str(e)}", ephemeral=True)
            return

    try:
        await member.add_roles(muted_role, reason=reason)

        # Log the mute in a moderation log channel
        log_channel = interaction.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="Member Muted",
                description=f"**User:** {member.mention}\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}" + 
                (f"\n**Duration:** {duration} minutes" if duration else ""),
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        # If duration is specified, schedule unmute
        if duration:
            await interaction.response.send_message(f"{member.name} has been muted for {duration} minutes.", ephemeral=True)
            await asyncio.sleep(duration * 60)
            await member.remove_roles(muted_role, reason="Mute duration expired")
        else:
            await interaction.response.send_message(f"{member.name} has been muted.", ephemeral=True)

    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to mute this user.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)


#----------------------------------

@bot.tree.command(name="unmute", description="Unmute a member")
async def unmute(interaction: discord.Interaction, member: discord.Member, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles and interaction.user.id != WICKS:
        await interaction.response.send_message("You do not have permission to unmute members.", ephemeral=True)
        return

    # Find muted role
    muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not muted_role:
        await interaction.response.send_message("Muted role not found.", ephemeral=True)
        return

    try:
        await member.remove_roles(muted_role, reason=reason)

        # Log the unmute in a moderation log channel
        log_channel = interaction.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="Member Unmuted",
                description=f"**User:** {member.mention}\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        await interaction.response.send_message(f"{member.name} has been unmuted.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to unmute this user.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)




# ----------------------------------

@bot.tree.command(name="warn", description="Warn a member")
async def warn(interaction: discord.Interaction, member: discord.Member, *, reason: str):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles and interaction.user.id != WICKS:
        await interaction.response.send_message("You do not have permission to warn members.", ephemeral=True)
        return

    # Load existing warnings
    warnings = load_warnings()
    user_id = str(member.id)

    # Initialize warnings for user if not exist
    if user_id not in warnings:
        warnings[user_id] = []

    # Add new warning
    warnings[user_id].append({
        "moderator_id": interaction.user.id,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat()
    })

    # Save warnings
    save_warnings(warnings)

    # Log the warning in a moderation log channel
    log_channel = interaction.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="Member Warned",
            description=f"**User:** {member.mention}\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}",
            color=discord.Color.yellow(),
            timestamp=datetime.utcnow()
        )
        await log_channel.send(embed=embed)

    # Notify the warned user
    try:
        await member.send(f"You have been warned in {interaction.guild.name}. Reason: {reason}")
    except:
        pass

    await interaction.response.send_message(f"{member.name} has been warned.", ephemeral=True)

# -----------------------------------

@bot.tree.command(name="warnings", description="View warnings for a member")
async def notes(interaction: discord.Interaction, member: discord.Member = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles and interaction.user.id != WICKS:
        await interaction.response.send_message("You do not have permission to view warnings.", ephemeral=True)
        return

    # If no member specified, show user's own warnings
    if not member:
        member = interaction.user

    # Load warnings
    warnings = load_warnings()
    user_id = str(member.id)

    # Check if user has any warnings
    if user_id not in warnings or not warnings[user_id]:
        await interaction.response.send_message(f"{member.name} has no warnings.", ephemeral=True)
        return

    # Create embed with warnings
    embed = discord.Embed(
        title=f"Warnings for {member.name}",
        color=discord.Color.red()
    )

    for i, warning in enumerate(warnings[user_id], 1):
        moderator = await interaction.guild.fetch_member(warning['moderator_id'])
        embed.add_field(
            name=f"Warning {i}",
            value=f"**Reason:** {warning['reason']}\n**By:** {moderator.mention}\n**Date:** {warning['timestamp']}",
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)



#------------------------------------

@bot.tree.command(name="purge", description="Delete multiple messages")
async def purge(interaction: discord.Interaction, amount: int):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles and interaction.user.id != WICKS:
        await interaction.response.send_message("You do not have permission to purge messages.", ephemeral=True)
        return

    try:
        # Delete messages
        deleted = await interaction.channel.purge(limit=amount)

        # Log the purge in a moderation log channel
        log_channel = interaction.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="Channel Purged",
                description=f"**Moderator:** {interaction.user.mention}\n**Messages Deleted:** {len(deleted)}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        await interaction.response.send_message(f"Deleted {len(deleted)} messages.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to delete messages.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)





# -------------------

@bot.tree.command(name="lock", description="Lock a channel")
async def lock(interaction: discord.Interaction, channel: discord.TextChannel = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles and interaction.user.id != WICKS:
        await interaction.response.send_message("You do not have permission to lock channels.", ephemeral=True)
        return

    # If no channel specified, use current channel
    channel = channel or interaction.channel

    try:
        # Overwrite permissions to prevent sending messages
        await channel.set_permissions(interaction.guild.default_role, send_messages=False)

        # Log the channel lock in a moderation log channel
        log_channel = interaction.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="Channel Locked",
                description=f"**Channel:** {channel.mention}\n**Moderator:** {interaction.user.mention}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        await interaction.response.send_message(f"{channel.mention} has been locked.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to lock this channel.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)




#-----------------------

        
@bot.tree.command(name="unlock", description="Unlock a channel")
async def unlock(interaction: discord.Interaction, channel: discord.TextChannel = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles and interaction.user.id != WICKS:
        await interaction.response.send_message("You do not have permission to unlock channels.", ephemeral=True)
        return

    # If no channel specified, use current channel
    channel = channel or interaction.channel

    try:
        # Restore default permissions
        await channel.set_permissions(interaction.guild.default_role, send_messages=True)

        # Log the channel unlock in a moderation log channel
        log_channel = interaction.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="Channel Unlocked",
                description=f"**Channel:** {channel.mention}\n**Moderator:** {interaction.user.mention}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        await interaction.response.send_message(f"{channel.mention} has been unlocked.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to unlock this channel.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)



#--------------------

@bot.tree.command(name="slowmode", description="Set channel slowmode")
async def slowmode(interaction: discord.Interaction, seconds: int, channel: discord.TextChannel = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles and interaction.user.id != WICKS:
        await interaction.response.send_message("You do not have permission to set slowmode.", ephemeral=True)
        return

    # If no channel specified, use current channel
    channel = channel or interaction.channel

    try:
        # Set slowmode
        await channel.edit(slowmode_delay=seconds)

        # Log the slowmode change in a moderation log channel
        log_channel = interaction.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="Slowmode Set",
                description=f"**Channel:** {channel.mention}\n**Moderator:** {interaction.user.mention}\n**Delay:** {seconds} seconds",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        await interaction.response.send_message(f"Slowmode set to {seconds} seconds in {channel.mention}.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to set slowmode.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)





@bot.tree.command(name="role_add", description="Add a role to a member")
async def role_add(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles and interaction.user.id != WICKS:
        await interaction.response.send_message("You do not have permission to add roles.", ephemeral=True)
        return

    try:
        await member.add_roles(role)

        # Log the role addition in a moderation log channel
        log_channel = interaction.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="Role Added",
                description=f"**User:** {member.mention}\n**Role:** {role.mention}\n**Moderator:** {interaction.user.mention}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        await interaction.response.send_message(f"Added {role.name} to {member.name}.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to add this role.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="role_remove", description="Remove a role from a member")
async def role_remove(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles and interaction.user.id != WICKS:
        await interaction.response.send_message("You do not have permission to remove roles.", ephemeral=True)
        return

    try:
        await member.remove_roles(role)

        # Log the role removal in a moderation log channel
        log_channel = interaction.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="Role Removed",
                description=f"**User:** {member.mention}\n**Role:** {role.mention}\n**Moderator:** {interaction.user.mention}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        await interaction.response.send_message(f"Removed {role.name} from {member.name}.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to remove this role.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)


@bot.tree.command(name="infract", description="Infract a user. (RESERVE)")
async def infract(interaction: discord.Interaction, user: discord.Member, punishment: str, reason: str, notes: str):

    role = discord.utils.get(interaction.guild.roles, id=INTERNAL_AFFAIRS_ID)
    if role not in interaction.user.roles and interaction.user.id != WICKS:
        role = discord.utils.get(interaction.guild.roles, id=OT_ROLE_ID)
        if role not in interaction.user.roles:
            await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
            return

    channel = await get_channel_by_id(interaction.guild, INFRACTIONS_CHANNEL_ID)
    if channel:
        await channel.send(f"{user.mention}")
        embed = discord.Embed(
            title="Infraction",
            description=f'The Internal Affairs team has decided to infract you. Please do not create any drama by this infraction. Please open a appeal ticket if you have any problems. \n\n**User getting infracted**:\n {user.mention} \n\n **Punishment**:\n {punishment} \n\n **Reason**:\n {reason} \n\n **Notes**: {notes} ',
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Issued by {interaction.user.name}")
        await channel.send(embed=embed)
        await interaction.response.send_message("Infraction logged!", ephemeral=True)
    else:
        await interaction.response.send_message("Internal error: channel not found!", ephemeral=True)

@bot.tree.command(name="promote", description="Promote a user. (RESERVE)")
async def promote(interaction: discord.Interaction, user: discord.Member, new_rank: discord.Role, reason: str):

    role = discord.utils.get(interaction.guild.roles, id=INTERNAL_AFFAIRS_ID)
    if role not in interaction.user.roles and interaction.user.id != WICKS:
        role = discord.utils.get(interaction.guild.roles, id=OT_ROLE_ID)
        if role not in interaction.user.roles:
            await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
            return

    channel = await get_channel_by_id(interaction.guild, PROMOTIONS_CHANNEL_ID)
    if channel:
        await channel.send(f"{user.mention}")
        embed = discord.Embed(
            title="Staff Promotion!",
            description=f' The Internal Affairs team has decided to promote you.  \n\n **User getting promoted**:\n {user.mention} \n\n **New Rank**:\n {new_rank.mention} \n\n **Reason**:\n {reason}',
       
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Promoted by {interaction.user.name}")
        await channel.send(embed=embed)

        try:
            await user.add_roles(new_rank)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to add roles to this user!", ephemeral=True)
            return
        except discord.HTTPException:
            await interaction.response.send_message("Failed to add the role. Please try again.", ephemeral=True)
            return

        await interaction.response.send_message("Promotion logged!", ephemeral=True)
    else:
        await interaction.response.send_message("Internal error: channel not found!", ephemeral=True)



@bot.tree.command(name="shift-promo", description="Automatically promotes users with over 3.5 hours of shift time")
async def auto_promotion(interaction: discord.Interaction, leaderboard: str):
    # Check if user has permission to run this command
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles and interaction.user.id != WICKS:
        await interaction.response.send_message("You do not have permission to run auto promotions.", ephemeral=True)
        return

    # Defer response as this might take some time
    await interaction.response.defer(ephemeral=True)

    # Clean the beginning of the leaderboard
    leaderboard = leaderboard.split(" - ", 1)[-1].strip() if " - " in leaderboard else leaderboard.strip()

    # Process the leaderboard data
    entries = leaderboard.strip().split(" - ")
    print(f"Entries after splitting: {entries}") # For debugging
    promotions = []
    errors = []

    for entry in entries:
        try:
            raw_entry = entry.strip()
            print(f"Raw Entry: {raw_entry}") # Debugging the whole entry

            member = None
            user_part = ""
            time_part = ""

            # Try to find a user mention first
            mention_match = re.search(r'(<@\d+>)', raw_entry)
            if mention_match:
                user_part = mention_match.group(1).strip()
                time_part = raw_entry.split(user_part, 1)[-1].strip()
                user_id = int(mention_match.group(1)[2:-1])
                try:
                    member = await interaction.guild.fetch_member(user_id)
                except discord.NotFound:
                    pass

            # If no mention, try to find a username
            if not member:
                username_match = re.search(r'(@[\w\s|\[\]\{\}\(\)\._-]+)', raw_entry)
                if username_match:
                    user_part_raw = username_match.group(1).strip()
                    user_part = re.sub(r'@|\[.*?\]|\{.*?\}|\(.*?\)', '', user_part_raw).strip()
                    time_part = raw_entry.split(user_part_raw, 1)[-1].strip()
                    for m in interaction.guild.members:
                        if (user_part.lower() in m.name.lower() or
                                user_part.lower() in m.display_name.lower() or
                                (m.nick and user_part.lower() in m.nick.lower())):
                            member = m
                            break

            if not member:
                errors.append(f"Could not find member in entry: {raw_entry}")
                continue

            print(f"Found User Part: {user_part}") # For debugging
            print(f"Raw Time Part: {time_part}") # For debugging

            # Extract hours and minutes from the time part
            hours = 0
            minutes = 0
            seconds = 0

            hours_match = re.search(r'(\d+)\s*hour', time_part.lower())
            if hours_match:
                hours = int(hours_match.group(1))

            minutes_match = re.search(r'(\d+)\s*minute', time_part.lower())
            if minutes_match:
                minutes = int(minutes_match.group(1))

            seconds_match = re.search(r'(\d+)\s*second', time_part.lower())
            if seconds_match:
                seconds = int(seconds_match.group(1))

            # Calculate total hours
            total_hours = hours + (minutes / 60) + (seconds / 3600)

            # Process entries with sufficient hours
            if total_hours >= 3.5:
                # Get the member's highest role
                member_roles = [role for role in member.roles if role.name != "@everyone"]
                if not member_roles:
                    errors.append(f"{member.display_name} has no roles")
                    continue

                highest_role = max(member_roles, key=lambda r: r.position)

                # Find the next higher role
                guild_roles = sorted(interaction.guild.roles, key=lambda r: r.position)
                next_role = None

                for role in guild_roles:
                    if role.position > highest_role.position:
                        if role.id in [1302858922725736511, 1302303847737196594, 1291653950348595232, 1302303324279668916, 1291653369748000809, 1302303590945263616, 1291653558906650665, 1297501782607401011, 1291653487008157747, 1306270186264985620, 1291661520593223680, 1352344098832650250, 1351319004966424606, 1291657293443895376, 1291746295576526848, 1291746295576526848, 1284791394199666724, 1291746295576526848, 1291657211935985676, 1302859217643900958]:
                            continue
                        next_role = role
                        break

                if not next_role:
                    errors.append(f"No higher role found for {member.display_name}")
                    continue

                # Execute the promotion using your existing /promote command
                command_channel = interaction.channel
                await command_channel.send(f"/promote {member.mention} {next_role.mention} Automatic promotion for {total_hours:.1f} hours of shift time")

                promotions.append(f"{member.display_name}: {highest_role.name} → {next_role.name} ({total_hours:.1f} hours)")

        except Exception as e:
            errors.append(f"Error processing entry: {entry[:30]}... - {str(e)}")

    # Create response message
    response = "Automatic promotion process completed!\n\n"

    if promotions:
        response += "**Promotions:**\n"
        response += "\n".join(f"• {promotion}" for promotion in promotions)
    else:
        response += "No users were eligible for promotion."

    # Send the response in chunks to avoid hitting Discord's message limit
    await interaction.followup.send(response[:1900], ephemeral=True)

    # Send errors in separate chunks if needed
    if errors:
        error_chunks = ["**Errors:**"]
        current_chunk = "**Errors:**"

        for error in errors:
            if len(current_chunk) + len(error) + 4 > 1900:  # Allow room for bullet point and newline
                error_chunks.append(current_chunk)
                current_chunk = "**Errors (continued):**"

            current_chunk += f"\n• {error}"

        error_chunks.append(current_chunk)

        # Send each chunk
        for chunk in error_chunks[1:]:  # Skip the first element which is just the header
            await interaction.followup.send(chunk[:1900], ephemeral=True)


# Run the bot
def main():
    if not TOKEN:
        print("Error: No Discord token found. Please set the DISCORD_TOKEN environment variable.")
        return
        
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
