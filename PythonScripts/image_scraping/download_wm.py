import os
import requests
import time

def download_wikimedia_images(query, total_images=100, output_dir="trump_photos"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    endpoint = "https://commons.wikimedia.org/w/api.php"
    
    downloaded = 0
    continue_token = None
    
    headers = {
        'User-Agent': 'TrumpImageScraper/1.0 (https://example.org/scraper; scraper@example.org) Python/3.14'
    }

    while downloaded < total_images:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6, # Files
            "gsrlimit": min(50, total_images - downloaded),
            "prop": "imageinfo",
            "iiprop": "url",
            "imlimit": "max"
        }
        
        if continue_token:
            params.update(continue_token)

        response = requests.get(endpoint, params=params, headers=headers)
        if response.status_code != 200:
            print("Failed to fetch API")
            break
            
        data = response.json()
        
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            print("No pages found")
            break
            
        for page_id, page_data in pages.items():
            if downloaded >= total_images:
                break
                
            imageinfo = page_data.get("imageinfo")
            if not imageinfo:
                continue
                
            image_url = imageinfo[0].get("url")
            if not image_url:
                continue
                
            if not (image_url.lower().endswith('.jpg') or image_url.lower().endswith('.png') or image_url.lower().endswith('.jpeg')):
                continue
                
            try:
                print(f"Downloading {image_url}")
                img_response = requests.get(image_url, headers=headers, timeout=10)
                if img_response.status_code == 200:
                    ext = image_url.split('.')[-1].lower()
                    filepath = os.path.join(output_dir, f"trump_wm_{downloaded+1}.{ext}")
                    with open(filepath, 'wb') as f:
                        f.write(img_response.content)
                    downloaded += 1
            except Exception as e:
                print(f"Error downloading {image_url}: {e}")
                
        if "continue" in data and downloaded < total_images:
            continue_token = data["continue"]
        else:
            break
            
    print(f"Successfully downloaded {downloaded} images from Wikimedia Commons.")

if __name__ == "__main__":
    download_wikimedia_images("特朗普", total_images=10)
