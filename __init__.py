"""
Web Scraper Image Library & Video Tools Custom Node for ComfyUI
This package provides:
- Nodes to load and search images from a curated library (Pixabay, Freepik, Unsplash)
- Video stitching and interpolation tools for seamless video generation
"""

import logging
logger = logging.getLogger(__name__)

# Import web scraper nodes and extension
try:
    from .webscraper_workflow import (
        LoadImageFromLibrary,
        SearchImageLibrary,
        WebScraperExtension,
        comfy_entrypoint,
        get_library_manager,
        DEFAULT_LIBRARY_PATH,
    )
    logger.info("Web scraper nodes loaded successfully")
except Exception as e:
    logger.error(f"Failed to import webscraper_workflow: {e}")
    import traceback
    logger.error(traceback.format_exc())
    # Define a dummy entrypoint to prevent loading errors
    async def comfy_entrypoint():
        from comfy_api.latest import ComfyExtension
        class DummyExtension(ComfyExtension):
            async def get_node_list(self):
                return []
        return DummyExtension()

# Web directory for frontend assets
WEB_DIRECTORY = "./web"

__all__ = [
    "LoadImageFromLibrary",
    "SearchImageLibrary",
    "WebScraperExtension",
    "comfy_entrypoint",
    "get_library_manager",
    "DEFAULT_LIBRARY_PATH",
    "WEB_DIRECTORY",
]
