"""
Web Scraper Node for ComfyUI
Allows users to scrape images from Pixabay, Unsplash, and Freepik
with configurable parameters through a drawer UI
"""

from __future__ import annotations

import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any
from typing_extensions import override

from comfy_api.latest import ComfyExtension, io

logger = logging.getLogger(__name__)


class WebScraperNode(io.ComfyNode):
    """
    Web Scraper Node - Opens a drawer UI for scraping images
    This node appears in its own "WebScraper" category in the sidebar
    """
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="WebScraper",
            display_name="Web Image Scraper",
            category="webscraper",
            inputs=[
                io.String.Input(
                    "scraper_id",
                    default="",
                    tooltip="Internal ID for scraper session (auto-generated)"
                )
            ],
            outputs=[
                io.String.Output(
                    display_name="status",
                    tooltip="Scraping status and results"
                )
            ],
        )
    
    @classmethod
    def execute(cls, scraper_id: str) -> io.NodeOutput:
        """
        This node primarily serves as a UI trigger.
        The actual scraping happens via API calls from the drawer UI.
        """
        return io.NodeOutput(f"Scraper session: {scraper_id}")


# Store active scraping sessions
_scraping_sessions: Dict[str, Dict[str, Any]] = {}


def get_scraping_session(session_id: str) -> Dict[str, Any]:
    """Get or create a scraping session"""
    if session_id not in _scraping_sessions:
        _scraping_sessions[session_id] = {
            "status": "idle",
            "progress": 0,
            "current_step": "",
            "total_images": 0,
            "scraped_images": 0,
            "errors": []
        }
    return _scraping_sessions[session_id]


