# Web Scraper Node Setup

## Overview

This custom node adds a **Web Image Scraper** node in its own **WebScraper** category in the ComfyUI sidebar. It provides a drawer UI for scraping images from Pixabay, Unsplash, and Freepik with configurable parameters.

## Features

✅ **Drawer UI** - Beautiful slide-out drawer interface  
✅ **Progress Tracking** - Real-time progress bar and status updates  
✅ **Configurable Parameters**:
   - Search query
   - Source (Pixabay/Unsplash/Freepik)
   - Category
   - Resolution (min width/height)
   - Aspect ratio
   - Max images
   - Tags

✅ **Automatic Library Integration** - Scraped images are automatically added to the library  
✅ **Load from Library** - The existing "Load Image from Library" node can load scraped images

## How to Use

1. **Add the Node**: 
   - Right-click in ComfyUI
   - Look for **"WebScraper"** category in the sidebar
   - Add **"Web Image Scraper"** node

2. **Open the Drawer**:
   - Click the "Open Scraper" button on the node
   - Or the drawer opens automatically when you add the node

3. **Configure Scraping**:
   - Enter search query (e.g., "sunset", "mountains")
   - Select source (Pixabay/Unsplash/Freepik)
   - Choose category
   - Set resolution requirements
   - Choose aspect ratio
   - Set max number of images
   - Add tags (optional)

4. **Start Scraping**:
   - Click "Start Scraping"
   - Watch progress in real-time
   - Images are automatically added to the library

5. **Load Images**:
   - Use the "Load Image from Library" node
   - Filter by category, tags, or search query
   - Scraped images will appear in results

## File Structure

```
ks-cn-web-scraper1/
├── webscraper_workflow.py    # Main node definitions
├── web_scraper_node.py       # Web scraper node with drawer
├── library_manager.py        # Library management utilities
├── web/
│   ├── web_scraper.js        # Drawer UI (development)
│   └── web_scraper.min.js    # Drawer UI (minified)
└── __init__.py
```

## API Endpoints

The node creates these API endpoints:

- `POST /webscraper/start` - Start a scraping session
- `POST /webscraper/cancel/{session_id}` - Cancel a session
- `GET /webscraper/status/{session_id}` - Get scraping status

## Implementation Notes

⚠️ **Important**: The current implementation includes placeholder code for actual scraping. You need to:

1. **Add API Keys**: Get API keys from:
   - Pixabay: https://pixabay.com/api/docs/
   - Unsplash: https://unsplash.com/developers
   - Freepik: https://www.freepik.com/api

2. **Implement Scraping Logic**: 
   - Edit `web_scraper_node.py`
   - Replace the placeholder code in `start_scraping()` function
   - Add actual API calls for each source

3. **Example Implementation**:
   ```python
   # For Pixabay
   api_key = "YOUR_PIXABAY_KEY"
   url = f"https://pixabay.com/api/?key={api_key}&q={query}&image_type=photo&min_width={min_width}&min_height={min_height}&per_page={max_images}"
   response = requests.get(url)
   data = response.json()
   for hit in data["hits"]:
       image_url = hit["largeImageURL"]
       # Download and save image
   ```

## Integration with Load Image from Library

The "Load Image from Library" node automatically works with scraped images because:

1. Scraped images are added to the library database via `library_manager.py`
2. The database stores all metadata (category, tags, source, resolution)
3. The LoadImageFromLibrary node queries this same database
4. No additional configuration needed!

## Troubleshooting

- **Node not appearing**: Restart ComfyUI completely
- **Drawer not opening**: Check browser console for errors
- **Scraping not working**: Implement actual API calls (see above)
- **Images not loading**: Check that images were successfully added to library database

## Next Steps

1. Get API keys from image sources
2. Implement actual scraping logic in `web_scraper_node.py`
3. Test with small batches first
4. Monitor API rate limits
5. Enjoy your curated image library!
