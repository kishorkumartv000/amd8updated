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
    verify_apple_dependencies,
    generate_apple_config
)


async def run_apple_downloader(url: str, user_id: int, options: list = None, user: dict = None) -> dict:
    """
    Execute Apple Music downloader script with proper config.yaml usage
    Preserves all original options and functionality
    """
    try:
        # Get/Create user directory with config
        output_dir = create_apple_directory(user_id)
        generate_apple_config(output_dir, user_id)  # Fixed 2-argument call

        # Build command with original flags
        cmd = [
            Config.DOWNLOADER_PATH,
            *([] if not options else options),
            url
        ]

        LOGGER.info(f"Apple Download Command: {' '.join(cmd)}")

        # Execute process with config.yaml environment
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=output_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "APPLE_CONFIG": os.path.join(output_dir, "config.yaml")}
        )

        return await _monitor_download_process(process, user, output_dir)
    except Exception as e:
        LOGGER.error(f"Apple Downloader Setup Failed: {str(e)}")
        return {'success': False, 'error': str(e)}


async def _monitor_download_process(process, user: dict, output_dir: str) -> dict:
    """
    Full original monitoring implementation with enhanced error detection
    """
    error_patterns = [
        r"Separator is not found",
        r"DRM protected",
        r"Invalid media token",
        r"Storefront mismatch",
        r"HTTP 403"
    ]
    
    stdout_chunks = []
    last_progress = 0
    
    try:
        while True:
            line = await process.stdout.readline()
            if not line:
                break
                
            line_str = line.decode().strip()
            stdout_chunks.append(line_str)
            
            # Check for critical errors
            if any(re.search(pattern, line_str) for pattern in error_patterns):
                raise RuntimeError(line_str)
            
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
        cleanup_apple_files(user['user_id'] if user else None)
        return {'success': False, 'error': str(e)}


def _parse_progress(line: str) -> int:
    """Original progress percentage parsing"""
    match = re.search(r'(\d+)%', line)
    return int(match.group(1)) if match else None


async def _update_progress(user: dict, progress: int):
    """Original progress update implementation"""
    try:
        if progress % 5 == 0:  # Throttle updates
            await edit_message(
                user['bot_msg'],
                f"🍎 Apple Music Progress: {progress}%\n"
                f"Format: {Config.APPLE_DEFAULT_FORMAT.upper()}"
            )
    except Exception as e:
        LOGGER.debug(f"Progress update error: {str(e)}")


async def handle_apple_download(url: str, user: dict, options: dict = None):
    """
    Full original handler with all features preserved
    """
    try:
        if not validate_apple_url(url):
            await edit_message(user['bot_msg'], "Invalid Apple Music URL")
            return

        verify_apple_dependencies()
        content_id = extract_content_id(url)
        LOGGER.debug(f"Apple Content ID: {content_id}")

        result = await run_apple_downloader(url, user['user_id'], options, user)
        
        if result['success']:
            await edit_message(user['bot_msg'], "✅ Apple Music download completed!")
        else:
            await edit_message(user['bot_msg'], f"❌ Failed: {result['error']}")

    except Exception as e:
        LOGGER.error(f"Apple Music Error: {str(e)}")
        await edit_message(user['bot_msg'], f"❌ Error: {str(e)}")
    finally:
        cleanup_apple_files(user['user_id'])


async def start_apple(link: str, user: dict, options: dict = None):
    """Complete original entry point implementation"""
    try:
        if not validate_apple_url(link):
            await edit_message(user['bot_msg'], "Invalid Apple Music URL")
            return

        verify_apple_dependencies()
        result = await run_apple_downloader(link, user['user_id'], options, user)
        
        if result['success']:
            await edit_message(user['bot_msg'], "✅ Download completed!")
        else:
            await edit_message(user['bot_msg'], f"❌ Failed: {result['error']}")

    except Exception as e:
        LOGGER.error(f"Apple Music Error: {str(e)}")
        await edit_message(user['bot_msg'], f"❌ Critical Error: {str(e)}")
    finally:
        cleanup_apple_files(user['user_id'])


async def _handle_progress(process, user: dict):
    """Original progress tracking implementation"""
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
    """Complete original option mapping with all flags"""
    option_map = {
        # Audio format options
        'aac': '--aac',
        'aac-type': '--aac-type',
        'alac-max': '--alac-max',
        'atmos': '--atmos',
        'atmos-max': '--atmos-max',
        
        # Content selection
        'all-album': '--all-album',
        'select': '--select',
        'song': '--song',
        
        # Video options
        'mv-audio-type': '--mv-audio-type',
        'mv-max': '--mv-max',
        
        # Debugging
        'debug': '--debug',
        
        # Metadata
        'album-folder-format': '--album-folder-format',
        'playlist-folder-format': '--playlist-folder-format',
        'song-file-format': '--song-file-format',
        
        # Advanced
        'lrc-format': '--lrc-format',
        'cover-size': '--cover-size',
        'storefront': '--storefront',
        'limit-max': '--limit-max'
    }
    
    cmd = []
    for key, value in (options or {}).items():
        if key in option_map:
            if isinstance(value, bool):
                cmd.append(option_map[key])
            else:
                cmd.extend([option_map[key], str(value)])
    return cmd
