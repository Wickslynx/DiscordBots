import discord
from discord.ext import commands
from datetime import datetime, time
import json
import os
import asyncio
from discord.ext import tasks
from pathlib import Path
import random
import string


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
        # Updated role_emoji_map with new roles
        self.role_emoji_map = {
            "🎉": None,                        
            "📢": None,                   
            "🎮": None,              
            "💀": None,
            "🚦": None,  # Session Ping
            "📈": None,  # Poll notification
            "🗓": None,   # Event notification
            "📸": None    # Media notification
        }
        
        super().__init__(
            command_prefix='!',
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

SESSION_PING_ROLE_ID = 1312376286769057792
POLL_NOTIFICATION_ROLE_ID = 1336748955891007599
EVENT_NOTIFICATION_ROLE_ID = 1336749372192325664
MEDIA_NOTIFICATION_ROLE_ID = 1336749395705856082

MODERATOR_ROLE_ID = 1308094201262637056  
MODERATION_LOG_CHANNEL_ID = 1355192082284675083

vote_counts = {}


# Global variables to store ticket configuration
TICKET_CONFIG = {}
ACTIVE_TICKETS = {}

class TicketSystem:
    def __init__(self, bot):
        self.bot = bot
        self.ticket_config = {}
        self.active_tickets = {}

    def generate_ticket_id(self):
        """Generate a unique ticket ID."""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    async def create_ticket_channel(self, interaction: discord.Interaction, ticket_type: str):
        """Create a ticket channel with specified configuration."""
        # Generate unique ticket ID
        ticket_id = self.generate_ticket_id()
        
        # Create channel name
        channel_name = f"{ticket_type}-{interaction.user.name[:4]}-{ticket_id}"
        
        # Create ticket channel
        try:
            # Use a constant for the ticket category ID
            category = interaction.guild.get_channel(1307742965657112627)
            if not category:
                await interaction.response.send_message(
                    "Ticket category not found. Please contact an administrator.", 
                    ephemeral=True
                )
                return None
            
            ticket_channel = await interaction.guild.create_text_channel(
                name=channel_name, 
                category=category
            )
            
            # Get required roles
            ownership_team = interaction.guild.get_role(OT_ID)
            internal_affairs = interaction.guild.get_role(INTERNAL_AFFAIRS_ID)
            
            # Verify roles exist
            if not ownership_team or not internal_affairs:
                await interaction.response.send_message(
                    "Required roles not found. Please contact an administrator.", 
                    ephemeral=True
                )
                await ticket_channel.delete()
                return None
            
            # Set channel permissions
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                ownership_team: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                internal_affairs: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            await ticket_channel.edit(overwrites=overwrites)
            
            # Get welcome message (use default if not configured)
            welcome_message = (
                self.ticket_config.get(interaction.guild.id, {}).get('welcome_message', 
                f"Welcome to {ticket_type.replace('-', ' ').title()} ticket support!")
            )
            
            # Create welcome embed
            embed = discord.Embed(
                title=f"{ticket_type.capitalize()} Ticket",
                description=welcome_message,
                color=discord.Color.blue()
            )
            embed.add_field(name="Ticket ID", value=ticket_id, inline=False)
            embed.add_field(name="Created By", value=interaction.user.mention, inline=False)
            
            # Send embed with ticket view
            ticket_view = TicketView(self, ticket_id)
            await ticket_channel.send(f"{interaction.user.mention}")
            await ticket_channel.send(embed=embed, view=ticket_view)
            
            # Track active tickets
            if interaction.guild.id not in self.active_tickets:
                self.active_tickets[interaction.guild.id] = {}
            self.active_tickets[interaction.guild.id][ticket_id] = {
                'channel_id': ticket_channel.id,
                'creator': interaction.user.id,
                'type': ticket_type
            }
            
            return ticket_channel
        
        except Exception as e:
            print(f"Error creating ticket channel: {e}")
            try:
                await interaction.response.send_message(
                    f"Failed to create ticket: {str(e)}", 
                    ephemeral=True
                )
            except:
                # If response already sent, use followup
                await interaction.followup.send(
                    f"Failed to create ticket: {str(e)}", 
                    ephemeral=True
                )
            return None


class TicketView(discord.ui.View):
    def __init__(self, ticket_system, ticket_id):
        super().__init__(timeout=None)
        self.ticket_system = ticket_system
        self.ticket_id = ticket_id



    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, custom_id="claim_ticket")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle ticket claim."""
        ticket_channel = interaction.channel
        await ticket_channel.edit(name=f"{ticket_channel.name}-claimed")
        await ticket_channel.send(f"{interaction.user.mention} has claimed this ticket.")
        
        # Disable claim button
        for item in self.children:
            if item.custom_id == "claim_ticket":
                item.disabled = True
                
        await interaction.message.edit(view=self)
        await interaction.response.send_message("Ticket claimed!", ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle ticket closure."""
        ticket_channel = interaction.channel

        # Remove from active tickets
        if interaction.guild.id in self.ticket_system.active_tickets:
            if self.ticket_id in self.ticket_system.active_tickets[interaction.guild.id]:
               del self.ticket_system.active_tickets[interaction.guild.id][self.ticket_id]

        await ticket_channel.delete()
        
