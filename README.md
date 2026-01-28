# Web Scraper Image Library & Video Tools for ComfyUI

A custom ComfyUI node package that provides:
- Easy access to a curated library of high-resolution images scraped from sites like Pixabay, Freepik, and Unsplash
- **Video stitching and interpolation tools** for seamless AI video generation

## Features

### Image Library
- **Searchable Image Library**: Search images by category, keywords, tags, or machine names
- **Category Support**: Generic categories (nature, animals, people, architecture, etc.) plus custom categories
- **Machine Name Detection**: Automatically detects and filters images by machine/hostname
- **Resolution Filtering**: Filter images by minimum width and height
- **Multiple Selection Modes**: Load first N results, random selection, or all matching images
- **SQLite Database**: Fast, efficient metadata storage and retrieval
- **Easy Integration**: Works seamlessly with your web scraper to populate the library

## Installation

1. Place this folder in your ComfyUI `custom_nodes` directory:
   ```
   ComfyUI/custom_nodes/webscraper/ks-cn-web-scraper1/
   ```

2. Restart ComfyUI. The nodes will be automatically loaded.

## Usage

### In ComfyUI

#### LoadImageFromLibrary Node

Loads images from your library based on search criteria:

- **Category**: Select a category to filter images (or leave empty for all)
- **Search Query**: Search by filename or tags
- **Machine Name**: Filter by machine name (auto-detected from system)
- **Min Width/Height**: Filter by minimum resolution
- **Max Results**: Maximum number of images to load
- **Selection Mode**: 
  - `first`: Load first N results
  - `random`: Randomly select N results
  - `all`: Load all matching results (up to max_results)

#### SearchImageLibrary Node

Searches the library and returns metadata as JSON. Useful for previewing available images.

### Populating the Library

Use the `library_manager.py` utility to add images from your web scraper:

```python
from library_manager import add_image_to_library

# Add a single image
add_image_to_library(
    image_path="/path/to/image.jpg",
    category="nature",
    tags=["landscape", "sunset", "mountains"],
    source="pixabay"
)
```

Or batch import from a JSON file:

```python
from library_manager import import_from_scraper_json

# Import from JSON file created by your scraper
results = import_from_scraper_json("scraper_results.json")
print(f"Added {results['success']} images, {results['failed']} failed")
```

### JSON Format for Batch Import

Your web scraper should create JSON files in this format:

```json
[
    {
        "image_path": "/full/path/to/image1.jpg",
        "category": "nature",
        "tags": ["landscape", "sunset"],
        "source": "pixabay",
        "machine_name": "optional-machine-name"
    },
    {
        "image_path": "/full/path/to/image2.jpg",
        "category": "animals",
        "tags": ["wildlife", "bird"],
        "source": "unsplash"
    }
]
```

## Library Structure

The library is stored in:
```
ComfyUI/image_library/
├── library.db          # SQLite database with metadata
├── metadata/           # Additional metadata files (if needed)
└── [your images]      # Images can be stored anywhere, paths are stored in DB
```

## Default Categories

- nature, animals, people, architecture, technology
- abstract, business, food, travel, sports
- art, music, science, health, education
- fashion, vehicles, landscapes, cityscapes, wildlife

You can add custom categories by using them when adding images to the library.

## Machine Name Detection

The node automatically:
1. Detects the system hostname
2. Retrieves machine names from the database
3. Allows filtering images associated with specific machines

This is useful for:
- Organizing images by which machine scraped them
- Filtering images for specific workflows
- Multi-machine setups

## Example Workflow

1. Run your web scraper to download images from Pixabay/Unsplash/Freepik
2. Use `library_manager.py` to add images to the library with metadata
3. In ComfyUI, use `LoadImageFromLibrary` node to search and load images
4. Connect the output to your image processing pipeline

## Requirements

- ComfyUI (latest version)
- Python packages (usually included with ComfyUI):
  - PIL/Pillow
  - torch
  - numpy
  - sqlite3 (built-in)

## Notes

- Images can be stored anywhere on your system - the database stores full paths
- The library database is automatically created on first use
- Search is case-insensitive for tags and filenames
- Empty search fields are ignored (shows all matching other criteria)

## Troubleshooting

**No images found:**
- Make sure you've populated the library using `library_manager.py`
- Check that image paths in the database are correct and files exist
- Verify your search criteria aren't too restrictive

**Node not appearing:**
- Check that the folder is in `custom_nodes/webscraper/ks-cn-web-scraper1/`
- Restart ComfyUI
- Check ComfyUI console for error messages

**Database errors:**
- Ensure write permissions in the library directory
- Check disk space
- Verify SQLite is working (usually built into Python)

---

## Video Stitching & Interpolation Nodes

These nodes help you seamlessly stitch multiple AI-generated video clips together.

### Video Stitch Interpolator

The main node for stitching videos together with smooth transitions.

**Inputs:**
- `video_a` (IMAGE): First video clip (batch of frames)
- `video_b` (IMAGE): Second video clip (batch of frames)
- `video_c`, `video_d` (optional): Additional clips to chain

**Parameters:**
- `overlap_frames` (1-30, default 4): Frames from each clip used for blending
- `crossfade_frames` (0-60, default 8): Duration of crossfade transition
- `interpolation_frames` (0-16, default 2): Generated in-between frames
- `interpolation_method`: 
  - `linear`: Constant speed blend
  - `ease_in_out`: Smooth acceleration/deceleration
  - `cosine`: Natural smooth curve
  - `sigmoid`: Sharp transition in middle
- `blend_mode`: `crossfade`, `additive`, `overlay`

**How it works:**
1. Takes the last N frames of video_a
2. Takes the first N frames of video_b
3. Generates interpolated frames between them
4. Applies crossfade blending
5. Outputs one seamless video

### Video Frame Blender

Simple node to blend/mix two video frame sequences.

**Parameters:**
- `blend_factor` (0.0-1.0): 0 = all frames_a, 1 = all frames_b
- `blend_mode`: `mix`, `add`, `multiply`, `screen`, `overlay`

### Video Loop Seamless

Creates a perfect loop from a video by blending end back to start.

**Parameters:**
- `blend_frames` (2-60): Frames to blend for seamless loop
- `blend_curve`: `linear`, `ease_in_out`, `cosine`

### Example Video Workflow

```
[Video Generator A] → [frames]
                            ↘
                             [Video Stitch Interpolator] → [seamless video]
                            ↗
[Video Generator B] → [frames]
```

1. Generate multiple short video clips with your AI model
2. Connect them to Video Stitch Interpolator
3. Adjust overlap and interpolation settings
4. Get one seamless combined video!

---

## Future Enhancements

Potential features to add:
- Image preview in node UI
- Tag autocomplete
- Image similarity search
- Batch operations in UI
- Integration with more scraper sources
- Image deduplication
- Thumbnail generation
- **RIFE AI interpolation** for video stitching
- **Optical flow** based frame interpolation
