import os
import re
import asyncio
from config import Config
from bot.logger import LOGGER
from bot.helpers.message import edit_message
from .utils import create_apple_directory

async def run_apple_downloader(url: str, user_id: int, options: list = None, user: dict = None) -> dict:
    """
    Execute Apple Music downloader script with proper configuration
    Args:
        url: Apple Music URL to download
        user_id: Telegram user ID for directory setup
        options: List of command-line options
        user: User details for progress updates
    Returns:
        dict: {'success': bool, 'error': str (if failed)}
    """
    try:
        # Get user-specific directory
        output_dir = create_apple_directory(user_id)
        
        # Validate downloader binary
        if not os.path.exists(Config.DOWNLOADER_PATH):
            raise FileNotFoundError(f"Apple downloader not found at {Config.DOWNLOADER_PATH}")

        # Build command with proper argument order
        cmd = [
            Config.DOWNLOADER_PATH,
            *([] if not options else options),
            "--save-dir", output_dir,  # Changed from --output to --save-dir
            url
        ]

        LOGGER.info(f"Executing Apple Download Command: {' '.join(cmd)}")

        # Run process in user directory
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
    (Preserved original implementation with enhanced logging)
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
            
            # Progress handling
            if user and 'bot_msg' in user:
                progress = _parse_progress(line_str)
                if progress and progress != last_progress:
                    await _update_progress(user, progress)
                    last_progress = progress

        # Get final process status
        stdout, stderr = await process.communicate()
        return_code = await process.wait()
        
        if return_code != 0:
            error_output = stderr.decode().strip() or "\n".join(stdout_chunks[-5:])
            LOGGER.error(f"Download failed with code {return_code}: {error_output}")
            return {'success': False, 'error': error_output}
            
        LOGGER.info("Apple Music download completed successfully")
        return {'success': True}

    except Exception as e:
        LOGGER.error(f"Download monitoring error: {str(e)}")
        return {'success': False, 'error': str(e)}

def _parse_progress(line: str) -> int:
    """Extract percentage from output line"""
    match = re.search(r'(\d+)%', line)
    return int(match.group(1)) if match else None

async def _update_progress(user: dict, progress: int):
    """Update Telegram progress message"""
    try:
        if progress % 5 == 0:  # Throttle updates
            await edit_message(
                user['bot_msg'],
                f"🍎 Download Progress: {progress}%"
            )
    except Exception as e:
        LOGGER.debug(f"Progress update failed: {str(e)}")

def build_apple_options(options: dict) -> list:
    """Convert user options to valid CLI flags"""
    option_map = {
        'song': '--track',          # Changed from --song to match actual binary
        'atmos': '--spatial',       # Changed from --atmos
        'alac-max': '--alac-quality', 
        'atmos-max': '--atmos-bitrate',
        'mv-max': '--video-quality',
        'select': '--selective',
        'all-album': '--full-album',
        'debug': '--verbose',
        'aac': '--aac-format',
        'aac-type': '--aac-profile',
        'mv-audio-type': '--video-audio'
    }
    
    cmd = []
    for key, value in (options or {}).items():
        if key in option_map:
            if isinstance(value, bool):
                cmd.append(option_map[key])
            else:
                cmd.extend([option_map[key], str(value)])
    return cmd
