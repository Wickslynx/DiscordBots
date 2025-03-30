import discord
from discord.ext import commands
from datetime import datetime, time
import os
import asyncio
from discord.ext import tasks
from pathlib import Path
import random
import string
# FILL THESE IN WITH THE RIGHT ONES:

APPLICATION_ID =  #Your application ID.
TICKET_CHANNEL_ID = #(Where the logs will be sent)



class Bot(commands.Bot):
    def __init__(self):
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            application_id=APPLICATION_ID
        )

    async def setup_hook(self):
        self.add_view(TicketView(ticket_system, None))
        self.add_view(TicketCreateView(ticket_system))
            
        await self.tree.sync()
        print("Commands synced globally")



bot = Bot()



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
                label="Welcome Message", 
                value="welcome_message", 
                description="Change the default welcome message for all tickets"
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
                'welcome_message': "Welcome to ticket support!",
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
            
            embed.add_field(name="Welcome Message", value=config.get('welcome_message', "Not set"), inline=False)
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
                "welcome_message": "Welcome Message",
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
        # Store the welcome message
        if interaction.guild.id not in ticket_system.ticket_config:
            ticket_system.ticket_config[interaction.guild.id] = {}
        
        ticket_system.ticket_config[interaction.guild.id]['welcome_message'] = option
        
        await interaction.response.send_message(
            f"Ticket welcome message set to:\n```\n{option}\n```", 
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
                label="Welcome Message", 
                value="welcome_message", 
                description="Change the default welcome message for all tickets"
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
                'welcome_message': "Welcome to ticket support!",
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
            
            embed.add_field(name="Welcome Message", value=config.get('welcome_message', "Not set"), inline=False)
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
                "welcome_message": "Welcome Message",
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
        
        # Get welcome message based on ticket type
        message_key = f"{ticket_type}_message"
        welcome_message = guild_config.get(
            message_key, 
            guild_config.get('welcome_message', f"Welcome to {ticket_type.replace('-', ' ').title()} ticket support!")
        )
        
        # Send banner if configured
        if ticket_banner:
            embed = discord.Embed()
            embed.set_image(url=ticket_banner)
            await ticket_channel.send(embed=embed)
        
        # Create welcome embed
        embed = discord.Embed(
            title=f"{ticket_type.capitalize()} Ticket",
            description=welcome_message,
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
