import os
import re
import shutil
import zipfile
import logging
import subprocess
from pathlib import Path
from config import Config
from bot.logger import LOGGER

logger = logging.getLogger(__name__)

def validate_apple_url(url: str) -> bool:
    """
    Validate Apple Music URL format
    Args:
        url: URL to validate
    Returns:
        bool: True if valid Apple Music content URL
    """
    patterns = [
        r"https://music\.apple\.com/.+/(album|song|playlist|music-video|artist)/.+",
        r"https://music\.apple\.com/.+/album/.+",
        r"https://music\.apple\.com/.+/playlist/.+"
    ]
    return any(re.match(pattern, url) for pattern in patterns)

def extract_content_id(url: str) -> str:
    """
    Extract Apple Music content ID from URL
    Args:
        url: Apple Music URL
    Returns:
        str: Content ID or 'unknown' if not found
    """
    match = re.search(r'/(album|song|playlist|music-video|artist)/[^/]+/(\d+)', url)
    return match.group(2) if match else "unknown"

def create_apple_directory(user_id: int) -> str:
    """
    Create Apple-specific directory structure
    Args:
        user_id: Telegram user ID
    Returns:
        str: Path to created directory
    """
    try:
        base_dir = os.path.join(
            Config.LOCAL_STORAGE,
            "Apple Music",
            str(user_id)
        )
        Path(base_dir).mkdir(parents=True, exist_ok=True)
        LOGGER.debug(f"Created Apple directory: {base_dir}")
        return base_dir
    except Exception as e:
        logger.error(f"Directory creation failed: {str(e)}")
        raise

def cleanup_apple_files(user_id: int):
    """
    Cleanup Apple Music temporary files
    Args:
        user_id: Telegram user ID
    """
    try:
        apple_dir = os.path.join(
            Config.LOCAL_STORAGE,
            "Apple Music",
            str(user_id)
        )
        if os.path.exists(apple_dir):
            shutil.rmtree(apple_dir, ignore_errors=True)
            LOGGER.debug(f"Cleaned Apple directory: {apple_dir}")
    except Exception as e:
        logger.error(f"Apple cleanup failed: {str(e)}")

def build_apple_options(options: dict) -> list:
    """
    Convert options dict to Apple downloader CLI arguments
    Args:
        options: User-provided options
    Returns:
        list: CLI arguments for downloader
    """
    cmd = []
    option_map = {
        'aac': '--aac',
        'aac-type': '--aac-type',
        'alac-max': '--alac-max',
        'all-album': '--all-album',
        'atmos': '--atmos',
        'atmos-max': '--atmos-max',
        'debug': '--debug',
        'mv-audio-type': '--mv-audio-type',
        'mv-max': '--mv-max',
        'select': '--select',
        'song': '--song'
    }
    
    for key, value in (options or {}).items():
        if key in option_map:
            if isinstance(value, bool):
                cmd.append(option_map[key])
            else:
                cmd.extend([option_map[key], str(value)])
    return cmd

def verify_apple_dependencies():
    """
    Verify required dependencies for Apple Music downloads
    Raises:
        RuntimeError: If any dependency is missing
    """
    required_tools = {
        'rclone': 'rclone version',
        'N_m3u8DL-RE': 'N_m3u8DL-RE --version',
        'MP4Box': 'MP4Box -version'
    }
    
    missing = []
    for tool, test_cmd in required_tools.items():
        try:
            subprocess.run(test_cmd.split(), 
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            missing.append(tool)
    
    if missing:
        raise RuntimeError(f"Missing required tools: {', '.join(missing)}")

def format_apple_quality(format_type: str) -> str:
    """
    Format quality information for user display
    Args:
        format_type: 'alac' or 'atmos'
    Returns:
        str: Human-readable quality info
    """
    qualities = {
        'alac': {
            192000: 'ALAC 16-bit/44.1kHz',
            256000: 'ALAC 24-bit/48kHz',
            320000: 'ALAC 24-bit/96kHz'
        },
        'atmos': {
            2768: 'Dolby Atmos 768kbps',
            3072: 'Dolby Atmos 1536kbps',
            3456: 'Dolby Atmos 3456kbps'
        }
    }
    quality = getattr(Config, f'APPLE_{format_type.upper()}_QUALITY')
    return qualities[format_type].get(quality, 'Unknown Quality')

def apple_supported_formats() -> dict:
    """
    Get supported formats and qualities
    Returns:
        dict: Format information for settings
    """
    return {
        'alac': ['192000', '256000', '320000'],
        'atmos': ['2768', '3072', '3456']
    }

def create_apple_zip(folder_path: str, user_id: int, metadata: dict) -> str:
    """
    Create zip file for Apple Music content
    Args:
        folder_path: Path to folder to zip
        user_id: Telegram user ID
        metadata: File metadata
    Returns:
        str: Path to created zip file
    """
    try:
        zip_name = f"{metadata['title']} - {metadata['artist']}.zip"
        zip_dir = os.path.join(Config.LOCAL_STORAGE, "Zips", str(user_id))
        zip_path = os.path.join(zip_dir, zip_name)
        
        os.makedirs(zip_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arcname)
        
        LOGGER.info(f"Created Apple zip archive: {zip_path}")
        return zip_path
    except Exception as e:
        logger.error(f"Zip creation failed: {str(e)}")
        raise
