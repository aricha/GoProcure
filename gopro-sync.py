#!/usr/bin/env python3
"""Download and organize GoPro media files in one step."""

import argparse
import sys
import subprocess
from pathlib import Path

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='gopro_media',
        help="Base directory for media files"
    )
    parser.add_argument(
        '--include-photos',
        action='store_true',
        help="Include photos in download"
    )
    parser.add_argument(
        '--max-items',
        type=int,
        help="Maximum number of items to download"
    )
    parser.add_argument(
        '--download-gpmf',
        action='store_true',
        help="Download GPMF data"
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Enable verbose logging"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    downloads_dir = Path(args.output_dir) / "downloads"
    
    try:
        # First download
        cmd = ["gopro-download", "-o", str(downloads_dir)]
        if args.include_photos:
            cmd.append("--include-photos")
        if args.max_items:
            cmd.extend(["--max-items", str(args.max_items)])
        if args.download_gpmf:
            cmd.append("--download-gpmf")
        if args.verbose:
            cmd.append("--verbose")
            
        print("Downloading media files...")
        subprocess.run(cmd, check=True)
        
        # Then organize
        cmd = ["gopro-organize", str(downloads_dir)]
        if args.verbose:
            cmd.append("--verbose")
            
        print("\nOrganizing media files...")
        subprocess.run(cmd, check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()