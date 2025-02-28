import discord
import asyncio
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from discord import app_commands
from collections import deque
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('music_bot')

# Configure Discord intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.voice_states = True

# YT-DLP options for audio extraction
YDL_OPTS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,        
    'no_warnings': True,       
    'source_address': '0.0.0.0',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }]
}

class Media:
    def __init__(self, title, url, requested_by, source=None):
        self.title = title
        self.url = url
        self.requested_by = requested_by
        self.source = source

class MusicClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.music_queue = deque()
        self.guild_voice_clients = {}  
        self.music_channels = {}  
        self.currently_playing = {}
        self.spotify = None
        
    async def setup_hook(self):
        await self.tree.sync()
        logger.info("Command tree synced")

client = MusicClient()

@client.event
async def on_ready():
    logger.info(f'Logged in as {client.user}')
    
    try:
        client.spotify = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(
                client_id="YOUR_SPOTIFY_CLIENT_ID",
                client_secret="YOUR_SPOTIFY_CLIENT_SECRET"
            )
        )
        logger.info("Spotify client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Spotify client: {str(e)}")
        logger.warning("Spotify functionality will be limited")

async def send_message(channel_id, message, is_error=False):
    """Utility function to send messages to a channel"""
    try:
        channel = client.get_channel(channel_id)
        if channel:
            if is_error:
                await channel.send(f"❌ Error: {message}")
            else:
                await channel.send(message)
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}")

async def get_audio_source(url):
    """Extract audio source information from URL"""
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise Exception("Could not extract audio information")
            return {
                'title': info.get('title', 'Unknown Title'),
                'url': info.get('url', info.get('formats', [{}])[0].get('url')),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', '')
            }
    except Exception as e:
        logger.error(f"Error extracting audio source: {str(e)}")
        raise

async def get_spotify_track(url):
    """Convert Spotify track to playable audio"""
    if not client.spotify:
        raise Exception("Spotify client not initialized")
    
    try:
        if "/track/" not in url:
            raise Exception("Invalid Spotify track URL")
            
        track_id = url.split('/')[-1].split('?')[0]
        track_info = client.spotify.track(track_id)
        track_name = track_info['name']
        artist_name = track_info['artists'][0]['name']
        search_query = f"{track_name} {artist_name} audio"
        thumbnail = track_info['album']['images'][0]['url'] if track_info['album']['images'] else None
        
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            search_results = ydl.extract_info(f"ytsearch:{search_query}", download=False)
            if not search_results or 'entries' not in search_results or not search_results['entries']:
                raise Exception("No results found for Spotify track")
            
            best_match = search_results['entries'][0]
            return {
                'title': f"{track_name} - {artist_name}",
                'url': best_match.get('url', best_match.get('formats', [{}])[0].get('url')),
                'duration': best_match.get('duration', 0),
                'thumbnail': thumbnail or best_match.get('thumbnail', '')
            }
    except Exception as e:
        logger.error(f"Error processing Spotify track: {str(e)}")
        raise

async def play_next(guild_id):
    """Play the next song in the queue"""
    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        if client.music_queue:
            client.music_queue.clear()
        return
    
    # Get next track if available
    if not client.music_queue:
        client.currently_playing[guild_id] = None
        return
    
    next_media = client.music_queue.popleft()
    client.currently_playing[guild_id] = next_media
    
    try:
        voice_client = client.guild_voice_clients[guild_id]
        
        # Create an FFmpeg audio source
        audio = discord.FFmpegPCMAudio(
            next_media.source['url'],
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            options="-vn -bufsize 1024k"
        )
        
        # Apply volume transformation
        audio = discord.PCMVolumeTransformer(audio, volume=0.5)
        
        # Play the audio
        voice_client.play(
            audio, 
            after=lambda e: handle_playback_error(e, guild_id)
        )
        
        # Send notification to configured channel
        if guild_id in client.music_channels:
            channel_id = client.music_channels[guild_id]
            
            # Create rich embed with song info
            embed = discord.Embed(
                title=f"🎵 Now Playing: {next_media.title}",
                description=f"Requested by {next_media.requested_by.mention}",
                color=discord.Color.blue()
            )
            
            # Add thumbnail if available
            if next_media.source.get('thumbnail'):
                embed.set_thumbnail(url=next_media.source['thumbnail'])
                
            # Add duration if available
            if next_media.source.get('duration'):
                minutes, seconds = divmod(next_media.source['duration'], 60)
                embed.add_field(name="Duration", value=f"{minutes}:{seconds:02d}")
                
            channel = client.get_channel(channel_id)
            if channel:
                await channel.send(embed=embed)
                
    except Exception as e:
        error_msg = f"Error playing media: {str(e)}"
        logger.error(error_msg)
        
        # Send error to the music channel
        if guild_id in client.music_channels:
            await send_message(client.music_channels[guild_id], error_msg, is_error=True)
        
        # Try to play next item
        asyncio.run_coroutine_threadsafe(play_next(guild_id), client.loop)

