import os
import mutagen
from mutagen.mp4 import MP4
from mutagen import File
from mutagen.flac import FLAC
from mutagen.mp3 import EasyMP3
from bot.logger import LOGGER

def extract_apple_metadata(file_path: str) -> dict:
    """
    Extract comprehensive metadata from Apple Music files
    Args:
        file_path: Path to media file
    Returns:
        dict: Metadata dictionary with keys:
            - title, artist, album, duration, tracknumber,
            - genre, date, isrc, cover, thumbnail, explicit
    """
    try:
        if file_path.endswith('.m4a'):
            return _extract_m4a_metadata(file_path)
        elif file_path.endswith(('.mp4', '.m4v', '.mov')):
            return _extract_video_metadata(file_path)
        else:
            return _extract_generic_metadata(file_path)
    except Exception as e:
        LOGGER.error(f"Metadata extraction failed: {str(e)}")
        return _default_metadata(file_path)

def _extract_m4a_metadata(file_path: str) -> dict:
    """Extract metadata from Apple Lossless files"""
    audio = MP4(file_path)
    return {
        'title': audio.get('\xa9nam', ['Unknown'])[0],
        'artist': audio.get('\xa9ART', ['Unknown Artist'])[0],
        'album': audio.get('\xa9alb', ['Unknown Album'])[0],
        'duration': int(audio.info.length),
        'tracknumber': audio.get('trkn', [(0, 0)])[0][0],
        'genre': audio.get('\xa9gen', [''])[0],
        'date': audio.get('\xa9day', [''])[0],
        'isrc': audio.get('----:com.apple.iTunes:ISRC', [''])[0],
        'cover': _extract_cover_art(audio, file_path),
        'thumbnail': _extract_cover_art(audio, file_path),
        'explicit': 'Explicit' if audio.get('rtng', [0])[0] == 1 else ''
    }

def _extract_video_metadata(file_path: str) -> dict:
    """Extract metadata from Apple Music videos"""
    video = MP4(file_path)
    return {
        'title': video.get('\xa9nam', ['Unknown'])[0],
        'artist': video.get('\xa9ART', ['Unknown Artist'])[0],
        'album': video.get('\xa9alb', ['Unknown Album'])[0],
        'duration': int(video.info.length),
        'width': video.get('width', [1920])[0],
        'height': video.get('height', [1080])[0],
        'cover': _extract_cover_art(video, file_path),
        'thumbnail': _extract_cover_art(video, file_path),
        'resolution': f"{video.get('width', [1920])[0]}x{video.get('height', [1080])[0]}"
    }

def _extract_generic_metadata(file_path: str) -> dict:
    """Handle other audio formats (FLAC, MP3)"""
    audio = File(file_path)
    return {
        'title': audio.get('title', ['Unknown'])[0],
        'artist': audio.get('artist', ['Unknown Artist'])[0],
        'album': audio.get('album', ['Unknown Album'])[0],
        'duration': int(audio.info.length),
        'tracknumber': audio.get('tracknumber', ['0'])[0],
        'genre': audio.get('genre', [''])[0],
        'date': audio.get('date', [''])[0],
        'isrc': audio.get('isrc', [''])[0],
        'cover': _extract_cover_art(audio, file_path),
        'thumbnail': _extract_cover_art(audio, file_path),
        'explicit': 'Explicit' if audio.get('explicit', '0') == '1' else ''
    }

def _extract_cover_art(handle, file_path: str) -> str:
    """Extract and save embedded cover art"""
    try:
        if hasattr(handle, 'pictures') and handle.pictures:
            cover_path = f"{os.path.splitext(file_path)[0]}.jpg"
            with open(cover_path, 'wb') as f:
                f.write(handle.pictures[0].data)
            return cover_path
        elif 'covr' in handle:
            cover_path = f"{os.path.splitext(file_path)[0]}.jpg"
            with open(cover_path, 'wb') as f:
                f.write(handle['covr'][0])
            return cover_path
        return None
    except Exception as e:
        LOGGER.error(f"Cover art extraction failed: {str(e)}")
        return None

def _default_metadata(file_path: str) -> dict:
    """Fallback metadata for failed extraction"""
    return {
        'title': os.path.basename(file_path),
        'artist': 'Unknown Artist',
        'album': 'Unknown Album',
        'duration': 0,
        'tracknumber': '0',
        'genre': '',
        'date': '',
        'isrc': '',
        'cover': None,
        'thumbnail': None,
        'explicit': ''
    }
