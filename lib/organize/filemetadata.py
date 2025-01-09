import json
import logging
import shutil
import subprocess
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class FileMetadataUpdater:
    """Updates media file metadata using exiftool"""
    
    def __init__(self):
        self._check_exiftool()
    
    def _check_exiftool(self):
        """Verify exiftool is installed"""
        if not shutil.which('exiftool'):
            raise RuntimeError(
                "exiftool is not installed. Please install it first:\n"
                "- macOS: brew install exiftool\n"
                "- Ubuntu/Debian: sudo apt-get install libimage-exiftool-perl\n"
                "- Windows: Download from https://exiftool.org"
            )
    
    def update_file_dates(self, media_path: Path, captured_at: str) -> bool:
        """Update file's creation and modification dates"""
        try:
            # Convert ISO date string to datetime, treating it as local time
            naive_date = datetime.strptime(captured_at.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
            
            # Attach local timezone
            local_tz = datetime.now().astimezone().tzinfo
            local_date = naive_date.replace(tzinfo=local_tz)
            
            # Format for exiftool (UTC)
            try:
                UTC = datetime.UTC
            except AttributeError:
                from datetime import timezone
                UTC = timezone.utc
                
            utc_date = local_date.astimezone(UTC)
            formatted_date = utc_date.strftime('%Y:%m:%d %H:%M:%S+00:00')
            
            # Format for macOS
            macos_date = naive_date.strftime('%m/%d/%Y %H:%M:%S')
            
            # Update using exiftool
            exif_cmd = [
                'exiftool',
                '-overwrite_original',
                '-preserveModifyDate',
                '-P',
                f'-AllDates={formatted_date}',
                f'-FileCreateDate={formatted_date}',
                f'-FileModifyDate={formatted_date}',
                str(media_path)
            ]
            
            exif_result = subprocess.run(exif_cmd, capture_output=True, text=True)
            
            if exif_result.returncode != 0:
                logger.error(f"Failed to update metadata: {exif_result.stderr}")
                return False
            
            # Try SetFile for macOS
            if shutil.which('SetFile'):
                setfile_cmd = [
                    'SetFile',
                    '-d', f'{macos_date}',
                    '-m', f'{macos_date}',
                    str(media_path)
                ]
                
                try:
                    subprocess.run(setfile_cmd, capture_output=True, text=True, check=True)
                except subprocess.CalledProcessError as e:
                    logger.warning(f"SetFile command failed (non-critical): {e}")
            
            # Use touch as fallback
            os.utime(media_path, (naive_date.timestamp(), naive_date.timestamp()))
            
            logger.info(f"Updated metadata for {media_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating metadata: {e}")
            return False

def load_metadata(metadata_path: Path) -> Optional[Dict]:
    """Load metadata from JSON file"""
    try:
        with open(metadata_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading metadata from {metadata_path}: {e}")
        return None

def get_capture_date(metadata: Dict) -> str:
    """Extract capture date from metadata"""
    if 'captured_at' not in metadata:
        raise ValueError("No 'captured_at' field found in metadata")
        
    capture_date = datetime.fromisoformat(metadata['captured_at'].replace('Z', ''))
    return capture_date.strftime('%Y-%m-%d')