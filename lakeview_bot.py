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
from typing import Optional


Path("storage").mkdir(exist_ok=True)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True  




REQUEST_CHANNEL_ID = 1359894733543182437
INFRACTIONS_CHANNEL_ID = 1291561077435404353
PROMOTIONS_CHANNEL_ID = 1291561077435404352
SUGGEST_CHANNEL_ID = 1291561076223246412
RETIREMENTS_CHANNEL_ID = 000000000000
TRAINING_CHANNEL_ID = 1359895882727952445
INTERNAL_AFFAIRS_ID = 1359895882727952445
LOA_CHANNEL_ID = 1291561077435404356
OT_ID = 1291561075019481135
STAFF_TEAM_ID = 1291561077435404356
AWAITING_TRAINING_ID = 1291561077435404356
LOA_ID = 1291561077435404356
HR_ID = 1291561077435404356

BOT_PREFIX = "w!"


MODERATOR_ROLE_ID = 1359895882727952445
MODERATION_LOG_CHANNEL_ID = 1359897697209028648

WARNINGS_FILE = "storage/warnings.json"
TICKET_CHANNEL_ID = 1359887760785408214

vote_counts = {}




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
     
        super().__init__(
            command_prefix=BOT_PREFIX,
            intents=intents,
            application_id='1359888968799359087'
        )

    async def setup_hook(self):
        self.add_view(ReactionButtons())
        self.add_view(TicketView(ticket_system, None))
        self.add_view(TicketCreateView(ticket_system))
        self.daily_check.start()
        
        global vote_counts
        try:
            with open('storage/vote_counts.json', 'r') as file:
                vote_counts = json.load(file)
        except FileNotFoundError:
            vote_counts = {}
            
        await self.tree.sync()
        print("Commands synced globally")
        

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



# Global variables to store ticket configuration
TICKET_CONFIG = {}
ACTIVE_TICKETS = {}

class TicketSystem:
    def __init__(self, bot):
        self.bot = bot
        self.ticket_config = {}
        self.active_tickets = {}
        self.max_tickets_per_user = 4  # Maximum tickets per user

    def generate_ticket_id(self):
        """Generate a unique ticket ID."""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    def get_user_ticket_count(self, guild_id, user_id):
        """Count how many active tickets a user has open."""
        if guild_id not in self.active_tickets:
            return 0
            
        count = 0
        for ticket_data in self.active_tickets[guild_id].values():
            if ticket_data['creator'] == user_id:
                count += 1
        return count

    async def create_ticket_channel(self, interaction: discord.Interaction, ticket_type: str):
        """Create a ticket channel with specified configuration."""
        # Check if user has reached the maximum number of tickets
        user_ticket_count = self.get_user_ticket_count(interaction.guild.id, interaction.user.id)
        if user_ticket_count >= self.max_tickets_per_user:
            await interaction.response.send_message(
                f"You already have {user_ticket_count} active tickets. Please close some before creating new ones.", 
                ephemeral=True
            )
            return None
            
        # Generate unique ticket ID
        ticket_id = self.generate_ticket_id()
        
        # Create channel name
        channel_name = f"{ticket_type}-{interaction.user.name[:4]}-{ticket_id}"
        
        # Create ticket channel
        try:
            # Use a constant for the ticket category ID
            category = interaction.guild.get_channel(1291561076223246410)
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
            
            # Get  message (use default if not configured)
            _message = (
                self.ticket_config.get(interaction.guild.id, {}).get('_message', 
                f" to {ticket_type.replace('-', ' ').title()} ticket support!")
            )
            
            # Create  embed
            embed = discord.Embed(
                title=f"{ticket_type.capitalize()} Ticket",
                description=_message,
                color=discord.Color.blue()
            )
            embed.add_field(name="Ticket ID", value=ticket_id, inline=False)
            embed.add_field(name="Created By", value=interaction.user.mention, inline=False)
            
            # Add ticket limit information
            new_ticket_count = user_ticket_count + 1
            embed.add_field(
                name="Ticket Limit", 
                value=f"You have {new_ticket_count}/{self.max_tickets_per_user} tickets open", 
                inline=False
            )
            
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


    @discord.ui.button(label="📥 Claim", style=discord.ButtonStyle.gray, custom_id="claim_ticket")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle ticket claim."""
        moderator_role = discord.utils.get(interaction.guild.roles, id=INTERNAL_AFFAIRS_ID)
        if moderator_role not in interaction.user.roles:
            await interaction.response.send_message("You do not have permission to claim this ticket.", ephemeral=True)
            return
        
        ticket_channel = interaction.channel
        await ticket_channel.edit(name=f"{ticket_channel.name}-claimed")
        
        # Find the creator and extract ticket ID
        ticket_id = None
        creator_id = None
        
        # Extract ticket ID from channel name
        for part in ticket_channel.name.split('-'):
            if len(part) == 6 and all(c in string.ascii_uppercase + string.digits for c in part):
                ticket_id = part
                break
        
        # Get creator from active tickets
        if ticket_id and interaction.guild.id in self.ticket_system.active_tickets and ticket_id in self.ticket_system.active_tickets[interaction.guild.id]:
            creator_id = self.ticket_system.active_tickets[interaction.guild.id][ticket_id].get('creator')
            # Store claimer info
            self.ticket_system.active_tickets[interaction.guild.id][ticket_id]['claimed_by'] = interaction.user.id
        
        # If we found the creator, modify their permissions
        if creator_id:
            creator = interaction.guild.get_member(creator_id)
            if creator:
                await ticket_channel.set_permissions(creator, read_messages=True, send_messages=False)
                await ticket_channel.send(f"{creator.mention}'s write access has been temporarily restricted while this ticket is being processed.")
        
        await ticket_channel.send(f"{interaction.user.mention} has claimed this ticket.")
        
        # Disable claim button
        for item in self.children:
            if item.custom_id == "claim_ticket":
                item.disabled = True
                
        await interaction.message.edit(view=self)
        await interaction.response.send_message("Ticket claimed!", ephemeral=True)

    @discord.ui.button(label="🔒 Close", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle ticket closure confirmation."""
        # Send the confirmation message with closure reason options
        close_view = TicketCloseView(self.ticket_system, self.ticket_id)
        await interaction.response.send_message("Why do you want to close this ticket?", view=close_view, ephemeral=False)


