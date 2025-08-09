import os
import shutil
import zipfile
import asyncio
from config import Config
from bot.helpers.utils import format_string, send_message, edit_message
from bot.providers.apple.utils import create_apple_zip  # Corrected import
from bot.logger import LOGGER
from bot.settings import bot_set  # Added missing import
from mutagen import File
from mutagen.mp4 import MP4
import re

async def track_upload(metadata, user):
    """
    Upload a single track
    Args:
        metadata: Track metadata
        user: User details
    """
    # Determine base path for different providers
    if "Apple Music" in metadata['filepath']:
        base_path = os.path.join(Config.LOCAL_STORAGE, "Apple Music")
    else:
        base_path = Config.LOCAL_STORAGE
    
    if Config.UPLOAD_MODE == 'Telegram':
        await send_message(
            user,
            metadata['filepath'],
            'audio',
            caption=await format_string(
                "🎵 **{title}**\n👤 {artist}\n🎧 {provider}",
                {
                    'title': metadata['title'],
                    'artist': metadata['artist'],
                    'provider': metadata.get('provider', 'Apple Music')
                }
            ),
            meta={
                'duration': metadata['duration'],
                'artist': metadata['artist'],
                'title': metadata['title'],
                'thumbnail': metadata['thumbnail']
            }
        )
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await rclone_upload(user, metadata['filepath'], base_path)
        text = await format_string(
            "🎵 **{title}**\n👤 {artist}\n🎧 {provider}\n🔗 [Direct Link]({r_link})",
            {
                'title': metadata['title'],
                'artist': metadata['artist'],
                'provider': metadata.get('provider', 'Apple Music'),
                'r_link': rclone_link
            }
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"
        await send_message(user, text)
    
    # Cleanup
    os.remove(metadata['filepath'])
    if metadata.get('thumbnail'):
        os.remove(metadata['thumbnail'])

async def music_video_upload(metadata, user):
    """
    Upload a music video
    Args:
        metadata: Video metadata
        user: User details
    """
    # Determine base path for different providers
    if "Apple Music" in metadata['filepath']:
        base_path = os.path.join(Config.LOCAL_STORAGE, "Apple Music")
    else:
        base_path = Config.LOCAL_STORAGE
    
    if Config.UPLOAD_MODE == 'Telegram':
        await send_message(
            user,
            metadata['filepath'],
            'video',
            caption=await format_string(
                "🎬 **{title}**\n👤 {artist}\n🎧 {provider} Music Video",
                {
                    'title': metadata['title'],
                    'artist': metadata['artist'],
                    'provider': metadata.get('provider', 'Apple Music')
                }
            ),
            meta=metadata
        )
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await rclone_upload(user, metadata['filepath'], base_path)
        text = await format_string(
            "🎬 **{title}**\n👤 {artist}\n🎧 {provider} Music Video\n🔗 [Direct Link]({r_link})",
            {
                'title': metadata['title'],
                'artist': metadata['artist'],
                'provider': metadata.get('provider', 'Apple Music'),
                'r_link': rclone_link
            }
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"
        await send_message(user, text)
    
    # Cleanup
    os.remove(metadata['filepath'])
    if metadata.get('thumbnail'):
        os.remove(metadata['thumbnail'])

async def album_upload(metadata, user):
    """
    Upload an album
    Args:
        metadata: Album metadata
        user: User details
    """
    # Determine base path for different providers
    if "Apple Music" in metadata['folderpath']:
        base_path = os.path.join(Config.LOCAL_STORAGE, "Apple Music")
    else:
        base_path = Config.LOCAL_STORAGE
    
    if Config.UPLOAD_MODE == 'Telegram':
        if Config.ALBUM_ZIP:
            zip_path = await create_apple_zip(
                metadata['folderpath'], 
                user['user_id'],
                metadata
            )
            
            caption = await format_string(
                "💿 **{album}**\n👤 {artist}\n🎧 {provider}",
                {
                    'album': metadata['title'],
                    'artist': metadata['artist'],
                    'provider': metadata.get('provider', 'Apple Music')
                }
            )
            
            await send_message(
                user,
                zip_path,
                'doc',
                caption=caption
            )
            os.remove(zip_path)
        else:
            for track in metadata['tracks']:
                await track_upload(track, user)
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await rclone_upload(user, metadata['folderpath'], base_path)
        text = await format_string(
            "💿 **{album}**\n👤 {artist}\n🎧 {provider}\n🔗 [Direct Link]({r_link})",
            {
                'album': metadata['title'],
                'artist': metadata['artist'],
                'provider': metadata.get('provider', 'Apple Music'),
                'r_link': rclone_link
            }
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"
        
        if metadata.get('poster_msg'):
            await edit_message(metadata['poster_msg'], text)
        else:
            await send_message(user, text)
    
    shutil.rmtree(metadata['folderpath'])

async def artist_upload(metadata, user):
    """
    Upload an artist's content
    Args:
        metadata: Artist metadata
        user: User details
    """
    # Determine base path for different providers
    if "Apple Music" in metadata['folderpath']:
        base_path = os.path.join(Config.LOCAL_STORAGE, "Apple Music")
    else:
        base_path = Config.LOCAL_STORAGE
    
    if Config.UPLOAD_MODE == 'Telegram':
        if Config.ARTIST_ZIP:
            zip_path = await create_apple_zip(
                metadata['folderpath'], 
                user['user_id'],
                metadata
            )
            
            caption = await format_string(
                "🎤 **{artist}**\n🎧 {provider} Discography",
                {
                    'artist': metadata['title'],
                    'provider': metadata.get('provider', 'Apple Music')
                }
            )
            
            await send_message(
                user,
                zip_path,
                'doc',
                caption=caption
            )
            os.remove(zip_path)
        else:
            for album in metadata['albums']:
                await album_upload(album, user)
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await rclone_upload(user, metadata['folderpath'], base_path)
        text = await format_string(
            "🎤 **{artist}**\n🎧 {provider} Discography\n🔗 [Direct Link]({r_link})",
            {
                'artist': metadata['title'],
                'provider': metadata.get('provider', 'Apple Music'),
                'r_link': rclone_link
            }
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"
        await send_message(user, text)
    
    shutil.rmtree(metadata['folderpath'])

async def playlist_upload(metadata, user):
    """
    Upload a playlist
    Args:
        metadata: Playlist metadata
        user: User details
    """
    # Determine base path for different providers
    if "Apple Music" in metadata['folderpath']:
        base_path = os.path.join(Config.LOCAL_STORAGE, "Apple Music")
    else:
        base_path = Config.LOCAL_STORAGE
    
    if Config.UPLOAD_MODE == 'Telegram':
        if Config.PLAYLIST_ZIP:
            zip_path = await create_apple_zip(
                metadata['folderpath'], 
                user['user_id'],
                metadata
            )
            
            caption = await format_string(
                "🎵 **{title}**\n👤 Curated by {artist}\n🎧 {provider} Playlist",
                {
                    'title': metadata['title'],
                    'artist': metadata.get('artist', 'Various Artists'),
                    'provider': metadata.get('provider', 'Apple Music')
                }
            )
            
            await send_message(
                user,
                zip_path,
                'doc',
                caption=caption
            )
            os.remove(zip_path)
        else:
            for track in metadata['tracks']:
                await track_upload(track, user)
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await rclone_upload(user, metadata['folderpath'], base_path)
        text = await format_string(
            "🎵 **{title}**\n👤 Curated by {artist}\n🎧 {provider} Playlist\n🔗 [Direct Link]({r_link})",
            {
                'title': metadata['title'],
                'artist': metadata.get('artist', 'Various Artists'),
                'provider': metadata.get('provider', 'Apple Music'),
                'r_link': rclone_link
            }
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"
        await send_message(user, text)
    
    shutil.rmtree(metadata['folderpath'])

async def rclone_upload(user, path, base_path):
    """
    Upload files via Rclone
    Args:
        user: User details
        path: Path to file/folder
        base_path: Base directory path
    Returns:
        rclone_link, index_link
    """
    if not Config.RCLONE_DEST:
        return None, None
    
    relative_path = str(path).replace(base_path, "").lstrip('/')
    
    rclone_link = None
    index_link = None

    if bot_set.link_options in ['RCLONE', 'Both']:
        cmd = f'rclone link --config ./rclone.conf "{Config.RCLONE_DEST}/{relative_path}"'
        task = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await task.communicate()

        if task.returncode == 0:
            rclone_link = stdout.decode().strip()
        else:
            LOGGER.debug(f"Rclone link failed: {stderr.decode().strip()}")
    
    if bot_set.link_options in ['Index', 'Both'] and Config.INDEX_LINK:
        index_link = f"{Config.INDEX_LINK}/{relative_path}"
    
    return rclone_link, index_link
