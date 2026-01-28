# Troubleshooting: WebScraper Node Not Appearing

## Quick Checks

1. **Restart ComfyUI completely** - Close and reopen the application
2. **Check the Console** - Look for error messages when ComfyUI starts
3. **Verify File Structure** - Make sure all files are in the correct location

## Expected Console Output

When ComfyUI starts, you should see messages like:
```
Successfully imported WebScraperNode
Adding WebScraperNode to extension
Extension returning 3 nodes
```

If you see errors instead, note them down.

## File Structure Check

Verify this structure exists:
```
custom_nodes/
└── webscraper/
    ├── __init__.py
    └── ks-cn-web-scraper1/
        ├── __init__.py
        ├── webscraper_workflow.py
        ├── web_scraper_node.py  ← MUST EXIST
        ├── library_manager.py
        └── web/
            ├── web_scraper.js
            └── web_scraper.min.js
```

## How to Find the Node

1. **In the Node Library Sidebar**:
   - Look for a category called **"webscraper"** (lowercase)
   - It should appear alphabetically in the list
   - Click on it to see "Web Image Scraper" node

2. **Using Search**:
   - Click in the search bar
   - Type: `webscraper` or `Web Image Scraper`
   - The node should appear in results

3. **Right-click Menu**:
   - Right-click in the canvas
   - Look for "webscraper" category
   - Select "Web Image Scraper"

## Common Issues

### Issue: Node not appearing at all
**Solution**: 
- Check ComfyUI console for import errors
- Verify `web_scraper_node.py` exists and has no syntax errors
- Make sure `__init__.py` files are present

### Issue: Category not showing
**Solution**:
- The category name is "webscraper" (lowercase, no spaces)
- Categories appear automatically when nodes are registered
- Try searching for the node instead

### Issue: Import errors in console
**Solution**:
- Check that all dependencies are available
- Verify Python can import `comfy_api.latest`
- Check for circular import issues

## Manual Verification

To verify the node is loading, check the ComfyUI console output when starting. You should see:
- No errors about "webscraper" or "WebScraperNode"
- Messages about nodes being loaded
- If you see "IMPORT FAILED" for webscraper, there's an issue

## Still Not Working?

1. **Check the exact error message** in ComfyUI console
2. **Verify Python version** - ComfyUI requires Python 3.8+
3. **Check file permissions** - Make sure files are readable
4. **Try moving the node** - Move `ks-cn-web-scraper1` directly to `custom_nodes/` (not nested)

If the node still doesn't appear after these checks, share the exact error messages from the ComfyUI console.
