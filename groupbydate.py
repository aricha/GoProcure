#!/usr/bin/env python3
from datetime import datetime
from pathlib import Path
from typing import Generator, Callable, List
import argparse
import shutil
import sys
import json

def find_video_files(source_dir: Path, recursive: bool = False) -> Generator[Path, None, None]:
    """
    Find all MP4 files in the source directory.
    
    Args:
        source_dir: Directory to search for video files
        recursive: If True, search in subdirectories as well
        
    Yields:
        Path objects for each video file found
    """
    pattern = "**/*.mp4" if recursive else "*.mp4"
    yield from source_dir.glob(pattern)

def get_capture_date(metadata_path: Path) -> str:
    """
    Extract capture date from video metadata JSON file.
    
    Args:
        metadata_path: Path to the metadata JSON file
        
    Returns:
        Formatted date string (YYYY-MM-DD)
        
    Raises:
        ValueError: If metadata file can't be parsed or doesn't contain capture date
    """
    try:
        with metadata_path.open() as f:
            metadata = json.load(f)
        
        if 'captured_at' not in metadata:
            raise ValueError("No 'captured_at' field found in metadata")
            
        capture_date = datetime.fromisoformat(metadata['captured_at'])
        return capture_date.strftime('%Y-%m-%d')
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse metadata JSON: {e}")
    except ValueError as e:
        raise ValueError(f"Invalid date format in metadata: {e}")

def find_related_files(video_path: Path) -> List[Path]:
    """
    Find all related JSON files for a video.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        List of paths to related files (metadata and highlights)
        
    Raises:
        FileNotFoundError: If metadata file doesn't exist
    """
    files = []
    
    # Find required metadata file
    metadata_path = video_path.with_name(f"{video_path.stem}_metadata.json")
    if not metadata_path.exists():
        raise FileNotFoundError(f"No metadata file found for {video_path.name}")
    files.append(metadata_path)
    
    # Find optional highlights file
    highlights_path = video_path.with_name(f"{video_path.stem}_highlights.json")
    if highlights_path.exists():
        files.append(highlights_path)
    
    return files

def organize_videos(source_dir: Path, *, copy: bool = False, dry_run: bool = False, recursive: bool = False) -> None:
    """
    Organizes video files and their corresponding JSON files into folders by date.
    
    Args:
        source_dir: Path to the directory containing the video files
        copy: If True, copy files instead of moving them
        dry_run: If True, only show what would be done without making changes
        recursive: If True, process subdirectories as well
    """
    # Create base output directory
    base_output_dir = source_dir / 'organized_videos'
    if not dry_run:
        base_output_dir.mkdir(exist_ok=True)
    
    # Choose operation
    operation: Callable[[Path, Path], None]
    operation_name: str
    if dry_run:
        operation = lambda src, dst: None
        operation_name = f"Would {'copy' if copy else 'move'}"
    else:
        operation = shutil.copy2 if copy else shutil.move
        operation_name = "Copying" if copy else "Moving"
    
    for video_path in find_video_files(source_dir, recursive):
        try:
            # Find all related files and get date from metadata
            related_files = find_related_files(video_path)
            try:
                date_folder = get_capture_date(related_files[0])  # First file is always metadata
            except ValueError as e:
                print(f"Error reading date for {video_path.name}: {e}", file=sys.stderr)
                continue
            
            # Create folder for this date
            date_dir = base_output_dir / date_folder
            if not dry_run:
                date_dir.mkdir(exist_ok=True)
            
            # Process video file
            dest_path = date_dir / video_path.name
            print(f"{operation_name} {video_path.name} to {date_folder}")
            operation(video_path, dest_path)
            
            # Process all related JSON files
            for related_file in related_files:
                related_dest = date_dir / related_file.name
                print(f"{operation_name} {related_file.name} to {date_folder}")
                operation(related_file, related_dest)
                
        except FileNotFoundError as e:
            print(f"Warning: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing {video_path}: {str(e)}", file=sys.stderr)

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Organize video files into folders by creation date from metadata.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "source_dir",
        type=Path,
        help="Directory containing the video files"
    )
    parser.add_argument(
        "-c",
        "--copy",
        action="store_true",
        help="Copy files instead of moving them"
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Show what would be done without making any changes"
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recursively process subdirectories"
    )
    return parser.parse_args()

def main() -> None:
    """Main entry point for the script."""
    try:
        args = parse_args()
        
        # Validate source directory
        if not args.source_dir.is_dir():
            print(f"Error: Directory not found: {args.source_dir}", file=sys.stderr)
            sys.exit(1)
        
        # Process the files
        organize_videos(
            args.source_dir,
            copy=args.copy,
            dry_run=args.dry_run,
            recursive=args.recursive
        )
        
        if args.dry_run:
            print("\nThis was a dry run. No files were actually modified.")
        else:
            print("Organization complete!")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()