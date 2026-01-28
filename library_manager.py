"""
Utility script to populate the image library from web scraper results
This can be used by your web scraper to add images to the library
"""

import os
import json
import sqlite3
import platform
from pathlib import Path
from typing import Optional, List, Dict, Any
from PIL import Image

try:
    from .webscraper_workflow import ImageLibraryManager, DEFAULT_LIBRARY_PATH
except ImportError:
    # Allow running as standalone script
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from webscraper_workflow import ImageLibraryManager, DEFAULT_LIBRARY_PATH


def add_image_to_library(
    image_path: str,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    source: Optional[str] = None,
    machine_name: Optional[str] = None,
    library_path: str = DEFAULT_LIBRARY_PATH
) -> bool:
    """
    Add an image to the library database
    
    Args:
        image_path: Path to the image file
        category: Category for the image (e.g., "nature", "animals")
        tags: List of tags/keywords for the image
        source: Source of the image (e.g., "pixabay", "unsplash", "freepik")
        machine_name: Machine name associated with this image
        library_path: Path to the library directory
    
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return False
    
    try:
        manager = ImageLibraryManager(library_path)
        
        # Get image metadata
        img = Image.open(image_path)
        width, height = img.size
        file_size = os.path.getsize(image_path)
        filename = os.path.basename(image_path)
        
        # Convert tags list to string
        tags_str = ",".join(tags) if tags else None
        
        # Get machine name if not provided
        if not machine_name:
            machine_name = platform.node()
        
        # Add to database
        conn = sqlite3.connect(str(manager.db_path))
        cursor = conn.cursor()
        
        # Check if image already exists
        cursor.execute("SELECT id FROM images WHERE filepath = ?", (image_path,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing entry
            image_id = existing[0]
            cursor.execute('''
                UPDATE images 
                SET category = ?, tags = ?, source = ?, 
                    resolution_width = ?, resolution_height = ?, 
                    file_size = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (category, tags_str, source, width, height, file_size, image_id))
        else:
            # Insert new entry
            cursor.execute('''
                INSERT INTO images 
                (filename, filepath, category, tags, source, resolution_width, resolution_height, file_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (filename, image_path, category, tags_str, source, width, height, file_size))
            image_id = cursor.lastrowid
        
        # Add machine name association
        if machine_name:
            cursor.execute('''
                INSERT OR IGNORE INTO machine_names (image_id, machine_name)
                VALUES (?, ?)
            ''', (image_id, machine_name))
        
        conn.commit()
        conn.close()
        
        print(f"Successfully added image to library: {filename}")
        return True
        
    except Exception as e:
        print(f"Error adding image to library: {e}")
        return False


def batch_add_images(
    image_data: List[Dict[str, Any]],
    library_path: str = DEFAULT_LIBRARY_PATH
) -> Dict[str, int]:
    """
    Batch add multiple images to the library
    
    Args:
        image_data: List of dictionaries, each containing:
            - image_path: Path to image file (required)
            - category: Optional category
            - tags: Optional list of tags
            - source: Optional source name
            - machine_name: Optional machine name
        library_path: Path to the library directory
    
    Returns:
        Dictionary with counts: {"success": X, "failed": Y}
    """
    results = {"success": 0, "failed": 0}
    
    for data in image_data:
        if add_image_to_library(
            image_path=data.get("image_path"),
            category=data.get("category"),
            tags=data.get("tags"),
            source=data.get("source"),
            machine_name=data.get("machine_name"),
            library_path=library_path
        ):
            results["success"] += 1
        else:
            results["failed"] += 1
    
    return results


def import_from_scraper_json(
    json_path: str,
    library_path: str = DEFAULT_LIBRARY_PATH
) -> Dict[str, int]:
    """
    Import images from a JSON file created by a web scraper
    
    Expected JSON format:
    [
        {
            "image_path": "/path/to/image.jpg",
            "category": "nature",
            "tags": ["landscape", "mountain"],
            "source": "pixabay",
            "machine_name": "optional-machine-name"
        },
        ...
    ]
    """
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found: {json_path}")
        return {"success": 0, "failed": 0}
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            image_data = json.load(f)
        
        return batch_add_images(image_data, library_path)
        
    except Exception as e:
        print(f"Error importing from JSON: {e}")
        return {"success": 0, "failed": 0}


if __name__ == "__main__":
    # Example usage
    print("Web Scraper Library Manager")
    print("=" * 40)
    
    # Example: Add a single image
    # add_image_to_library(
    #     image_path="/path/to/image.jpg",
    #     category="nature",
    #     tags=["landscape", "sunset"],
    #     source="pixabay"
    # )
    
    print("Use this module to populate your image library from web scraper results")
