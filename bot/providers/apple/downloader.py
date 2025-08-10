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

async def _handle_progress(process, user: dict):
    """
    Real-time progress monitoring
    Args:
        process: Running subprocess
        user: User details
    """
    while True:
        line = await process.stdout.readline()
        if not line:
            break
            
        line_str = line.decode().strip()
        if '%' in line_str:
            progress = int(re.search(r'(\d+)%', line_str).group(1))
            if progress % 5 == 0:  # Throttle updates
                await edit_message(
                    user['bot_msg'],
                    f"🍎 Download Progress: {progress}%"
                )

    # Check final status
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        error = stderr.decode().strip() or "Unknown error"
        raise RuntimeError(f"Downloader failed: {error}")