def handle_playback_error(error, guild_id):
    """Handle errors during playback and play next song"""
    if error:
        error_msg = f"Playback error: {str(error)}"
        logger.error(error_msg)
        
        # Send error to the music channel
        if guild_id in client.music_channels:
            asyncio.run_coroutine_threadsafe(
                send_message(client.music_channels[guild_id], error_msg, is_error=True), 
                client.loop
            )
    
    # Play next item
    asyncio.run_coroutine_threadsafe(play_next(guild_id), client.loop)

@client.tree.command(name="play", description="Play a song from YouTube or Spotify URL")
@app_commands.describe(url="YouTube or Spotify URL to play")
async def play(interaction: discord.Interaction, url: str):
    await interaction.response.defer(thinking=True)
    
    if not interaction.user.voice:
        await interaction.followup.send("❌ You need to be in a voice channel to use this command!")
        return
        
    guild_id = interaction.guild.id
    
    try:
        if "spotify.com/track" in url:
            source = await get_spotify_track(url)
        else:
            source = await get_audio_source(url)
    except Exception as e:
        error_msg = f"Error retrieving the song: {str(e)}"
        await interaction.followup.send(f"❌ Error: {error_msg}")
        return
        
    song = Media(source['title'], url, interaction.user, source)

    # Connect to voice channel if not already connected
    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        try:
            voice_channel = interaction.user.voice.channel
            voice_client = await voice_channel.connect()
            client.guild_voice_clients[guild_id] = voice_client
            logger.info(f"Connected to voice channel {voice_channel.name} in {interaction.guild.name}")
        except discord.errors.ClientException as e:
            await interaction.followup.send(f"❌ Error connecting to voice channel: {str(e)}")
            return
    
    # Add song to queue
    client.music_queue.append(song)
    
    # Start playing if nothing is currently playing
    if guild_id not in client.currently_playing or client.currently_playing[guild_id] is None:
        await play_next(guild_id)
        await interaction.followup.send(f"▶️ Now playing: **{song.title}**")
    else:
        # Create a simple queue position message
        position = len(client.music_queue)
        await interaction.followup.send(f"🎵 Added to queue (#{position}): **{song.title}**")

