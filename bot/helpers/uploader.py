import os
import shutil
import zipfile
from config import Config
from bot.helpers.utils import format_string, send_message, edit_message
from bot.providers.apple.utils import create_apple_zip  # Corrected import
from bot.logger import LOGGER

async def track_upload(metadata, user):
    """
    Upload a single track
    Args:
        metadata: Track metadata
        user: User details
    """
    try:
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
        os.remove(metadata['filepath'])
    except Exception as e:
        LOGGER.error(f"Track upload failed: {str(e)}")
        raise

async def music_video_upload(metadata, user):
    """
    Upload a music video
    Args:
        metadata: Video metadata
        user: User details
    """
    try:
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
        os.remove(metadata['filepath'])
    except Exception as e:
        LOGGER.error(f"Video upload failed: {str(e)}")
        raise

async def album_upload(metadata, user):
    """
    Upload an album
    Args:
        metadata: Album metadata
        user: User details
    """
    try:
        if Config.ALBUM_ZIP:
            zip_path = await create_apple_zip(
                metadata['folderpath'], 
                user['user_id'],
                metadata
            )
            
            await send_message(
                user,
                zip_path,
                'doc',
                caption=await format_string(
                    "💿 **{album}**\n👤 {artist}\n🎧 {provider}",
                    {
                        'album': metadata['title'],
                        'artist': metadata['artist'],
                        'provider': metadata.get('provider', 'Apple Music')
                    }
                )
            )
            os.remove(zip_path)
        else:
            for track in metadata['tracks']:
                await track_upload(track, user)
                
        shutil.rmtree(metadata['folderpath'])
    except Exception as e:
        LOGGER.error(f"Album upload failed: {str(e)}")
        raise

async def artist_upload(metadata, user):
    """
    Upload artist content
    Args:
        metadata: Artist metadata
        user: User details
    """
    try:
        if Config.ARTIST_ZIP:
            zip_path = await create_apple_zip(
                metadata['folderpath'],
                user['user_id'],
                metadata
            )
            
            await send_message(
                user,
                zip_path,
                'doc',
                caption=await format_string(
                    "🎤 **{artist}**\n🎧 {provider} Discography",
                    {
                        'artist': metadata['title'],
                        'provider': metadata.get('provider', 'Apple Music')
                    }
                )
            )
            os.remove(zip_path)
        else:
            for album in metadata['albums']:
                await album_upload(album, user)
                
        shutil.rmtree(metadata['folderpath'])
    except Exception as e:
        LOGGER.error(f"Artist upload failed: {str(e)}")
        raise

async def playlist_upload(metadata, user):
    """
    Upload a playlist
    Args:
        metadata: Playlist metadata
        user: User details
    """
    try:
        if Config.PLAYLIST_ZIP:
            zip_path = await create_apple_zip(
                metadata['folderpath'],
                user['user_id'],
                metadata
            )
            
            await send_message(
                user,
                zip_path,
                'doc',
                caption=await format_string(
                    "🎵 **{title}**\n👤 Curated by {artist}\n🎧 {provider} Playlist",
                    {
                        'title': metadata['title'],
                        'artist': metadata.get('artist', 'Various Artists'),
                        'provider': metadata.get('provider', 'Apple Music')
                    }
                )
            )
            os.remove(zip_path)
        else:
            for track in metadata['tracks']:
                await track_upload(track, user)
                
        shutil.rmtree(metadata['folderpath'])
    except Exception as e:
        LOGGER.error(f"Playlist upload failed: {str(e)}")
        raise
