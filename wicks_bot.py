import discord
import asyncio
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from discord import app_commands
from collections import deque

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.voice_states = True

ydl_opts_audio = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,        
    'no_warnings': True,       
    'source_address': '0.0.0.0'  
}

ydl_opts_video = {
    'format': 'best[height<=720]',
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
        self.video_queue = deque()
        self.guild_voice_clients = {}  
        self.music_channels = {}  
        self.currently_playing = {}
        self.currently_playing_type = {}
        self.spotify = None
        
    async def setup_hook(self):
        await self.tree.sync()
        
class Media:
    def __init__(self, title, url, requested_by, source=None, media_type="audio"):
        self.title = title
        self.url = url
        self.requested_by = requested_by
        self.source = source
        self.media_type = media_type

client = MusicClient()

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    
    try:
        client.spotify = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(
                client_id="YOUR_SPOTIFY_CLIENT_ID",
                client_secret="YOUR_SPOTIFY_CLIENT_SECRET"
            )
        )
        print("Spotify client initialized successfully")
    except Exception as e:
        print(f"Failed to initialize Spotify client: {str(e)}")
        print("Spotify functionality may be limited")

async def send_error_message(channel_id, error_message):
    try:
        channel = client.get_channel(channel_id)
        if channel:
            await channel.send(f"Error: {error_message}")
    except Exception as e:
        print(f"Failed to send error message: {str(e)}")

async def get_audio_source(url):
    try:
        with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise Exception("Could not extract audio information")
            return {
                'title': info.get('title', 'Unknown Title'),
                'url': info.get('url')
            }
    except Exception as e:
        print(f"Error extracting audio source: {str(e)}")
        raise

async def get_video_source(url):
    try:
        with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise Exception("Could not extract video information")
            return {
                'title': info.get('title', 'Unknown Title'),
                'url': info.get('url'),
                'width': info.get('width', 720),
                'height': info.get('height', 480)
            }
    except Exception as e:
        print(f"Error extracting video source: {str(e)}")
        raise

async def get_spotify_track(url):
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
        
        with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
            search_results = ydl.extract_info(f"ytsearch:{search_query}", download=False)
            if not search_results or 'entries' not in search_results or not search_results['entries']:
                raise Exception("No results found for Spotify track")
            
            best_match = search_results['entries'][0]
            return {
                'title': f"{track_name} - {artist_name}",
                'url': best_match.get('url')
            }
    except Exception as e:
        print(f"Error processing Spotify track: {str(e)}")
        raise
