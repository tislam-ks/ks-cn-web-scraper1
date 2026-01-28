"""
Web Scraper Image Library Custom Node for ComfyUI
This package provides nodes to load and search images from a curated library
created by web scrapers (Pixabay, Freepik, Unsplash, etc.)
"""

try:
    from .webscraper_workflow import (
        LoadImageFromLibrary,
        SearchImageLibrary,
        WebScraperExtension,
        comfy_entrypoint,
        get_library_manager,
        DEFAULT_LIBRARY_PATH,
    )
except Exception as e:
    import logging
    logging.error(f"Failed to import webscraper_workflow: {e}")
    import traceback
    logging.error(traceback.format_exc())
    # Define a dummy entrypoint to prevent loading errors
    async def comfy_entrypoint():
        from comfy_api.latest import ComfyExtension
        class DummyExtension(ComfyExtension):
            async def get_node_list(self):
                return []
        return DummyExtension()

__all__ = [
    "LoadImageFromLibrary",
    "SearchImageLibrary",
    "WebScraperExtension",
    "comfy_entrypoint",
    "get_library_manager",
    "DEFAULT_LIBRARY_PATH",
]
