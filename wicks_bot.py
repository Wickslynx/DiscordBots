import discord
import asyncio
import yt_dlp
import os
import datetime
from discord import app_commands
from collections import deque

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.voice_states = True

ydl_opts = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'no_warnings': True,
    'source_address': '0.0.0.0'
}

class MusicClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        # Create command tree once
        self.tree = app_commands.CommandTree(self)
        self.music_queue = deque()
        self.guild_voice_clients = {}
        self.music_channels = {}
        self.currently_playing = {}
        self.synced = False  # Track if commands have been synced
        
        # Error logging
        self.error_logs = deque(maxlen=100)  # Store last 100 errors
        self.log_file = "bot_errors.log"
        
        # Create log file if it doesn't exist
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w") as f:
                f.write("=== Bot Error Log ===\n")

    async def setup_hook(self):
        # This is called when the bot starts up
        # We'll only sync commands from here to prevent 
        # the "Unknown Integration" error
        pass
        
    def log_error(self, error_message, error_source):
        """Log an error to both memory and file"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_error = f"[{timestamp}] {error_source}: {error_message}"
        
        # Add to memory log
        self.error_logs.append(full_error)
        
        # Write to file
        try:
            with open(self.log_file, "a") as f:
                f.write(f"{full_error}\n")
        except Exception as e:
            print(f"Failed to write to log file: {e}")

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
    
    # Sync commands only if they haven't been synced yet
    if not client.synced:
        # Global sync - can take up to an hour to propagate
        await client.tree.sync()
        print("Command tree synced globally")
        client.synced = True

async def get_audio_source(url, interaction=None):
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown Title'),
                'url': info.get('url')
            }
    except Exception as e:
        error_msg = f"Error extracting audio source: {str(e)}"
        client.log_error(str(e), f"get_audio_source({url})")
        if interaction:
            await interaction.followup.send(f"❌ {error_msg}")
        print(error_msg)
        raise

async def play_next(guild_id):
    if not client.music_queue:
        if guild_id in client.currently_playing:
            client.currently_playing[guild_id] = None
        return
        
    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        client.music_queue.clear()
        return
        
    next_song = client.music_queue.popleft()

    client.currently_playing[guild_id] = next_song

    try:
        audio = discord.FFmpegPCMAudio(
            next_song.source['url'],
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            options="-vn -bufsize 1024k"
        )
        audio = discord.PCMVolumeTransformer(audio, volume=0.5)

        voice_client = client.guild_voice_clients[guild_id]
        voice_client.play(
            audio,
            after=lambda e: handle_playback_error(e, guild_id)
        )

        if guild_id in client.music_channels:
            channel = client.get_channel(client.music_channels[guild_id])
            if channel:
                await channel.send(f"🎵 Now playing: **{next_song.title}** (requested by {next_song.requested_by.mention})")

    except Exception as e:
        client.log_error(str(e), f"play_next(guild_id={guild_id})")
        print(f"Error playing song: {str(e)}")
        asyncio.run_coroutine_threadsafe(play_next(guild_id), client.loop)

def handle_playback_error(error, guild_id):
    if error:
        client.log_error(str(error), f"playback_error(guild_id={guild_id})")
        print(f"Playback error: {error}")
    asyncio.run_coroutine_threadsafe(play_next(guild_id), client.loop)

@client.tree.command(name="playsong", description="Play a song from YouTube URL")
@app_commands.describe(url="YouTube URL of the song to play")
async def playsong(interaction: discord.Interaction, url: str):
    await interaction.response.defer(thinking=True)

    if not interaction.guild:
        await interaction.followup.send("This command can only be used in a server!")
        return

    guild_id = interaction.guild.id

    try:
        # Check if user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("You need to be in a voice channel to use this command!")
            return
            
        voice_channel = interaction.user.voice.channel
    except Exception as e:
        client.log_error(str(e), f"playsong_voice_check(user={interaction.user.id})")
        print(f"Error checking voice state: {e}")
        await interaction.followup.send("You need to be in a voice channel to use this command!")
        return
    
    try:
        source = await get_audio_source(url, interaction)
    except Exception as e:
        client.log_error(str(e), f"playsong_get_source(url={url})")
        await interaction.followup.send(f"Error retrieving the song: {str(e)}")
        return

    song = Song(source['title'], url, interaction.user, source)

    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        try:
            voice_client = await voice_channel.connect()
            client.guild_voice_clients[guild_id] = voice_client
        except discord.errors.ClientException as e:
            client.log_error(str(e), f"playsong_connect(guild={guild_id}, channel={voice_channel.id})")
            await interaction.followup.send(f"Error connecting to voice channel: {str(e)}")
            return

    client.music_queue.append(song)

    if guild_id not in client.currently_playing or client.currently_playing[guild_id] is None:
        await play_next(guild_id)
        await interaction.followup.send(f"🎵 Now playing: **{song.title}**")
    else:
        await interaction.followup.send(f"🎵 Added to queue: **{song.title}**")

@client.tree.command(name="skip", description="Skip the current song")
async def skip(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server!")
        return
        
    guild_id = interaction.guild.id

    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        await interaction.response.send_message("I'm not playing anything right now!")
        return

    if guild_id not in client.currently_playing or client.currently_playing[guild_id] is None:
        await interaction.response.send_message("Nothing is playing right now!")
        return

    client.guild_voice_clients[guild_id].stop()

    await interaction.response.send_message("⏭️ Skipped to the next song!")

@client.tree.command(name="stop", description="Stop playback and clear the queue")
async def stop(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server!")
        return
        
    guild_id = interaction.guild.id

    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        await interaction.response.send_message("I'm not playing anything right now!")
        return

    client.music_queue.clear()
    client.guild_voice_clients[guild_id].stop()

    client.currently_playing[guild_id] = None

    await interaction.response.send_message("⏹️ Playback stopped and queue cleared!")

@client.tree.command(name="pause", description="Pause the current song")
async def pause(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server!")
        return
        
    guild_id = interaction.guild.id

    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        await interaction.response.send_message("❌ I'm not playing anything right now!")
        return

    try:
        voice_client = client.guild_voice_clients[guild_id]
        if voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("⏸️ Playback paused!")
        else:
            await interaction.response.send_message("❌ Nothing is playing right now!")
    except Exception as e:
        client.log_error(str(e), f"pause_command(guild={guild_id})")
        await interaction.response.send_message(f"❌ Failed to pause: {str(e)}")

@client.tree.command(name="resume", description="Resume the paused song")
async def resume(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server!")
        return
        
    guild_id = interaction.guild.id

    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        await interaction.response.send_message("❌ I'm not connected to a voice channel!")
        return

    try:
        voice_client = client.guild_voice_clients[guild_id]
        if voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("▶️ Playback resumed!")
        else:
            await interaction.response.send_message("❌ Playback is not paused!")
    except Exception as e:
        client.log_error(str(e), f"resume_command(guild={guild_id})")
        await interaction.response.send_message(f"❌ Failed to resume: {str(e)}")

@client.tree.command(name="volume", description="Set the playback volume (0-100)")
@app_commands.describe(level="Volume level (0-100)")
async def volume(interaction: discord.Interaction, level: int):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server!")
        return
        
    guild_id = interaction.guild.id

    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        await interaction.response.send_message("❌ I'm not playing anything right now!")
        return

    if level < 0 or level > 100:
        await interaction.response.send_message("❌ Volume must be between 0 and 100!")
        return

    try:
        voice_client = client.guild_voice_clients[guild_id]
        if hasattr(voice_client.source, 'volume'):
            voice_client.source.volume = level / 100.0
            await interaction.response.send_message(f"🔊 Volume set to {level}%")
        else:
            await interaction.response.send_message("❌ Cannot adjust volume for current source!")
    except Exception as e:
        client.log_error(str(e), f"volume_command(guild={guild_id}, level={level})")
        await interaction.response.send_message(f"❌ Failed to set volume: {str(e)}")

@client.tree.command(name="queue", description="Show the current music queue")
async def queue(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server!")
        return
        
    guild_id = interaction.guild.id

    if not client.music_queue and (guild_id not in client.currently_playing or client.currently_playing[guild_id] is None):
        await interaction.response.send_message("The queue is empty!")
        return

    queue_text = "🎵 **Current Queue:**\n"

    if guild_id in client.currently_playing and client.currently_playing[guild_id]:
        current_song = client.currently_playing[guild_id]
        queue_text += f"▶️ **Now Playing**: {current_song.title} (requested by {current_song.requested_by.display_name})\n\n"

    if client.music_queue:
        queue_text += "📋 **Up Next**:\n"
        for i, song in enumerate(client.music_queue, 1):
            queue_text += f"{i}. {song.title} (requested by {song.requested_by.display_name})\n"
    else:
        queue_text += "📋 **Up Next**: Nothing in queue!"

    await interaction.response.send_message(queue_text)

@client.tree.command(name="disconnect", description="Disconnect the bot from voice channel")
async def disconnect(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server!")
        return
        
    guild_id = interaction.guild.id

    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        await interaction.response.send_message("I'm not in a voice channel!")
        return

    client.music_queue.clear()
    client.currently_playing[guild_id] = None

    await client.guild_voice_clients[guild_id].disconnect()
    del client.guild_voice_clients[guild_id]

    await interaction.response.send_message("
