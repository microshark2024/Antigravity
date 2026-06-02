import os
import requests
import time

def download_wikimedia_videos(query, total_videos=10, output_dir="trump_videos"):
    """
    Search and download videos from Wikimedia Commons matching the query.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    endpoint = "https://commons.wikimedia.org/w/api.php"
    downloaded = 0
    continue_token = None
    
    headers = {
        'User-Agent': 'TrumpVideoScraper/1.0 (https://example.org/scraper; scraper@example.org) Python/3.14'
    }

    print(f"Searching for videos of '{query}' on Wikimedia Commons...")

    # We will search multiple pages if needed, but since videos are less common than photos,
    # we increase the gsrlimit to get a broader list of candidate files.
    while downloaded < total_videos:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6, # Files
            "gsrlimit": 80,    # Search more files per page to find enough videos
            "prop": "imageinfo",
            "iiprop": "url",
            "imlimit": "max"
        }
        
        if continue_token:
            params.update(continue_token)

        try:
            response = requests.get(endpoint, params=params, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"Failed to fetch API: HTTP {response.status_code}")
                break
        except Exception as e:
            print(f"Request error: {e}")
            break
            
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            print("No more pages found matching the query.")
            break
            
        for page_id, page_data in pages.items():
            if downloaded >= total_videos:
                break
                
            imageinfo = page_data.get("imageinfo")
            if not imageinfo:
                continue
                
            video_url = imageinfo[0].get("url")
            if not video_url:
                continue
                
            # Filter for common video extensions
            video_url_lower = video_url.lower()
            valid_extensions = ('.webm', '.mp4', '.ogv', '.ogg')
            if not any(video_url_lower.endswith(ext) for ext in valid_extensions):
                continue
                
            try:
                print(f"\n[{downloaded + 1}/{total_videos}] Downloading: {video_url}")
                
                # Start downloading the video stream to save memory
                img_response = requests.get(video_url, headers=headers, stream=True, timeout=30)
                if img_response.status_code == 200:
                    ext = video_url.split('.')[-1].lower()
                    filename = f"trump_video_{downloaded+1}.{ext}"
                    filepath = os.path.join(output_dir, filename)
                    
                    # Log size if available
                    total_size = int(img_response.headers.get('content-length', 0))
                    if total_size > 0:
                        print(f"Size: {total_size / (1024 * 1024):.2f} MB")
                    
                    with open(filepath, 'wb') as f:
                        for chunk in img_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                
                    print(f"Saved to: {filepath}")
                    downloaded += 1
                    # Polite delay between downloads
                    time.sleep(1)
                else:
                    print(f"Failed to download video (HTTP {img_response.status_code})")
            except Exception as e:
                print(f"Error downloading {video_url}: {e}")
                
        if "continue" in data and downloaded < total_videos:
            continue_token = data["continue"]
        else:
            break
            
    print(f"\nSuccessfully downloaded {downloaded}/{total_videos} videos from Wikimedia Commons.")

if __name__ == "__main__":
    download_wikimedia_videos("Donald Trump", total_videos=10)
