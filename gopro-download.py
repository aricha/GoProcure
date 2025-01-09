#!/usr/bin/env python3
"""Download media files from GoPro Cloud."""

import argparse
import sys
from pathlib import Path
from lib.config import setup_logging
from lib.download.client import GoProAPIClient, ConfigManager
from lib.download.downloader import MediaDownloader, MediaProcessor
from lib.download.constants import Config

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='gopro_downloads',
        help="Output directory for downloaded files"
    )
    parser.add_argument(
        '--include-photos',
        action='store_true',
        help="Include photos in download"
    )
    parser.add_argument(
        '--max-items',
        type=int,
        default=Config.MAX_ITEMS,
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
    setup_logging(args.verbose)
    
    config = Config(
        INCLUDE_PHOTOS=args.include_photos,
        MAX_ITEMS=args.max_items
    )
    
    try:
        config_manager = ConfigManager()
        creds = config_manager.load_credentials()
        
        client = GoProAPIClient(creds['access_token'], creds['user_id'], config)
        downloader = MediaDownloader(client)
        processor = MediaProcessor(client, downloader, Path(args.output_dir))
        
        processor.process_media_items(args.download_gpmf)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()