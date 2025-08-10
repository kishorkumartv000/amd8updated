import os
import re
import asyncio
from config import Config
from bot.logger import LOGGER
from bot.helpers.message import edit_message
from .utils import (
    validate_apple_url,
    extract_content_id,
    create_apple_directory,
    cleanup_apple_files,
    verify_apple_dependencies
)

# Global config file next to the downloader executable
APPLE_CONFIG_PATH = os.path.join(
    os.path.dirname(Config.DOWNLOADER_PATH),
    "config.yaml"
)

async def run_apple_downloader(url: str, user_id: int, options: list = None, user: dict = None) -> dict:
    """
    Execute downloader using single global config
    Args:
        url: Apple Music URL
        user_id: Telegram user ID (for directory creation)
        options: Command-line options
        user: User details for progress updates
    Returns:
        dict: Success status and error message
    """
    try:
        # Create user-specific output directory
        output_dir = create_apple_directory(user_id)
        
        # Verify downloader exists
        if not os.path.exists(Config.DOWNLOADER_PATH):
            raise FileNotFoundError("Apple downloader not found at configured path")

        # Build command with global config
        cmd = [
            Config.DOWNLOADER_PATH,
            *([] if not options else options),
            "--output", output_dir,
            url
        ]

        LOGGER.info(f"Executing Apple Download: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=os.path.dirname(Config.DOWNLOADER_PATH),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "APPLE_CONFIG": APPLE_CONFIG_PATH}
        )

        return await _monitor_download_process(process, user, output_dir)
    except Exception as e:
        LOGGER.error(f"Downloader setup failed: {str(e)}")
        return {'success': False, 'error': str(e)}

async def _monitor_download_process(process, user: dict, output_dir: str) -> dict:
    """Monitor download process with single config"""
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
            
            # Check for critical errors
            if any(re.search(pattern, line_str) for pattern in error_patterns):
                raise RuntimeError(line_str)
            
            # Update progress if available
            if user and 'bot_msg' in user:
                if (progress := _parse_progress(line_str)) is not None:
                    await _update_progress(user, progress)

        # Verify successful completion
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            error = stderr.decode().strip() or "Unknown error occurred"
            raise RuntimeError(error)
            
        return {'success': True}
    except Exception as e:
        LOGGER.error(f"Download failed: {str(e)}")
        cleanup_apple_files(output_dir)
        return {'success': False, 'error': str(e)}
    finally:
        if user and 'bot_msg' in user:
            await edit_message(user['bot_msg'], "Cleaning up temporary files...")

def _parse_progress(line: str) -> int:
    """Extract progress percentage from output"""
    match = re.search(r'(\d+)%', line)
    return int(match.group(1)) if match else None

async def _update_progress(user: dict, progress: int):
    """Update progress message with throttling"""
    try:
        if progress % 5 == 0:  # Update every 5%
            await edit_message(
                user['bot_msg'],
                f"🍎 Download Progress: {progress}%\n"
                f"Format: {Config.APPLE_DEFAULT_FORMAT.upper()}"
            )
    except Exception as e:
        LOGGER.debug(f"Progress update skipped: {str(e)}")

async def handle_apple_download(url: str, user: dict, options: dict = None):
    """Main download handler"""
    try:
        if not validate_apple_url(url):
            await edit_message(user['bot_msg'], "❌ Invalid Apple Music URL")
            return

        verify_apple_dependencies()
        
        result = await run_apple_downloader(url, user['user_id'], options, user)
        
        if result['success']:
            await edit_message(user['bot_msg'], "✅ Download completed successfully!")
        else:
            await edit_message(user['bot_msg'], f"❌ Failed: {result['error']}")
    except Exception as e:
        LOGGER.error(f"Critical error: {str(e)}")
        await edit_message(user['bot_msg'], f"⚠️ System error: {str(e)}")
    finally:
        cleanup_apple_files(user['user_id'])

async def start_apple(link: str, user: dict, options: dict = None):
    """Command entry point"""
    try:
        await edit_message(user['bot_msg'], "Starting Apple Music download...")
        result = await run_apple_downloader(link, user['user_id'], options, user)
        
        if result['success']:
            await edit_message(user['bot_msg'], "✅ Successfully downloaded!")
        else:
            await edit_message(user['bot_msg'], f"❌ Failed: {result['error']}")
    except Exception as e:
        LOGGER.error(f"Start failed: {str(e)}")
        await edit_message(user['bot_msg'], f"⚠️ Critical error: {str(e)}")
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
