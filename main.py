PAGE_SIZE = 50
ACCESS_TOKEN = "***REMOVED***
USER_ID = "***REMOVED***"
INCLUDE_PHOTOS = False

import requests
import json
from datetime import datetime
import os
from pathlib import Path

class GoProAPI:
    def __init__(self, access_token, user_id):
        self.base_url = "https://api.gopro.com"
        self.cookies = {
            "gp_access_token": access_token,
            "gp_user_id": user_id
        }
    
    def get_headers(self):
        return {
            "Accept": "application/vnd.gopro.jk.media.search+json; version=2.0.0",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
            "Origin": "https://gopro.com",
            "Referer": "https://gopro.com/"
        }
    
    def get_videos(self, page=1, per_page=PAGE_SIZE):
        """Get list of videos with pagination"""
        types = "Burst,BurstVideo,Continuous,LoopedVideo,TimeLapse,TimeLapseVideo,Video"
        if INCLUDE_PHOTOS:
            types += ",Photo"
        
        params = {
            "processing_states": "rendering,pretranscoding,transcoding,stabilizing,ready,failure",
            "fields": "camera_model,captured_at,content_title,content_type,created_at,gopro_user_id,gopro_media,filename,file_extension,file_size,height,fov,id,item_count,mce_type,moments_count,on_public_profile,orientation,play_as,ready_to_edit,ready_to_view,resolution,source_duration,token,type,width,stabilized,submitted_at,thumbnail_available,captured_at_timezone,available_labels",
            "type": types,
            "page": page,
            "per_page": per_page
        }
        
        response = requests.get(
            f"{self.base_url}/media/search",
            params=params,
            headers=self.get_headers(),
            cookies=self.cookies
        )
        
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
            raise Exception(f"Failed to get videos: {response.status_code}")
            
        return response.json()

    def download_media(self, media_item, item_path):
        """Download both the video and its GPMF data"""
        # Get download info
        response = requests.get(
            f"{self.base_url}/media/{media_item['id']}/download",
            headers=self.get_headers(),
            cookies=self.cookies
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get download URL: {response.status_code} {response.text}")
        
        response_json = response.json()
        
        # Download main video file
        video_url = response_json.get('_embedded', {}).get('files', [{}])[0].get('url')
        if video_url:
            self._download_file(video_url, item_path)
        
        # print("JSON: ", json.dumps(response_json, indent=2, sort_keys=True))  # sort_keys=True is optional but makes it even more readable

        # Download GPMF data if available
        gpmf_url = self.get_gpmf_url(response_json)
        if gpmf_url:
            p = Path(item_path)
            gpmf_path = p.with_name(f"{p.stem}_gpmf{p.suffix}")
            self._download_file(gpmf_url, gpmf_path)

            if gpmf_path.exists():
                highlights = self.extract_gpmf_data(gpmf_path)
                if highlights:
                    print(f"Found {len(highlights)} HiLight tags")

    def _download_file(self, url, output_path):
        """Helper method to download a file with progress indicator"""
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
                    print(f"\rDownloading {output_path}: {percentage}%", end="")
        print()  # New line after completion

    def get_gpmf_url(self, response_json):
        """Extract the GPMF sidecar file URL from the download response"""
        sidecar_files = response_json.get('_embedded', {}).get('sidecar_files', [])
        for file in sidecar_files:
            if file.get('label') == 'gpmf':
                return file.get('url')
        return None

    def extract_gpmf_data(self, video_path):
        """Extract GPMF data from MP4 file to find HiLight moments"""
        try:
            # Find the GPMF atom in the MP4
            import subprocess
            import json
            
            # Use ffprobe to get detailed stream info
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
            
            # Look for GPMF stream
            gpmf_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_tag_string') == 'gpmd':
                    gpmf_stream = stream
                    break
            
            if not gpmf_stream:
                print(f"No GPMF stream found in {video_path}")
                return None
                
            # Extract GPMF data
            stream_index = gpmf_stream['index']
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-map', f'0:{stream_index}',
                '-codec', 'copy',
                '-f', 'data',
                '-'
            ]
            
            result = subprocess.run(cmd, capture_output=True)
            gpmf_data = result.stdout
            
            # Now parse the GPMF data
            # HiLight tags are typically marked with 'HLMT' in the GPMF stream
            highlights = []
            for i in range(len(gpmf_data) - 4):
                tag = gpmf_data[i:i+4]
                if tag == b'HLMT':
                    # The timestamp should be nearby in the stream
                    # This is a simplification - proper GPMF parsing would be more complex
                    highlights.append({
                        'offset': i,
                        'timestamp': None  # Would need proper GPMF parsing to get exact timestamp
                    })
            
            return highlights
            
        except Exception as e:
            print(f"Error extracting GPMF data: {e}")
            return None

def main():
    # Initialize API client
    gopro = GoProAPI(ACCESS_TOKEN, USER_ID)
    
    # Create output directory
    output_dir = Path("gopro_downloads")
    output_dir.mkdir(exist_ok=True)
    
    try:
        # Get first page of videos and print the full response to see its structure
        videos = gopro.get_videos(page=1)
        # print("API Response structure:")
        # print(json.dumps(videos, indent=2))
        
        # Process videos based on the actual response structure
        media_items = videos.get('_embedded', {}).get('media', [])
        print(f"Found {len(media_items)} media items")
        
        existing_items = 0
        for media_item in media_items:
            filename = Path(media_item['filename']).with_suffix('').name
            # Determine appropriate file extension
            extension = media_item['file_extension'].lower()

            if media_item['moments_count'] > 0:
                print('Found', media_item['moments_count'], 'HiLight tags in', filename)
            
            # Save metadata
            metadata_path = output_dir / f"{filename}_metadata.json"
            if not metadata_path.exists():
                with open(metadata_path, 'w') as f:
                    json.dump(media_item, f, indent=2)
            
            # Download the media
            media_path = output_dir / f"{filename}.{extension}"
            if not media_path.exists():  # Skip if already downloaded
                gopro.download_media(media_item, media_path)
            else:
                existing_items += 1
        
        if existing_items > 0:
            print("Skipped downloading", existing_items, "existing items")

    except Exception as e:
        print(f"An error occurred: {e}")
        raise e

if __name__ == "__main__":
    main()