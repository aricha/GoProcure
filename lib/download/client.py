import json
import logging
import requests
from typing import Dict, Optional
from pathlib import Path
from .constants import Config

logger = logging.getLogger(__name__)

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
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
            "Origin": "https://gopro.com",
            "Referer": "https://gopro.com/"
        }
    
    def get_media_items(self, page: int = 1) -> Dict:
        """Fetch media items with pagination"""
        types = "Burst,BurstVideo,Continuous,LoopedVideo,TimeLapse,TimeLapseVideo,Video"
        if self.config.INCLUDE_PHOTOS:
            types += ",Photo"
            
        params = {
            "processing_states": "ready,failure",
            "fields": "camera_model,captured_at,file_extension,filename,id,moments_count",
            "type": types,
            "page": page,
            "per_page": min(self.config.MAX_ITEMS, self.config.PAGE_SIZE)
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
    
    def get_video_highlights(self, video_id: str) -> Dict:
        """Fetch HiLight moments for a video"""
        response = requests.get(
            f"{self.config.BASE_URL}/media/{video_id}/moments",
            headers=self._get_headers(),
            cookies=self.cookies
        )
        response.raise_for_status()
        return response.json()