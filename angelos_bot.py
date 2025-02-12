import discord
from discord.ext import commands
from datetime import datetime
import json
from discord.ext import tasks
from datetime import datetime, time

        
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
        print("Commands synced globally")

    @tasks.loop(time=time(0, 0))  # (00:00)
    async def daily_check(self):
        loa_data = load_loa_data()
        today = datetime.now().strftime('%Y-%m-%d')
        
        for user_id, info in list(loa_data.items()):
            if info['start_date'] == today:
                try:
                    user = await self.fetch_user(int(user_id))
                    await user.send(f"Your LOA period has started today and will end on {info['end_date']}")
                except:
                    print(f"Could not send start notification to user {user_id}")

    
            if info['end_date'] == today:
                try:
                    user = await self.fetch_user(int(user_id))
                    await user.send("Your LOA period has ended today!")

                    guild = self.get_guild(1223694900084867247)  
                    if guild:
                        member = guild.get_member(int(user_id))
                        if member:
                            await member.remove_roles(guild.get_role(LOA_ID))
                    del loa_data[user_id]
                    save_loa_data(loa_data)
                except:
                    print(f"Could not process end of LOA for user {user_id}")
        
        
        
    @daily_check.before_loop
    async def before_daily_check(self):
        await self.wait_until_ready()

# Create bot instance.
bot = Bot()

# Channel IDs.
WELCOME_CHANNEL_ID = 1337432747094048890
LEAVES_CHANNEL_ID = 1337432777066549288
ANNOUNCEMENT_CHANNEL_ID = 1223929286528991253  
REQUEST_CHANNEL_ID = 1337111618517073972  
INFRACTIONS_CHANNEL_ID = 1307758472179355718
PROMOTIONS_CHANNEL_ID = 1310272690434736158 
SUGGEST_CHANNEL_ID = 1223930187868016670
RETIREMENTS_CHANNEL_ID = 1337106483862831186
TRAINING_CHANNEL_ID =1312742612658163735
INTERNAL_AFFAIRS_ID = 1308094201262637056
LOA_CHANNEL_ID = 1308084741009838241
OT_ID = 1223922259727483003
STAFF_TEAM_ID = 1223920619993956372
AWAITING_TRAINING_ID = 1309972134604308500
LOA_ID = 1322405982462017546
HR_ID = 

# Helper functions 
async def get_channel_by_id(guild, channel_id):
    return guild.get_channel(channel_id)

def save_loa_data(data):
    with open('storage/LOA.json', 'w') as file:
        json.dump(data, file, indent=4)

