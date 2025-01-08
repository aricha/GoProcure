import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
import subprocess
from typing import Optional, Dict
import shutil
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MetadataUpdater:
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
        """
        Update file's creation and modification dates using exiftool and macOS-specific tools
        Returns True if successful, False otherwise
        """
        try:
            # Convert ISO date string to datetime, treating it as local time despite the Z
            naive_date = datetime.strptime(captured_at.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
            
            # Attach local timezone from system
            local_tz = datetime.now().astimezone().tzinfo
            local_date = naive_date.replace(tzinfo=local_tz)
            
            # Debug logging
            logger.debug(f"Original time (local): {local_date}")
            
            # Format for exiftool (convert to UTC)
            try:
                # Python 3.11+
                UTC = datetime.UTC
            except AttributeError:
                # Earlier Python versions
                from datetime import timezone
                UTC = timezone.utc
                
            utc_date = local_date.astimezone(UTC)
            formatted_date = utc_date.strftime('%Y:%m:%d %H:%M:%S+00:00')
            
            # Format for macOS (keep in local time)
            macos_date = naive_date.strftime('%m/%d/%Y %H:%M:%S')
            
            # Update metadata using exiftool
            exif_cmd = [
                'exiftool',
                '-overwrite_original',
                '-preserveModifyDate',
                '-P',  # Preserve file modification date/time
                f'-AllDates={formatted_date}',  # Set all date/time tags
                f'-FileCreateDate={formatted_date}',  # Specific file system create date
                f'-FileModifyDate={formatted_date}',  # Specific file system modify date
                str(media_path)
            ]
            
            exif_result = subprocess.run(exif_cmd, capture_output=True, text=True)
            
            if exif_result.returncode != 0:
                logger.error(f"Failed to update metadata for {media_path}: {exif_result.stderr}")
                return False
            
            # Try to use SetFile for macOS (if available)
            if shutil.which('SetFile'):
                setfile_cmd = [
                    'SetFile',
                    '-d', f'{macos_date}',  # Creation date
                    '-m', f'{macos_date}',  # Modification date
                    str(media_path)
                ]
                
                try:
                    subprocess.run(setfile_cmd, capture_output=True, text=True, check=True)
                except subprocess.CalledProcessError as e:
                    logger.warning(f"SetFile command failed (non-critical): {e}")
            
            # Use touch as a fallback/additional method
            os.utime(media_path, (naive_date.timestamp(), naive_date.timestamp()))
                
            logger.info(f"Updated metadata and file system dates for {media_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating metadata for {media_path}: {e}")
            return False

def load_metadata(metadata_path: Path) -> Optional[Dict]:
    """Load metadata from JSON file"""
    try:
        with open(metadata_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading metadata from {metadata_path}: {e}")
        return None

def process_directory(directory: Path, dry_run: bool = False):
    """Process all media files in directory"""
    updater = MetadataUpdater()
    processed = 0
    errors = 0
    
    # Find all metadata files
    metadata_files = list(directory.glob("*_metadata.json"))
    logger.info(f"Found {len(metadata_files)} metadata files")
    
    for metadata_path in metadata_files:
        # Load metadata
        metadata = load_metadata(metadata_path)
        if not metadata:
            errors += 1
            continue
        
        # Get captured_at timestamp
        captured_at = metadata.get('captured_at')
        if not captured_at:
            logger.warning(f"No captured_at found in {metadata_path}")
            errors += 1
            continue
        
        # Find corresponding media file
        filename = metadata_path.stem.replace('_metadata', '')
        extension = metadata.get('file_extension', '').lower()
        media_path = metadata_path.parent / f"{filename}.{extension}"
        
        if not media_path.exists():
            logger.warning(f"Media file not found: {media_path}")
            errors += 1
            continue
        
        # Update metadata
        if dry_run:
            logger.info(f"Would update {media_path} with date {captured_at}")
            processed += 1
        else:
            if updater.update_file_dates(media_path, captured_at):
                processed += 1
            else:
                errors += 1
    
    # Print summary
    logger.info(f"Processing complete. Successfully processed: {processed}, Errors: {errors}")
    
def main():
    parser = argparse.ArgumentParser(description="Update GoPro media file metadata from downloaded metadata")
    parser.add_argument('-d', '--directory', type=str, default='gopro_downloads',
                      help="Directory containing downloaded files")
    parser.add_argument('--dry-run', action='store_true',
                      help="Show what would be done without making changes")
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        return
    
    process_directory(directory, args.dry_run)

if __name__ == "__main__":
    main()