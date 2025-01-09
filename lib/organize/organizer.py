import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Generator, List, Tuple
import json
from .metadata import MetadataUpdater

logger = logging.getLogger(__name__)

def find_video_files(source_dir: Path, recursive: bool = False) -> Generator[Path, None, None]:
    """Find all MP4 files in the source directory"""
    pattern = "**/*.mp4" if recursive else "*.mp4"
    yield from source_dir.glob(pattern)

def find_related_files(video_path: Path) -> Tuple[Path, List[Path]]:
    """Find metadata and optional highlights files"""
    files = []
    
    # Find required metadata file
    metadata_path = video_path.with_name(f"{video_path.stem}_metadata.json")
    if not metadata_path.exists():
        raise FileNotFoundError(f"No metadata file found for {video_path.name}")
    
    # Find optional highlights file
    highlights_path = video_path.with_name(f"{video_path.stem}_highlights.json")
    if highlights_path.exists():
        files.append(highlights_path)
    
    return metadata_path, files

def load_metadata(metadata_path: Path) -> dict:
    """Load and validate metadata file"""
    try:
        with open(metadata_path) as f:
            metadata = json.load(f)
        
        if 'captured_at' not in metadata:
            raise ValueError("No 'captured_at' field found in metadata")
            
        return metadata
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse metadata JSON: {e}")
        return None
    except ValueError as e:
        logger.error(f"Invalid date format in metadata: {e}")
        return None

def get_capture_date(metadata: dict) -> str:
    """Extract capture date from metadata file"""
    if 'captured_at' not in metadata:
        raise ValueError("No 'captured_at' field found in metadata")
        
    capture_date = datetime.fromisoformat(metadata['captured_at'].replace('Z', ''))
    return capture_date.strftime('%Y-%m-%d')

class VideoOrganizer:
    """Handles organizing videos into date-based folders"""
    def __init__(self, source_dir: Path, *, copy: bool = False, dry_run: bool = False):
        self.source_dir = source_dir
        self.copy = copy
        self.dry_run = dry_run
        self.metadata_updater = MetadataUpdater()
        
        # Create base output directory
        self.output_dir = source_dir / 'organized_videos'
        if not dry_run:
            self.output_dir.mkdir(exist_ok=True)
    
    def _move_or_copy_file(self, src: Path, dest: Path) -> None:
        """Move or copy file based on settings"""
        if self.dry_run:
            op_name = 'copy' if self.copy else 'move'
            logger.info(f"Would {op_name} {src.name} to {dest}")
            return
            
        operation = shutil.copy2 if self.copy else shutil.move
        operation(src, dest)
        op_name = 'Copied' if self.copy else 'Moved'
        logger.info(f"{op_name} {src.name} to {dest}")
    
    def process_video(self, video_path: Path) -> bool:
        """Process a single video file and its related files"""
        try:
            # Find related files
            metadata_path, related_files = find_related_files(video_path)
            metadata = load_metadata(metadata_path)
            
            # Get date and create folder
            date_folder = get_capture_date(metadata)
            date_dir = self.output_dir / date_folder
            
            if not self.dry_run:
                # Update metadata dates
                if not self.metadata_updater.update_file_dates(video_path, metadata['captured_at']):
                    return False
                
                date_dir.mkdir(exist_ok=True)
            
            # Move/copy video file
            dest_path = date_dir / video_path.name
            self._move_or_copy_file(video_path, dest_path)
            
            # Move/copy metadata file
            self._move_or_copy_file(metadata_path, date_dir / metadata_path.name)
            
            # Move/copy any related files
            for related_file in related_files:
                self._move_or_copy_file(related_file, date_dir / related_file.name)
            
            return True
            
        except Exception as e:
            import traceback
            logger.error(f"Error processing {video_path}: {e}")
            print(traceback.format_exc())
            return False

    def process_directory(self, recursive: bool = False) -> Tuple[int, int]:
        """Process all videos in directory"""
        processed = 0
        errors = 0
        
        for video_path in find_video_files(self.source_dir, recursive):
            if self.process_video(video_path):
                processed += 1
            else:
                errors += 1
        
        return processed, errors