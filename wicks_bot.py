import discord
import asyncio
import yt_dlp
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
        self.tree = app_commands.CommandTree(self)
        self.music_queue = deque()
        self.guild_voice_clients = {}
        self.music_channels = {}
        self.currently_playing = {}

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
        if interaction:
            await interaction.followup.send(f"❌ {error_msg}")
        print(error_msg)
        raise

async def play_next(guild_id):
    if not client.music_queue:
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
        print(f"Error playing song: {str(e)}")
        await interaction.followup.send(f"❌ Error playing song: {str(e)}")
        asyncio.run_coroutine_threadsafe(play_next(guild_id), client.loop)

def handle_playback_error(error, guild_id):
    if error:
        print(f"Playback error: {error}")
    asyncio.run_coroutine_threadsafe(play_next(guild_id), client.loop)

@client.tree.command(name="playsong", description="Play a song from YouTube URL")
async def playsong(interaction: discord.Interaction, url: str):
    await interaction.response.defer(thinking=True)

    for state in interaction.guild.voice_states.values():
        if state.user.id == interaction.user.id:
            member_in_voice = True
            voice_channel = state.channel
            break
    
    if not member_in_voice or voice_channel is None:
        await interaction.followup.send("You need to be in a voice channel to use this command!")
        return

    guild_id = interaction.guild.id

    try:
        source = await get_audio_source(url, interaction)
    except Exception as e:
        await interaction.followup.send(f"Error retrieving the song: {str(e)}")
        return

    song = Song(source['title'], url, interaction.user, source)

    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        try:
            voice_channel = interaction.user.voice.channel
            voice_client = await voice_channel.connect()
            client.guild_voice_clients[guild_id] = voice_client
        except discord.errors.ClientException as e:
            await interaction.followup.send(f"Error connecting to voice channel: {str(e)}")
            return

    client.music_queue.append(song)

    if guild_id not in client.currently_playing or client.currently_playing[guild_id] is None:
        await play_next(guild_id)
        await interaction.followup.send(f"🎵 Now playing: **{song.title}**")
    else:
        await interaction.followup.send(f"🎵 Added to queue: **{song.title}**")

@client.tree.command(name="playfile", description="Play a file from attachment")
async def playfile(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    if not interaction.user.voice:
        await interaction.followup.send("You need to be in a voice channel to use this command!")
        return

    if not interaction.message or not interaction.message.attachments:
        await interaction.followup.send("Please attach an audio file to your message!")
        return

    guild_id = interaction.guild.id

    attachment = interaction.message.attachments[0]

    if not any(attachment.filename.endswith(ext) for ext in ['.mp3', '.wav', '.ogg', '.m4a']):
        await interaction.followup.send("Please upload an audio file (mp3, wav, ogg, m4a)!")
        return

    source = {
        'title': attachment.filename,
        'url': attachment.url
    }

    song = Song(attachment.filename, attachment.url, interaction.user, source)

    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        try:
            voice_channel = interaction.user.voice.channel
            voice_client = await voice_channel.connect()
            client.guild_voice_clients[guild_id] = voice_client
        except discord.errors.ClientException as e:
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
        await interaction.response.send_message(f"❌ Failed to pause: {str(e)}")

@client.tree.command(name="resume", description="Resume the paused song")
async def resume(interaction: discord.Interaction):
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
        await interaction.response.send_message(f"❌ Failed to resume: {str(e)}")

@client.tree.command(name="volume", description="Set the playback volume (0-100)")
@app_commands.describe(level="Volume level (0-100)")
async def volume(interaction: discord.Interaction, level: int):
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
        await interaction.response.send_message(f"❌ Failed to set volume: {str(e)}")

@client.tree.command(name="config", description="Configure the music channel")
async def config(interaction: discord.Interaction, channel: discord.TextChannel = None):
    guild_id = interaction.guild.id

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need administrator permissions to use this command!")
        return

    if channel:
        client.music_channels[guild_id] = channel.id
        await interaction.response.send_message(f"Music notifications will now be sent to {channel.mention}!")
    else:
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
    guild_id = interaction.guild.id

    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        await interaction.response.send_message("I'm not in a voice channel!")
        return

    client.music_queue.clear()
    client.currently_playing[guild_id] = None

    await client.guild_voice_clients[guild_id].disconnect()
    del client.guild_voice_clients[guild_id]

    await interaction.response.send_message("👋 Disconnected from voice channel!")

token = ""

client.run(token)
