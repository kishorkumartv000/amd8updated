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
    build_apple_options,
    verify_apple_dependencies
)


async def run_apple_downloader(url: str, user_id: int, options: list = None, user: dict = None) -> dict:
    """
    Execute Apple Music downloader script with original flags
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
        
        # Validate downloader exists
        if not os.path.exists(Config.DOWNLOADER_PATH):
            raise FileNotFoundError(f"Apple downloader not found at {Config.DOWNLOADER_PATH}")

        # Build command with original flags
        cmd = [
            Config.DOWNLOADER_PATH,
            *([] if not options else options),
            "--output", output_dir,
            url  # URL comes last
        ]

        LOGGER.info(f"Apple Download Command: {' '.join(cmd)}")

        # Execute process
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
    (Preserved original implementation)
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

        # Get final status
        stdout, stderr = await process.communicate()
        return_code = await process.wait()
        
        if return_code != 0:
            error_output = stderr.decode().strip() or "\n".join(stdout_chunks[-5:])
            LOGGER.error(f"Download failed (Code {return_code}): {error_output}")
            return {'success': False, 'error': error_output}
            
        LOGGER.info("Apple Music download completed successfully")
        return {'success': True}

    except Exception as e:
        LOGGER.error(f"Monitoring failed: {str(e)}")
        return {'success': False, 'error': str(e)}


def _parse_progress(line: str) -> int:
    """Extract progress percentage from output line"""
    match = re.search(r'(\d+)%', line)
    return int(match.group(1)) if match else None


async def _update_progress(user: dict, progress: int):
    """Update progress message in Telegram"""
    try:
        if progress % 5 == 0:  # Throttle updates
            await edit_message(
                user['bot_msg'],
                f"🍎 Apple Music Progress: {progress}%"
            )
    except Exception as e:
        LOGGER.debug(f"Progress update error: {str(e)}")


async def handle_apple_download(url: str, user: dict, options: dict = None):
    """
    Main entry point for Apple Music downloads
    Args:
        url: Apple Music URL
        user: User details dictionary
        options: Command-line options
    """
    try:
        # Validate URL format
        if not validate_apple_url(url):
            await edit_message(user['bot_msg'], "Invalid Apple Music URL")
            return

        # Verify system dependencies
        verify_apple_dependencies()

        # Extract content ID for tracking
        content_id = extract_content_id(url)
        LOGGER.debug(f"Apple Content ID: {content_id}")

        # Create user-specific directory
        output_dir = create_apple_directory(user['user_id'])

        # Build download command
        apple_cmd = [
            Config.DOWNLOADER_PATH,
            *build_apple_options(options or {}),
            "--output", output_dir,
            url
        ]

        # Log final command
        LOGGER.info(f"Apple Command: {' '.join(apple_cmd)}")

        # Execute download process
        process = await asyncio.create_subprocess_exec(
            *apple_cmd,
            cwd=output_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Monitor progress
        await _handle_progress(process, user)

        # Final cleanup
        cleanup_apple_files(user['user_id'])
        await edit_message(user['bot_msg'], "✅ Apple Music download completed!")

    except Exception as e:
        LOGGER.error(f"Apple Music Error: {str(e)}")
        await edit_message(user['bot_msg'], f"❌ Apple Music Error: {str(e)}")
        cleanup_apple_files(user['user_id'])


async def start_apple(link: str, user: dict, options: dict = None):
    """Main entry point for Apple Music downloads"""
    try:
        # Validate URL
        if not validate_apple_url(link):
            await edit_message(user['bot_msg'], "Invalid Apple Music URL")
            return

        # Verify dependencies
        verify_apple_dependencies()

        # Create user directory
        output_dir = create_apple_directory(user['user_id'])

        # Build download command
        cmd = [
            Config.DOWNLOADER_PATH,
            *build_apple_options(options or {}),
            "--output", output_dir,
            link
        ]

        LOGGER.info(f"Apple Command: {' '.join(cmd)}")

        # Execute download
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=output_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Monitor progress
        await _handle_progress(process, user)
        
        # Final cleanup
        cleanup_apple_files(user['user_id'])
        await edit_message(user['bot_msg'], "✅ Apple Music download completed!")

    except Exception as e:
        LOGGER.error(f"Apple Music Error: {str(e)}")
        await edit_message(user['bot_msg'], f"❌ Apple Error: {str(e)}")
        cleanup_apple_files(user['user_id'])


async def _handle_progress(process, user: dict):
    """Real-time progress tracking"""
    while True:
        line = await process.stdout.readline()
        if not line:
            break
            
        line_str = line.decode().strip()
        if '%' in line_str:
            progress = int(re.search(r'(\d+)%', line_str).group(1))
            if progress % 5 == 0:
                await edit_message(
                    user['bot_msg'],
                    f"🍎 Progress: {progress}%"
                )

    # Check exit status
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        error = stderr.decode().strip() or "Unknown error"
        raise RuntimeError(f"Downloader failed: {error}")


def build_apple_options(options: dict) -> list:
    """Convert user options to original Apple flags"""
    option_map = {
        # Original flag mappings
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
