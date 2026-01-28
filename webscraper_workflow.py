"""
Web Scraper Image Library Node for ComfyUI
Loads and searches images from a curated library created by web scrapers
Supports category-based search, keyword search, and machine name detection
"""

from __future__ import annotations

import os
import json
import logging
import platform
import sqlite3
import traceback
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

import numpy as np
import torch
from PIL import Image, ImageSequence, ImageOps
from typing_extensions import override

import folder_paths
import node_helpers
from comfy_api.latest import ComfyExtension, io, ui

# Configure logging FIRST (before any imports that might use it)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import server for API routes (may not be available at import time)
try:
    from server import PromptServer
except ImportError:
    PromptServer = None

# Try to import video stitch nodes
VideoStitchInterpolator = None
VideoStitchMultiple = None
VideoFrameBlender = None
VideoLoopSeamless = None
try:
    from .video_stitch_node import (
        VideoStitchInterpolator,
        VideoStitchMultiple,
        VideoFrameBlender,
        VideoLoopSeamless
    )
    logger.info("Video stitch nodes imported successfully")
except Exception as e:
    logger.warning(f"Could not import video stitch nodes: {e}")
    # Try direct import as fallback
    try:
        import video_stitch_node
        VideoStitchInterpolator = video_stitch_node.VideoStitchInterpolator
        VideoStitchMultiple = video_stitch_node.VideoStitchMultiple
        VideoFrameBlender = video_stitch_node.VideoFrameBlender
        VideoLoopSeamless = video_stitch_node.VideoLoopSeamless
        logger.info("Video stitch nodes imported via direct import")
    except Exception as e2:
        logger.warning(f"Direct import also failed: {e2}")

# Default library path - can be configured
DEFAULT_LIBRARY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
    "image_library"
)

# Generic categories for image organization
DEFAULT_CATEGORIES = [
    "nature", "animals", "people", "architecture", "technology",
    "abstract", "business", "food", "travel", "sports",
    "art", "music", "science", "health", "education",
    "fashion", "vehicles", "landscapes", "cityscapes", "wildlife"
]


