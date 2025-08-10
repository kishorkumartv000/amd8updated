from .apple import AppleMusicCore, start_apple
from .apple.downloader import handle_apple_download
from .downloader import run_apple_downloader
from .metadata import extract_apple_metadata
from .uploader import (  # Added this line
    apple_track_upload,
    apple_album_upload,
    apple_music_video_upload,
    apple_playlist_upload,
    apple_artist_upload,
    apple_rclone_upload
)

__all__ = [
    'AppleMusicCore',
    'start_apple',
    'handle_apple_download',
    'run_apple_downloader',
    'extract_apple_metadata',
    # Add these new exports
    'apple_track_upload',
    'apple_album_upload',
    'apple_music_video_upload',
    'apple_playlist_upload',
    'apple_artist_upload',
    'apple_rclone_upload'
]