def load_loa_data():
    try:
        with open('storage/LOA.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}



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

#Request command.
@bot.tree.command(name="request", description="Request more staff to the server")
async def request(interaction: discord.Interaction):
    
    channel = await get_channel_by_id(interaction.guild, REQUEST_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="Staff request",
            description="There are low staff in the server, please join!",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Requested by {interaction.user.name}")
        content = "@here"
        await channel.send(content=content, embed=embed)
        await interaction.response.send_message("Staff request sent!", ephemeral=True)
        
    else:
        await interaction.response.send_message("Internal error: Channel not found.", ephemeral=True)
        
@bot.tree.command(name="training_request", description="Request a trainer to train you.")
async def training_request(interaction: discord.Interaction):
    role = discord.utils.get(interaction.guild.roles, id=AWAITING_TRAINING_ID)
    if role not in interaction.user.roles:
        await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
        return
    
    channel = await get_channel_by_id(interaction.guild, TRAINING_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="Training request!",
            description=f"{interaction.user.mention} has requested training! If you are available please start an training session.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"")
        content = "<@&1308148725331394642>"
        await channel.send(content=content, embed=embed)
        await interaction.response.send_message("Training request sent!", ephemeral=True)
        
    else:
        await interaction.response.send_message("Internal error: Channel not found.", ephemeral=True)

@bot.tree.command(name="ban", description="Ban a member from the server.")
async def ban(interaction: discord.Interaction, member: discord.Member, *, reason: str = None):
    role = discord.utils.get(interaction.guild.roles, id=HR_ID)
    if role not in interaction.user.roles:
        role = discord.utils.get(interaction.guild.roles, id=OT_ID)
        if role not in interaction.user.roles:
            await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
            return
        
    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"{member.mention} has been banned from the server.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to ban this user.", ephemeral=True)
    except discord.HTTPException:
        await interaction.response.send_message("An error occurred while trying to ban this user.", ephemeral=True)
            
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
    channel = await get_channel_by_id(interaction.guild, SUGGEST_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="**Suggestion:**",
            description=suggestion,
            color=discord.Color.yellow(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"**Suggested by {interaction.user.name}**")
        content = ""
        upvote_button = discord.ui.Button(style=discord.ButtonStyle.success, label="0")
        downvote_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="0")
                                
        components = [discord.ui.ActionRow(upvote_button, downvote_button)]
        upvote_button.callback = upvote_button_callback
        downvote_button.callback = downvote_button_callback
            
        sent_message = await channel.send(content=content, embed=embed, components=components)
        
        await interaction.response.send_message("Suggestion submitted!", ephemeral=True)
    else:
        await interaction.response.send_message("Internal error: Channel not found.", ephemeral=True)

async def upvote_button_callback(interaction: discord.Interaction):
    button = interaction.component
    current_label = button.label
    upvotes = int(current_label)
    upvotes += 1
    button.label = f"{upvotes}"
    await update_buttons(interaction)

async def downvote_button_callback(interaction: discord.Interaction):
    button = interaction.component
    current_label = button.label
    downvotes = int(current_label)
    downvotes += 1
    button.label = f"{downvotes}"
    await update_buttons(interaction)

async def update_buttons(interaction: discord.Interaction):
    await interaction.message.edit(components=interaction.message.components)
    await interaction.response.defer()




@bot.tree.command(name="infract", description="Infract a user.")
async def infract(interaction: discord.Interaction, user: discord.Member, punishment: str, reason: str, notes: str):

    role = discord.utils.get(interaction.guild.roles, id=INTERNAL_AFFAIRS_ID)
    if role not in interaction.user.roles:
        role = discord.utils.get(interaction.guild.roles, id=OT_ID)
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

    role = discord.utils.get(interaction.guild.roles, id=INTERNAL_AFFAIRS_ID)
    if role not in interaction.user.roles:
        role = discord.utils.get(interaction.guild.roles, id=OT_ID)
        if role not in interaction.user.roles:
            await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
            return

    channel = await get_channel_by_id(interaction.guild, PROMOTIONS_CHANNEL_ID)
    if channel:
        await channel.send(f"{user.mention}")
        embed = discord.Embed(
            title="Staff Promotion!",
            description=f'The High ranking team has decided to grant you a promotion! \n\n **User getting promoted**:\n {user.mention} \n\n **New Rank**:\n {new_rank.mention} \n\n **Reason**:\n {reason}',
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

@bot.tree.command(name="retire", description="Retire yourself, THIS IS A ONE WAY ACTION, THERE IS NO GOING BACK.")
async def retire(interaction: discord.Interaction, last_words: str):

    role = discord.utils.get(interaction.guild.roles, id=STAFF_TEAM_ID)
    if role not in interaction.user.roles:
        await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
        return

    channel = await get_channel_by_id(interaction.guild, RETIREMENTS_CHANNEL_ID)
    if channel:
        await channel.send(f"{interaction.user.mention}")
        embed = discord.Embed(
            title="Retirement :(",
            description=f'{interaction.user.mention} has decided to **retire!** \n  The Los Angoles **staff team** wishes you best of luck! \n\n  **Last words:** \n {last_words} \n \n  Goodbye!',
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Best of wishes from the ownership and development team!")
        sent_message = await channel.send(embed=embed)
        await sent_message.add_reaction('❤️')
        await sent_message.add_reaction('🫡')
        await sent_message.add_reaction('😭')
        
        await interaction.response.send_message("Retirement sent, your roles will be removed in the near future.", ephemeral=True)
    else:
        await interaction.response.send_message("Internal error: channel not found!", ephemeral=True)



async def deny_button_callback(interaction: discord.Interaction):
    role = discord.utils.get(interaction.guild.roles, id=OT_ID)
    if role not in interaction.user.roles:
        await interaction.response.send_message("You don't have permission to deny LOA requests!", ephemeral=True)
        return

    embed = interaction.message.embeds[0]
    embed.color = discord.Color.red()
    embed.add_field(name="Status", value=f"Denied by {interaction.user.mention}", inline=False)

    view = discord.ui.View()
    approve_button = discord.ui.Button(label="Approve", style=discord.ButtonStyle.green, custom_id="approve_loa", disabled=True)
    deny_button = discord.ui.Button(label="Deny", style=discord.ButtonStyle.red, custom_id="deny_loa", disabled=True)
    view.add_item(approve_button)
    view.add_item(deny_button)

    await interaction.message.edit(embed=embed, view=view)
    await interaction.response.send_message(f"LOA request denied!", ephemeral=True)



async def approve_button_callback(interaction: discord.Interaction):
    role = discord.utils.get(interaction.guild.roles, id=OT_ID)
    if role not in interaction.user.roles:
        await interaction.response.send_message("You don't have permission to approve LOA requests!", ephemeral=True)
        return
        
    embed = interaction.message.embeds[0]
    embed.color = discord.Color.green()
    embed.add_field(name="Status", value=f"Approved by {interaction.user.mention}", inline=False)
    
    
    user_field = discord.utils.get(embed.fields, name="Staff Member")
    start_date_field = discord.utils.get(embed.fields, name="Start Date")
    end_date_field = discord.utils.get(embed.fields, name="End Date")
    
    if all([user_field, start_date_field, end_date_field]):

        user_id = ''.join(filter(str.isdigit, user_field.value))

        start_date = datetime.strptime(start_date_field.value, "%B %d, %Y").strftime('%Y-%m-%d')
        end_date = datetime.strptime(end_date_field.value, "%B %d, %Y").strftime('%Y-%m-%d')
        
        loa_data = load_loa_data()
        loa_data[user_id] = {
            'start_date': start_date,
            'end_date': end_date
        }
        save_loa_data(loa_data)

        try:
            member = interaction.guild.get_member(int(user_id))
            if member:
                await member.add_roles(interaction.guild.get_role(LOA_ID))
        except:
            await interaction.followup.send("Failed to add LOA role", ephemeral=True)

    # Update buttons
    view = discord.ui.View()
    approve_button = discord.ui.Button(label="Approve", style=discord.ButtonStyle.green, custom_id="approve_loa", disabled=True)
    deny_button = discord.ui.Button(label="Deny", style=discord.ButtonStyle.red, custom_id="deny_loa", disabled=True)
    view.add_item(approve_button)
    view.add_item(deny_button)
    
    await interaction.message.edit(embed=embed, view=view)
    await interaction.response.send_message("LOA request approved!", ephemeral=True)




@bot.tree.command(name="loa_request", description="Submit a Leave of Absence request")
async def loa_request(interaction: discord.Interaction, start_date: str, end_date: str, reason: str):

    role = discord.utils.get(interaction.guild.roles, id=STAFF_TEAM_ID)
    if role not in interaction.user.roles:
        await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
        return
    
    
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        if end < start:
            await interaction.response.send_message(
                "End date must be after start date!", 
                ephemeral=True
            )
            return
            
        if start < datetime.now():
            await interaction.response.send_message(
                "Start date cannot be in the past!", 
                ephemeral=True
            )
            return
            
    except ValueError:
        await interaction.response.send_message(
            "Invalid date format! Please use YYYY-MM-DD (e.g., 2024-02-08)", 
            ephemeral=True
        )
        return

    duration = (end - start).days + 1
    
    channel = await get_channel_by_id(interaction.guild, LOA_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="Leave of Absence Request",
            description=f"A staff member has submitted an LOA request.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Staff Member", 
            value=interaction.user.mention, 
            inline=False
        )
        embed.add_field(
            name="Start Date", 
            value=start.strftime("%B %d, %Y"), 
            inline=True
        )
        embed.add_field(
            name="End Date", 
            value=end.strftime("%B %d, %Y"), 
            inline=True
        )
        embed.add_field(
            name="Duration", 
            value=f"{duration} {'day' if duration == 1 else 'days'}", 
            inline=True
        )
        embed.add_field(
            name="Reason", 
            value=reason, 
            inline=False
        )
        
        embed.set_footer(text=f"Submitted by {interaction.user.name}")
        
        # Create view with buttons
        view = discord.ui.View()
        approve_button = discord.ui.Button(
            label="Approve", 
            style=discord.ButtonStyle.green, 
            custom_id="approve_loa"
        )
        deny_button = discord.ui.Button(
            label="Deny", 
            style=discord.ButtonStyle.red, 
            custom_id="deny_loa"
        )
        
      
        approve_button.callback = approve_button_callback
        deny_button.callback = deny_button_callback
        
        view.add_item(approve_button)
        view.add_item(deny_button)
        
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            "Your LOA request has been submitted for approval!", 
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "Internal error: Channel not found.", 
            ephemeral=True
        )




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

token = ""

def main():
    bot.run(token)

if __name__ == "__main__":
    main()
