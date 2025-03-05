import discord
from discord.ext import commands
from datetime import datetime, time
import json
import os
from discord.ext import tasks
from pathlib import Path

Path("storage").mkdir(exist_ok=True)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True  

class ReactionButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, custom_id="approve_loa")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
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
            except Exception as e:
                await interaction.followup.send(f"Failed to add LOA role: {str(e)}", ephemeral=True)

        for item in self.children:
            item.disabled = True
        
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("LOA request approved!", ephemeral=True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, custom_id="deny_loa")
    async def deny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, id=OT_ID)
        if role not in interaction.user.roles:
            await interaction.response.send_message("You don't have permission to deny LOA requests!", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Status", value=f"Denied by {interaction.user.mention}", inline=False)

        for item in self.children:
            item.disabled = True

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(f"LOA request denied!", ephemeral=True)

class VoteView(discord.ui.View):
    def __init__(self, message_id=None):
        super().__init__(timeout=None)
        self.message_id = message_id
        
    @discord.ui.button(label="✔️ 0", style=discord.ButtonStyle.success, custom_id="upvote")
    async def upvote_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_upvote(interaction, self)
        
    @discord.ui.button(label="🗙 0", style=discord.ButtonStyle.danger, custom_id="downvote")
    async def downvote_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_downvote(interaction, self)

class Bot(commands.Bot):
    def __init__(self):
        self.reaction_role_message_id = None
        self.role_emoji_map = {
            "🎉": None,                        
            "📢": None,                   
            "🎮": None,              
            "💀": None
        }
        
        super().__init__(
            command_prefix='/',
            intents=intents,
            application_id='1336770228134088846'
        )

    async def setup_hook(self):
        self.add_view(ReactionButtons())
        self.daily_check.start()
        
        global vote_counts
        try:
            with open('storage/vote_counts.json', 'r') as file:
                vote_counts = json.load(file)
        except FileNotFoundError:
            vote_counts = {}
            
        await self.tree.sync()
        print("Commands synced globally")
        
        try:
            with open('storage/reaction_roles.json', 'r') as file:
                data = json.load(file)
                self.reaction_role_message_id = data.get('message_id')
                self.role_emoji_map = data.get('roles', self.role_emoji_map)
        except FileNotFoundError:
            print("No reaction role data found. It will be created when the command is used.")

    @tasks.loop(time=time(0, 0))
    async def daily_check(self):
        loa_data = load_loa_data()
        today = datetime.now().strftime('%Y-%m-%d')
        
        for user_id, info in list(loa_data.items()):
            if info['start_date'] == today:
                try:
                    user = await self.fetch_user(int(user_id))
                    await user.send(f"Your LOA period has started today and will end on {info['end_date']}")
                except Exception as e:
                    print(f"Could not send start notification to user {user_id}: {str(e)}")

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
                except Exception as e:
                    print(f"Could not process end of LOA for user {user_id}: {str(e)}")
        
    @daily_check.before_loop
    async def before_daily_check(self):
        await self.wait_until_ready()

bot = Bot()

WELCOME_CHANNEL_ID = 1337432747094048890
LEAVES_CHANNEL_ID = 1337432777066549288
ANNOUNCEMENT_CHANNEL_ID = 1223929286528991253  
REQUEST_CHANNEL_ID = 1337111618517073972  
INFRACTIONS_CHANNEL_ID = 1307758472179355718
PROMOTIONS_CHANNEL_ID = 1310272690434736158 
SUGGEST_CHANNEL_ID = 1223930187868016670
RETIREMENTS_CHANNEL_ID = 1337106483862831186
TRAINING_CHANNEL_ID = 1312742612658163735
INTERNAL_AFFAIRS_ID = 1308094201262637056
LOA_CHANNEL_ID = 1308084741009838241
OT_ID = 1223922259727483003
STAFF_TEAM_ID = 1223920619993956372
AWAITING_TRAINING_ID = 1309972134604308500
LOA_ID = 1322405982462017546
HR_ID = 1309973478539268136
REACTION_ID = 1309877009815572501

ROLE_RED_ID = 1336748921153912974
ROLE_BLUE_ID = 1312376313167745125
ROLE_GREEN_ID = 1336749372192325664
ROLE_YELLOW_ID = 1336749415440060489

vote_counts = {}

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

def save_vote_counts():
    with open('storage/vote_counts.json', 'w') as file:
        json.dump(vote_counts, file, indent=4)

def save_reaction_role_data(message_id, role_emoji_map):
    data = {
        'message_id': message_id,
        'roles': role_emoji_map
    }
    with open('storage/reaction_roles.json', 'w') as file:
        json.dump(data, file, indent=4)

@bot.event



async def on_raw_reaction_add(payload):
    if payload.message_id != bot.reaction_role_message_id:
        return

    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    emoji = str(payload.emoji)
    if emoji in bot.role_emoji_map:
        role_id = bot.role_emoji_map[emoji]
        role = guild.get_role(role_id)
        if role:
            member = guild.get_member(payload.user_id)
            if member:
                await member.add_roles(role)
                try:
                    await member.send(f"You have been given the {role.name} role!")
                except discord.HTTPException:
                    pass  # Cannot send DM





@bot.event
async def on_raw_reaction_remove(payload):
    if payload.message_id != bot.reaction_role_message_id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    
    emoji = str(payload.emoji)
    if emoji in bot.role_emoji_map:
        role_id = bot.role_emoji_map[emoji]
        role = guild.get_role(role_id)
        if role:
            member = guild.get_member(payload.user_id)
            if member:
                await member.remove_roles(role)
                try:
                    await member.send(f"Your {role.name} role has been removed!")
                except discord.HTTPException:
                    pass  # Cannot send DM


@bot.tree.command(name="reaction_role", description="Set up reaction roles")
async def reaction_role(interaction: discord.Interaction, red_role: discord.Role = None, blue_role: discord.Role = None, green_role: discord.Role = None, yellow_role: discord.Role = None):
    try:
        # Explicit role and admin checks
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
            return

        # Validate each role input
        roles_to_set = {
            "🎉": red_role,
            "📢": blue_role,
            "🎮": green_role,
            "💀": yellow_role
        }

        # Update role emoji map
        for emoji, role in roles_to_set.items():
            if role:
                bot.role_emoji_map[emoji] = role.id

        # Find the reaction roles channel
        channel = await get_channel_by_id(interaction.guild, REACTION_ID)
        if not channel:
            await interaction.response.send_message("Could not find the specified reaction roles channel.", ephemeral=True)
            return

        # Create embed description
        description = "React to this message to get roles:\n\n"
        for emoji, role_id in bot.role_emoji_map.items():
            role = interaction.guild.get_role(role_id) if role_id else None
            role_name = role.name if role else "Not set"
            description += f"{emoji} - {role_name}\n"

        # Create and send embed
        embed = discord.Embed(
            title="Reaction roles!",
            description=description,
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        # Send message and add reactions
        message = await channel.send(embed=embed)
        bot.reaction_role_message_id = message.id

        # Save reaction role data
        save_reaction_role_data(message.id, bot.role_emoji_map)

        # Add reactions
        for emoji in bot.role_emoji_map.keys():
            await message.add_reaction(emoji)

        await interaction.response.send_message("Reaction roles added successfully!", ephemeral=True)

    except Exception as e:
        print(f"Detailed error in reaction_role command: {e}")
        try:
            await interaction.response.send_message(f"An unexpected error occurred: {str(e)}", ephemeral=True)
        except:
            # Fallback if response is already sent
            await interaction.followup.send(f"An unexpected error occurred: {str(e)}", ephemeral=True)
            
#Request command.
@bot.tree.command(name="request", description="Request more staff to the server")
async def request(interaction: discord.Interaction):
    
    channel = await get_channel_by_id(interaction.guild, REACTION_ID)
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
    # Check permissions first
    role = discord.utils.get(interaction.guild.roles, id=HR_ID)
    role_ot = discord.utils.get(interaction.guild.roles, id=OT_ID)
    
    if role not in interaction.user.roles and role_ot not in interaction.user.roles:
        await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
        return
        
    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"{member.mention} has been banned from the server.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to ban this user.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"An error occurred while trying to ban this user: {str(e)}", ephemeral=True)
            
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

@bot.tree.command(name="suggest", description="Submit a suggestion to the suggest channel.")
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
        
        
        view = VoteView()
        
        await interaction.response.send_message("Suggestion submitted!", ephemeral=True)
        sent_message = await channel.send(embed=embed, view=view)
        
        # Set the message ID for the view
        view.message_id = str(sent_message.id)
        
        # Initialize in vote_counts
        vote_counts[view.message_id] = {"upvotes": 0, "downvotes": 0, "voted_users": {}}
        save_vote_counts()
    else:
        await interaction.response.send_message("Internal error: Channel not found.", ephemeral=True)
            
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
