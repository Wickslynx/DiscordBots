import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, time, timedelta, timezone
import json
import os
import asyncio
from discord.ext import tasks
from pathlib import Path
import random
import string


Path("storage").mkdir(exist_ok=True)

import discord
from discord.ext import commands

class Bot(commands.Bot):
    def __init__(self):

        intents = discord.Intents.default()
        intents.message_content = True  
        
        self.WICKS = None
        
        super().__init__(
            command_prefix=';',
            intents=intents,
            application_id='1380181236177309796'
        )
    
    async def setup_hook(self):
        self.WICKS = await self.fetch_user(1159829981803860009)
        print(f"Fetched user: {self.WICKS}")

bot = Bot()
        
   

bot = Bot()


OT_ID = 1379824630361231401
STAFF_ID = 1351445385196994600

LOG_ID = 1355192082284675083

WARNINGS_FILE = "storage/warnings.json"



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
        


#--------------------------------------

bot.tree.command(name="ban", description="Ban a member from the server")
async def ban(interaction: discord.Interaction, member: discord.Member, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=STAFF_ID)
    if moderator_role not in interaction.user.roles:
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
        log_channel = interaction.guild.get_channel(LOG_ID)
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



@bot.command(name="ban")
async def ban(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    moderator_role = discord.utils.get(ctx.guild.roles, id=STAFF_ID)
    if moderator_role not in ctx.author.roles:
        await ctx.send("You do not have permission to ban members.")
        return

    try:
        try:
            await member.send(f"You have been banned from {ctx.guild.name}. Reason: {reason}")
        except:
            pass

        await member.ban(reason=reason)

        log_channel = ctx.guild.get_channel(LOG_ID)
        if log_channel:
            embed = discord.Embed(
                title="Member Banned",
                description=f"**User:** {member.mention}\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason}",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed)

        await ctx.send(f"{member.name} has been banned.")
    except discord.Forbidden:
        await ctx.send("I do not have permission to ban this user.")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")





#----------------------------


@bot.tree.command(name="unban", description="Unban a member from the server")
async def unban(interaction: discord.Interaction, user_id: str, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=STAFF_ID)
    if moderator_role not in interaction.user.roles:
        await interaction.response.send_message("You do not have permission to unban members.", ephemeral=True)
        return

    try:
        # Unban the user
        await interaction.guild.unban(discord.Object(id=int(user_id)), reason=reason)

        # Log the unban in a moderation log channel
        log_channel = interaction.guild.get_channel(LOG_ID)
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


@bot.command(name="unban")
async def unban(ctx, user_id: str, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(ctx.guild.roles, id=STAFF_ID)
    if moderator_role not in ctx.author.roles:
        await ctx.send("You do not have permission to unban members.")
        return

    try:
        # Unban the user
        await ctx.guild.unban(discord.Object(id=int(user_id)), reason=reason)

        # Log the unban in a moderation log channel
        log_channel = ctx.guild.get_channel(LOG_ID)
        if log_channel:
            embed = discord.Embed(
                title="Member Unbanned",
                description=f"**User ID:** {user_id}\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        await ctx.send(f"User with ID {user_id} has been unbanned.")
    except discord.NotFound:
        await ctx.send("User not found in the ban list.")
    except discord.Forbidden:
        await ctx.send("I do not have permission to unban this user.")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")


#-------------------------------

@bot.tree.command(name="mute", description="Mute a member")
async def mute(interaction: discord.Interaction, member: discord.Member, duration: int = None, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=STAFF_ID)
    if moderator_role not in interaction.user.roles:
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
        log_channel = interaction.guild.get_channel(LOG_ID)
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

@bot.command(name="mute")
async def mute(ctx, member: discord.Member, duration: int = None, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(ctx.guild.roles, id=STAFF_ID)
    if moderator_role not in ctx.author.roles:
        await ctx.send("You do not have permission to mute members.")
        return

    # Find or create the Muted role
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        try:
            muted_role = await ctx.guild.create_role(name="Muted")
            # Set permissions for the role
            for channel in ctx.guild.channels:
                await channel.set_permissions(muted_role, send_messages=False)
        except Exception as e:
            await ctx.send(f"Failed to create muted role: {str(e)}")
            return

    try:
        # Add the Muted role to the member
        await member.add_roles(muted_role, reason=reason)

        # Log the mute in a moderation log channel
        log_channel = ctx.guild.get_channel(LOG_ID)
        if log_channel:
            embed = discord.Embed(
                title="Member Muted",
                description=f"**User:** {member.mention}\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason}" +
                (f"\n**Duration:** {duration} minutes" if duration else ""),
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        # Notify the moderator and schedule unmute if a duration is provided
        if duration:
            await ctx.send(f"{member.name} has been muted for {duration} minutes.")
            await asyncio.sleep(duration * 60)  # Wait for the specified duration
            await member.remove_roles(muted_role, reason="Mute duration expired")
        else:
            await ctx.send(f"{member.name} has been muted.")

    except discord.Forbidden:
        await ctx.send("I do not have permission to mute this user.")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")

#----------------------------------

@bot.tree.command(name="unmute", description="Unmute a member")
async def unmute(interaction: discord.Interaction, member: discord.Member, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=STAFF_ID)
    if moderator_role not in interaction.user.roles:
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
        log_channel = interaction.guild.get_channel(LOG_ID)
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


@bot.command(name="unmute")
async def unmute(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(ctx.guild.roles, id=STAFF_ID)
    if moderator_role not in ctx.author.roles:
        await ctx.send("You do not have permission to unmute members.")
        return

    # Find muted role
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        await ctx.send("Muted role not found.")
        return

    try:
        # Remove the Muted role from the member
        await member.remove_roles(muted_role, reason=reason)

        # Log the unmute in a moderation log channel
        log_channel = ctx.guild.get_channel(LOG_ID)
        if log_channel:
            embed = discord.Embed(
                title="Member Unmuted",
                description=f"**User:** {member.mention}\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        # Notify the moderator of success
        await ctx.send(f"{member.name} has been unmuted.")
    except discord.Forbidden:
        # Handle case where bot lacks permissions
        await ctx.send("I do not have permission to unmute this user.")
    except Exception as e:
        # Handle general errors
        await ctx.send(f"An error occurred: {str(e)}")



# ----------------------------------

@bot.tree.command(name="warn", description="Warn a member")
async def warn(interaction: discord.Interaction, member: discord.Member, *, reason: str):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=STAFF_ID)
    if moderator_role not in interaction.user.roles:
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
    log_channel = interaction.guild.get_channel(LOG_ID)
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




@bot.command(name="warn")
async def warn(ctx, member: discord.Member, *, reason: str):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(ctx.guild.roles, id=STAFF_ID)
    if moderator_role not in ctx.author.roles:
        await ctx.send("You do not have permission to warn members.")
        return

    try:
        # Load existing warnings
        warnings = load_warnings()  # Replace with your actual function to load warnings
        user_id = str(member.id)

        # Initialize warnings for the user if they don't already exist
        if user_id not in warnings:
            warnings[user_id] = []

        # Add the new warning
        warnings[user_id].append({
            "moderator_id": ctx.author.id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Save warnings
        save_warnings(warnings)  # Replace with your actual function to save warnings

        # Log the warning in a moderation log channel
        log_channel = ctx.guild.get_channel(LOG_ID)
        if log_channel:
            embed = discord.Embed(
                title="Member Warned",
                description=f"**User:** {member.mention}\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason}",
                color=discord.Color.yellow(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        # Notify the warned user
        try:
            await member.send(f"You have been warned in {ctx.guild.name}. Reason: {reason}")
        except:
            pass  # Ignore if the user cannot be messaged

        # Confirm the action to the moderator
        await ctx.send(f"{member.name} has been warned.")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")


# -----------------------------------

@bot.tree.command(name="notes", description="View warnings for a member")
async def notes(interaction: discord.Interaction, member: discord.Member = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=STAFF_ID)
    if moderator_role not in interaction.user.roles:
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
    moderator_role = discord.utils.get(interaction.guild.roles, id=STAFF_ID)
    if moderator_role not in interaction.user.roles:
        await interaction.response.send_message("You do not have permission to purge messages.", ephemeral=True)
        return

    try:
        # Delete messages
        deleted = await interaction.channel.purge(limit=amount+1)

        # Log the purge in a moderation log channel
        log_channel = interaction.guild.get_channel(LOG_ID)
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

@bot.command(name="purge")
async def purge(ctx, amount: int):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(ctx.guild.roles, id=STAFF_ID)
    if moderator_role not in ctx.author.roles:
        await ctx.send("You do not have permission to purge messages.")
        return

    try:
        # Delete messages
        deleted = await ctx.channel.purge(limit=amount)

        # Log the purge in a moderation log channel
        log_channel = ctx.guild.get_channel(LOG_ID)
        if log_channel:
            embed = discord.Embed(
                title="Channel Purged",
                description=f"**Moderator:** {ctx.author.mention}\n**Messages Deleted:** {len(deleted)}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        # Notify the moderator of success
        await ctx.send(f"Deleted {len(deleted)} messages.")
    except discord.Forbidden:
        await ctx.send("I do not have permission to delete messages.")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")




# -------------------

@bot.tree.command(name="lock", description="Lock a channel")
async def lock(interaction: discord.Interaction, channel: discord.TextChannel = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=STAFF_ID)
    if moderator_role not in interaction.user.roles:
        await interaction.response.send_message("You do not have permission to lock channels.", ephemeral=True)
        return

    # If no channel specified, use current channel
    channel = channel or interaction.channel

    try:
        # Overwrite permissions to prevent sending messages
        await channel.set_permissions(interaction.guild.default_role, send_messages=False)

        # Log the channel lock in a moderation log channel
        log_channel = interaction.guild.get_channel(LOG_ID)
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


@bot.command(name="lock")
async def lock(ctx, channel: discord.TextChannel = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(ctx.guild.roles, id=STAFF_ID)
    if moderator_role not in ctx.author.roles:
        await ctx.send("You do not have permission to lock channels.")
        return

    # If no channel is specified, use the current channel
    channel = channel or ctx.channel

    try:
        # Overwrite permissions to prevent sending messages
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)

        # Log the channel lock in a moderation log channel
        log_channel = ctx.guild.get_channel(LOG_ID)
        if log_channel:
            embed = discord.Embed(
                title="Channel Locked",
                description=f"**Channel:** {channel.mention}\n**Moderator:** {ctx.author.mention}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        # Notify the moderator of success
        await ctx.send(f"{channel.mention} has been locked.")
    except discord.Forbidden:
        await ctx.send("I do not have permission to lock this channel.")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")



#-----------------------

        
@bot.tree.command(name="unlock", description="Unlock a channel")
async def unlock(interaction: discord.Interaction, channel: discord.TextChannel = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=STAFF_ID)
    if moderator_role not in interaction.user.roles:
        await interaction.response.send_message("You do not have permission to unlock channels.", ephemeral=True)
        return

    # If no channel specified, use current channel
    channel = channel or interaction.channel

    try:
        # Restore default permissions
        await channel.set_permissions(interaction.guild.default_role, send_messages=True)

        # Log the channel unlock in a moderation log channel
        log_channel = interaction.guild.get_channel(LOG_ID)
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


@bot.command(name="unlock")
async def unlock(ctx, channel: discord.TextChannel = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(ctx.guild.roles, id=STAFF_ID)
    if moderator_role not in ctx.author.roles:
        await ctx.send("You do not have permission to unlock channels.")
        return

    # If no channel is specified, use the current channel
    channel = channel or ctx.channel

    try:
        # Restore default permissions
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)

        # Log the channel unlock in a moderation log channel
        log_channel = ctx.guild.get_channel(LOG_ID)
        if log_channel:
            embed = discord.Embed(
                title="Channel Unlocked",
                description=f"**Channel:** {channel.mention}\n**Moderator:** {ctx.author.mention}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        # Notify the moderator of success
        await ctx.send(f"{channel.mention} has been unlocked.")
    except discord.Forbidden:
        await ctx.send("I do not have permission to unlock this channel.")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")


#--------------------

@bot.tree.command(name="slowmode", description="Set channel slowmode")
async def slowmode(interaction: discord.Interaction, seconds: int, channel: discord.TextChannel = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=STAFF_ID)
    if moderator_role not in interaction.user.roles:
        await interaction.response.send_message("You do not have permission to set slowmode.", ephemeral=True)
        return

    # If no channel specified, use current channel
    channel = channel or interaction.channel

    try:
        # Set slowmode
        await channel.edit(slowmode_delay=seconds)

        # Log the slowmode change in a moderation log channel
        log_channel = interaction.guild.get_channel(LOG_ID)
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



@bot.command(name="slowmode")
async def slowmode(ctx, seconds: int, channel: discord.TextChannel = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(ctx.guild.roles, id=STAFF_ID)
    if moderator_role not in ctx.author.roles:
        await ctx.send("You do not have permission to set slowmode.")
        return

    # If no channel is specified, use the current channel
    channel = channel or ctx.channel

    try:
        # Set slowmode
        await channel.edit(slowmode_delay=seconds)

        # Log the slowmode change in a moderation log channel
        log_channel = ctx.guild.get_channel(LOG_ID)
        if log_channel:
            embed = discord.Embed(
                title="Slowmode Set",
                description=f"**Channel:** {channel.mention}\n**Moderator:** {ctx.author.mention}\n**Delay:** {seconds} seconds",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            await log_channel.send(embed=embed)

        # Notify the moderator of success
        await ctx.send(f"Slowmode set to {seconds} seconds in {channel.mention}.")
    except discord.Forbidden:
        await ctx.send("I do not have permission to set slowmode.")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")



role = app_commands.Group(name="role", description="Role related commands")

@role.tree.command(name="add", description="Add a role to a member")
async def role_add(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=STAFF_ID)
    if moderator_role not in interaction.user.roles:
        await interaction.response.send_message("You do not have permission to add roles.", ephemeral=True)
        return

    try:
        await member.add_roles(role)

        # Log the role addition in a moderation log channel
        log_channel = interaction.guild.get_channel(LOG_ID)
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


@role.tree.command(name="remove", description="Remove a role from a member")
async def role_remove(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=STAFF_ID)
    if moderator_role not in interaction.user.roles:
        await interaction.response.send_message("You do not have permission to remove roles.", ephemeral=True)
        return

    try:
        await member.remove_roles(role)

        # Log the role removal in a moderation log channel
        log_channel = interaction.guild.get_channel(LOG_ID)
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

            
@bot.tree.command(name="say", description="Make the bot say a message.")
async def say(interaction: discord.Interaction, message: str):
    role = discord.utils.get(interaction.guild.roles, id=OT_ID)
    if role in interaction.user.roles:
        await interaction.response.send_message("Message sent!", ephemeral=True)
        await interaction.channel.send(message)
    else:
        await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)

# Updated vote handling functions
async def handle_upvote(interaction: discord.Interaction, view: VoteView):
    if not view.message_id:
        view.message_id = str(interaction.message.id)
    
    message_id = view.message_id
    user_id = str(interaction.user.id)
    
    if message_id not in vote_counts:
        vote_counts[message_id] = {"upvotes": 0, "downvotes": 0, "voted_users": {}}
    
    if user_id in vote_counts[message_id]["voted_users"] and vote_counts[message_id]["voted_users"][user_id] == "up":
        vote_counts[message_id]["upvotes"] -= 1
        del vote_counts[message_id]["voted_users"][user_id]
    else:
        if user_id in vote_counts[message_id]["voted_users"] and vote_counts[message_id]["voted_users"][user_id] == "down":
            vote_counts[message_id]["downvotes"] -= 1
        
        vote_counts[message_id]["upvotes"] += 1
        vote_counts[message_id]["voted_users"][user_id] = "up"
    
    # Update button labels
    for child in view.children:
        if child.custom_id == "upvote":
            child.label = f"✔️ {vote_counts[message_id]['upvotes']}"
        elif child.custom_id == "downvote":
            child.label = f"🗙 {vote_counts[message_id]['downvotes']}"
    
    # Save vote counts
    save_vote_counts()
    
    await interaction.response.edit_message(view=view)

async def handle_downvote(interaction: discord.Interaction, view: VoteView):
    if not view.message_id:
        view.message_id = str(interaction.message.id)
    
    message_id = view.message_id
    user_id = str(interaction.user.id)
    
    if message_id not in vote_counts:
        vote_counts[message_id] = {"upvotes": 0, "downvotes": 0, "voted_users": {}}
    
    if user_id in vote_counts[message_id]["voted_users"] and vote_counts[message_id]["voted_users"][user_id] == "down":
        vote_counts[message_id]["downvotes"] -= 1
        del vote_counts[message_id]["voted_users"][user_id]
    else:
        if user_id in vote_counts[message_id]["voted_users"] and vote_counts[message_id]["voted_users"][user_id] == "up":
            vote_counts[message_id]["upvotes"] -= 1
        
        vote_counts[message_id]["downvotes"] += 1
        vote_counts[message_id]["voted_users"][user_id] = "down"
    
    # Update button labels
    for child in view.children:
        if child.custom_id == "upvote":
            child.label = f"✔️ {vote_counts[message_id]['upvotes']}"
        elif child.custom_id == "downvote":
            child.label = f"🗙 {vote_counts[message_id]['downvotes']}"
    
    # Save vote counts
    save_vote_counts()
    
    await interaction.response.edit_message(view=view)

            

            

@bot.tree.command(name="delete", description="Delete messages containing a specific word in this channel")
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


# Error handler.
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
    
@bot.event
async def on_ready():
  print("Starting...")
    
token = ""

def main():
    bot.run(token)

if __name__ == "__main__":
    main()