class TicketCreateView(discord.ui.View):
    def __init__(self, ticket_system):
        super().__init__()
        self.ticket_system = ticket_system
    
    @discord.ui.select(
        custom_id="ticket_create_select", 
        placeholder="Select Ticket Type", 
        min_values=1, 
        max_values=1,
        options=[
            discord.SelectOption(
                label="General Support", 
                value="support", 
                description="Create a general support ticket"
            ),
            discord.SelectOption(
                label="Reports", 
                value="report", 
                description="Submit a report or issue"
            ),
            discord.SelectOption(
                label="Appeals", 
                value="appeal", 
                description="Submit an appeal"
            ),
            discord.SelectOption(
                label="Partnership/Paid Ad", 
                value="paid-ad", 
                description="Partnership or paid advertisement inquiry"
            )
        ]
    )
    async def ticket_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """Handle ticket type selection and creation."""
        ticket_type = select.values[0]
        
        # Check if ticket type is configured for this guild
        if interaction.guild.id not in self.ticket_system.ticket_config:
            await interaction.response.send_message(
                "Ticket system has not been configured. Please contact an administrator.", 
                ephemeral=True
            )
            return
        
        # Create ticket channel
        ticket_channel = await self.ticket_system.create_ticket_channel(interaction, ticket_type)
        
        if ticket_channel:
            await interaction.response.send_message(
                f"Ticket created! Check {ticket_channel.mention}", 
                ephemeral=True
            )

@bot.tree.command(name="tickets-config", description="Configure ticket messages")
async def tickets_config(interaction: discord.Interaction, message: str = None):
    """Configure welcome message for tickets."""
    # If no message provided, prompt for one
    if not message:
        await interaction.response.send_message(
            "Please provide a welcome message for tickets. "
            "Use `/tickets-config <message>` with your desired message.", 
            ephemeral=True
        )
        return
    
    # Store the welcome message
    if interaction.guild.id not in ticket_system.ticket_config:
        ticket_system.ticket_config[interaction.guild.id] = {}
    
    ticket_system.ticket_config[interaction.guild.id]['welcome_message'] = message
    
    await interaction.response.send_message(
        f"Ticket welcome message set to:\n```\n{message}\n```", 
        ephemeral=True
    )

@bot.tree.command(name="ticket-setup", description="Śend the ticket message.")
async def create_ticket(interaction: discord.Interaction):
    """Create a ticket via dropdown."""
    # Create the ticket selection view
    view = TicketCreateView(ticket_system)
    
    # Create an embed to explain ticket creation
    embed = discord.Embed(
        title="🎫 Create a Ticket",
        description="Select the type of ticket you want to create below.",
        color=discord.Color.blue()
    )
    
    try:
        # Send the embed and view in the current channel
        await interaction.channel.send(embed=embed, view=view)
        
        # Respond with an ephemeral message
        await interaction.response.send_message("Ticket message created", ephemeral=True)
    
    except discord.HTTPException as e:
        print(f"Error in create-ticket: {e}")
        try:
            await interaction.followup.send(
                "Failed to create ticket selection. Please try again.",
                ephemeral=True
            )
        except:
            # Fallback error logging if both response methods fail
            print(f"Critical error in ticket setup: {e}")


        
