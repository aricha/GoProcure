from dataclasses import dataclass

@dataclass
class Config:
    """Configuration settings for the application"""
    PAGE_SIZE: int = 100
    MAX_ITEMS: int = 1000
    INCLUDE_PHOTOS: bool = False
    BASE_URL: str = "https://api.gopro.com"