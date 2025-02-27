import discord
from discord import app_commands


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True 


class AFKClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.afk_messages = {}  

    async def setup_hook(self):
        
        await self.tree.sync()  

client = AFKClient()

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.tree.command(name="afk", description="Set your AFK status with a message")
async def afk(interaction: discord.Interaction, message: str):

    original_nick = interaction.user.display_name
    
    client.afk_messages[interaction.user.id] = message
    

    try:
        await interaction.user.edit(nick=f"AFK| {original_nick}")
    except discord.Forbidden:
      
        pass
        

    await interaction.response.send_message(f"{interaction.user.mention} is AFK: {message}")

@client.event
async def on_message(message):
    if message.author == client.user:  
        return
        

    if message.author.id in client.afk_messages:
  
        current_nick = message.author.display_name
        if current_nick.startswith("AFK| "):
            try:
                await message.author.edit(nick=current_nick[5:]) 
            except discord.Forbidden:
                pass
                

        del client.afk_messages[message.author.id]
      
        await message.channel.send(f"{message.author.mention} is no longer AFK.")
    

    for user_id, afk_msg in list(client.afk_messages.items()):
        if message.mentions and any(user_id == mention.id for mention in message.mentions): 
            user = message.guild.get_member(user_id)
            if user:
                await message.channel.send(f"{user.name} is AFK: {afk_msg}")

token = ""

client.run(token)