@client.tree.command(name="playfile", description="Play a file from attachment")
async def playfile(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    
    if not interaction.user.voice:
        await interaction.followup.send("❌ You need to be in a voice channel to use this command!")
        return

    if not interaction.message or not interaction.message.attachments:
        await interaction.followup.send("❌ Please attach an audio file to your message!")
        return
        
    guild_id = interaction.guild.id
    attachment = interaction.message.attachments[0]
    
    # Check if the attachment is an audio file
    if not any(attachment.filename.endswith(ext) for ext in ['.mp3', '.wav', '.ogg', '.m4a']):
        await interaction.followup.send("❌ Please upload an audio file (mp3, wav, ogg, m4a)!")
        return
    
    source = {
        'title': attachment.filename,
        'url': attachment.url,
        'duration': 0,  # Duration unknown for attachments
        'thumbnail': None
    }
    
    song = Media(attachment.filename, attachment.url, interaction.user, source)
    
    # Connect to voice channel if not already connected
    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        try:
            voice_channel = interaction.user.voice.channel
            voice_client = await voice_channel.connect()
            client.guild_voice_clients[guild_id] = voice_client
            logger.info(f"Connected to voice channel {voice_channel.name} in {interaction.guild.name}")
        except discord.errors.ClientException as e:
            await interaction.followup.send(f"❌ Error connecting to voice channel: {str(e)}")
            return
    
    # Add song to queue
    client.music_queue.append(song)
    
    # Start playing if nothing is currently playing
    if guild_id not in client.currently_playing or client.currently_playing[guild_id] is None:
        await play_next(guild_id)
        await interaction.followup.send(f"▶️ Now playing: **{song.title}**")
    else:
        position = len(client.music_queue)
        await interaction.followup.send(f"🎵 Added to queue (#{position}): **{song.title}**")

@client.tree.command(name="skip", description="Skip the current song")
async def skip(interaction: discord.Interaction):
    guild_id = interaction.guild.id

    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        await interaction.response.send_message("❌ I'm not playing anything right now!")
        return
    
    if guild_id not in client.currently_playing or client.currently_playing[guild_id] is None:
        await interaction.response.send_message("❌ Nothing is playing right now!")
        return
    
    try:
        skipped_song = client.currently_playing[guild_id].title
        client.guild_voice_clients[guild_id].stop()
        await interaction.response.send_message(f"⏭️ Skipped: **{skipped_song}**")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to skip: {str(e)}")

@client.tree.command(name="stop", description="Stop playback and clear the queue")
async def stop(interaction: discord.Interaction):
    guild_id = interaction.guild.id

    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        await interaction.response.send_message("❌ I'm not playing anything right now!")
        return
    
    try:
        # Clear queue and stop playback
        client.music_queue.clear()
        client.guild_voice_clients[guild_id].stop()
        client.currently_playing[guild_id] = None
        
        await interaction.response.send_message("⏹️ Playback stopped and queue cleared!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to stop: {str(e)}")

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
@app_commands.describe(channel="Channel to send music notifications to")
async def config(interaction: discord.Interaction, channel: discord.TextChannel = None):
    guild_id = interaction.guild.id
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need administrator permissions to use this command!")
        return
        
    try:
        if channel:
            client.music_channels[guild_id] = channel.id
            await interaction.response.send_message(f"✅ Music notifications will now be sent to {channel.mention}!")
        else:
            if guild_id in client.music_channels:
                del client.music_channels[guild_id]
            await interaction.response.send_message("✅ Music channel configuration has been reset.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to configure channel: {str(e)}")

@client.tree.command(name="queue", description="Show the current song queue")
async def queue(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    
    try:
        if not client.music_queue and (
            guild_id not in client.currently_playing or client.currently_playing[guild_id] is None):
            await interaction.response.send_message("📋 Queue is empty!")
            return
            
        # Create embedded queue display
        embed = discord.Embed(
            title="🎵 Music Queue",
            description="Current song queue",
            color=discord.Color.blue()
        )
        
        # Add current song
        if guild_id in client.currently_playing and client.currently_playing[guild_id]:
            current = client.currently_playing[guild_id]
            embed.add_field(
                name="▶️ Now Playing",
                value=f"{current.title} (requested by {current.requested_by.display_name})",
                inline=False
            )
            
            # Add duration if available
            if current.source.get('duration'):
                minutes, seconds = divmod(current.source['duration'], 60)
                embed.add_field(name="Duration", value=f"{minutes}:{seconds:02d}", inline=True)
        
        # Add queued songs
        if client.music_queue:
            queue_text = ""
            for i, song in enumerate(client.music_queue, 1):
                # Truncate long titles to avoid embed errors
                title = song.title if len(song.title) < 50 else song.title[:47] + "..."
                queue_text += f"{i}. {title} (by {song.requested_by.display_name})\n"
                
                # Split into multiple fields if needed
                if i % 10 == 0 or i == len(client.music_queue):
                    embed.add_field(
                        name=f"🎶 Queue (showing {i-9 if i % 10 == 0 else (i-i%10)+1}-{i}/{len(client.music_queue)})",
                        value=queue_text,
                        inline=False
                    )
                    queue_text = ""
        else:
            embed.add_field(name="🎶 Queue", value="Nothing in queue!", inline=False)
            
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Error displaying queue: {str(e)}")
        await interaction.response.send_message(f"❌ Failed to display queue: {str(e)}")

@client.tree.command(name="disconnect", description="Disconnect the bot from voice channel")
async def disconnect(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    
    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        await interaction.response.send_message("❌ I'm not in a voice channel!")
        return
    
    try:
        # Clear queue and stop playback
        client.music_queue.clear()
        client.currently_playing[guild_id] = None
        
        await client.guild_voice_clients[guild_id].disconnect()
        del client.guild_voice_clients[guild_id]
        
        await interaction.response.send_message("👋 Disconnected from voice channel!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to disconnect: {str(e)}")

@client.tree.command(name="playlist", description="Play a Spotify playlist")
@app_commands.describe(url="Spotify playlist URL")
async def playlist(interaction: discord.Interaction, url: str):
    await interaction.response.defer(thinking=True)
    
    if not interaction.user.voice:
        await interaction.followup.send("❌ You need to be in a voice channel to use this command!")
        return
    
    if "spotify.com/playlist" not in url:
        await interaction.followup.send("❌ Please provide a valid Spotify playlist URL!")
        return
    
    guild_id = interaction.guild.id
    
    try:
        if not client.spotify:
            await interaction.followup.send("❌ Spotify integration is not available!")
            return
        
        # Extract playlist ID
        playlist_id = url.split('/')[-1].split('?')[0]
        
        # Get playlist info
        playlist = client.spotify.playlist(playlist_id)
        playlist_name = playlist['name']
        
        # Connect to voice channel if not already connected
        if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
            try:
                voice_channel = interaction.user.voice.channel
                voice_client = await voice_channel.connect()
                client.guild_voice_clients[guild_id] = voice_client
                logger.info(f"Connected to voice channel {voice_channel.name} in {interaction.guild.name}")
            except discord.errors.ClientException as e:
                await interaction.followup.send(f"❌ Error connecting to voice channel: {str(e)}")
                return
        
        # Send initial message
        await interaction.followup.send(f"🎵 Loading playlist: **{playlist_name}**")
        
        # Get tracks from playlist (limited to first 20 to avoid rate limits)
        tracks = playlist['tracks']['items'][:20]
        
        # Add each track to the queue
        added_count = 0
        for item in tracks:
            track = item['track']
            track_name = track['name']
            artist_name = track['artists'][0]['name']
            
            try:
                # Create a search query for YouTube
                search_query = f"{track_name} {artist_name} audio"
                
                # Get audio source
                with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                    search_results = ydl.extract_info(f"ytsearch:{search_query}", download=False)
                    if not search_results or 'entries' not in search_results or not search_results['entries']:
                        continue
                    
                    best_match = search_results['entries'][0]
                    source = {
                        'title': f"{track_name} - {artist_name}",
                        'url': best_match.get('url', best_match.get('formats', [{}])[0].get('url')),
                        'duration': best_match.get('duration', 0),
                        'thumbnail': track['album']['images'][0]['url'] if track['album']['images'] else None
                    }
                    
                    song = Media(source['title'], f"https://open.spotify.com/track/{track['id']}", interaction.user, source)
                    client.music_queue.append(song)
                    added_count += 1
                    
            except Exception as e:
                logger.error(f"Error adding track {track_name}: {str(e)}")
                continue
        
        # Start playing if nothing is currently playing
        if guild_id not in client.currently_playing or client.currently_playing[guild_id] is None:
            await play_next(guild_id)
        
        # Send summary message
        await interaction.channel.send(f"✅ Added {added_count} tracks from **{playlist_name}** to the queue!")
            
    except Exception as e:
        error_msg = f"Error processing playlist: {str(e)}"
        logger.error(error_msg)
        await interaction.followup.send(f"❌ {error_msg}")

# Add event listener for voice state updates to handle disconnects
@client.event
async def on_voice_state_update(member, before, after):
    # If the bot was disconnected or left alone in a voice channel
    if member.id == client.user.id and after.channel is None:
        guild_id = before.channel.guild.id
        
        # Clear queue and reset state
        if guild_id in client.guild_voice_clients:
            del client.guild_voice_clients[guild_id]
        
        if guild_id in client.currently_playing:
            client.currently_playing[guild_id] = None
            
        client.music_queue.clear()
        logger.info(f"Bot disconnected from voice in {before.channel.guild.name}")
    
    # Check if the bot is alone in a voice channel
    elif before.channel != after.channel:
        for guild in client.guilds:
            if guild.voice_client and guild.voice_client.is_connected():
                channel = guild.voice_client.channel
                members = channel.members
                
                # If bot is the only one left in the channel
                if len(members) == 1 and client.user.id in [m.id for m in members]:
                    guild_id = guild.id
                    
                    # Clear queue, reset state, and disconnect
                    if guild_id in client.currently_playing:
                        client.currently_playing[guild_id] = None
                    
                    client.music_queue.clear()
                    
                    # Disconnect after a delay (5 min)
                    await asyncio.sleep(300)
                    
                    # Check again if still alone before disconnecting
                    if guild.voice_client and len(guild.voice_client.channel.members) == 1:
                        await guild.voice_client.disconnect()
                        if guild_id in client.guild_voice_clients:
                            del client.guild_voice_clients[guild_id]
                        
                        # Notify in music channel if available
                        if guild_id in client.music_channels:
                            await send_message(
                                client.music_channels[guild_id],
                                "👋 Disconnected from voice channel due to inactivity."
                            )
                        
                        logger.info(f"Bot auto-disconnected from voice in {guild.name} due to inactivity")


token = ""

client.run(token)
