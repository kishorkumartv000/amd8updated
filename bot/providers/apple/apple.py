import os
import logging
import asyncio
from config import Config
from .downloader import run_apple_downloader
from .metadata import extract_apple_metadata
from .utils import (
    create_apple_directory,
    cleanup_apple_files,
    validate_apple_url
)
from .uploader import (
    apple_track_upload,
    apple_album_upload,
    apple_music_video_upload,
    apple_playlist_upload,
    apple_artist_upload
)
from bot.helpers.utils import format_string
from bot.logger import LOGGER

logger = logging.getLogger(__name__)

class AppleMusicCore:
    """Main Apple Music processor handling all operations"""
    def __init__(self):
        self.name = "apple"
        self.supported_types = [
            'album', 'song', 'playlist', 
            'music-video', 'artist'
        ]

    async def process(self, url: str, user: dict, options: dict = None):
        """Main processing pipeline for Apple Music content"""
        try:
            if not validate_apple_url(url):
                raise ValueError("Invalid Apple Music URL format")

            user_dir = create_apple_directory(user['user_id'])
            
            download_result = await run_apple_downloader(
                url, 
                user_dir, 
                options, 
                user
            )
            
            if not download_result['success']:
                raise RuntimeError(download_result['error'])

            content_type, processed_data = await self._process_content(user_dir, url)
            await self._handle_upload(content_type, processed_data, user)
            cleanup_apple_files(user['user_id'])
            await self._send_completion_message(user)

        except Exception as e:
            logger.error(f"Apple Music processing failed: {str(e)}", exc_info=True)
            cleanup_apple_files(user['user_id'])
            await self._handle_error(user, str(e))
            raise

    async def _process_content(self, directory: str, url: str):
        """Process downloaded files and extract metadata"""
        items = []
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if any(file_path.endswith(ext) for ext in ('.m4a', '.flac', '.mp4', '.mov')):
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
        """Identify content type from URL and files"""
        if 'music-video' in url:
            return 'video'
        if 'playlist' in url:
            return 'playlist'
        if 'artist' in url:
            return 'artist'
        return 'album' if len(items) > 1 else 'track'

    async def _handle_upload(self, content_type: str, data: dict, user: dict):
        """Route to Apple-specific upload handler"""
        upload_handlers = {
            'track': apple_track_upload,
            'video': apple_music_video_upload,
            'album': apple_album_upload,
            'playlist': apple_playlist_upload,
            'artist': apple_artist_upload
        }
        
        if content_type not in upload_handlers:
            raise ValueError(f"Unsupported content type: {content_type}")
        
        await upload_handlers[content_type](data, user)

    async def _send_completion_message(self, user: dict):
        """Send final success message"""
        await user['bot_msg'].edit_text(
            format_string(
                "✅ Apple Music download completed!\n"
                "Format: {format}\n"
                "Quality: {quality}",
                {
                    'format': Config.APPLE_DEFAULT_FORMAT.upper(),
                    'quality': Config.APPLE_ALAC_QUALITY if Config.APPLE_DEFAULT_FORMAT == 'alac' 
                             else Config.APPLE_ATMOS_QUALITY
                }
            )
        )

    async def _handle_error(self, user: dict, error: str):
        """Handle error messaging"""
        await user['bot_msg'].edit_text(
            f"❌ Apple Music Error:\n{error}"
        )

async def start_apple(link: str, user: dict, options: dict = None):
    """Public entry point for Apple Music downloads"""
    processor = AppleMusicCore()
    await processor.process(link, user, options)