async def play_next(guild_id):
    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        if client.music_queue:
            client.music_queue.clear()
        if client.video_queue:
            client.video_queue.clear()
        return
    
    # Determine which queue to pull from based on current media type
    next_media = None
    current_type = client.currently_playing_type.get(guild_id)
    
    if current_type == "audio":
        if client.music_queue:
            next_media = client.music_queue.popleft()
        elif client.video_queue:  # If audio queue empty, check video queue
            next_media = client.video_queue.popleft()
            current_type = "video"
    elif current_type == "video":
        if client.video_queue:
            next_media = client.video_queue.popleft()
        elif client.music_queue:  # If video queue empty, check audio queue
            next_media = client.music_queue.popleft()
            current_type = "audio"
    else:
        # If nothing is currently playing, check both queues
        if client.music_queue:
            next_media = client.music_queue.popleft()
            current_type = "audio"
        elif client.video_queue:
            next_media = client.video_queue.popleft()
            current_type = "video"
    
    # If no media found in any queue
    if not next_media:
        client.currently_playing[guild_id] = None
        client.currently_playing_type[guild_id] = None
        return
    
    client.currently_playing[guild_id] = next_media
    client.currently_playing_type[guild_id] = current_type
    
    try:
        voice_client = client.guild_voice_clients[guild_id]
        
        # Play audio for both audio and video types
        audio = discord.FFmpegPCMAudio(
            next_media.source['url'],
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            options="-vn -bufsize 1024k"  # Always strip video, we'll handle video separately
        )
        audio = discord.PCMVolumeTransformer(audio, volume=0.5)
        voice_client.play(
            audio, 
            after=lambda e: handle_playback_error(e, guild_id)
        )
        
        # Send appropriate notification
        if guild_id in client.music_channels:
            channel = client.get_channel(client.music_channels[guild_id])
            if channel:
                if current_type == "audio":
                    await channel.send(f"🎵 Now playing: **{next_media.title}** (requested by {next_media.requested_by.mention})")
                else:  # For videos that were queued, we'll send the embed again when it starts playing
                    # Create rich embed with video link
                    embed = discord.Embed(
                        title=f"📺 Now Playing: {next_media.title}",
                        description=f"Requested by {next_media.requested_by.mention}",
                        color=discord.Color.red()
                    )
                    
                    # Try to get thumbnail
                    try:
                        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                            video_info = ydl.extract_info(next_media.url, download=False)
                            if 'thumbnail' in video_info:
                                embed.set_image(url=video_info['thumbnail'])
                    except:
                        pass
                    
                    # Add video link
                    if "youtube.com/watch?v=" in next_media.url:
                        video_id = next_media.url.split("watch?v=")[1].split("&")[0]
                        embed.description += f"\n\n[Watch on YouTube](https://www.youtube.com/watch?v={video_id})"
                    elif "youtu.be/" in next_media.url:
                        video_id = next_media.url.split("youtu.be/")[1].split("?")[0]
                        embed.description += f"\n\n[Watch on YouTube](https://www.youtube.com/watch?v={video_id})"
                    else:
                        embed.description += f"\n\n[Watch Video]({next_media.url})"
                    
                    await channel.send(embed=embed)
    
    except Exception as e:
        error_msg = f"Error playing media: {str(e)}"
        print(error_msg)
        
        # Send error to the music channel
        if guild_id in client.music_channels:
            await send_error_message(client.music_channels[guild_id], error_msg)
        
        # Try to play next item
        asyncio.run_coroutine_threadsafe(play_next(guild_id), client.loop)



def handle_playback_error(error, guild_id):
    if error:
        error_msg = f"Playback error: {str(error)}"
        print(error_msg)
        
        # Send error to the music channel
        if guild_id in client.music_channels:
            asyncio.run_coroutine_threadsafe(
                send_error_message(client.music_channels[guild_id], error_msg), 
                client.loop
            )
    
    # Play next item
    asyncio.run_coroutine_threadsafe(play_next(guild_id), client.loop)

@client.tree.command(name="playsong", description="Play a song from YouTube or Spotify URL")
async def playsong(interaction: discord.Interaction, url: str):
    await interaction.response.defer(thinking=True)
    
    if not interaction.user.voice:
        await interaction.followup.send("You need to be in a voice channel to use this command!")
        return
        
    guild_id = interaction.guild.id
    
    try:
        if "spotify.com/track" in url:
            source = await get_spotify_track(url)
        else:
            source = await get_audio_source(url)
    except Exception as e:
        error_msg = f"Error retrieving the song: {str(e)}"
        await interaction.followup.send(f"Error: {error_msg}")
        return
        
    song = Media(source['title'], url, interaction.user, source, media_type="audio")

    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        try:
            voice_channel = interaction.user.voice.channel
            voice_client = await voice_channel.connect()
            client.guild_voice_clients[guild_id] = voice_client
        except discord.errors.ClientException as e:
            await interaction.followup.send(f"Error: Error connecting to voice channel: {str(e)}")
            return
    
    client.music_queue.append(song)
    
    if guild_id not in client.currently_playing or client.currently_playing[guild_id] is None:
        client.currently_playing_type[guild_id] = "audio"
        await play_next(guild_id)
        await interaction.followup.send(f"🎵 Now playing: **{song.title}**")
    else:
        await interaction.followup.send(f"🎵 Added to queue: **{song.title}**")

