import os
import re
import logging
import asyncio
from config import Config
from bot.logger import LOGGER
from bot.helpers.message import edit_message
from .downloader import run_apple_downloader
from .metadata import extract_apple_metadata
from .utils import (
    validate_apple_url,
    extract_content_id,
    create_apple_directory,
    cleanup_apple_files,
    format_apple_quality
)

logger = logging.getLogger(__name__)

class AppleMusicCore:
    """Main processor for Apple Music content"""
    
    def __init__(self):
        self.name = "apple"
        self.supported_types = [
            'album', 'song', 'playlist',
            'music-video', 'artist'
        ]

    async def process(self, url: str, user: dict, options: dict = None):
        """Main processing pipeline for Apple Music content"""
        try:
            # Validate Apple Music URL
            if not validate_apple_url(url):
                await self._handle_error(user, "Invalid Apple Music URL")
                return

            # Create user-specific directory
            user_dir = create_apple_directory(user['user_id'])
            LOGGER.info(f"Created Apple directory: {user_dir}")

            # Execute downloader
            download_result = await run_apple_downloader(
                url, 
                user_dir, 
                options, 
                user
            )
            
            if not download_result['success']:
                raise RuntimeError(download_result['error'])

            # Process downloaded files
            content_type, processed_data = await self._process_content(user_dir, url)
            
            # Handle upload based on content type
            await self._handle_upload(content_type, processed_data, user)

            # Final cleanup
            cleanup_apple_files(user['user_id'])
            await self._send_completion_message(user)

        except Exception as e:
            logger.error(f"Apple Music processing failed: {str(e)}", exc_info=True)
            cleanup_apple_files(user['user_id'])
            await self._handle_error(user, str(e))

    async def _process_content(self, directory: str, url: str):
        """Process downloaded files and extract metadata"""
        items = []
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if self._is_media_file(file_path):
                    try:
                        metadata = extract_apple_metadata(file_path)
                        metadata.update({
                            'filepath': file_path,
                            'provider': self.name
                        })
                        items.append(metadata)
                    except Exception as e:
                        LOGGER.error(f"Metadata extraction failed: {str(e)}")

        if not items:
            raise ValueError("No valid media files found")

        return self._determine_content_type(url, items), {
            'items': items,
            'folderpath': directory,
            'title': items[0].get('album', items[0]['title']),
            'artist': items[0]['artist']
        }

    def _determine_content_type(self, url: str, items: list) -> str:
        """Identify content type from URL and file structure"""
        if 'music-video' in url:
            return 'video'
        if 'playlist' in url:
            return 'playlist'
        if 'artist' in url:
            return 'artist'
        return 'album' if len(items) > 1 else 'track'

    def _is_media_file(self, path: str) -> bool:
        """Check if file is supported media type"""
        return any(path.endswith(ext) for ext in ('.m4a', '.flac', '.mp4', '.mov'))

    async def _handle_upload(self, content_type: str, data: dict, user: dict):
        """Route to appropriate upload handler"""
        handlers = {
            'track': self._upload_track,
            'video': self._upload_video,
            'album': self._upload_album,
            'playlist': self._upload_playlist,
            'artist': self._upload_artist
        }
        
        if content_type not in handlers:
            raise ValueError(f"Unsupported content type: {content_type}")
        
        await handlers[content_type](data, user)

    async def _upload_track(self, data: dict, user: dict):
        """Upload single track"""
        from bot.helpers.uploader import track_upload
        await track_upload(data['items'][0], user)

    async def _upload_video(self, data: dict, user: dict):
        """Upload music video"""
        from bot.helpers.uploader import music_video_upload
        await music_video_upload(data['items'][0], user)

    async def _upload_album(self, data: dict, user: dict):
        """Upload album"""
        from bot.helpers.uploader import album_upload
        await album_upload(data, user)

    async def _upload_playlist(self, data: dict, user: dict):
        """Upload playlist"""
        from bot.helpers.uploader import playlist_upload
        await playlist_upload(data, user)

    async def _upload_artist(self, data: dict, user: dict):
        """Upload artist content"""
        from bot.helpers.uploader import artist_upload
        await artist_upload(data, user)

    async def _send_completion_message(self, user: dict):
        """Send final success message"""
        quality = format_apple_quality(Config.APPLE_DEFAULT_FORMAT)
        await edit_message(
            user['bot_msg'],
            f"✅ Apple Music Download Complete!\n"
            f"Format: {Config.APPLE_DEFAULT_FORMAT.upper()}\n"
            f"Quality: {quality}"
        )

    async def _handle_error(self, user: dict, error: str):
        """Handle error messaging"""
        await edit_message(
            user['bot_msg'],
            f"❌ Apple Music Error:\n{error}"
        )

async def start_apple(link: str, user: dict, options: dict = None):
    """Entry point for Apple Music downloads"""
    processor = AppleMusicCore()
    await processor.process(link, user, options)
