#!/usr/bin/env python3
"""Organize GoPro media files by date and update metadata."""

import argparse
import sys
from pathlib import Path
from lib.config import setup_logging
from lib.organize.organizer import VideoOrganizer

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source_dir",
        type=Path,
        help="Directory containing the video files"
    )
    parser.add_argument(
        "-c", "--copy",
        action="store_true",
        help="Copy files instead of moving them"
    )
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively process subdirectories"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    setup_logging(args.verbose)
    
    try:
        if not args.source_dir.is_dir():
            print(f"Error: Directory not found: {args.source_dir}", file=sys.stderr)
            sys.exit(1)
        
        organizer = VideoOrganizer(
            args.source_dir,
            copy=args.copy,
            dry_run=args.dry_run
        )
        
        processed, errors = organizer.process_directory(args.recursive)
        
        if args.dry_run:
            print("\nThis was a dry run. No files were modified.")
        print(f"\nProcessing complete. Successfully processed: {processed}, Errors: {errors}")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()