@client.tree.command(name="playvideo", description="Stream a video from YouTube URL")
async def playvideo(interaction: discord.Interaction, url: str):
    await interaction.response.defer(thinking=True)
    
    if not interaction.user.voice:
        await interaction.followup.send("You need to be in a voice channel to use this command!")
        return
        
    guild_id = interaction.guild.id
    
    try:
     
        source = await get_audio_source(url)  
        original_url = url  #
        
     
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            video_info = ydl.extract_info(url, download=False)
            video_title = video_info.get('title', 'Unknown Video')
            thumbnail = video_info.get('thumbnail', '')
    except Exception as e:
        error_msg = f"Error retrieving the video: {str(e)}"
        await interaction.followup.send(f"Error: {error_msg}")
        return
        

    video = Media(video_title, original_url, interaction.user, source, media_type="video")

    # Connect to voice channel if not already connected
    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        try:
            voice_channel = interaction.user.voice.channel
            voice_client = await voice_channel.connect()
            client.guild_voice_clients[guild_id] = voice_client
        except discord.errors.ClientException as e:
            await interaction.followup.send(f"Error: Error connecting to voice channel: {str(e)}")
            return
    
    # Add to video queue
    client.video_queue.append(video)
    
    # Create rich embed with video
    embed = discord.Embed(
        title=f"📺 Video: {video_title}",
        description=f"Requested by {interaction.user.mention}",
        color=discord.Color.red()
    )
    
    if thumbnail:
        embed.set_image(url=thumbnail)
    
    # If YouTube URL, reformat it for embedding
    if "youtube.com/watch?v=" in original_url:
        video_id = original_url.split("watch?v=")[1].split("&")[0]
        embed_url = f"https://www.youtube.com/embed/{video_id}"
        embed.description += f"\n\n[Watch on YouTube]({original_url})"
    elif "youtu.be/" in original_url:
        video_id = original_url.split("youtu.be/")[1].split("?")[0]
        embed_url = f"https://www.youtube.com/embed/{video_id}"
        embed.description += f"\n\n[Watch on YouTube]({original_url})"
    else:
        embed_url = original_url
        embed.description += f"\n\n[Watch Video]({original_url})"
    
    # Send video embed to the music channel or to the interaction channel
    target_channel = client.get_channel(client.music_channels.get(guild_id, interaction.channel_id))
    await target_channel.send(embed=embed)
    
    # Start playing the audio portion if nothing is currently playing
    if guild_id not in client.currently_playing or client.currently_playing[guild_id] is None:
        client.currently_playing_type[guild_id] = "video"
        await play_next(guild_id)
        await interaction.followup.send(f"📺 Now playing video audio: **{video_title}**\nCheck {target_channel.mention} for the video!")
    else:
        await interaction.followup.send(f"📺 Added to video queue: **{video_title}**\nVideo link posted in {target_channel.mention}!")
        

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
    
    song = Media(attachment.filename, attachment.url, interaction.user, source, media_type="audio")
    
    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        try:
            voice_channel = interaction.user.voice.channel
            voice_client = await voice_channel.connect()
            client.guild_voice_clients[guild_id] = voice_client
        except discord.errors.ClientException as e:
            await interaction.followup.send(f"Error: Error connecting to voice channel: {str(e)}")
            return
    
    client.music_queue.append(song)
    
    if guild_id not in client.currently_playing or client.currently_playing[guild_id] is None:
        client.currently_playing_type[guild_id] = "audio"
        await play_next(guild_id)
        await interaction.followup.send(f"🎵 Now playing: **{song.title}**")
    else:
        await interaction.followup.send(f"🎵 Added to queue: **{song.title}**")