# Modify create_ticket_channel to use configured welcome message
async def create_ticket_channel(self, interaction: discord.Interaction, ticket_type: str):
    """Create a ticket channel with specified configuration."""
    # Generate unique ticket ID
    ticket_id = self.generate_ticket_id()
    
    # Create channel name
    channel_name = f"{ticket_type}-{interaction.user.name[:4]}-{ticket_id}"
    
    # Create ticket channel
    try:
        category = interaction.guild.get_channel(TICKET_CATEGORY_ID)
        ticket_channel = await interaction.guild.create_text_channel(
            name=channel_name, 
            category=category
        )
        
        # Get required roles
        ownership_team = interaction.guild.get_role(OT_ID)
        internal_affairs = interaction.guild.get_role(INTERNAL_AFFAIRS_ID)
        
        # Set channel permissions
        await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await ticket_channel.set_permissions(ownership_team, read_messages=True, send_messages=True)
        await ticket_channel.set_permissions(internal_affairs, read_messages=True, send_messages=True)
        
        # Get welcome message (use default if not configured)
        welcome_message = (
            self.ticket_config.get(interaction.guild.id, {}).get('welcome_message', 
            f"Welcome to {ticket_type.replace('-', ' ').title()} ticket support!")
        )
        
        # Create welcome embed
        embed = discord.Embed(
            title=f"{ticket_type.capitalize()} Ticket",
            description=welcome_message,
            color=discord.Color.blue()
        )
        embed.add_field(name="Ticket ID", value=ticket_id, inline=False)
        embed.add_field(name="Created By", value=interaction.user.mention, inline=False)
        
        # Send embed with ticket view
        ticket_view = TicketView(self, ticket_id)
        await ticket_channel.send(embed=embed, view=ticket_view)
        
        # Track active tickets
        if interaction.guild.id not in self.active_tickets:
            self.active_tickets[interaction.guild.id] = {}
        self.active_tickets[interaction.guild.id][ticket_id] = {
            'channel_id': ticket_channel.id,
            'creator': interaction.user.id,
            'type': ticket_type
        }
        
        return ticket_channel
    
    except Exception as e:
        await interaction.followup.send(f"Failed to create ticket: {str(e)}", ephemeral=True)
        return None



ticket_system = TicketSystem(bot)

@bot.tree.command(name="ticket-create", description="Create a new ticket")
async def ticket_create(interaction: discord.Interaction, ticket_type: str):
    role = discord.utils.get(interaction.guild.roles, id=INTERNAL_AFFAIRS_ID)
    if role not in interaction.user.roles:
        await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
        return
        
    """Create a new ticket."""
    # Validate ticket type
    if (interaction.guild.id not in ticket_system.ticket_config or 
        ticket_type not in ticket_system.ticket_config[interaction.guild.id]['ticket_types']):
        await interaction.response.send_message(
            "Invalid ticket type. Use the tickets-config command to set up ticket types.", 
            ephemeral=True
        )
        return
        
    # Create ticket channel
    ticket_channel = await ticket_system.create_ticket_channel(interaction, ticket_type)
    if ticket_channel:
        await interaction.response.send_message(
            f"Ticket created! Check {ticket_channel.mention}", 
            ephemeral=True
        )

@bot.tree.command(name="ticket-add", description="Add a user to the current ticket")
async def ticket_add(interaction: discord.Interaction, member: discord.Member):
    role = discord.utils.get(interaction.guild.roles, id=INTERNAL_AFFAIRS_ID)
    if role not in interaction.user.roles:
        await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
        return
        
    """Add a user to the current ticket channel."""
    # Verify this is a ticket channel
    if not interaction.channel.name.startswith(("support-", "report-", "appeal-", "paid-ad-")):
        await interaction.response.send_message(
            "This command can only be used in a ticket channel.", 
            ephemeral=True
        )
        return
        
    await interaction.channel.set_permissions(member, read_messages=True, send_messages=True)
    await interaction.response.send_message(f"{member.mention} has been added to the ticket.")

