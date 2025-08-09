from .apple import AppleMusicCore, start_apple
from .downloader import run_apple_downloader
from .metadata import extract_apple_metadata

__all__ = [
    'AppleMusicCore',
    'start_apple',
    'run_apple_downloader',
    'extract_apple_metadata'
]