@client.tree.command(name="skip", description="Skip the current media")
async def skip(interaction: discord.Interaction):
    guild_id = interaction.guild.id

    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        await interaction.response.send_message("I'm not playing anything right now!")
        return
    
    if guild_id not in client.currently_playing or client.currently_playing[guild_id] is None:
        await interaction.response.send_message("Nothing is playing right now!")
        return
    
    try:
        client.guild_voice_clients[guild_id].stop()
        await interaction.response.send_message("⏭️ Skipped to the next item!")
    except Exception as e:
        await interaction.response.send_message(f"Error: Failed to skip: {str(e)}")

@client.tree.command(name="stop", description="Stop playback and clear all queues")
async def stop(interaction: discord.Interaction):
    guild_id = interaction.guild.id

    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        await interaction.response.send_message("I'm not playing anything right now!")
        return
    
    try:
        client.music_queue.clear()
        client.video_queue.clear()
        
        client.guild_voice_clients[guild_id].stop()
        
        client.currently_playing[guild_id] = None
        client.currently_playing_type[guild_id] = None
        
        await interaction.response.send_message("⏹️ Playback stopped and queues cleared!")
    except Exception as e:
        await interaction.response.send_message(f"Error: Failed to stop: {str(e)}")

@client.tree.command(name="config", description="Configure the music channel")
async def config(interaction: discord.Interaction, channel: discord.TextChannel = None):
    guild_id = interaction.guild.id
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need administrator permissions to use this command!")
        return
        
    try:
        if channel:
            client.music_channels[guild_id] = channel.id
            await interaction.response.send_message(f"Media notifications will now be sent to {channel.mention}!")
        else:
            if guild_id in client.music_channels:
                del client.music_channels[guild_id]
            await interaction.response.send_message("Music channel configuration has been reset.")
    except Exception as e:
        await interaction.response.send_message(f"Error: Failed to configure channel: {str(e)}")

@client.tree.command(name="queue", description="Show the current media queues")
async def queue(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    
    try:
        if (not client.music_queue and not client.video_queue) and (
            guild_id not in client.currently_playing or client.currently_playing[guild_id] is None):
            await interaction.response.send_message("All queues are empty!")
            return
            
        queue_text = "**Current Media Queues:**\n"
        
        if guild_id in client.currently_playing and client.currently_playing[guild_id]:
            current_media = client.currently_playing[guild_id]
            media_type = "🎵 Audio" if client.currently_playing_type.get(guild_id) == "audio" else "📺 Video"
            queue_text += f"▶️ **Now Playing ({media_type})**: {current_media.title} (requested by {current_media.requested_by.display_name})\n\n"
        
        if client.music_queue:
            queue_text += "🎵 **Audio Queue**:\n"
            for i, song in enumerate(client.music_queue, 1):
                queue_text += f"{i}. {song.title} (requested by {song.requested_by.display_name})\n"
        else:
            queue_text += "🎵 **Audio Queue**: Nothing in queue!\n"
        
        if client.video_queue:
            queue_text += "\n📺 **Video Queue**:\n"
            for i, video in enumerate(client.video_queue, 1):
                queue_text += f"{i}. {video.title} (requested by {video.requested_by.display_name})\n"
        else:
            queue_text += "\n📺 **Video Queue**: Nothing in queue!"
            
        await interaction.response.send_message(queue_text)
    except Exception as e:
        await interaction.response.send_message(f"Error: Failed to display queues: {str(e)}")

@client.tree.command(name="disconnect", description="Disconnect the bot from voice channel")
async def disconnect(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    
    if guild_id not in client.guild_voice_clients or not client.guild_voice_clients[guild_id].is_connected():
        await interaction.response.send_message("I'm not in a voice channel!")
        return
    
    try:
        client.music_queue.clear()
        client.video_queue.clear()
        client.currently_playing[guild_id] = None
        client.currently_playing_type[guild_id] = None
        
        await client.guild_voice_clients[guild_id].disconnect()
        del client.guild_voice_clients[guild_id]
        
        await interaction.response.send_message("👋 Disconnected from voice channel!")
    except Exception as e:
        await interaction.response.send_message(f"Error: Failed to disconnect: {str(e)}")

token = ""

client.run(token)
