import os
import re
import asyncio
from config import Config
from bot.logger import LOGGER
from bot.helpers.message import edit_message
from .utils import (
    validate_apple_url,
    extract_content_id,
    verify_apple_dependencies,
    cleanup_apple_files
)

# Global config path (set in config.yaml)
APPLE_CONFIG_PATH = os.path.join(
    os.path.dirname(Config.DOWNLOADER_PATH),
    "config.yaml"
)

async def run_apple_downloader(url: str, user_id: int, options: list = None, user: dict = None) -> dict:
    """
    Execute downloader using global config.yaml paths
    Removed --output flag dependency
    """
    try:
        # Verify dependencies and config
        verify_apple_dependencies()
        if not os.path.exists(APPLE_CONFIG_PATH):
            raise FileNotFoundError(f"Apple config missing at {APPLE_CONFIG_PATH}")

        # Build base command
        cmd = [
            Config.DOWNLOADER_PATH,
            *([] if not options else options),
            url
        ]

        LOGGER.info(f"Apple Command: {' '.join(cmd)}")

        # Execute with global config
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=os.path.dirname(Config.DOWNLOADER_PATH),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "APPLE_CONFIG": APPLE_CONFIG_PATH}
        )

        return await _monitor_download_process(process, user)
    except Exception as e:
        LOGGER.error(f"Setup Failed: {str(e)}")
        return {'success': False, 'error': str(e)}

async def _monitor_download_process(process, user: dict) -> dict:
    """Monitor process using config.yaml paths"""
    error_patterns = [
        r"Separator is not found",
        r"DRM protected",
        r"Invalid media token",
        r"Storefront mismatch"
    ]
    
    try:
        while True:
            line = await process.stdout.readline()
            if not line:
                break
                
            line_str = line.decode().strip()
            
            # Error detection
            if any(re.search(pattern, line_str) for pattern in error_patterns):
                raise RuntimeError(line_str)
            
            # Progress updates
            if user and (progress := _parse_progress(line_str)):
                await _update_progress(user, progress)

        # Verify completion
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            error = stderr.decode().strip() or "Unknown error"
            raise RuntimeError(error)
            
        return {'success': True}
    except Exception as e:
        LOGGER.error(f"Download Failed: {str(e)}")
        return {'success': False, 'error': str(e)}

def _parse_progress(line: str) -> int:
    """Extract percentage from output"""
    match = re.search(r'(\d+)%', line)
    return int(match.group(1)) if match else None

async def _update_progress(user: dict, progress: int):
    """Throttled progress updates"""
    try:
        if progress % 5 == 0:
            await edit_message(
                user['bot_msg'],
                f"🍎 Apple Music Progress: {progress}%\n"
                f"Format: {Config.APPLE_DEFAULT_FORMAT.upper()}"
            )
    except Exception as e:
        LOGGER.debug(f"Progress update skipped: {str(e)}")

async def handle_apple_download(url: str, user: dict, options: dict = None):
    """Main handler using config.yaml paths"""
    try:
        if not validate_apple_url(url):
            await edit_message(user['bot_msg'], "❌ Invalid URL")
            return

        result = await run_apple_downloader(url, user['user_id'], options, user)
        
        if result['success']:
            await edit_message(user['bot_msg'], "✅ Download completed!")
        else:
            await edit_message(user['bot_msg'], f"❌ Failed: {result['error']}")
    except Exception as e:
        LOGGER.error(f"Critical Error: {str(e)}")
        await edit_message(user['bot_msg'], f"⚠️ Error: {str(e)}")
    finally:
        cleanup_apple_files(user['user_id'])

async def start_apple(link: str, user: dict, options: dict = None):
    """Entry point with global config"""
    try:
        await edit_message(user['bot_msg'], "Starting Apple Music download...")
        result = await run_apple_downloader(link, user['user_id'], options, user)
        
        if result['success']:
            await edit_message(user['bot_msg'], "✅ Success!")
        else:
            await edit_message(user['bot_msg'], f"❌ Failed: {result['error']}")
    except Exception as e:
        LOGGER.error(f"Start Failed: {str(e)}")
        await edit_message(user['bot_msg'], f"⚠️ Critical Error: {str(e)}")
    finally:
        cleanup_apple_files(user['user_id'])

def build_apple_options(options: dict) -> list:
    """Original option mapping preserved"""
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
    
    cmd = []
    for key, value in (options or {}).items():
        if key in option_map:
            if isinstance(value, bool):
                cmd.append(option_map[key])
            else:
                cmd.extend([option_map[key], str(value)])
    return cmd