class TicketCloseView(discord.ui.View):
    """View for ticket closure confirmation with reason selection."""
    def __init__(self, ticket_system, ticket_id):
        super().__init__(timeout=None)
        self.ticket_system = ticket_system
        self.ticket_id = ticket_id

    @discord.ui.button(label="Solved", style=discord.ButtonStyle.green, custom_id="close_reason_solved")
    async def solved_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.close_ticket(interaction, "Solved")

    @discord.ui.button(label="User didn't respond", style=discord.ButtonStyle.gray, custom_id="close_reason_no_response")
    async def no_response_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.close_ticket(interaction, "User didn't respond")

    @discord.ui.button(label="Placeholder", style=discord.ButtonStyle.red, custom_id="close_reason_not_allowed")
    async def not_allowed_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.close_ticket(interaction, "Placeholder")

    @discord.ui.button(label="Other", style=discord.ButtonStyle.gray, custom_id="close_reason_other")
    async def other_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.close_ticket(interaction, "Other")

    async def close_ticket(self, interaction: discord.Interaction, reason: str):
        """Handle the actual ticket closure with the selected reason."""
        ticket_channel = interaction.channel
        
        # Log the closure reason in the ticket channel
        await ticket_channel.send(f"Ticket closed by {interaction.user.mention}. Reason: {reason}")
        
        # Send logs to the logging channel
        TICKET_LOGS_CHANNEL_ID = TICKET_CHANNEL_ID  # Replace with your actual logs channel ID
        logs_channel = interaction.guild.get_channel(TICKET_LOGS_CHANNEL_ID)
        
        if logs_channel:
            # Create a detailed embed for logging
            embed = discord.Embed(
                title="Ticket Closed",
                description=f"Ticket **#{self.ticket_id}** has been closed",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Closed By", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=True)
            embed.add_field(name="Channel", value=ticket_channel.name, inline=False)
            
            # You can add more info like ticket creation time, original requester, etc.
            # if you store that information in your ticket system
            
            await logs_channel.send(embed=embed)
        else:
            # If we can't find the logs channel, log to console
            print(f"Could not find logs channel with ID {TICKET_LOGS_CHANNEL_ID}")
        
        # Remove from active tickets
        if interaction.guild.id in self.ticket_system.active_tickets:
            if self.ticket_id in self.ticket_system.active_tickets[interaction.guild.id]:
                del self.ticket_system.active_tickets[interaction.guild.id][self.ticket_id]
        
        # Disable all buttons to prevent further interactions
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        
        # Optional: Add a short delay before deleting the channel
        await interaction.response.send_message(f"Closing ticket. Reason: {reason}", ephemeral=True)
        await asyncio.sleep(3)  # Wait 3 seconds before deleting
        await ticket_channel.delete()


class TicketConfigModal(discord.ui.Modal):
    def __init__(self, title: str, default_text: str = ""):
        super().__init__(title=title)
        
        self.message_input = discord.ui.TextInput(
            label="Enter your message",
            style=discord.TextStyle.paragraph,
            placeholder="Enter your custom message here...",
            default=default_text,
            required=True,
            max_length=1000
        )
        self.add_item(self.message_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        return self.message_input.value

class TicketConfigView(discord.ui.View):
    def __init__(self, ticket_system):
        super().__init__(timeout=300)  # 5 minute timeout
        self.ticket_system = ticket_system
    
    @discord.ui.select(
        custom_id="ticket_config_select", 
        placeholder="Select what to configure", 
        min_values=1, 
        max_values=1,
        options=[
            discord.SelectOption(
                label=" Message", 
                value="_message", 
                description="Change the default  message for all tickets"
            ),
            discord.SelectOption(
                label="Support Ticket Message", 
                value="support_message", 
                description="Change the message for support tickets"
            ),
            discord.SelectOption(
                label="Report Ticket Message", 
                value="report_message", 
                description="Change the message for report tickets"
            ),
            discord.SelectOption(
                label="Appeal Ticket Message", 
                value="appeal_message", 
                description="Change the message for appeal tickets"
            ),
            discord.SelectOption(
                label="Partnership/Ad Ticket Message", 
                value="paid_ad_message", 
                description="Change the message for partnership/ad tickets"
            ),
            discord.SelectOption(
                label="Set Ticket Banner", 
                value="ticket_banner", 
                description="Upload an image to show at the top of ticket messages"
            ),
            discord.SelectOption(
                label="Preview Current Settings", 
                value="preview", 
                description="See your current ticket configuration"
            )
        ]
    )
    async def config_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        guild_id = interaction.guild.id
        
        # Initialize config for guild if not already done
        if guild_id not in self.ticket_system.ticket_config:
            self.ticket_system.ticket_config[guild_id] = {
                '_message': " to ticket support!",
                'support_message': "Please describe your issue and someone will assist you shortly.",
                'report_message': "Please provide details about what you're reporting and any evidence.",
                'appeal_message': "Please explain why you believe this decision should be reconsidered.",
                'paid_ad_message': "Please provide details about your partnership or advertisement request.",
                'ticket_banner': None
            }
        
        config = self.ticket_system.ticket_config[guild_id]
        selected_option = select.values[0]
        
        if selected_option == "preview":
            # Create an embed to show current settings
            embed = discord.Embed(
                title="Current Ticket Configuration",
                description="Here are your current ticket settings:",
                color=discord.Color.blue()
            )
            
            embed.add_field(name=" Message", value=config.get('_message', "Not set"), inline=False)
            embed.add_field(name="Support Ticket Message", value=config.get('support_message', "Not set"), inline=False)
            embed.add_field(name="Report Ticket Message", value=config.get('report_message', "Not set"), inline=False)
            embed.add_field(name="Appeal Ticket Message", value=config.get('appeal_message', "Not set"), inline=False)
            embed.add_field(name="Partnership/Ad Message", value=config.get('paid_ad_message', "Not set"), inline=False)
            
            banner_status = "Set" if config.get('ticket_banner') else "Not set"
            embed.add_field(name="Ticket Banner", value=banner_status, inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        elif selected_option == "ticket_banner":
            # Prompt for banner upload
            await interaction.response.send_message(
                "Please upload an image to use as the ticket banner. Send the image in your next message.",
                ephemeral=True
            )
            
            def check(message):
                return message.author.id == interaction.user.id and message.attachments
            
            try:
                # Wait for user to upload an image
                message = await self.ticket_system.bot.wait_for('message', check=check, timeout=60.0)
                
                # Check if the attachment is an image
                if not message.attachments[0].content_type.startswith('image/'):
                    await interaction.followup.send("The uploaded file is not an image. Please try again with an image file.", ephemeral=True)
                    return
                
                # Store the image URL
                config['ticket_banner'] = message.attachments[0].url
                
                # Let the user know it was successful
                await interaction.followup.send("Ticket banner has been set successfully!", ephemeral=True)
                
                # Delete the user's message to keep the channel clean
                try:
                    await message.delete()
                except:
                    pass
                
            except asyncio.TimeoutError:
                await interaction.followup.send("You took too long to upload an image. Please try again.", ephemeral=True)
        
        else:
            # Handle text configuration options
            message_types = {
                "_message": " Message",
                "support_message": "Support Ticket Message",
                "report_message": "Report Ticket Message",
                "appeal_message": "Appeal Ticket Message",
                "paid_ad_message": "Partnership/Ad Ticket Message"
            }
            
            # Get current value for this setting
            current_text = config.get(selected_option, "")
            
            # Create and show modal for text input
            modal = TicketConfigModal(f"Edit {message_types[selected_option]}", current_text)
            await interaction.response.send_modal(modal)
            
            # Wait for modal submission
            try:
                submitted_value = await modal.wait()
                if submitted_value:
                    # Update the configuration
                    config[selected_option] = submitted_value
                    await interaction.followup.send(f"{message_types[selected_option]} has been updated!", ephemeral=True)
            except:
                # Modal was closed without submission
                pass

# Replace your existing tickets-config command with this version

@bot.tree.command(name="tickets-config", description="Configure the ticket system")
async def tickets_config(interaction: discord.Interaction, option: str = None):
    """Configure ticket messages and settings"""
    # Check for appropriate permissions
    if not interaction.user.guild_permissions.administrator and not any(
        role.id == INTERNAL_AFFAIRS_ID for role in interaction.user.roles
    ):
        await interaction.response.send_message(
            "You need appropriate permissions to configure the ticket system.",
            ephemeral=True
        )
        return
    
    # If option is provided, handle the legacy text-only configuration
    if option is not None:
        # Store the  message
        if interaction.guild.id not in ticket_system.ticket_config:
            ticket_system.ticket_config[interaction.guild.id] = {}
        
        ticket_system.ticket_config[interaction.guild.id]['_message'] = option
        
        await interaction.response.send_message(
            f"Ticket  message set to:\n```\n{option}\n```", 
            ephemeral=True
        )
        return
    
    # Show the configuration view if no option is provided
    view = TicketConfigView(ticket_system)
    
    embed = discord.Embed(
        title="Ticket System Configuration",
        description="Select an option below to configure your ticket system.",
        color=discord.Color.blue()
    )
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# Add these classes after the command definition

class TicketConfigModal(discord.ui.Modal):
    def __init__(self, title: str, default_text: str = ""):
        super().__init__(title=title)
        
        self.message_input = discord.ui.TextInput(
            label="Enter your message",
            style=discord.TextStyle.paragraph,
            placeholder="Enter your custom message here...",
            default=default_text,
            required=True,
            max_length=1000
        )
        self.add_item(self.message_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        return self.message_input.value

class TicketConfigView(discord.ui.View):
    def __init__(self, ticket_system):
        super().__init__(timeout=300)  # 5 minute timeout
        self.ticket_system = ticket_system
    
    @discord.ui.select(
        custom_id="ticket_config_select", 
        placeholder="Select what to configure", 
        min_values=1, 
        max_values=1,
        options=[
            discord.SelectOption(
                label=" Message", 
                value="_message", 
                description="Change the default  message for all tickets"
            ),
            discord.SelectOption(
                label="Support Ticket Message", 
                value="support_message", 
                description="Change the message for support tickets"
            ),
            discord.SelectOption(
                label="Report Ticket Message", 
                value="report_message", 
                description="Change the message for report tickets"
            ),
            discord.SelectOption(
                label="Appeal Ticket Message", 
                value="appeal_message", 
                description="Change the message for appeal tickets"
            ),
            discord.SelectOption(
                label="Partnership/Ad Ticket Message", 
                value="paid_ad_message", 
                description="Change the message for partnership/ad tickets"
            ),
            discord.SelectOption(
                label="Set Ticket Banner", 
                value="ticket_banner", 
                description="Upload an image to show at the top of ticket messages"
            ),
            discord.SelectOption(
                label="Preview Current Settings", 
                value="preview", 
                description="See your current ticket configuration"
            )
        ]
    )
    async def config_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        guild_id = interaction.guild.id
        
        # Initialize config for guild if not already done
        if guild_id not in self.ticket_system.ticket_config:
            self.ticket_system.ticket_config[guild_id] = {
                '_message': " to ticket support!",
                'support_message': "Please describe your issue and someone will assist you shortly.",
                'report_message': "Please provide details about what you're reporting and any evidence.",
                'appeal_message': "Please explain why you believe this decision should be reconsidered.",
                'paid_ad_message': "Please provide details about your partnership or advertisement request.",
                'ticket_banner': None
            }
        
        config = self.ticket_system.ticket_config[guild_id]
        selected_option = select.values[0]
        
        if selected_option == "preview":
            # Create an embed to show current settings
            embed = discord.Embed(
                title="Current Ticket Configuration",
                description="Here are your current ticket settings:",
                color=discord.Color.blue()
            )
            
            embed.add_field(name=" Message", value=config.get('_message', "Not set"), inline=False)
            embed.add_field(name="Support Ticket Message", value=config.get('support_message', "Not set"), inline=False)
            embed.add_field(name="Report Ticket Message", value=config.get('report_message', "Not set"), inline=False)
            embed.add_field(name="Appeal Ticket Message", value=config.get('appeal_message', "Not set"), inline=False)
            embed.add_field(name="Partnership/Ad Message", value=config.get('paid_ad_message', "Not set"), inline=False)
            
            banner_status = "Set" if config.get('ticket_banner') else "Not set"
            embed.add_field(name="Ticket Banner", value=banner_status, inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        elif selected_option == "ticket_banner":
            # Prompt for banner upload
            await interaction.response.send_message(
                "Please upload an image to use as the ticket banner. Send the image in your next message.",
                ephemeral=True
            )
            
            def check(message):
                return message.author.id == interaction.user.id and message.attachments
            
            try:
                # Wait for user to upload an image
                message = await self.ticket_system.bot.wait_for('message', check=check, timeout=60.0)
                
                # Check if the attachment is an image
                if not message.attachments[0].content_type.startswith('image/'):
                    await interaction.followup.send("The uploaded file is not an image. Please try again with an image file.", ephemeral=True)
                    return
                
                # Store the image URL
                config['ticket_banner'] = message.attachments[0].url
                
                # Let the user know it was successful
                await interaction.followup.send("Ticket banner has been set successfully!", ephemeral=True)
                
                # Delete the user's message to keep the channel clean
                try:
                    await message.delete()
                except:
                    pass
                
            except asyncio.TimeoutError:
                await interaction.followup.send("You took too long to upload an image. Please try again.", ephemeral=True)
        
        else:
            # Handle text configuration options
            message_types = {
                "_message": " Message",
                "support_message": "Support Ticket Message",
                "report_message": "Report Ticket Message",
                "appeal_message": "Appeal Ticket Message",
                "paid_ad_message": "Partnership/Ad Ticket Message"
            }
            
            # Get current value for this setting
            current_text = config.get(selected_option, "")
            
            # Create and show modal for text input
            modal = TicketConfigModal(f"Edit {message_types[selected_option]}", current_text)
            await interaction.response.send_modal(modal)
            
            # Wait for modal submission
            try:
                interaction_response = await self.ticket_system.bot.wait_for(
                    "modal_submit",
                    check=lambda i: i.data["custom_id"] == modal.custom_id and i.user.id == interaction.user.id,
                    timeout=300.0
                )
                
                # Get the submitted value
                submitted_value = interaction_response.data["components"][0]["components"][0]["value"]
                
                # Update the configuration
                config[selected_option] = submitted_value
                
                # Respond to the modal submission
                await interaction_response.response.send_message(
                    f"{message_types[selected_option]} has been updated!", 
                    ephemeral=True
                )
                
            except asyncio.TimeoutError:
                # Modal timed out
                pass
                


# Modify the ticket creation process to use the custom messages:
async def create_ticket_channel(self, interaction: discord.Interaction, ticket_type: str):
    """Create a ticket channel with specified configuration."""
    # Check if user has reached the maximum number of tickets
    user_ticket_count = self.get_user_ticket_count(interaction.guild.id, interaction.user.id)
    if user_ticket_count >= self.max_tickets_per_user:
        await interaction.response.send_message(
            f"You already have {user_ticket_count} active tickets. Please close some before creating new ones.", 
            ephemeral=True
        )
        return None
        
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
        
        # Get guild configuration
        guild_config = self.ticket_config.get(interaction.guild.id, {})
        
        # Get ticket banner if set
        ticket_banner = guild_config.get('ticket_banner')
        
        # Get  message based on ticket type
        message_key = f"{ticket_type}_message"
        _message = guild_config.get(
            message_key, 
            guild_config.get('_message', f" to {ticket_type.replace('-', ' ').title()} ticket support!")
        )
        
        # Send banner if configured
        if ticket_banner:
            embed = discord.Embed()
            embed.set_image(url=ticket_banner)
            await ticket_channel.send(embed=embed)
        
        # Create  embed
        embed = discord.Embed(
            title=f"{ticket_type.capitalize()} Ticket",
            description=_message,
            color=discord.Color.blue()
        )
        embed.add_field(name="Ticket ID", value=ticket_id, inline=False)
        embed.add_field(name="Created By", value=interaction.user.mention, inline=False)
        
        # Add ticket limit information
        new_ticket_count = user_ticket_count + 1
        embed.add_field(
            name="Ticket Limit", 
            value=f"You have {new_ticket_count}/{self.max_tickets_per_user} tickets open", 
            inline=False
        )
        
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


# Update the TicketCreateView to include banner
class TicketCreateView(discord.ui.View):
    def __init__(self, ticket_system):
        super().__init__(timeout=None)
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
        
        # Create ticket channel
        ticket_channel = await self.ticket_system.create_ticket_channel(interaction, ticket_type)
        
        if ticket_channel:
            await interaction.response.send_message(
                f"Ticket created! Check {ticket_channel.mention}", 
                ephemeral=True
            )


    # New ticket claim command
@bot.tree.command(name="ticket-claim", description="Claim the current ticket")
async def ticket_claim(interaction: discord.Interaction):
    """Claim the current ticket."""
    # Verify this is a ticket channel
    if not interaction.channel.name.startswith(("support-", "report-", "appeal-", "paid-ad-")):
        await interaction.response.send_message(
            "This command can only be used in a ticket channel.", 
            ephemeral=True
        )
        return
    
    # Check if the user has the required role
    moderator_role = discord.utils.get(interaction.guild.roles, id=INTERNAL_AFFAIRS_ID)
    if moderator_role not in interaction.user.roles:
        await interaction.response.send_message(
            "You do not have permission to claim this ticket.",
            ephemeral=True
        )
        return
    
    # Check if ticket is already claimed
    if "-claimed" in interaction.channel.name:
        await interaction.response.send_message(
            "This ticket is already claimed.", 
            ephemeral=True
        )
        return
    
    # Claim the ticket
    await interaction.channel.edit(name=f"{interaction.channel.name}-claimed")
    
    # Extract ticket ID from channel name
    ticket_id = None
    for part in interaction.channel.name.split('-'):
        if len(part) == 6 and all(c in string.ascii_uppercase + string.digits for c in part):
            ticket_id = part
            break
    
    # Update the active tickets with claimer info if ticket ID was found
    if ticket_id and interaction.guild.id in ticket_system.active_tickets and ticket_id in ticket_system.active_tickets[interaction.guild.id]:
        ticket_system.active_tickets[interaction.guild.id][ticket_id]['claimed_by'] = interaction.user.id
    
    await interaction.response.send_message(f"{interaction.user.mention} has claimed this ticket.")


# New ticket unclaim command
@bot.tree.command(name="ticket-unclaim", description="Unclaim the current ticket")
async def ticket_unclaim(interaction: discord.Interaction):
    """Unclaim the current ticket."""
    # Verify this is a ticket channel
    if not interaction.channel.name.startswith(("support-", "report-", "appeal-", "paid-ad-")):
        await interaction.response.send_message(
            "This command can only be used in a ticket channel.", 
            ephemeral=True
        )
        return
    
    # Check if the user has the required role
    moderator_role = discord.utils.get(interaction.guild.roles, id=INTERNAL_AFFAIRS_ID)
    if moderator_role not in interaction.user.roles:
        await interaction.response.send_message(
            "You do not have permission to unclaim this ticket.",
            ephemeral=True
        )
        return
    
    # Check if ticket is claimed
    if "-claimed" not in interaction.channel.name:
        await interaction.response.send_message(
            "This ticket is not claimed.", 
            ephemeral=True
        )
        return
    
    # Extract ticket ID from channel name
    ticket_id = None
    for part in interaction.channel.name.split('-'):
        if len(part) == 6 and all(c in string.ascii_uppercase + string.digits for c in part):
            ticket_id = part
            break
    
    # Check if the user is the one who claimed it
    if ticket_id and interaction.guild.id in ticket_system.active_tickets and ticket_id in ticket_system.active_tickets[interaction.guild.id]:
        claimed_by = ticket_system.active_tickets[interaction.guild.id][ticket_id].get('claimed_by')
        if claimed_by and claimed_by != interaction.user.id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "You can only unclaim tickets that you have claimed.",
                ephemeral=True
            )
            return
        
        # Remove claimer info
        if 'claimed_by' in ticket_system.active_tickets[interaction.guild.id][ticket_id]:
            del ticket_system.active_tickets[interaction.guild.id][ticket_id]['claimed_by']
    
    # Unclaim the ticket - remove the "claimed" suffix
    new_name = interaction.channel.name.replace("-claimed", "")
    await interaction.channel.edit(name=new_name)
    
    await interaction.response.send_message(f"{interaction.user.mention} has unclaimed this ticket.")
    

# Update the ticket-setup command to include the banner
@bot.tree.command(name="ticket-setup", description="Send the ticket message.")
async def ticket_setup(interaction: discord.Interaction):
    """Create a ticket via dropdown."""
    # Check for proper permissions
    if not interaction.user.guild_permissions.administrator and not any(
        role.id == INTERNAL_AFFAIRS_ID for role in interaction.user.roles
    ):
        await interaction.response.send_message(
            "You need administrator permissions to set up the ticket system.",
            ephemeral=True
        )
        return
    
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
        await interaction.response.send_message("Ticket setup initiated.", ephemeral=True)
        
        # Check if there's a banner configured
        guild_config = ticket_system.ticket_config.get(interaction.guild.id, {})
        ticket_banner = guild_config.get('ticket_banner')
        
        # Send banner if configured
        if ticket_banner:
            banner_embed = discord.Embed()
            banner_embed.set_image(url=ticket_banner)
            await interaction.channel.send(embed=banner_embed)
        
        # Send the actual ticket creation message in the current channel
        await interaction.channel.send(embed=embed, view=view)
    
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
    
    # Acknowledge the interaction first
    await interaction.response.defer(ephemeral=True)
    
    # Modify channel permissions 
    await interaction.channel.set_permissions(member, read_messages=True, send_messages=True)
    
    # Send a follow-up message
    await interaction.followup.send(f"{member.mention} has been added to the ticket.")



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
    await interaction.response.send_message(f"{member.mention} has been removed from the ticket.", ephemeral=True)


@bot.tree.command(name="ticket-close", description="Close the current ticket")
async def ticket_close(interaction: discord.Interaction):
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
    
    # Acknowledge the interaction first
    await interaction.response.defer(ephemeral=True)
    
    # Remove from active tickets
    if interaction.guild.id in ticket_system.active_tickets:
        ticket_id = interaction.channel.name.split('-')[-1]
        if ticket_id in ticket_system.active_tickets[interaction.guild.id]:
            del ticket_system.active_tickets[interaction.guild.id][ticket_id]
    
    # Delete the channel
    await interaction.channel.delete()
    
    # Optional: Send a follow-up message if the channel deletion fails
    await interaction.followup.send("Ticket has been forcibly closed.")
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


#--------------------------------------

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



@bot.command(name="ban")
async def ban(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    moderator_role = discord.utils.get(ctx.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in ctx.author.roles:
        await ctx.send("You do not have permission to ban members.")
        return

    try:
        try:
            await member.send(f"You have been banned from {ctx.guild.name}. Reason: {reason}")
        except:
            pass

        await member.ban(reason=reason)

        log_channel = ctx.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
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


@bot.command(name="unban")
async def unban(ctx, user_id: str, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(ctx.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in ctx.author.roles:
        await ctx.send("You do not have permission to unban members.")
        return

    try:
        # Unban the user
        await ctx.guild.unban(discord.Object(id=int(user_id)), reason=reason)

        # Log the unban in a moderation log channel
        log_channel = ctx.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
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

@bot.command(name="mute")
async def mute(ctx, member: discord.Member, duration: int = None, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(ctx.guild.roles, id=MODERATOR_ROLE_ID)
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
        log_channel = ctx.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
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


@bot.command(name="unmute")
async def unmute(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(ctx.guild.roles, id=MODERATOR_ROLE_ID)
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
        log_channel = ctx.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
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




@bot.command(name="warn")
async def warn(ctx, member: discord.Member, *, reason: str):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(ctx.guild.roles, id=MODERATOR_ROLE_ID)
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
        log_channel = ctx.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
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



#------------------------------------

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

@bot.command(name="purge")
async def purge(ctx, amount: int):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(ctx.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in ctx.author.roles:
        await ctx.send("You do not have permission to purge messages.")
        return

    try:
        # Delete messages
        deleted = await ctx.channel.purge(limit=amount)

        # Log the purge in a moderation log channel
        log_channel = ctx.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
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


@bot.command(name="lock")
async def lock(ctx, channel: discord.TextChannel = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(ctx.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in ctx.author.roles:
        await ctx.send("You do not have permission to lock channels.")
        return

    # If no channel is specified, use the current channel
    channel = channel or ctx.channel

    try:
        # Overwrite permissions to prevent sending messages
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)

        # Log the channel lock in a moderation log channel
        log_channel = ctx.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
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


@bot.command(name="unlock")
async def unlock(ctx, channel: discord.TextChannel = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(ctx.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in ctx.author.roles:
        await ctx.send("You do not have permission to unlock channels.")
        return

    # If no channel is specified, use the current channel
    channel = channel or ctx.channel

    try:
        # Restore default permissions
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)

        # Log the channel unlock in a moderation log channel
        log_channel = ctx.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
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



@bot.command(name="slowmode")
async def slowmode(ctx, seconds: int, channel: discord.TextChannel = None):
    # Check if user has moderator permissions
    moderator_role = discord.utils.get(ctx.guild.roles, id=MODERATOR_ROLE_ID)
    if moderator_role not in ctx.author.roles:
        await ctx.send("You do not have permission to set slowmode.")
        return

    # If no channel is specified, use the current channel
    channel = channel or ctx.channel

    try:
        # Set slowmode
        await channel.edit(slowmode_delay=seconds)

        # Log the slowmode change in a moderation log channel
        log_channel = ctx.guild.get_channel(MODERATION_LOG_CHANNEL_ID)
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

    i = 0
    while i < len(entries) - 1:  # Process in pairs (time and then user)
        try:
            # Get the time part (from the odd index)
            time_part_raw = entries[i].strip()
            print(f"Raw Time Part: {time_part_raw}") # For debugging

            # Get the user part (from the even index)
            user_part_raw = entries[i + 1].strip()
            print(f"Raw User Part: {user_part_raw}") # For debugging

            # Remove :passed: or :failed: from the user part
            user_part = re.sub(r'^:passed:|:failed:', '', user_part_raw).strip()
            print(f"Cleaned User Part: {user_part}") # For debugging

            member = None
            mention_match = re.search(r'(<@\d+>)', user_part)

            if mention_match:
                user_id = int(mention_match.group(1)[2:-1])
                try:
                    member = await interaction.guild.fetch_member(user_id)
                except discord.NotFound:
                    pass

            if not member:
                username_match = re.search(r'(@[\w\s|\[\]\{\}\(\)\._-]+)', user_part)
                if username_match:
                    user_part_cleaned = re.sub(r'@|\[.*?\]|\{.*?\}|\(.*?\)', '', username_match.group(1)).strip()
                    for m in interaction.guild.members:
                        if (user_part_cleaned.lower() in m.name.lower() or
                                user_part_cleaned.lower() in m.display_name.lower() or
                                (m.nick and user_part_cleaned.lower() in m.nick.lower())):
                            member = m
                            break

            if not member:
                errors.append(f"Could not find member: {user_part}")
                i += 2 # Move to the next pair
                continue

            # Extract hours and minutes from the time part
            hours = 0
            minutes = 0
            seconds = 0

            hours_match = re.search(r'(\d+)\s*hour', time_part_raw.lower())
            if hours_match:
                hours = int(hours_match.group(1))

            minutes_match = re.search(r'(\d+)\s*minute', time_part_raw.lower())
            if minutes_match:
                minutes = int(minutes_match.group(1))

            seconds_match = re.search(r'(\d+)\s*second', time_part_raw.lower())
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
                    i += 2
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

                if member and next_role:
                    try:
                        # Invoke the promote command
                        await bot.tree.invoke(
                            interaction,  # Pass the original interaction context
                            'promote',    # The name of the command
                            user=member,
                            new_rank=next_role,
                            reason=f"Automatic promotion for {total_hours:.1f} hours of shift time"
                        )
                        promotions.append(f"{member.display_name}: {highest_role.name} → {next_role.name} ({total_hours:.1f} hours)")
                    except Exception as e:
                        errors.append(f"Error calling promote command for {member.display_name}: {e}")
                elif not next_role:
                    errors.append(f"No higher role found for {member.display_name}")

        except Exception as e:
            errors.append(f"Error processing entry: {entries[i][:30]}... - {str(e)}")

        i += 2  # Move to the next pair (time and then user)

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

@bot.tree.command(name="prefix", description="Change the current prefix.")
async def prefix(interaction: discord.Interaction, prefix: Optional[str] = None):
    if prefix is None:
        await interaction.response.send_message(f"The current prefix is {BOT_PREFIX}!")
    else:
        BOT_PREFIX = prefix
        await interaction.reponse.send_message(f"Updated bot prefix to {prefix}!")

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
