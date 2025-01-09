import logging
from typing import Dict, Optional
from pathlib import Path
import requests
import json
from .client import GoProAPIClient

logger = logging.getLogger(__name__)

class MediaDownloader:
    """Handles downloading of media files"""
    def __init__(self, api_client: GoProAPIClient):
        self.api_client = api_client
    
    def download_media(self, media_item: Dict, output_path: Path, download_gpmf: bool = False):
        """Download media and optionally its GPMF data"""
        download_info = self.api_client.get_download_info(media_item['id'])
        
        # Download main media file
        video_url = download_info.get('_embedded', {}).get('files', [{}])[0].get('url')
        if video_url:
            self._download_file(video_url, output_path)
        
        # Download GPMF data if requested
        if download_gpmf:
            gpmf_url = self._get_gpmf_url(download_info)
            if gpmf_url:
                gpmf_path = output_path.with_name(f"{output_path.stem}_gpmf{output_path.suffix}")
                self._download_file(gpmf_url, gpmf_path)
    
    def _download_file(self, url: str, output_path: Path):
        """Download a file with progress indication"""
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        
        with open(output_path, 'wb') as f:
            if total_size == 0:
                f.write(response.content)
            else:
                downloaded = 0
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)
                    percentage = int(100 * downloaded / total_size)
                    print(f"\rDownloading {output_path.name}: {percentage}%", end="")
        print()
    
    @staticmethod
    def _get_gpmf_url(download_info: Dict) -> Optional[str]:
        """Extract GPMF sidecar file URL from download response"""
        sidecar_files = download_info.get('_embedded', {}).get('sidecar_files', [])
        for file in sidecar_files:
            if file.get('label') == 'gpmf':
                return file.get('url')
        return None

class MediaProcessor:
    """Orchestrates the processing of media items"""
    def __init__(self, api_client: GoProAPIClient, downloader: MediaDownloader, output_dir: Path):
        self.api_client = api_client
        self.downloader = downloader
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
    
    def process_media_items(self, download_gpmf: bool = False):
        """Process all media items"""
        try:
            num_pages = max(self.api_client.config.MAX_ITEMS // self.api_client.config.PAGE_SIZE, 1)
            item_count = 0
            existing_items = 0
            
            for page in range(1, num_pages + 1):
                items_response = self.api_client.get_media_items(page)
                media_items = items_response.get('_embedded', {}).get('media', [])
                
                if not media_items:
                    break
                    
                item_count += len(media_items)
                
                for media_item in media_items:
                    if self._process_single_item(media_item, download_gpmf):
                        existing_items += 1
                        
                if item_count >= self.api_client.config.MAX_ITEMS:
                    break

            logger.info(f"Found {item_count} media items, {existing_items} already downloaded")
                
        except Exception as e:
            logger.error(f"Error processing media items: {e}")
            raise
    
    def _process_single_item(self, media_item: Dict, download_gpmf: bool) -> bool:
        """Process a single media item, returns True if item already existed"""
        try:
            filename = Path(media_item['filename']).with_suffix('').name
            extension = media_item['file_extension'].lower()
            
            # Handle highlights
            if media_item['moments_count'] > 0:
                self._save_highlights(media_item, filename)
            
            # Save metadata
            self._save_metadata(media_item, filename)
            
            # Download media if it doesn't exist
            media_path = self.output_dir / f"{filename}.{extension}"
            if media_path.exists():
                logger.debug(f"Skipping existing file: {filename}.{extension}")
                return True
                
            self.downloader.download_media(media_item, media_path, download_gpmf)
            return False
            
        except Exception as e:
            logger.error(f"Error processing {media_item.get('filename', 'unknown')}: {e}")
            return False
    
    def _save_highlights(self, media_item: Dict, filename: str):
        """Save highlights data if available"""
        highlights_path = self.output_dir / f"{filename}_highlights.json"
        if not highlights_path.exists():
            logger.info(f"Found {media_item['moments_count']} HiLight tags in {filename}")
            highlights = self.api_client.get_video_highlights(media_item['id'])
            with open(highlights_path, 'w') as f:
                json.dump(highlights, f, indent=2)
    
    def _save_metadata(self, media_item: Dict, filename: str):
        """Save media item metadata"""
        metadata_path = self.output_dir / f"{filename}_metadata.json"
        if not metadata_path.exists():
            with open(metadata_path, 'w') as f:
                json.dump(media_item, f, indent=2)