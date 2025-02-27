import discord
from discord.ext import commands

# Set up intents (remove duplicate line)
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # Need this to read message content

# Create bot (remove duplicate line)
bot = commands.Bot(command_prefix="/", intents=intents)

# For storing messages (remove duplicate line)
afk_messages = {}  

@bot.command(name="afk")
async def afk(ctx, *, user_message: str):
    # Save the original nickname before changing it
    original_nick = ctx.author.display_name
    
    # Store the AFK message
    afk_messages[ctx.author.id] = user_message
    
    # Update nickname with AFK prefix
    try:
        await ctx.author.edit(nick=f"AFK| {original_nick}")
    except discord.Forbidden:
        # Handle case where bot doesn't have permission to change nicknames
        pass
        
    # Send confirmation message (fixed variable name from 'message' to 'user_message')
    await ctx.send(f"AFK: {ctx.author.name}: {user_message}")

@bot.event
async def on_message(message):
    if message.author == bot.user:  # Prevent bot from answering itself.
        return
        
    # Check if the message author was AFK
    if message.author.id in afk_messages:
        # Get the original nickname (remove AFK prefix)
        current_nick = message.author.display_name
        if current_nick.startswith("AFK| "):
            try:
                await message.author.edit(nick=current_nick[5:])  # Remove the "AFK| " prefix
            except discord.Forbidden:
                pass
                
        # Remove from AFK list
        del afk_messages[message.author.id]
        # Fixed message wording
        await message.channel.send(f"{message.author.name} is no longer AFK.")
    
    # Check if message mentions any AFK users
    for user_id, afk_msg in afk_messages.items():
        if message.mentions and any(user_id == mention.id for mention in message.mentions): 
            user = message.guild.get_member(user_id)
            if user:
                await message.channel.send(f"{user.name} is AFK: {afk_msg}")
    
    # This line is important! It processes commands
    await bot.process_commands(message)

# Add your bot token inside the quotes
bot.run("YOUR_BOT_TOKEN_HERE")