@bot.tree.command(name="ticket-remove", description="Remove a user from the current ticket")
async def ticket_remove(interaction: discord.Interaction, member: discord.Member):
    role = discord.utils.get(interaction.guild.roles, id=INTERNAL_AFFAIRS_ID)
    if role not in interaction.user.roles:
        await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
        return
        
    """Remove a user from the current ticket channel."""
     # Verify this is a ticket channel
    if not interaction.channel.name.startswith(("support-", "report-", "appeal-", "paid-ad-")):
        await interaction.response.send_message(
            "This command can only be used in a ticket channel.", 
            ephemeral=True
        )
        return
        
    await interaction.channel.set_permissions(member, read_messages=False, send_messages=False)
    await interaction.response.send_message(f"{member.mention} has been removed from the ticket.")

@bot.tree.command(name="ticket-force-close", description="Forcibly close the current ticket")
async def ticket_force_close(interaction: discord.Interaction):
    role = discord.utils.get(interaction.guild.roles, id=INTERNAL_AFFAIRS_ID)
    if role not in interaction.user.roles:
        await interaction.response.send_message(f'Sorry {interaction.user.mention}, you do not have the required role to run this command.', ephemeral=True)
        return
        
    # Verify this is a ticket channel
    if not interaction.channel.name.startswith(("support-", "report-", "appeal-", "paid-ad-")):
        await interaction.response.send_message(
            "This command can only be used in a ticket channel.", 
            ephemeral=True
        )
        return
        
    # Remove from active tickets
    if interaction.guild.id in ticket_system.active_tickets:
            ticket_id = interaction.channel.name.split('-')[-1]
            if ticket_id in ticket_system.active_tickets[interaction.guild.id]:
                del ticket_system.active_tickets[interaction.guild.id][ticket_id]
        
    await interaction.channel.delete()
        


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
        
def save_warnings(warnings):
    with open('storage/warnings.json', 'w') as file:
        json.dump(warnings, file, indent=4)

def load_warnings():
    try:
        with open('storage/warnings.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
        
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

# Updated reaction_role command to include new roles
@bot.tree.command(name="reaction_role", description="Set up reaction roles")
async def reaction_role(interaction: discord.Interaction, 
                       red_role: discord.Role = None, 
                       blue_role: discord.Role = None, 
                       green_role: discord.Role = None, 
                       yellow_role: discord.Role = None,
                       session_ping_role: discord.Role = None,  # New parameter for Session Ping
                       poll_notification_role: discord.Role = None,  # New parameter for Poll notification
                       event_notification_role: discord.Role = None,  # New parameter for Event notification
                       media_notification_role: discord.Role = None):  # New parameter for Media notification
    try:
        # Explicit role and admin checks
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
            return

        # Validate each role input - updated with new roles
        roles_to_set = {
            "🎉": red_role,
            "📢": blue_role,
            "🎮": green_role,
            "💀": yellow_role,
            "🚦": session_ping_role,
            "📈": poll_notification_role,
            "🗓": event_notification_role,
            "📸": media_notification_role
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

bot.tree.command(name="ban", description="Ban a member from the server")
async def ban(interaction: discord.Interaction, member: discord.Member, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
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

@bot.tree.command(name="unban", description="Unban a member from the server")
async def unban(interaction: discord.Interaction, user_id: str, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles:
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

@bot.tree.command(name="mute", description="Mute a member")
async def mute(interaction: discord.Interaction, member: discord.Member, duration: int = None, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
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

@bot.tree.command(name="unmute", description="Unmute a member")
async def unmute(interaction: discord.Interaction, member: discord.Member, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
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

@bot.tree.command(name="warn", description="Warn a member")
async def warn(interaction: discord.Interaction, member: discord.Member, *, reason: str):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
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

@bot.tree.command(name="notes", description="View warnings for a member")
async def notes(interaction: discord.Interaction, member: discord.Member = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
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

@bot.tree.command(name="purge", description="Delete multiple messages")
async def purge(interaction: discord.Interaction, amount: int):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles:
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

@bot.tree.command(name="lock", description="Lock a channel")
async def lock(interaction: discord.Interaction, channel: discord.TextChannel = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles:
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

@bot.tree.command(name="unlock", description="Unlock a channel")
async def unlock(interaction: discord.Interaction, channel: discord.TextChannel = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles:
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

@bot.tree.command(name="slowmode", description="Set channel slowmode")
async def slowmode(interaction: discord.Interaction, seconds: int, channel: discord.TextChannel = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(interaction.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in interaction.user.roles:
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
    if moderator_role not in interaction.user.roles:
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
    if moderator_role not in interaction.user.roles:
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
