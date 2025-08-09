import os
import shutil
import zipfile
import asyncio
import re
from config import Config
from mutagen import File
from mutagen.mp4 import MP4
from bot.helpers.utils import format_string, send_message, edit_message
from .utils import create_apple_zip
from bot.logger import LOGGER
from bot.settings import bot_set

async def apple_track_upload(metadata, user):
    """Apple Music-specific track upload"""
    base_path = os.path.join(Config.LOCAL_STORAGE, "Apple Music")
    
    if Config.UPLOAD_MODE == 'Telegram':
        await send_message(
            user,
            metadata['filepath'],
            'audio',
            caption=await format_string(
                "🎵 **{title}**\n👤 {artist}\n🎧 Apple Music",
                {'title': metadata['title'], 'artist': metadata['artist']}
            ),
            meta={
                'duration': metadata['duration'],
                'artist': metadata['artist'],
                'title': metadata['title'],
                'thumbnail': metadata['thumbnail']
            }
        )
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await apple_rclone_upload(user, metadata['filepath'], base_path)
        text = await format_string(
            "🎵 **{title}**\n👤 {artist}\n🎧 Apple Music\n🔗 [Direct Link]({r_link})",
            {'title': metadata['title'], 'artist': metadata['artist'], 'r_link': rclone_link}
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"
        await send_message(user, text)
    
    os.remove(metadata['filepath'])
    if metadata.get('thumbnail'):
        os.remove(metadata['thumbnail'])

async def apple_music_video_upload(metadata, user):
    """Apple Music-specific video upload"""
    base_path = os.path.join(Config.LOCAL_STORAGE, "Apple Music")
    
    if Config.UPLOAD_MODE == 'Telegram':
        await send_message(
            user,
            metadata['filepath'],
            'video',
            caption=await format_string(
                "🎬 **{title}**\n👤 {artist}\n🎧 Apple Music Video",
                {'title': metadata['title'], 'artist': metadata['artist']}
            ),
            meta=metadata
        )
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await apple_rclone_upload(user, metadata['filepath'], base_path)
        text = await format_string(
            "🎬 **{title}**\n👤 {artist}\n🎧 Apple Music Video\n🔗 [Direct Link]({r_link})",
            {'title': metadata['title'], 'artist': metadata['artist'], 'r_link': rclone_link}
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"
        await send_message(user, text)
    
    os.remove(metadata['filepath'])
    if metadata.get('thumbnail'):
        os.remove(metadata['thumbnail'])

async def apple_album_upload(metadata, user):
    """Apple Music-specific album upload"""
    base_path = os.path.join(Config.LOCAL_STORAGE, "Apple Music")
    
    if Config.UPLOAD_MODE == 'Telegram':
        if Config.ALBUM_ZIP:
            zip_path = await create_apple_zip(metadata['folderpath'], user['user_id'], metadata)
            await send_message(
                user,
                zip_path,
                'doc',
                caption=await format_string(
                    "💿 **{album}**\n👤 {artist}\n🎧 Apple Music",
                    {'album': metadata['title'], 'artist': metadata['artist']}
                )
            )
            os.remove(zip_path)
        else:
            for track in metadata['tracks']:
                await apple_track_upload(track, user)
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await apple_rclone_upload(user, metadata['folderpath'], base_path)
        text = await format_string(
            "💿 **{album}**\n👤 {artist}\n🎧 Apple Music\n🔗 [Direct Link]({r_link})",
            {'album': metadata['title'], 'artist': metadata['artist'], 'r_link': rclone_link}
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"
        await send_message(user, text)
    
    shutil.rmtree(metadata['folderpath'])

async def apple_artist_upload(metadata, user):
    """Apple Music-specific artist upload"""
    base_path = os.path.join(Config.LOCAL_STORAGE, "Apple Music")
    
    if Config.UPLOAD_MODE == 'Telegram':
        if Config.ARTIST_ZIP:
            zip_path = await create_apple_zip(metadata['folderpath'], user['user_id'], metadata)
            await send_message(
                user,
                zip_path,
                'doc',
                caption=await format_string(
                    "🎤 **{artist}**\n🎧 Apple Music Discography",
                    {'artist': metadata['title']}
                )
            )
            os.remove(zip_path)
        else:
            for album in metadata['albums']:
                await apple_album_upload(album, user)
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await apple_rclone_upload(user, metadata['folderpath'], base_path)
        text = await format_string(
            "🎤 **{artist}**\n🎧 Apple Music Discography\n🔗 [Direct Link]({r_link})",
            {'artist': metadata['title'], 'r_link': rclone_link}
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"
        await send_message(user, text)
    
    shutil.rmtree(metadata['folderpath'])

async def apple_playlist_upload(metadata, user):
    """Apple Music-specific playlist upload"""
    base_path = os.path.join(Config.LOCAL_STORAGE, "Apple Music")
    
    if Config.UPLOAD_MODE == 'Telegram':
        if Config.PLAYLIST_ZIP:
            zip_path = await create_apple_zip(metadata['folderpath'], user['user_id'], metadata)
            await send_message(
                user,
                zip_path,
                'doc',
                caption=await format_string(
                    "🎵 **{title}**\n👤 Curated by {artist}\n🎧 Apple Music Playlist",
                    {'title': metadata['title'], 'artist': metadata.get('artist', 'Various Artists')}
                )
            )
            os.remove(zip_path)
        else:
            for track in metadata['tracks']:
                await apple_track_upload(track, user)
    elif Config.UPLOAD_MODE == 'Rclone':
        rclone_link, index_link = await apple_rclone_upload(user, metadata['folderpath'], base_path)
        text = await format_string(
            "🎵 **{title}**\n👤 Curated by {artist}\n🎧 Apple Music Playlist\n🔗 [Direct Link]({r_link})",
            {'title': metadata['title'], 'artist': metadata.get('artist', 'Various Artists'), 'r_link': rclone_link}
        )
        if index_link:
            text += f"\n📁 [Index Link]({index_link})"
        await send_message(user, text)
    
    shutil.rmtree(metadata['folderpath'])

async def apple_rclone_upload(user, path, base_path):
    """Apple Music-specific Rclone upload"""
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
            LOGGER.error(f"Apple Rclone Error: {stderr.decode().strip()}")
    
    if bot_set.link_options in ['Index', 'Both'] and Config.INDEX_LINK:
        index_link = f"{Config.INDEX_LINK}/{relative_path}"
    
    return rclone_link, index_link
