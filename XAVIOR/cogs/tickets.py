import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import string
import random
import os

TICKET_CATEGORY_ID = 1307742965657112627
TICKET_LOG_CHANNEL_ID = 1355452294417879121
TICKET_CONFIG_FILE = 'storage/ticket_config.json'

class TicketSystem:
    def __init__(self):
        self.ticket_config = {}
        self.active_tickets = {}
        self.max_tickets_per_user = 4
        self.load_config()

    def generate_ticket_id(self):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    def get_user_ticket_count(self, guild_id, user_id):
        return sum(1 for t in self.active_tickets.get(guild_id, {}).values() if t['creator'] == user_id)

    def load_config(self):
        if os.path.exists(TICKET_CONFIG_FILE):
            with open(TICKET_CONFIG_FILE, 'r') as f:
                self.ticket_config = json.load(f)

    def save_config(self):
        with open(TICKET_CONFIG_FILE, 'w') as f:
            json.dump(self.ticket_config, f, indent=4)

    async def create_ticket_channel(self, bot, interaction: discord.Interaction, ticket_type: str):
        if self.get_user_ticket_count(interaction.guild.id, interaction.user.id) >= self.max_tickets_per_user:
            await interaction.response.send_message("You have too many open tickets.", ephemeral=True)
            return None

        ticket_id = self.generate_ticket_id()
        channel_name = f"{ticket_type}-{interaction.user.name[:4]}-{ticket_id}"
        category = interaction.guild.get_channel(TICKET_CATEGORY_ID)

        if not category:
            await interaction.response.send_message("Ticket category not found.", ephemeral=True)
            return None

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await interaction.guild.create_text_channel(name=channel_name, category=category)
        await channel.edit(overwrites=overwrites)

        embed = discord.Embed(title="🎫 Ticket Opened",
                              description=f"Type: **{ticket_type}**\nID: `{ticket_id}`",
                              color=discord.Color.blue())
        await channel.send(f"{interaction.user.mention}", embed=embed, view=TicketView(self, ticket_id))

        self.active_tickets.setdefault(interaction.guild.id, {})[ticket_id] = {
            'channel_id': channel.id,
            'creator': interaction.user.id,
            'type': ticket_type
        }

        return channel


class TicketView(discord.ui.View):
    def __init__(self, system: TicketSystem, ticket_id):
        super().__init__(timeout=None)
        self.system = system
        self.ticket_id = ticket_id

    @discord.ui.button(label="🔒 Close", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = self.system.active_tickets.get(interaction.guild.id, {}).get(self.ticket_id)
        if not ticket:
            return await interaction.response.send_message("Ticket not found.", ephemeral=True)

        embed = discord.Embed(title="❌ Ticket Closed",
                              description=f"Ticket ID `{self.ticket_id}` closed by {interaction.user.mention}",
                              color=discord.Color.red())

        log_channel = interaction.guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed)

        del self.system.active_tickets[interaction.guild.id][self.ticket_id]

        await interaction.channel.delete()


class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.system = TicketSystem()

    @app_commands.command(name="ticket", description="Create a new ticket")
    @app_commands.describe(ticket_type="The type of ticket to create")
    async def ticket(self, interaction: discord.Interaction, ticket_type: str):
        await self.system.create_ticket_channel(self.bot, interaction, ticket_type)


async def setup(bot):
    await bot.add_cog(TicketCog(bot))
