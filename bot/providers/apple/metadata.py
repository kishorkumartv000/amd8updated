import os
import re
import base64
import mutagen
from pathlib import Path
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.mp3 import EasyMP3
from mutagen import File
from bot.logger import LOGGER

def extract_apple_metadata(file_path: str) -> dict:
    """
    Enhanced metadata extraction with format detection
    Preserves original structure with improved error handling
    """
    try:
        ext = Path(file_path).suffix.lower()
        handlers = {
            '.m4a': _extract_m4a_metadata,
            '.mp4': _extract_video_metadata,
            '.m4v': _extract_video_metadata,
            '.mov': _extract_video_metadata,
            '.flac': _extract_flac_metadata,
            '.mp3': _extract_mp3_metadata
        }
        return handlers.get(ext, _extract_generic_metadata)(file_path)
    except Exception as e:
        LOGGER.error(f"Metadata Error: {str(e)}")
        return _default_metadata(file_path)

def _extract_m4a_metadata(file_path: str) -> dict:
    """Apple Lossless (ALAC) metadata with enhanced fields"""
    try:
        audio = MP4(file_path)
        return {
            'title': audio.get('\xa9nam', ['Unknown'])[0],
            'artist': audio.get('\xa9ART', ['Unknown Artist'])[0],
            'album': audio.get('\xa9alb', ['Unknown Album'])[0],
            'duration': int(audio.info.length),
            'tracknumber': str(audio.get('trkn', [(0,0)])[0][0]).zfill(2),
            'genre': audio.get('\xa9gen', [''])[0],
            'date': audio.get('\xa9day', [''])[0],
            'isrc': audio.get('----:com.apple.iTunes:ISRC', [''])[0],
            'cover': _extract_cover_art(audio, file_path),
            'thumbnail': _extract_cover_art(audio, file_path),
            'explicit': 'Explicit' if audio.get('rtng', [0])[0] == 1 else '',
            'bitrate': audio.info.bitrate,
            'codec': 'ALAC' if 'alac' in audio.info.codec else 'AAC'
        }
    except Exception as e:
        LOGGER.warning(f"ALAC Extraction Failed: {str(e)}")
        return _default_metadata(file_path)

def _extract_video_metadata(file_path: str) -> dict:
    """Video metadata extraction with resolution detection"""
    try:
        video = MP4(file_path)
        return {
            'title': video.get('\xa9nam', ['Unknown'])[0],
            'artist': video.get('\xa9ART', ['Unknown Artist'])[0],
            'duration': int(video.info.length),
            'width': video.get('width', [1920])[0],
            'height': video.get('height', [1080])[0],
            'cover': _extract_cover_art(video, file_path),
            'thumbnail': _extract_cover_art(video, file_path),
            'resolution': f"{video.get('width', [1920])[0]}x{video.get('height', [1080])[0]}",
            'codec': video.info.codec_description
        }
    except Exception as e:
        LOGGER.warning(f"Video Extraction Failed: {str(e)}")
        return _default_metadata(file_path)

def _extract_flac_metadata(file_path: str) -> dict:
    """FLAC metadata with high-res audio support"""
    try:
        audio = FLAC(file_path)
        return {
            'title': audio.get('title', ['Unknown'])[0],
            'artist': audio.get('artist', ['Unknown Artist'])[0],
            'album': audio.get('album', ['Unknown Album'])[0],
            'duration': int(audio.info.length),
            'bitdepth': audio.info.bits_per_sample,
            'samplerate': audio.info.sample_rate,
            'cover': _extract_cover_art(audio, file_path),
            'isrc': audio.get('isrc', [''])[0],
            'genre': audio.get('genre', [''])[0]
        }
    except Exception as e:
        LOGGER.warning(f"FLAC Extraction Failed: {str(e)}")
        return _default_metadata(file_path)

def _extract_mp3_metadata(file_path: str) -> dict:
    """MP3 metadata with ID3 tag support"""
    try:
        audio = EasyMP3(file_path)
        return {
            'title': audio.get('title', ['Unknown'])[0],
            'artist': audio.get('artist', ['Unknown Artist'])[0],
            'album': audio.get('album', ['Unknown Album'])[0],
            'duration': int(audio.info.length),
            'tracknumber': audio.get('tracknumber', ['0'])[0],
            'genre': audio.get('genre', [''])[0],
            'cover': _extract_cover_art(audio, file_path)
        }
    except Exception as e:
        LOGGER.warning(f"MP3 Extraction Failed: {str(e)}")
        return _default_metadata(file_path)

def _extract_generic_metadata(file_path: str) -> dict:
    """Fallback for unsupported formats"""
    try:
        audio = File(file_path)
        return {
            'title': audio.get('title', ['Unknown'])[0],
            'artist': audio.get('artist', ['Unknown Artist'])[0],
            'album': audio.get('album', ['Unknown Album'])[0],
            'duration': int(audio.info.length),
            'cover': _extract_cover_art(audio, file_path)
        }
    except Exception as e:
        LOGGER.warning(f"Generic Extraction Failed: {str(e)}")
        return _default_metadata(file_path)

def _extract_cover_art(media, file_path: str) -> str:
    """Comprehensive cover art extraction from working utils.py"""
    try:
        # MP4/ALAC cover art
        if 'covr' in media:
            cover_data = media['covr'][0]
            cover_path = f"{os.path.splitext(file_path)[0]}.jpg"
            with open(cover_path, 'wb') as f:
                f.write(cover_data)
            return cover_path
        
        # ID3 (MP3) embedded art
        if hasattr(media, 'tags') and 'APIC:' in media.tags:
            pic = media.tags['APIC:'].data
            cover_path = f"{os.path.splitext(file_path)[0]}.jpg"
            with open(cover_path, 'wb') as f:
                f.write(pic)
            return cover_path
        
        # FLAC embedded art
        if isinstance(media, FLAC) and media.pictures:
            for pic in media.pictures:
                if pic.type == 3:  # Front cover
                    cover_path = f"{os.path.splitext(file_path)[0]}.jpg"
                    with open(cover_path, 'wb') as f:
                        f.write(pic.data)
                    return cover_path
        
        # Vorbis comments (OGG/OPUS)
        if 'metadata_block_picture' in media:
            for block in media.get('metadata_block_picture', []):
                try:
                    data = base64.b64decode(block)
                    pic = FLAC.Picture(data)
                    if pic.type == 3:
                        cover_path = f"{os.path.splitext(file_path)[0]}.jpg"
                        with open(cover_path, 'wb') as f:
                            f.write(pic.data)
                        return cover_path
                except:
                    continue
        
        return None
    except Exception as e:
        LOGGER.error(f"Cover Art Error: {str(e)}")
        return None

def _default_metadata(file_path: str) -> dict:
    """Enhanced fallback metadata with filename parsing"""
    try:
        stem = Path(file_path).stem
        # Attempt to parse artist - title from filename
        if '-' in stem:
            parts = stem.split('-', 1)
            artist = parts[0].strip()
            title = parts[1].strip()
        else:
            artist = 'Unknown Artist'
            title = stem
            
        return {
            'title': title,
            'artist': artist,
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
    except:
        return {
            'title': 'Unknown',
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
