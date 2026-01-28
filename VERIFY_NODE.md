# How to Verify the WebScraper Node is Loading

## Step 1: Check ComfyUI Console Output

When ComfyUI starts, look for these messages in the console/terminal:

**SUCCESS messages you should see:**
```
Successfully imported WebScraperNode using absolute import
Adding WebScraperNode to extension
Extension returning 3 nodes: ['LoadImageFromLibrary (category: image/library)', 'SearchImageLibrary (category: image/library)', 'WebScraper (category: webscraper)']
```

**If you see errors instead:**
- Note the exact error message
- Check if it says "IMPORT FAILED" for webscraper
- Look for Python traceback errors

## Step 2: Verify Node Registration

After ComfyUI starts, the node should be registered. To verify:

1. **Right-click on the canvas**
2. **Look for "webscraper" category** in the menu
3. **Or search for "Web Image Scraper"** in the search bar

## Step 3: Check File Structure

Make sure these files exist:
```
custom_nodes/webscraper/ks-cn-web-scraper1/
├── __init__.py
├── webscraper_workflow.py
├── web_scraper_node.py  ← CRITICAL - must exist
├── library_manager.py
└── web/
    ├── web_scraper.js
    └── web_scraper.min.js
```

## Step 4: Test Import Manually (Optional)

You can test if the import works by running:
```python
cd "C:\Users\Render-14-AI_Artists\Downloads\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI\custom_nodes\webscraper\ks-cn-web-scraper1"
python test_import.py
```

This will show if the imports work correctly.

## Common Issues and Solutions

### Issue: "comfy_entrypoint not found"
**Solution**: The module isn't loading correctly. Check that `webscraper_workflow.py` exists and has the `comfy_entrypoint` function.

### Issue: "WebScraperNode is None"
**Solution**: The import is failing. Check that `web_scraper_node.py` exists and has no syntax errors.

### Issue: Node appears but category doesn't show
**Solution**: The category is "webscraper" (lowercase). It should appear automatically when the node is registered. Try searching for the node instead.

### Issue: No errors but node still not visible
**Solution**: 
1. Hard refresh the browser (Ctrl+F5)
2. Clear browser cache
3. Check if other custom nodes are visible (if not, there's a broader ComfyUI issue)

## What to Share for Debugging

If the node still doesn't appear, share:
1. **Exact console output** when ComfyUI starts (especially lines mentioning "webscraper")
2. **Any error messages** (even warnings)
3. **Whether other custom nodes work** (to rule out ComfyUI configuration issues)
