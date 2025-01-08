import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import requests
import subprocess
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Configuration settings for the application"""
    PAGE_SIZE: int = 70
    INCLUDE_PHOTOS: bool = False
    BASE_URL: str = "https://api.gopro.com"

class ConfigManager:
    """Handles loading and saving of credentials"""
    def __init__(self, config_path: str = 'config.json'):
        self.config_path = config_path
        
    def load_credentials(self) -> Dict[str, str]:
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self._create_template_config()
            raise SystemExit(1)
    
    def _create_template_config(self):
        template = {
            "access_token": "your-access-token-here",
            "user_id": "your-user-id-here"
        }
        logger.info(f"Creating template config file at {self.config_path}")
        with open(self.config_path, 'w') as f:
            json.dump(template, f, indent=2)
        logger.info("Please edit config.json and replace the placeholder values with your credentials.")

class GoProAPIClient:
    """Handles all API interactions with GoPro"""
    def __init__(self, access_token: str, user_id: str, config: Config):
        self.config = config
        self.cookies = {
            "gp_access_token": access_token,
            "gp_user_id": user_id
        }
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/vnd.gopro.jk.media.search+json; version=2.0.0",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
            "Origin": "https://gopro.com",
            "Referer": "https://gopro.com/"
        }
    
    def get_media_items(self, page: int = 1) -> Dict:
        """Fetch media items with pagination"""
        types = "Burst,BurstVideo,Continuous,LoopedVideo,TimeLapse,TimeLapseVideo,Video"
        if self.config.INCLUDE_PHOTOS:
            types += ",Photo"
            
        params = {
            "processing_states": "rendering,pretranscoding,transcoding,stabilizing,ready,failure",
            "fields": "camera_model,captured_at,content_title,content_type,created_at,gopro_user_id,gopro_media,filename,file_extension,file_size,height,fov,id,item_count,mce_type,moments_count,on_public_profile,orientation,play_as,ready_to_edit,ready_to_view,resolution,source_duration,token,type,width,stabilized,submitted_at,thumbnail_available,captured_at_timezone,available_labels",
            "type": types,
            "page": page,
            "per_page": self.config.PAGE_SIZE
        }
        
        response = requests.get(
            f"{self.config.BASE_URL}/media/search",
            params=params,
            headers=self._get_headers(),
            cookies=self.cookies
        )
        
        response.raise_for_status()
        return response.json()
    
    def get_download_info(self, media_id: str) -> Dict:
        """Get download information for a media item"""
        response = requests.get(
            f"{self.config.BASE_URL}/media/{media_id}/download",
            headers=self._get_headers(),
            cookies=self.cookies
        )
        response.raise_for_status()
        return response.json()
    
    def get_video_highlights(self, video_id: str) -> Optional[Dict]:
        """Fetch HiLight moments for a video"""
        response = requests.get(
            f"{self.config.BASE_URL}/media/{video_id}/moments?fields=time&per_page=100",
            headers=self._get_headers(),
            cookies=self.cookies
        )
        response.raise_for_status()
        return response.json()

class MediaDownloader:
    """Handles downloading and processing of media files"""
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

class GPMFProcessor:
    """Handles GPMF data extraction and processing"""
    @staticmethod
    def extract_gpmf_data(video_path: Path) -> Optional[List[Dict]]:
        """Extract GPMF data and find HiLight moments"""
        try:
            # Get stream info
            stream_info = GPMFProcessor._get_stream_info(video_path)
            if not stream_info:
                return None
            
            # Extract GPMF data
            gpmf_data = GPMFProcessor._extract_gpmf_stream(video_path, stream_info['index'])
            
            # Parse HiLight tags
            return GPMFProcessor._parse_highlights(gpmf_data)
            
        except Exception as e:
            logger.error(f"Error extracting GPMF data: {e}")
            return None
    
    @staticmethod
    def _get_stream_info(video_path: Path) -> Optional[Dict]:
        """Get GPMF stream information using ffprobe"""
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-show_format',
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        for stream in data.get('streams', []):
            if stream.get('codec_tag_string') == 'gpmd':
                return stream
        return None
    
    @staticmethod
    def _extract_gpmf_stream(video_path: Path, stream_index: int) -> bytes:
        """Extract GPMF stream data using ffmpeg"""
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-map', f'0:{stream_index}',
            '-codec', 'copy',
            '-f', 'data',
            '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True)
        return result.stdout
    
    @staticmethod
    def _parse_highlights(gpmf_data: bytes) -> List[Dict]:
        """Parse GPMF data for HiLight tags"""
        highlights = []
        for i in range(len(gpmf_data) - 4):
            if gpmf_data[i:i+4] == b'HLMT':
                highlights.append({
                    'offset': i,
                    'timestamp': None
                })
        return highlights

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
            items_response = self.api_client.get_media_items()
            media_items = items_response.get('_embedded', {}).get('media', [])
            logger.info(f"Found {len(media_items)} media items")
            
            existing_items = 0
            for media_item in media_items:
                if self._process_single_item(media_item, download_gpmf):
                    existing_items += 1
            
            if existing_items > 0:
                logger.info(f"Skipped downloading {existing_items} existing items")
                
        except Exception as e:
            logger.error(f"Error processing media items: {e}")
            raise
    
    def _process_single_item(self, media_item: Dict, download_gpmf: bool) -> bool:
        """Process a single media item, returns True if item already existed"""
        filename = Path(media_item['filename']).with_suffix('').name
        extension = media_item['file_extension'].lower()
        
        # Handle highlights
        if media_item['moments_count'] > 0:
            self._save_highlights(media_item, filename)
        
        # Save metadata
        self._save_metadata(media_item, filename)
        
        # Download media
        media_path = self.output_dir / f"{filename}.{extension}"
        if media_path.exists():
            return True
            
        self.downloader.download_media(media_item, media_path, download_gpmf)
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

def main():
    parser = argparse.ArgumentParser(description="GoPro Media Downloader and GPMF Extractor")
    parser.add_argument('-o', '--output-folder', type=str, default='gopro_downloads',
                      help="Path to the output folder")
    parser.add_argument('--download-gpmf', action='store_true',
                      help="Opt into downloading GPMF and extracting its data")
    parser.add_argument('--extract-gpmf', type=str,
                      help="Path to the video file to extract GPMF data from")
    parser.add_argument('-p', '--photos', action='store_true',
                      help="Include photos")
    args = parser.parse_args()

    # Initialize configuration
    config = Config(INCLUDE_PHOTOS=args.photos)
    config_manager = ConfigManager()
    creds = config_manager.load_credentials()
    
    # Handle GPMF extraction request
    if args.extract_gpmf:
        video_path = Path(args.extract_gpmf)
        highlights = GPMFProcessor.extract_gpmf_data(video_path)
        if highlights:
            logger.info(f"Found {len(highlights)} HiLight tags")
        else:
            logger.info("No HiLight tags found")
        return

    # Initialize components
    api_client = GoProAPIClient(creds['access_token'], creds['user_id'], config)
    downloader = MediaDownloader(api_client)
    processor = MediaProcessor(api_client, downloader, Path(args.output_folder))
    
    # Process media items
    processor.process_media_items(args.download_gpmf)

if __name__ == "__main__":
    main()