async def start_scraping(
    session_id: str,
    query: str,
    source: str,
    category: str,
    min_width: int,
    min_height: int,
    aspect_ratio: str,
    max_images: int,
    tags: list,
    api_key: str = None,
    exclude_ai: bool = True,
    photos_only: bool = True
) -> Dict[str, Any]:
    """
    Start the scraping process
    This is called from the API route
    """
    session = get_scraping_session(session_id)
    session["status"] = "scraping"
    session["progress"] = 0
    session["current_step"] = "Initializing scraper..."
    session["total_images"] = max_images
    session["scraped_images"] = 0
    session["errors"] = []
    
    try:
        # Import library manager
        try:
            from .library_manager import add_image_to_library
        except ImportError:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent))
            from library_manager import add_image_to_library
        
        import requests
        import platform
        from pathlib import Path
        import time
        
        # Create download directory - use the same path as library_manager
        try:
            from .library_manager import DEFAULT_LIBRARY_PATH
        except ImportError:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent))
            from library_manager import DEFAULT_LIBRARY_PATH
        
        download_dir = Path(DEFAULT_LIBRARY_PATH) / "scraped_images"
        download_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Download directory: {download_dir}")
        
        session["current_step"] = f"Connecting to {source}..."
        session["progress"] = 10
        
        scraped_count = 0
        
        # Set API key from parameter
        if api_key:
            if source == "freepik":
                os.environ["FREEPIK_API_KEY"] = api_key
            elif source == "pixabay":
                os.environ["PIXABAY_API_KEY"] = api_key
            elif source == "unsplash":
                os.environ["UNSPLASH_ACCESS_KEY"] = api_key
        
        # Helper function to get image URL from APIs
        # Note: exclude_ai and photos_only are captured from outer scope
        def get_image_url_from_api(source_name, search_query, page_num, per_page=1):
            """Get image URL from various APIs"""
            try:
                if source_name == "freepik":
                    # Freepik API - requires API key
                    api_key = os.getenv("FREEPIK_API_KEY", "")
                    if not api_key:
                        logger.error("Freepik API key not set!")
                        return None
                    
                    # Freepik API endpoint for searching
                    # Documentation: https://docs.freepik.com/api-reference/resources/get-all-resources
                    url = f"https://api.freepik.com/v1/resources"
                    headers = {
                        "x-freepik-api-key": api_key
                    }
                    params = {
                        "term": search_query,  # Note: Freepik uses "term" not "search"
                        "page": page_num + 1,
                        "limit": per_page,
                        "order": "relevance"  # Order by relevance
                    }
                    
                    # Note: Freepik API filters parameter format is not well documented
                    # We'll rely primarily on client-side filtering and only try API filters if they work
                    # For now, skip API-level filters and do all filtering client-side
                    # This ensures we get results even if the API doesn't support the filter format
                    
                    logger.info(f"Freepik API request: search='{search_query}', page={page_num + 1}, exclude_ai={exclude_ai}, photos_only={photos_only}")
                    logger.info(f"Request params: {params}")
                    response = requests.get(url, headers=headers, params=params, timeout=10)
                    logger.info(f"Freepik API response status: {response.status_code}")
                    
                    # Check for API errors
                    if response.status_code != 200:
                        logger.error(f"Freepik API error {response.status_code}: {response.text[:500]}")
                        if response.status_code == 400:
                            logger.error("Bad request - check if filters parameter format is correct")
                        return None
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            logger.info(f"Freepik API response structure: {list(data.keys())}")
                            
                            # Freepik returns data in 'data' field
                            resources = data.get("data", [])
                            logger.info(f"Freepik API returned {len(resources)} resources")
                            
                            if len(resources) == 0:
                                logger.warning(f"No resources returned from API. Response: {json.dumps(data, indent=2)[:500]}")
                                return None
                        except Exception as e:
                            logger.error(f"Error parsing API response: {e}")
                            logger.error(f"Response text: {response.text[:500]}")
                            return None
                        
                        # Client-side filtering (backup to API filters)
                        photo_resources = []
                        for res in resources:
                            image_type = res.get("image", {}).get("type", "")
                            title = res.get("title", "").lower()
                            url = res.get("url", "").lower()
                            filename = res.get("filename", "").lower()
                            
                            # Check if it's a photo
                            is_photo = image_type == "photo"
                            
                            # If photos_only is enabled, skip non-photos (but allow if type is empty/unknown)
                            if photos_only:
                                if image_type and image_type not in ["", None, "photo"]:
                                    logger.info(f"✗ Skipping {res.get('id')} - not a photo (type: {image_type})")
                                    continue
                                # If type is empty/None, we'll check other indicators below
                            
                            # Exclude AI-generated images if exclude_ai is enabled
                            if exclude_ai:
                                is_ai_generated = (
                                    "ai" in title or 
                                    "ai-generated" in title or
                                    "ai-generated" in url or
                                    "ai-generated" in filename or
                                    ("generated" in title and ("ai" in title or "artificial" in title or "machine" in title)) or
                                    "midjourney" in title or
                                    "dall-e" in title or
                                    "stable diffusion" in title or
                                    "/ai-" in url or  # Freepik AI images often have /ai- in URL
                                    "ai-image" in url
                                )
                                
                                # Check author - some AI generators have specific author names
                                author = res.get("author", {})
                                author_name = author.get("name", "").lower() if author else ""
                                author_slug = author.get("slug", "").lower() if author else ""
                                is_ai_author = (
                                    "ai" in author_name or 
                                    "generator" in author_name or
                                    "ai" in author_slug
                                )
                                
                                # Check URL pattern for AI
                                is_ai_url = "/ai-generated/" in url or "/ai-" in url
                                
                                if is_ai_generated or is_ai_author or is_ai_url:
                                    logger.info(f"✗ Skipping {res.get('id')} - AI-generated content detected")
                                    continue
                            
                            # Exclude vectors, icons, illustrations, animations if photos_only is enabled
                            if photos_only:
                                is_vector_like = (
                                    "vector" in title or
                                    "icon" in title or
                                    "illustration" in title or
                                    "drawing" in title or
                                    "cartoon" in title or
                                    "animated" in title or
                                    "animation" in title or
                                    "gif" in filename or
                                    "/free-vector" in url or
                                    "/free-icon" in url or
                                    image_type == "vector" or
                                    image_type == "icon"
                                )
                                
                                if is_vector_like:
                                    logger.info(f"✗ Skipping {res.get('id')} - vector/animation-like content")
                                    continue
                            
                            # Accept this resource
                            photo_resources.append(res)
                            logger.info(f"✓ ACCEPTED photo {res.get('id')}: '{res.get('title', 'N/A')[:60]}' (type: {image_type})")
                        
                        logger.info(f"=== FILTERING SUMMARY ===")
                        logger.info(f"Total resources returned: {len(resources)}")
                        logger.info(f"Photos found after filtering: {len(photo_resources)}")
                        logger.info(f"Filter settings: exclude_ai={exclude_ai}, photos_only={photos_only}")
                        logger.info(f"Skipped: {len(resources) - len(photo_resources)} resources")
                        
                        if len(photo_resources) == 0:
                            if len(resources) > 0:
                                logger.warning(f"⚠️  No photos found! All {len(resources)} results were filtered out.")
                                logger.warning(f"   Sample of what was returned:")
                                for idx, res in enumerate(resources[:5]):  # Show first 5 for debugging
                                    img_type = res.get('image', {}).get('type', 'unknown')
                                    logger.warning(f"   [{idx+1}] ID: {res.get('id')}, Type: {img_type}, Title: {res.get('title', 'N/A')[:50]}")
                                    logger.warning(f"       URL: {res.get('url', 'N/A')[:100]}")
                                logger.warning(f"   Filter settings: exclude_ai={exclude_ai}, photos_only={photos_only}")
                                logger.warning(f"   Try: 1) Unchecking 'Exclude AI' or 'Photos only' 2) Different search term")
                            else:
                                logger.error(f"⚠️  No resources returned from Freepik API!")
                                logger.error(f"   Check: 1) API key is valid 2) Search query returns results 3) Network connection")
                            return None
                        
                        if photo_resources and len(photo_resources) > 0:
                            resource = photo_resources[0]
                            logger.info(f"Selected photo resource ID: {resource.get('id')}, Title: {resource.get('title', 'N/A')}")
                            
                            resource_id = resource.get("id")
                            logger.info(f"Resource ID: {resource_id}")
                            
                            if resource_id:
                                # Check available formats first
                                available_formats = resource.get("meta", {}).get("available_formats", {})
                                logger.info(f"Available formats for resource {resource_id}: {list(available_formats.keys())}")
                                
                                # Get download URL for this resource - try to get highest resolution
                                download_url = f"https://api.freepik.com/v1/resources/{resource_id}/download"
                                logger.info(f"Requesting download URL from: {download_url}")
                                download_response = requests.get(download_url, headers=headers, timeout=10)
                                logger.info(f"Download response status: {download_response.status_code}")
                                
                                if download_response.status_code == 200:
                                    download_data = download_response.json()
                                    logger.info(f"Download response structure: {list(download_data.keys())}")
                                    logger.info(f"Full download response: {json.dumps(download_data, indent=2)[:1000]}...")
                                    
                                    # Try to find the best URL from the response
                                    image_url = None
                                    if "data" in download_data:
                                        data = download_data["data"]
                                        if isinstance(data, dict):
                                            # Try various URL fields in order of preference
                                            image_url = (
                                                data.get("url") or 
                                                data.get("signed_url") or 
                                                data.get("download_url") or
                                                data.get("high_res_url")
                                            )
                                        elif isinstance(data, list) and len(data) > 0:
                                            # If data is a list, get the first item's URL
                                            first_item = data[0]
                                            if isinstance(first_item, dict):
                                                image_url = first_item.get("url") or first_item.get("signed_url")
                                    
                                    if image_url:
                                        logger.info(f"✓ Got Freepik download URL: {image_url[:150]}...")
                                        return image_url
                                    else:
                                        logger.warning(f"Download URL not found in response. Full data: {json.dumps(download_data, indent=2)[:500]}")
                                elif download_response.status_code == 402:
                                    logger.warning("⚠️ Freepik download requires premium subscription for full resolution")
                                    logger.warning("Using preview image instead (smaller resolution)")
                                elif download_response.status_code == 403:
                                    logger.warning("⚠️ Access forbidden - API key may not have download permissions")
                                else:
                                    logger.error(f"✗ Download request failed: {download_response.status_code} - {download_response.text[:300]}")
                            
                            # Fallback: try to get image URL directly from resource
                            # Freepik API structure: resource.image.source.url
                            image_obj = resource.get("image", {})
                            if image_obj:
                                source_obj = image_obj.get("source", {})
                                if source_obj:
                                    image_url = source_obj.get("url")
                                    if image_url:
                                        logger.info(f"✓ Using Freepik image.source.url: {image_url[:100]}...")
                                        return image_url
                            
                            # Last resort: try other possible fields
                            image_url = resource.get("url") or resource.get("image_url") or resource.get("preview_url") or resource.get("thumbnail_url")
                            if image_url:
                                logger.info(f"Using Freepik resource URL (fallback): {image_url[:100]}...")
                                return image_url
                            else:
                                logger.error(f"✗ No image URL found in resource. Available keys: {list(resource.keys())}")
                                logger.error(f"✗ Full resource structure: {json.dumps(resource, indent=2)[:2000]}")
                        elif len(photo_resources) == 0:
                            logger.warning(f"No photo resources found (found {len(resources)} total resources, but none are photos)")
                            logger.warning(f"Resource types found: {[r.get('image', {}).get('type', 'unknown') for r in resources[:5]]}")
                        else:
                            logger.warning("No resources returned from Freepik API")
                            logger.warning(f"Full API response: {json.dumps(data, indent=2)[:1000]}")
                    elif response.status_code == 401:
                        logger.error("Freepik API key is invalid or unauthorized. Check your API key.")
                    elif response.status_code == 429:
                        logger.error("Freepik rate limit reached.")
                    else:
                        logger.error(f"Freepik API error: {response.status_code} - {response.text[:200]}")
                    return None
                    
                elif source_name == "pixabay":
                    # Pixabay API requires a key - Get free API key from https://pixabay.com/api/docs/
                    api_key = os.getenv("PIXABAY_API_KEY", "")
                    if not api_key:
                        logger.error("Pixabay API key not set! Set PIXABAY_API_KEY environment variable.")
                        logger.error("Get a free key at: https://pixabay.com/api/docs/")
                        return None
                    
                    # Build URL with filters
                    url = f"https://pixabay.com/api/?key={api_key}&q={search_query}&image_type=photo&per_page={per_page}&page={page_num + 1}"
                    if min_width > 0:
                        url += f"&min_width={min_width}"
                    if min_height > 0:
                        url += f"&min_height={min_height}"
                    
                    logger.info(f"Pixabay API request: {url.replace(api_key, 'KEY_HIDDEN')}")
                    response = requests.get(url, timeout=10)
                    logger.info(f"Pixabay API response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"Pixabay API returned {len(data.get('hits', []))} hits")
                        if data.get("hits") and len(data["hits"]) > 0:
                            # Get the largest image available
                            hit = data["hits"][0]
                            image_url = hit.get("largeImageURL") or hit.get("webformatURL") or hit.get("previewURL")
                            logger.info(f"Selected image URL: {image_url}")
                            return image_url
                        else:
                            logger.warning("No hits returned from Pixabay API")
                    elif response.status_code == 429:
                        logger.error("Pixabay rate limit reached. Wait a minute or use a different API key.")
                    elif response.status_code == 400:
                        logger.error("Pixabay API error: Bad request. Check your API key and query.")
                        try:
                            error_data = response.json()
                            logger.error(f"Pixabay error details: {error_data}")
                        except:
                            pass
                    else:
                        logger.error(f"Pixabay API returned status {response.status_code}: {response.text[:200]}")
                    return None
                    
                elif source_name == "unsplash":
                    # Unsplash provides FREE high-resolution images!
                    # Register at https://unsplash.com/developers to get a free API key
                    access_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
                    if not access_key:
                        logger.warning("Unsplash API key not set. Set UNSPLASH_ACCESS_KEY environment variable.")
                        logger.warning("Register at https://unsplash.com/developers to get a FREE API key.")
                        logger.warning("Unsplash provides HIGH RESOLUTION images for free!")
                        return None
                    
                    url = f"https://api.unsplash.com/search/photos?query={search_query}&page={page_num + 1}&per_page=1&orientation=landscape"
                    headers = {"Authorization": f"Client-ID {access_key}"}
                    
                    logger.info(f"Unsplash API request: query='{search_query}', page={page_num + 1}")
                    response = requests.get(url, headers=headers, timeout=10)
                    logger.info(f"Unsplash API response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        total_results = data.get("total", 0)
                        results = data.get("results", [])
                        logger.info(f"Unsplash API returned {len(results)} results (total: {total_results})")
                        
                        if results and len(results) > 0:
                            result = results[0]
                            urls = result.get("urls", {})
                            
                            # Get the highest resolution available
                            # Order: raw > full > regular > small > thumb
                            # raw = original upload, full = high quality, regular = 1080px wide
                            image_url = (
                                urls.get("full") or      # High quality (usually 2000-4000px)
                                urls.get("regular") or   # 1080px wide
                                urls.get("raw")          # Original (can be very large)
                            )
                            
                            if image_url:
                                # Get image dimensions from response
                                width = result.get("width", "?")
                                height = result.get("height", "?")
                                logger.info(f"✓ Unsplash image: {width}x{height} - {image_url[:100]}...")
                                return image_url
                            else:
                                logger.warning(f"No URL found in Unsplash result: {urls}")
                        else:
                            logger.warning(f"No results from Unsplash for query: {search_query}")
                    elif response.status_code == 401:
                        logger.error("Unsplash API key is invalid. Check your UNSPLASH_ACCESS_KEY.")
                    elif response.status_code == 403:
                        logger.error("Unsplash rate limit exceeded. Try again later.")
                    else:
                        logger.warning(f"Unsplash API returned status {response.status_code}: {response.text[:200]}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error fetching from {source_name} API: {e}")
                return None
        
        # Scrape images
        page_num = 0
        images_per_page = 1  # Get one image per API call
        max_pages_to_try = max_images * 3  # Try up to 3x pages to find photos (in case we hit vectors)
        
        for i in range(max_images):
            if session["status"] == "cancelled":
                break
                
            session["current_step"] = f"Downloading image {i+1}/{max_images} from {source}..."
            session["progress"] = 10 + int((i / max_images) * 80)
            
            # Try multiple pages if needed to find a photo
            image_url = None
            pages_tried = 0
            
            while not image_url and pages_tried < 10:  # Try up to 10 pages to find a photo
                try:
                    # Get image URL from API
                    logger.info(f"Fetching image {i+1} from {source} API (page {page_num + 1}, attempt {pages_tried + 1})...")
                    image_url = get_image_url_from_api(source, query, page_num)
                    
                    if image_url:
                        logger.info(f"✓ Found photo image on page {page_num + 1}")
                        break
                    else:
                        logger.info(f"No photo found on page {page_num + 1}, trying next page...")
                        page_num += 1
                        pages_tried += 1
                        await asyncio.sleep(0.2)  # Small delay between page requests
                except Exception as e:
                    logger.error(f"Error fetching from page {page_num + 1}: {e}")
                    page_num += 1
                    pages_tried += 1
                    continue
            
            if not image_url:
                error_msg = f"No photo images found from {source} for query '{query}' after trying {pages_tried} pages"
                logger.warning(error_msg)
                session["errors"].append(f"Image {i+1}: {error_msg}")
                page_num += 1
                continue
            
            try:
                logger.info(f"Got image URL: {image_url[:100]}...")
                
                # Download the image
                logger.info(f"Downloading image from: {image_url}")
                
                # For Freepik, we might need to handle redirects or special headers
                headers_for_download = {}
                if source == "freepik":
                    # Some Freepik URLs might need referer or user-agent
                    headers_for_download = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Referer": "https://www.freepik.com/"
                    }
                
                response = requests.get(image_url, headers=headers_for_download, timeout=30, stream=True, allow_redirects=True)
                
                if response.status_code == 200:
                    # Determine file extension from content type or URL
                    content_type = response.headers.get('content-type', '')
                    ext = '.jpg'
                    if 'png' in content_type:
                        ext = '.png'
                    elif 'webp' in content_type:
                        ext = '.webp'
                    elif image_url.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                        ext = os.path.splitext(image_url)[1] or '.jpg'
                    
                    # Create unique filename
                    timestamp = int(time.time())
                    safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).strip()[:20]
                    filename = f"{source}_{safe_query}_{timestamp}_{i}{ext}"
                    image_path = download_dir / filename
                    
                    # Save image
                    with open(image_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    logger.info(f"Saved image to: {image_path}")
                    
                    # Verify image was saved
                    if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
                        # Add to library
                        all_tags = tags.copy() if tags else []
                        all_tags.extend([query, source])
                        
                        logger.info(f"Adding image to library: {image_path}")
                        logger.info(f"  Category: {category}, Tags: {all_tags}, Source: {source}")
                        logger.info(f"  File exists: {os.path.exists(image_path)}, Size: {os.path.getsize(image_path) if os.path.exists(image_path) else 0} bytes")
                        
                        try:
                            success = add_image_to_library(
                                image_path=str(image_path),
                                category=category,
                                tags=all_tags,
                                source=source
                            )
                            
                            logger.info(f"add_image_to_library returned: {success}")
                            
                            if success:
                                scraped_count += 1
                                session["scraped_images"] = scraped_count
                                logger.info(f"✓ Successfully added image {i+1} to library: {filename}")
                            else:
                                logger.error(f"✗ add_image_to_library returned False for {image_path}")
                                session["errors"].append(f"Image {i+1}: Failed to add to library (function returned False)")
                        except Exception as e:
                            logger.error(f"✗ Exception calling add_image_to_library: {e}", exc_info=True)
                            session["errors"].append(f"Image {i+1}: Exception adding to library: {str(e)}")
                    else:
                        logger.error(f"Image file not saved properly: {image_path}")
                        session["errors"].append(f"Image {i+1}: File save failed")
                else:
                    logger.error(f"Failed to download image: HTTP {response.status_code}")
                    logger.error(f"Response headers: {dict(response.headers)}")
                    logger.error(f"Response text (first 500 chars): {response.text[:500]}")
                    session["errors"].append(f"Image {i+1}: Download failed (HTTP {response.status_code})")
                
                # Move to next page for next image
                page_num += 1
                await asyncio.sleep(0.5)  # Small delay between requests
                
            except Exception as e:
                logger.error(f"Error scraping image {i+1}: {e}", exc_info=True)
                session["errors"].append(f"Image {i+1}: {str(e)}")
                page_num += 1
                continue
        
        session["status"] = "completed"
        session["progress"] = 100
        session["current_step"] = f"Completed! Scraped {scraped_count} images."
        
        logger.info(f"Scraping completed: {scraped_count}/{max_images} images successfully added to library")
        
        return {
            "success": True,
            "scraped_count": scraped_count,
            "message": f"Successfully scraped {scraped_count} images and added to library"
        }
        
    except Exception as e:
        logger.error(f"Scraping error: {e}", exc_info=True)
        session["status"] = "error"
        session["current_step"] = f"Error: {str(e)}"
        session["errors"].append(str(e))
        return {
            "success": False,
            "error": str(e)
        }


def cancel_scraping(session_id: str) -> Dict[str, Any]:
    """Cancel an active scraping session"""
    if session_id in _scraping_sessions:
        _scraping_sessions[session_id]["status"] = "cancelled"
        return {"success": True, "message": "Scraping cancelled"}
    return {"success": False, "error": "Session not found"}


def get_scraping_status(session_id: str) -> Dict[str, Any]:
    """Get the current status of a scraping session"""
    if session_id in _scraping_sessions:
        return _scraping_sessions[session_id]
    return {"error": "Session not found"}
