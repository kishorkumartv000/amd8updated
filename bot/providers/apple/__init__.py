from .apple import AppleMusicCore
from .apple.downloader import start_apple
from .downloader import run_apple_downloader, handle_apple_download
from .metadata import extract_apple_metadata
from .uploader import (
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
    'run_apple_downloader',
    'handle_apple_download',
    'extract_apple_metadata',
    'apple_track_upload',
    'apple_album_upload',
    'apple_music_video_upload',
    'apple_playlist_upload',
    'apple_artist_upload',
    'apple_rclone_upload'
]
