import os
import re
import asyncio
from config import Config
from bot.logger import LOGGER
from bot.helpers.message import edit_message
from .utils import create_apple_directory  # Import from utils

async def run_apple_downloader(url: str, user_id: int, options: list = None, user: dict = None) -> dict:
    """
    Execute Apple Music downloader script using user-specific config
    Args:
        url: Apple Music URL to download
        user_id: Telegram user ID for directory setup
        options: List of command-line options
        user: User details for progress updates
    Returns:
        dict: {'success': bool, 'error': str (if failed)}
    """
    try:
        # Get/Create user directory with config
        output_dir = create_apple_directory(user_id)
        
        if not os.path.exists(Config.DOWNLOADER_PATH):
            raise FileNotFoundError(f"Apple downloader not found at {Config.DOWNLOADER_PATH}")

        # Build command with proper structure
        cmd = [
            Config.DOWNLOADER_PATH,
            *([] if not options else options),
            "--output", output_dir,
            url
        ]

        LOGGER.info(f"Apple Download Command: {' '.join(cmd)}")

        # Run in user directory containing config.yaml
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=output_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        return await _monitor_download_process(process, user)

    except Exception as e:
        LOGGER.error(f"Apple Downloader Setup Failed: {str(e)}")
        return {'success': False, 'error': str(e)}

async def _monitor_download_process(process, user: dict) -> dict:
    """
    Monitor download process and handle output
    (Original implementation preserved)
    """
    stdout_chunks = []
    last_progress = 0
    
    try:
        while True:
            line = await process.stdout.readline()
            if not line:
                break
                
            line_str = line.decode().strip()
            stdout_chunks.append(line_str)
            
            if user and 'bot_msg' in user:
                progress = _parse_progress(line_str)
                if progress and progress != last_progress:
                    await _update_progress(user, progress)
                    last_progress = progress

        stdout, stderr = await process.communicate()
        return_code = process.returncode
        
        if return_code != 0:
            error_output = stderr.decode().strip() or "\n".join(stdout_chunks[-5:])
            LOGGER.error(f"Apple Download Failed (Code {return_code}): {error_output}")
            return {'success': False, 'error': error_output}
            
        LOGGER.info("Apple Music download completed successfully")
        return {'success': True}

    except Exception as e:
        LOGGER.error(f"Download monitoring failed: {str(e)}")
        return {'success': False, 'error': str(e)}

def _parse_progress(line: str) -> int:
    """Extract progress percentage from output line"""
    match = re.search(r'(\d+)%', line)
    return int(match.group(1)) if match else None

async def _update_progress(user: dict, progress: int):
    """Update progress message in Telegram"""
    try:
        if progress % 5 == 0:
            await edit_message(
                user['bot_msg'],
                f"🍎 Apple Music Download Progress: {progress}%"
            )
    except Exception as e:
        LOGGER.debug(f"Progress update failed: {str(e)}")

def build_apple_options(options: dict) -> list:
    """Convert options dict to CLI arguments (Full mapping)"""
    option_map = {
        'song': '--song',
        'atmos': '--atmos',
        'alac-max': '--alac-max',
        'atmos-max': '--atmos-max',
        'mv-max': '--mv-max',
        'select': '--select',
        'all-album': '--all-album',
        'debug': '--debug',
        'aac': '--aac',
        'aac-type': '--aac-type',
        'mv-audio-type': '--mv-audio-type'
    }
    
    cmd = []
    for key, value in (options or {}).items():
        if key in option_map:
            if isinstance(value, bool):
                cmd.append(option_map[key])
            else:
                cmd.extend([option_map[key], str(value)])
    return cmd
