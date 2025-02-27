import discord
import asyncio
import yt_dlp
from discord import app_commands
from collections import deque

# Set up intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.voice_states = True

# Configure yt-dlp to extract audio only
ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'noplaylist': True,
    'quiet': True
}

class MusicClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.music_queue = deque()
        self.guild_voice_clients = {}  # Renamed to avoid conflict
        self.music_channels = {}  # Config for music channels per guild
        self.currently_playing = {}  # Track currently playing song

    async def setup_hook(self):
        await self.tree.sync()
        
class Song:
    def __init__(self, title, url, requested_by, source=None):
        self.title = title
        self.url = url
        self.requested_by = requested_by
        self.source = source

client = MusicClient()

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

async def get_audio_source(url):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            'title': info.get('title', 'Unknown Title'),
            'url': info.get('url')
        }

async def play_next(guild_id):
    if not client.music_queue:
        client.currently_playing[guild_id] = None
        return
        
    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        client.music_queue.clear()
        return
        
    # Get the next song
    next_song = client.music_queue.popleft()
    
    # Update currently playing
    client.currently_playing[guild_id] = next_song
    
    # Create FFmpeg audio source
    audio = discord.FFmpegPCMAudio(next_song.source['url'])
    
    # Start playing
    voice_client = client.guild_voice_clients[guild_id]
    voice_client.play(audio, after=lambda e: asyncio.run_coroutine_threadsafe(
        play_next(guild_id), client.loop).result())
    
    # Notify which channel to send to
    if guild_id in client.music_channels:
        channel = client.get_channel(client.music_channels[guild_id])
        if channel:
            await channel.send(f"🎵 Now playing: **{next_song.title}** (requested by {next_song.requested_by.mention})")

@client.tree.command(name="playsong", description="Play a song from YouTube URL")
async def playsong(interaction: discord.Interaction, url: str):
    await interaction.response.defer(thinking=True)
    
    # Check if user is in a voice channel
    if not interaction.user.voice:
        await interaction.followup.send("You need to be in a voice channel to use this command!")
        return
        
    guild_id = interaction.guild.id
    
    # Get audio source
    try:
        source = await get_audio_source(url)
    except Exception as e:
        await interaction.followup.send(f"Error retrieving the song: {str(e)}")
        return
        
    # Create song object
    song = Song(source['title'], url, interaction.user, source)
    
    # Connect to voice channel if not already connected
    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        voice_channel = interaction.user.voice.channel
        voice_client = await voice_channel.connect()
        client.guild_voice_clients[guild_id] = voice_client
    
    # Add song to queue
    client.music_queue.append(song)
    
    # Start playing if nothing is playing
    if guild_id not in client.currently_playing or client.currently_playing[guild_id] is None:
        await play_next(guild_id)
        await interaction.followup.send(f"🎵 Now playing: **{song.title}**")
    else:
        await interaction.followup.send(f"🎵 Added to queue: **{song.title}**")

@client.tree.command(name="playfile", description="Play a file from attachment")
async def playfile(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    
    # Check if user is in a voice channel
    if not interaction.user.voice:
        await interaction.followup.send("You need to be in a voice channel to use this command!")
        return
        
    # Check if there's an attachment
    if not interaction.message or not interaction.message.attachments:
        await interaction.followup.send("Please attach an audio file to your message!")
        return
        
    guild_id = interaction.guild.id
    
    # Get the first attachment
    attachment = interaction.message.attachments[0]
    
    # Only allow audio files
    if not any(attachment.filename.endswith(ext) for ext in ['.mp3', '.wav', '.ogg', '.m4a']):
        await interaction.followup.send("Please upload an audio file (mp3, wav, ogg, m4a)!")
        return
        
    # Create source dict similar to YouTube
    source = {
        'title': attachment.filename,
        'url': attachment.url
    }
    
    # Create song object
    song = Song(attachment.filename, attachment.url, interaction.user, source)
    
    # Connect to voice channel if not already connected
    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        voice_channel = interaction.user.voice.channel
        voice_client = await voice_channel.connect()
        client.guild_voice_clients[guild_id] = voice_client
    
    # Add song to queue
    client.music_queue.append(song)
    
    # Start playing if nothing is playing
    if guild_id not in client.currently_playing or client.currently_playing[guild_id] is None:
        await play_next(guild_id)
        await interaction.followup.send(f"🎵 Now playing: **{song.title}**")
    else:
        await interaction.followup.send(f"🎵 Added to queue: **{song.title}**")

@client.tree.command(name="skip", description="Skip the current song")
async def skip(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    
    # Check if bot is in a voice channel
    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        await interaction.response.send_message("I'm not playing anything right now!")
        return
        
    # Check if something is playing
    if guild_id not in client.currently_playing or client.currently_playing[guild_id] is None:
        await interaction.response.send_message("Nothing is playing right now!")
        return
        
    # Stop current song (this will trigger play_next due to the after parameter)
    client.guild_voice_clients[guild_id].stop()
    
    await interaction.response.send_message("⏭️ Skipped to the next song!")

@client.tree.command(name="config", description="Configure the music channel")
async def config(interaction: discord.Interaction, channel: discord.TextChannel = None):
    guild_id = interaction.guild.id
    
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need administrator permissions to use this command!")
        return
        
    if channel:
        # Set the music channel
        client.music_channels[guild_id] = channel.id
        await interaction.response.send_message(f"Music notifications will now be sent to {channel.mention}!")
    else:
        # Remove the music channel configuration
        if guild_id in client.music_channels:
            del client.music_channels[guild_id]
        await interaction.response.send_message("Music channel configuration has been reset.")

@client.tree.command(name="queue", description="Show the current music queue")
async def queue(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    
    if not client.music_queue and (guild_id not in client.currently_playing or client.currently_playing[guild_id] is None):
        await interaction.response.send_message("The queue is empty!")
        return
        
    queue_text = "🎵 **Current Queue:**\n"
    
    # Add currently playing song
    if guild_id in client.currently_playing and client.currently_playing[guild_id]:
        current_song = client.currently_playing[guild_id]
        queue_text += f"▶️ **Now Playing**: {current_song.title} (requested by {current_song.requested_by.display_name})\n\n"
    
    # Add queue
    if client.music_queue:
        queue_text += "📋 **Up Next**:\n"
        for i, song in enumerate(client.music_queue, 1):
            queue_text += f"{i}. {song.title} (requested by {song.requested_by.display_name})\n"
    else:
        queue_text += "📋 **Up Next**: Nothing in queue!"
        
    await interaction.response.send_message(queue_text)

token = ""
client.run(token)
