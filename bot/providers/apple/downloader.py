import os
import re
import asyncio
import subprocess
from config import Config
from bot.logger import LOGGER
from bot.helpers.message import edit_message

async def run_apple_downloader(url: str, output_dir: str, options: list = None, user: dict = None) -> dict:
    """
    Execute Apple Music downloader script with proper configuration
    Args:
        url: Apple Music URL to download
        output_dir: Directory to save downloaded files
        options: List of command-line options
        user: User details for progress updates
    Returns:
        dict: {'success': bool, 'error': str (if failed)}
    """
    try:
        # Validate downloader path
        if not os.path.exists(Config.DOWNLOADER_PATH):
            raise FileNotFoundError(f"Apple downloader not found at {Config.DOWNLOADER_PATH}")

        # Create config file
        config_path = os.path.join(output_dir, "apple_config.yaml")
        _create_config_file(config_path, output_dir)

        # Build command
        cmd = [
            Config.DOWNLOADER_PATH,
            "--config", config_path,
            "--output", output_dir
        ]
        
        # Add user options
        if options:
            cmd.extend(options)
        cmd.append(url)

        LOGGER.info(f"Apple Download Command: {' '.join(cmd)}")

        # Run downloader process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=output_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Monitor progress
        return await _monitor_download_process(process, user)

    except Exception as e:
        LOGGER.error(f"Apple Downloader Setup Failed: {str(e)}")
        return {'success': False, 'error': str(e)}

def _create_config_file(config_path: str, output_dir: str):
    """
    Generate Apple Music downloader configuration
    Args:
        config_path: Full path to config file
        output_dir: Base output directory
    """
    config_content = f"""# Apple Music Configuration
lrc-type: "lyrics"
lrc-format: "lrc"
embed-lrc: true
save-lrc-file: true
save-artist-cover: true
save-animated-artwork: false
emby-animated-artwork: false
embed-cover: true
cover-size: 5000x5000
cover-format: original
max-memory-limit: 256
decrypt-m3u8-port: "127.0.0.1:10020"
get-m3u8-port: "127.0.0.1:20020"
get-m3u8-from-device: true
get-m3u8-mode: hires
aac-type: aac-lc
alac-max: {Config.APPLE_ALAC_QUALITY}
atmos-max: {Config.APPLE_ATMOS_QUALITY}
limit-max: 200
album-folder-format: "{{AlbumName}}"
playlist-folder-format: "{{PlaylistName}}"
song-file-format: "{{SongNumber}}. {{SongName}}"
artist-folder-format: "{{UrlArtistName}}"
explicit-choice : "[E]"
clean-choice : "[C]"
apple-master-choice : "[M]"
use-songinfo-for-playlist: false
dl-albumcover-for-playlist: false
mv-audio-type: atmos
mv-max: 2160
alac-save-folder: {os.path.join(output_dir, "alac")}
atmos-save-folder: {os.path.join(output_dir, "atmos")}
"""

    with open(config_path, 'w') as f:
        f.write(config_content)
    LOGGER.debug(f"Created Apple config at {config_path}")

async def _monitor_download_process(process, user: dict) -> dict:
    """
    Monitor download process and handle output
    Args:
        process: Running subprocess
        user: User details for progress updates
    Returns:
        dict: Process result
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
            
            # Update progress if available
            if user and 'bot_msg' in user:
                progress = _parse_progress(line_str)
                if progress and progress != last_progress:
                    await _update_progress(user, progress)
                    last_progress = progress

        # Get remaining output
        stdout, stderr = await process.communicate()
        stdout_chunks.extend(stdout.decode().splitlines())
        
        # Check result
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
        if progress % 5 == 0:  # Throttle updates
            await edit_message(
                user['bot_msg'],
                f"🍎 Apple Music Download Progress: {progress}%"
            )
    except Exception as e:
        LOGGER.debug(f"Progress update failed: {str(e)}")
