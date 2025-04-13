import discord
from discord.ext import commands
from discord import app_commands
import json
import os

CONFIG_DIR = 'configs'
os.makedirs(CONFIG_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "WELCOME_CHANNEL_ID": None,
    "LEAVES_CHANNEL_ID": None,
    "ANNOUNCEMENT_CHANNEL_ID": None,
    "REQUEST_CHANNEL_ID": None,
    "INFRACTIONS_CHANNEL_ID": None,
    "PROMOTIONS_CHANNEL_ID": None,
    "SUGGEST_CHANNEL_ID": None,
    "RETIREMENTS_CHANNEL_ID": None,
    "TRAINING_CHANNEL_ID": None,
    "INTERNAL_AFFAIRS_ID": None,
    "LOA_CHANNEL_ID": None,
    "OT_ID": None,
    "STAFF_TEAM_ID": None,
    "AWAITING_TRAINING_ID": None,
    "LOA_ID": None
}

class ConfigCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_configs = {}

    def get_config_path(self, guild_id):
        return os.path.join(CONFIG_DIR, f'{guild_id}.json')

    def get_guild_config(self, guild_id):
        gid = str(guild_id)
        if gid not in self.guild_configs:
            self.guild_configs[gid] = self.load_guild_config(gid)
        return self.guild_configs[gid]

    def load_guild_config(self, gid):
        path = self.get_config_path(gid)
        config = DEFAULT_CONFIG.copy()
        if os.path.exists(path):
            with open(path, 'r') as f:
                loaded = json.load(f)
                config.update(loaded)
        return config

    def save_guild_config(self, guild_id):
        gid = str(guild_id)
        path = self.get_config_path(gid)
        if gid in self.guild_configs:
            with open(path, 'w') as f:
                json.dump(self.guild_configs[gid], f, indent=4)

    @app_commands.command(name="config", description="Configure the bot settings")
    @app_commands.describe(action="The action to perform (view, set, reset)")
    @app_commands.choices(action=[
        app_commands.Choice(name="view", value="view"),
        app_commands.Choice(name="set", value="set"),
        app_commands.Choice(name="reset", value="reset")
    ])
    async def config(self, interaction: discord.Interaction, action: str):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ You need administrator permissions to use this command.", ephemeral=True)

        guild_id = interaction.guild_id

        if action == "view":
            await self.view_config(interaction, guild_id)
        elif action == "set":
            await interaction.response.send_message("📝 Configuration UI not yet implemented.", ephemeral=True)
        elif action == "reset":
            self.guild_configs[str(guild_id)] = DEFAULT_CONFIG.copy()
            self.save_guild_config(guild_id)
            await interaction.response.send_message("✅ Configuration has been reset.", ephemeral=True)

    async def view_config(self, interaction: discord.Interaction, guild_id):
        config = self.get_guild_config(guild_id)

        embed = discord.Embed(
            title="📊 Current Bot Configuration",
            color=discord.Color.blue()
        )

        for key, value in config.items():
            if key.endswith("_ID") and value:
                if "CHANNEL" in key:
                    display = f"<#{value}>"
                else:
                    display = f"<@&{value}>"
            else:
                display = "Not set"
            embed.add_field(name=key, value=display, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ConfigCog(bot))