class ImageLibraryManager:
    """Manages the image library database and search functionality"""
    
    def __init__(self, library_path: str = DEFAULT_LIBRARY_PATH):
        self.library_path = Path(library_path)
        self.library_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.library_path / "library.db"
        self.metadata_dir = self.library_path / "metadata"
        self.metadata_dir.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for image metadata"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL UNIQUE,
                category TEXT,
                tags TEXT,
                source TEXT,
                resolution_width INTEGER,
                resolution_height INTEGER,
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS machine_names (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id INTEGER,
                machine_name TEXT,
                FOREIGN KEY (image_id) REFERENCES images(id)
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_category ON images(category)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_tags ON images(tags)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_machine_name ON machine_names(machine_name)
        ''')
        
        conn.commit()
        conn.close()
    
    def get_categories(self) -> List[str]:
        """Get all available categories from the database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT category FROM images 
            WHERE category IS NOT NULL AND category != ''
            ORDER BY category
        ''')
        
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # Add default categories if database is empty
        if not categories:
            return DEFAULT_CATEGORIES
        return sorted(list(set(categories + DEFAULT_CATEGORIES)))
    
    def get_machine_names(self) -> List[str]:
        """Extract machine names from the system and database"""
        machine_names = []
        
        # Get system hostname
        hostname = platform.node()
        if hostname:
            machine_names.append(hostname)
        
        # Get machine names from database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT machine_name FROM machine_names WHERE machine_name IS NOT NULL')
        db_names = [row[0] for row in cursor.fetchall()]
        machine_names.extend(db_names)
        conn.close()
        
        return sorted(list(set(machine_names)))
    
    def search_images(
        self,
        category: Optional[str] = None,
        search_query: Optional[str] = None,
        machine_name: Optional[str] = None,
        min_width: Optional[int] = None,
        min_height: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search images in the library"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        query = "SELECT id, filename, filepath, category, tags, source, resolution_width, resolution_height FROM images WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if search_query:
            query += " AND (filename LIKE ? OR tags LIKE ?)"
            search_pattern = f"%{search_query}%"
            params.extend([search_pattern, search_pattern])
        
        if machine_name:
            query += """ AND id IN (
                SELECT image_id FROM machine_names WHERE machine_name = ?
            )"""
            params.append(machine_name)
        
        if min_width:
            query += " AND resolution_width >= ?"
            params.append(min_width)
        
        if min_height:
            query += " AND resolution_height >= ?"
            params.append(min_height)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        images = []
        for row in results:
            images.append({
                "id": row[0],
                "filename": row[1],
                "filepath": row[2],
                "category": row[3],
                "tags": row[4],
                "source": row[5],
                "width": row[6],
                "height": row[7]
            })
        
        return images
    
    def get_image_files(self, search_results: List[Dict[str, Any]]) -> List[str]:
        """Get list of image file paths from search results"""
        files = []
        for result in search_results:
            filepath = result["filepath"]
            if os.path.exists(filepath):
                files.append(filepath)
            else:
                logger.warning(f"Image file not found: {filepath}")
        return files


# Global library manager instance
_library_manager: Optional[ImageLibraryManager] = None

def get_library_manager() -> ImageLibraryManager:
    """Get or create the global library manager instance"""
    global _library_manager
    if _library_manager is None:
        _library_manager = ImageLibraryManager()
    return _library_manager


def load_and_process_image(image_path: str) -> torch.Tensor:
    """Load and process a single image file - matches ComfyUI's LoadImage node"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    img = node_helpers.pillow(Image.open, image_path)
    
    # Handle EXIF orientation (same as ComfyUI's LoadImage)
    img = node_helpers.pillow(ImageOps.exif_transpose, img)
    
    # Handle different image modes (same as ComfyUI's LoadImage)
    if img.mode == "I":
        img = img.point(lambda i: i * (1 / 255))
    
    # Convert to RGB
    image = img.convert("RGB")
    
    # Convert to numpy array and normalize to 0-1 range
    image = np.array(image).astype(np.float32) / 255.0
    
    # Add batch dimension - result is [1, H, W, 3]
    image = torch.from_numpy(image)[None,]
    
    logger.info(f"Loaded image: {image_path}, shape: {image.shape}, dtype: {image.dtype}")
    
    return image


class LoadImageFromLibrary(io.ComfyNode):
    """
    Load images from the web scraper library
    Supports searching by category, keywords, and machine names
    """
    
    @classmethod
    def define_schema(cls):
        # Get categories and machine names with error handling
        # This allows the node to load even if the database doesn't exist yet
        try:
            manager = get_library_manager()
            categories = manager.get_categories()
            machine_names = manager.get_machine_names()
        except Exception as e:
            logger.warning(f"Could not initialize library manager in define_schema: {e}. Using defaults.")
            categories = DEFAULT_CATEGORIES
            machine_names = [platform.node()] if platform.node() else []
        
        return io.Schema(
            node_id="LoadImageFromLibrary",
            display_name="Load Image from Library",
            category="webscraper",
            inputs=[
                io.Combo.Input(
                    "category",
                    options=[""] + categories,
                    default="",
                    tooltip="Filter images by category. Leave empty for all categories."
                ),
                io.String.Input(
                    "search_query",
                    default="",
                    multiline=False,
                    tooltip="Search images by filename or tags. Leave empty to show all."
                ),
                io.Combo.Input(
                    "machine_name",
                    options=[""] + machine_names,
                    default="",
                    tooltip="Filter images associated with a specific machine name. Leave empty for all machines."
                ),
                io.Int.Input(
                    "min_width",
                    default=0,
                    min=0,
                    max=8192,
                    step=1,
                    tooltip="Minimum image width in pixels"
                ),
                io.Int.Input(
                    "min_height",
                    default=0,
                    min=0,
                    max=8192,
                    step=1,
                    tooltip="Minimum image height in pixels"
                ),
                io.Int.Input(
                    "max_results",
                    default=100,
                    min=1,
                    max=1000,
                    step=1,
                    tooltip="Maximum number of images to search (pool size for selection)"
                ),
                io.Int.Input(
                    "image_index",
                    default=0,
                    min=0,
                    max=999,
                    step=1,
                    tooltip="⭐ CHANGE THIS to select different images! 0=first, 1=second, 2=third, etc."
                ),
                io.Int.Input(
                    "seed",
                    default=0,
                    min=0,
                    max=0xffffffff,
                    step=1,
                    tooltip="Random seed for 'random' mode. Different seed = different image."
                ),
                io.Combo.Input(
                    "selection_mode",
                    options=["index", "random"],
                    default="random",
                    tooltip="'index' = select by image_index number, 'random' = random selection using seed"
                )
            ],
            outputs=[
                io.Image.Output(
                    display_name="images",
                    tooltip="Loaded image from the library"
                )
            ],
        )
    
    @classmethod
    def execute(
        cls,
        category: str,
        search_query: str,
        machine_name: str,
        min_width: int,
        min_height: int,
        max_results: int,
        image_index: int,
        seed: int,
        selection_mode: str
    ) -> io.NodeOutput:
        import random
        
        manager = get_library_manager()
        
        # Clean up empty strings
        category = category if category else None
        search_query = search_query.strip() if search_query else None
        machine_name = machine_name if machine_name else None
        
        # Search images
        search_results = manager.search_images(
            category=category,
            search_query=search_query,
            machine_name=machine_name,
            min_width=min_width if min_width > 0 else None,
            min_height=min_height if min_height > 0 else None,
            limit=max_results
        )
        
        if not search_results:
            logger.warning("No images found matching the search criteria")
            # Return a dummy image to prevent errors
            dummy_image = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
            return io.NodeOutput(dummy_image)
        
        logger.info(f"Found {len(search_results)} images matching criteria")
        
        # Apply selection mode - pick one image based on mode
        if selection_mode == "random":
            # Use seed for reproducible random selection
            random.seed(seed)
            selected_index = random.randint(0, len(search_results) - 1)
            selected_result = search_results[selected_index]
            logger.info(f"Random selection (seed={seed}): picked image at index {selected_index}")
        else:  # "index" mode - use image_index
            # Wrap around if index is out of range
            actual_index = image_index % len(search_results)
            selected_result = search_results[actual_index]
            logger.info(f"Index selection: picked image at index {actual_index} (requested: {image_index}, total: {len(search_results)})")
        
        # Get the image file path
        filepath = selected_result.get("filepath", "")
        if not filepath or not os.path.exists(filepath):
            logger.warning(f"Image file not found: {filepath}")
            dummy_image = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
            return io.NodeOutput(dummy_image)
        
        # Load the image
        try:
            img_tensor = load_and_process_image(filepath)
            logger.info(f"Loaded image: {os.path.basename(filepath)}, shape: {img_tensor.shape}")
            # Return just the tensor - ComfyUI will handle the preview
            return io.NodeOutput(img_tensor)
        except Exception as e:
            logger.error(f"Error loading image {filepath}: {e}")
            dummy_image = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
            return io.NodeOutput(dummy_image)


class SearchImageLibrary(io.ComfyNode):
    """
    Search the image library and return metadata
    Useful for previewing what images are available
    """
    
    @classmethod
    def define_schema(cls):
        # Get categories and machine names with error handling
        try:
            manager = get_library_manager()
            categories = manager.get_categories()
            machine_names = manager.get_machine_names()
        except Exception as e:
            logger.warning(f"Could not initialize library manager in define_schema: {e}. Using defaults.")
            categories = DEFAULT_CATEGORIES
            machine_names = [platform.node()] if platform.node() else []
        
        return io.Schema(
            node_id="SearchImageLibrary",
            display_name="Search Image Library",
            category="webscraper",
            inputs=[
                io.Combo.Input(
                    "category",
                    options=[""] + categories,
                    default="",
                    tooltip="Filter images by category"
                ),
                io.String.Input(
                    "search_query",
                    default="",
                    multiline=False,
                    tooltip="Search images by filename or tags"
                ),
                io.Combo.Input(
                    "machine_name",
                    options=[""] + machine_names,
                    default="",
                    tooltip="Filter images by machine name"
                ),
                io.Int.Input(
                    "max_results",
                    default=20,
                    min=1,
                    max=100,
                    step=1,
                    tooltip="Maximum number of results to return"
                )
            ],
            outputs=[
                io.String.Output(
                    display_name="results",
                    tooltip="JSON string with search results metadata"
                )
            ],
        )
    
    @classmethod
    def execute(
        cls,
        category: str,
        search_query: str,
        machine_name: str,
        max_results: int
    ) -> io.NodeOutput:
        manager = get_library_manager()
        
        # Clean up empty strings
        category = category if category else None
        search_query = search_query.strip() if search_query else None
        machine_name = machine_name if machine_name else None
        
        # Search images
        search_results = manager.search_images(
            category=category,
            search_query=search_query,
            machine_name=machine_name,
            limit=max_results
        )
        
        # Convert to JSON string
        results_json = json.dumps(search_results, indent=2)
        logger.info(f"Found {len(search_results)} images matching search criteria")
        
        return io.NodeOutput(results_json)


# Import the web scraper node
# Try absolute import first (more reliable when module is loaded directly)
WebScraperNode = None
start_scraping = None
cancel_scraping = None
get_scraping_status = None

try:
    import sys
    from pathlib import Path
    node_dir = Path(__file__).parent
    if str(node_dir) not in sys.path:
        sys.path.insert(0, str(node_dir))
    from web_scraper_node import WebScraperNode, start_scraping, cancel_scraping, get_scraping_status
    logger.info("Successfully imported WebScraperNode using absolute import")
except Exception as e1:
    logger.debug(f"Absolute import failed: {e1}, trying relative import...")
    try:
        from .web_scraper_node import WebScraperNode, start_scraping, cancel_scraping, get_scraping_status
        logger.info("Successfully imported WebScraperNode using relative import")
    except Exception as e2:
        logger.warning(f"Could not import WebScraperNode (absolute: {e1}, relative: {e2})")
        import traceback
        logger.warning(traceback.format_exc())
        WebScraperNode = None
        start_scraping = None
        cancel_scraping = None
        get_scraping_status = None


class WebScraperExtension(ComfyExtension):
    """ComfyUI Extension for Web Scraper Image Library"""
    
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        nodes = [
            LoadImageFromLibrary,
            SearchImageLibrary,
        ]
        
        # Try to import WebScraperNode if it wasn't imported earlier
        if WebScraperNode is None:
            logger.warning("WebScraperNode was None, attempting direct import...")
            try:
                import sys
                from pathlib import Path
                node_dir = Path(__file__).parent
                if str(node_dir) not in sys.path:
                    sys.path.insert(0, str(node_dir))
                # Import with a different name to avoid conflicts
                import web_scraper_node
                WSN = web_scraper_node.WebScraperNode
                logger.info("Successfully imported WebScraperNode via direct import")
                nodes.append(WSN)
            except Exception as e:
                logger.error(f"Failed to import WebScraperNode directly: {e}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.info("Adding WebScraperNode to extension")
            nodes.append(WebScraperNode)
        
        # Add video stitch nodes
        video_nodes = [
            VideoStitchInterpolator,
            VideoStitchMultiple,
            VideoFrameBlender,
            VideoLoopSeamless,
        ]
        for vn in video_nodes:
            if vn is not None:
                nodes.append(vn)
                logger.info(f"Added video node: {vn.__name__}")
            else:
                logger.warning(f"Video node was None, skipping")
        
        # Log node details for debugging
        node_info = []
        for n in nodes:
            try:
                schema = n.define_schema()
                category = schema.category
                node_id = schema.node_id
                display_name = schema.display_name
                node_info.append(f"{node_id} (category: {category}, display: {display_name})")
                logger.info(f"Registered node: {node_id} in category '{category}' with display name '{display_name}'")
            except Exception as e:
                logger.error(f"Error getting schema for node {n}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                node_info.append(str(n))
        logger.info(f"Extension returning {len(nodes)} nodes: {node_info}")
        return nodes


# Register web directory for frontend extension
WEB_DIRECTORY = os.path.join(os.path.dirname(__file__), "web")


# Add API routes for web scraper
def setup_api_routes():
    """Setup API routes for web scraper"""
    try:
        from server import PromptServer
        from aiohttp import web
        import uuid
        
        @PromptServer.instance.routes.post("/webscraper/start")
        async def start_scraper(request):
            try:
                data = await request.json()
                session_id = str(uuid.uuid4())
                
                # Get API key from request
                api_key = data.get("api_key", "")
                if not api_key:
                    return web.json_response({
                        "success": False,
                        "error": "API key is required"
                    }, status=400)
                
                # Set API key as environment variable for this session
                import os
                source = data.get("source", "freepik")
                if source == "freepik":
                    os.environ["FREEPIK_API_KEY"] = api_key
                elif source == "pixabay":
                    os.environ["PIXABAY_API_KEY"] = api_key
                elif source == "unsplash":
                    os.environ["UNSPLASH_ACCESS_KEY"] = api_key
                
                if start_scraping:
                    # Start scraping in background
                    asyncio.create_task(start_scraping(
                        session_id=session_id,
                        query=data.get("query", ""),
                        source=data.get("source", "freepik"),
                        category=data.get("category", "nature"),
                        min_width=data.get("min_width", 1920),
                        min_height=data.get("min_height", 1080),
                        aspect_ratio=data.get("aspect_ratio", "any"),
                        max_images=data.get("max_images", 10),
                        tags=data.get("tags", []),
                        api_key=api_key,
                        exclude_ai=data.get("exclude_ai", True),
                        photos_only=data.get("photos_only", True)
                    ))
                    
                    return web.json_response({
                        "success": True,
                        "session_id": session_id
                    })
                else:
                    return web.json_response({
                        "success": False,
                        "error": "Scraper not available"
                    }, status=500)
            except Exception as e:
                logger.error(f"Error starting scraper: {e}", exc_info=True)
                return web.json_response({
                    "success": False,
                    "error": str(e)
                }, status=500)
        
        @PromptServer.instance.routes.post("/webscraper/cancel/{session_id}")
        async def cancel_scraper(request):
            try:
                session_id = request.match_info["session_id"]
                if cancel_scraping:
                    result = cancel_scraping(session_id)
                    return web.json_response(result)
                else:
                    return web.json_response({
                        "success": False,
                        "error": "Scraper not available"
                    }, status=500)
            except Exception as e:
                logger.error(f"Error cancelling scraper: {e}", exc_info=True)
                return web.json_response({
                    "success": False,
                    "error": str(e)
                }, status=500)
        
        @PromptServer.instance.routes.get("/webscraper/status/{session_id}")
        async def get_status(request):
            try:
                session_id = request.match_info["session_id"]
                if get_scraping_status:
                    status = get_scraping_status(session_id)
                    return web.json_response(status)
                else:
                    return web.json_response({
                        "error": "Scraper not available"
                    }, status=500)
            except Exception as e:
                logger.error(f"Error getting status: {e}", exc_info=True)
                return web.json_response({
                    "error": str(e)
                }, status=500)
        
        @PromptServer.instance.routes.get("/webscraper/library/images")
        async def get_library_images(request):
            """Get images from the library with optional filters"""
            try:
                manager = get_library_manager()
                
                # Get query parameters
                category = request.query.get("category", None)
                search_query = request.query.get("search_query", None)
                machine_name = request.query.get("machine_name", None)
                min_width = request.query.get("min_width", None)
                min_height = request.query.get("min_height", None)
                limit = int(request.query.get("limit", 50))
                
                # Convert string parameters
                min_width = int(min_width) if min_width else None
                min_height = int(min_height) if min_height else None
                
                # Check total images in database first
                conn = sqlite3.connect(str(manager.db_path))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM images")
                total_count = cursor.fetchone()[0]
                conn.close()
                logger.info(f"Total images in database: {total_count}")
                
                # Search images
                images = manager.search_images(
                    category=category if category else None,
                    search_query=search_query if search_query else None,
                    machine_name=machine_name if machine_name else None,
                    min_width=min_width if min_width and min_width > 0 else None,
                    min_height=min_height if min_height and min_height > 0 else None,
                    limit=limit
                )
                
                logger.info(f"Library search: category={category}, search_query={search_query}, found {len(images)} images (total in DB: {total_count})")
                
                # Convert file paths to URLs that can be accessed by the frontend
                result = []
                for img in images:
                    filepath = img["filepath"]
                    if os.path.exists(filepath):
                        # Use the filepath directly - ComfyUI should be able to serve it
                        # The frontend will construct the URL
                        result.append({
                            "id": img["id"],
                            "filename": img["filename"],
                            "filepath": filepath,
                            "category": img["category"],
                            "tags": img["tags"],
                            "source": img["source"],
                            "width": img["width"],
                            "height": img["height"]
                        })
                    else:
                        logger.warning(f"Image file not found: {filepath}")
                
                logger.info(f"Returning {len(result)} valid images to frontend")
                return web.json_response({
                    "success": True,
                    "images": result,
                    "count": len(result)
                })
            except Exception as e:
                logger.error(f"Error getting library images: {e}", exc_info=True)
                return web.json_response({
                    "success": False,
                    "error": str(e)
                }, status=500)
        
        @PromptServer.instance.routes.get("/webscraper/library/categories")
        async def get_categories(request):
            """Get available categories"""
            try:
                manager = get_library_manager()
                categories = manager.get_categories()
                return web.json_response({
                    "success": True,
                    "categories": categories
                })
            except Exception as e:
                logger.error(f"Error getting categories: {e}", exc_info=True)
                return web.json_response({
                    "success": False,
                    "error": str(e)
                }, status=500)
        
        @PromptServer.instance.routes.get("/webscraper/library/machine_names")
        async def get_machine_names(request):
            """Get available machine names"""
            try:
                manager = get_library_manager()
                machine_names = manager.get_machine_names()
                return web.json_response({
                    "success": True,
                    "machine_names": machine_names
                })
            except Exception as e:
                logger.error(f"Error getting machine names: {e}", exc_info=True)
                return web.json_response({
                    "success": False,
                    "error": str(e)
                }, status=500)
        
        @PromptServer.instance.routes.get("/webscraper/library/debug")
        async def debug_library(request):
            """Debug endpoint to check library status"""
            try:
                manager = get_library_manager()
                conn = sqlite3.connect(str(manager.db_path))
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute("SELECT COUNT(*) FROM images")
                total_count = cursor.fetchone()[0]
                
                # Get sample images
                cursor.execute("SELECT id, filename, filepath, category, source FROM images LIMIT 5")
                sample_images = cursor.fetchall()
                
                # Get categories
                cursor.execute("SELECT DISTINCT category FROM images WHERE category IS NOT NULL")
                categories = [row[0] for row in cursor.fetchall()]
                
                conn.close()
                
                return web.json_response({
                    "success": True,
                    "total_images": total_count,
                    "db_path": str(manager.db_path),
                    "db_exists": os.path.exists(manager.db_path),
                    "library_dir": str(manager.library_path),
                    "library_dir_exists": os.path.exists(manager.library_path),
                    "sample_images": [
                        {
                            "id": img[0],
                            "filename": img[1],
                            "filepath": img[2],
                            "file_exists": os.path.exists(img[2]) if img[2] else False,
                            "category": img[3],
                            "source": img[4]
                        }
                        for img in sample_images
                    ],
                    "categories": categories
                })
            except Exception as e:
                logger.error(f"Error in debug endpoint: {e}", exc_info=True)
                return web.json_response({
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }, status=500)
        
        @PromptServer.instance.routes.post("/webscraper/library/test-add")
        async def test_add_image(request):
            """Test endpoint to add a dummy image to verify database works"""
            try:
                from PIL import Image as PILImage
                import numpy as np
                
                manager = get_library_manager()
                test_dir = manager.library_path / "test_images"
                test_dir.mkdir(parents=True, exist_ok=True)
                
                # Create a simple test image
                test_image_path = test_dir / "test_image.png"
                img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
                test_img = PILImage.fromarray(img_array)
                test_img.save(test_image_path)
                
                # Add to library
                from library_manager import add_image_to_library
                success = add_image_to_library(
                    image_path=str(test_image_path),
                    category="test",
                    tags=["test", "debug"],
                    source="test"
                )
                
                return web.json_response({
                    "success": success,
                    "message": "Test image created and added to library" if success else "Failed to add test image",
                    "image_path": str(test_image_path),
                    "image_exists": os.path.exists(test_image_path)
                })
            except Exception as e:
                logger.error(f"Error in test-add endpoint: {e}", exc_info=True)
                return web.json_response({
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }, status=500)
        
        @PromptServer.instance.routes.get("/webscraper/library/image/{image_id}")
        async def get_image_file(request):
            """Serve image file by ID"""
            try:
                image_id = int(request.match_info["image_id"])
                manager = get_library_manager()
                
                # Get image info from database
                conn = sqlite3.connect(str(manager.db_path))
                cursor = conn.cursor()
                cursor.execute("SELECT filepath FROM images WHERE id = ?", (image_id,))
                result = cursor.fetchone()
                conn.close()
                
                if not result or not os.path.exists(result[0]):
                    return web.Response(status=404)
                
                filepath = result[0]
                
                # Determine content type
                ext = os.path.splitext(filepath)[1].lower()
                content_type = "image/png"
                if ext in [".jpg", ".jpeg"]:
                    content_type = "image/jpeg"
                elif ext == ".webp":
                    content_type = "image/webp"
                
                # Read and serve the file
                with open(filepath, 'rb') as f:
                    image_data = f.read()
                    return web.Response(body=image_data, content_type=content_type)
            except Exception as e:
                logger.error(f"Error serving image: {e}", exc_info=True)
                return web.Response(status=500)
        
        logger.info("Web scraper API routes registered")
    except Exception as e:
        logger.warning(f"Could not register web scraper API routes: {e}")


# Setup routes when module loads
try:
    import asyncio
    # Try to setup routes immediately if server is available
    if PromptServer and hasattr(PromptServer, 'instance') and PromptServer.instance:
        setup_api_routes()
except Exception as e:
    logger.debug(f"Could not setup routes immediately: {e}")


async def comfy_entrypoint() -> WebScraperExtension:
    """Entry point for ComfyUI to load this extension"""
    # Setup API routes
    setup_api_routes()
    return WebScraperExtension()
