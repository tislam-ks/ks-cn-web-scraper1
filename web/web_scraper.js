// Web Scraper Drawer UI for ComfyUI
import { app } from "/scripts/app.js";

const DRAWER_ID = "web-scraper-drawer";
let currentSessionId = null;
let statusInterval = null;

// Create drawer HTML
function createDrawerHTML() {
    return `
<div id="${DRAWER_ID}" class="web-scraper-drawer" style="display:none;">
    <div class="drawer-overlay"></div>
    <div class="drawer-content">
        <div class="drawer-header">
            <h2>Web Image Scraper</h2>
            <button class="drawer-close" onclick="closeWebScraperDrawer()">×</button>
        </div>
        <div class="drawer-body">
            <div class="form-group">
                <label>Search Query</label>
                <input type="text" id="scraper-query" placeholder="e.g., sunset, mountains, nature" />
            </div>
            <div class="form-group">
                <label>Source</label>
                <select id="scraper-source">
                    <option value="unsplash">⭐ Unsplash (FREE High-Res!)</option>
                    <option value="freepik">Freepik (Preview Size ~626px)</option>
                    <option value="pixabay">Pixabay</option>
                </select>
                <small id="source-info" style="color: #4a9eff; font-size: 11px; display: block; margin-top: 4px;">
                    ⭐ Unsplash provides FREE high-resolution images (2000-4000px)!
                </small>
            </div>
            <div class="form-group" id="api-key-group">
                <label>API Key</label>
                <input type="password" id="scraper-api-key" placeholder="Enter your API key" />
                <small id="api-key-help" style="color: #888; font-size: 11px; display: block; margin-top: 4px;">
                    Get your API key from <a href="https://unsplash.com/developers" target="_blank" style="color: #4a9eff;">Unsplash Developers</a> (free!)
                </small>
            </div>
            <div class="form-group">
                <label>Category</label>
                <select id="scraper-category">
                    <option value="nature">Nature</option>
                    <option value="animals">Animals</option>
                    <option value="people">People</option>
                    <option value="architecture">Architecture</option>
                    <option value="technology">Technology</option>
                    <option value="abstract">Abstract</option>
                    <option value="business">Business</option>
                    <option value="food">Food</option>
                    <option value="travel">Travel</option>
                    <option value="sports">Sports</option>
                </select>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Min Width (px)</label>
                    <input type="number" id="scraper-min-width" value="1920" min="100" max="8192" />
                </div>
                <div class="form-group">
                    <label>Min Height (px)</label>
                    <input type="number" id="scraper-min-height" value="1080" min="100" max="8192" />
                </div>
            </div>
            <div class="form-group">
                <label>Aspect Ratio</label>
                <select id="scraper-aspect-ratio">
                    <option value="any">Any</option>
                    <option value="16:9">16:9 (Widescreen)</option>
                    <option value="4:3">4:3 (Standard)</option>
                    <option value="1:1">1:1 (Square)</option>
                    <option value="9:16">9:16 (Portrait)</option>
                    <option value="21:9">21:9 (Ultrawide)</option>
                </select>
            </div>
            <div class="form-group">
                <label>Max Images</label>
                <input type="number" id="scraper-max-images" value="10" min="1" max="100" />
            </div>
            <div class="form-group">
                <label>Tags (comma-separated)</label>
                <input type="text" id="scraper-tags" placeholder="landscape, sunset, mountains" />
            </div>
            <div class="form-group" style="display: flex; align-items: center; gap: 10px;">
                <input type="checkbox" id="scraper-exclude-ai" checked style="width: auto; cursor: pointer;" />
                <label for="scraper-exclude-ai" style="margin: 0; cursor: pointer;">Exclude AI-generated images</label>
            </div>
            <div class="form-group" style="display: flex; align-items: center; gap: 10px;">
                <input type="checkbox" id="scraper-photos-only" checked style="width: auto; cursor: pointer;" />
                <label for="scraper-photos-only" style="margin: 0; cursor: pointer;">Photos only (exclude vectors/icons)</label>
            </div>
            <div class="progress-container" id="scraper-progress" style="display:none;">
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill"></div>
                </div>
                <div class="progress-text" id="progress-text">Initializing...</div>
                <div class="progress-stats" id="progress-stats"></div>
            </div>
            <div class="drawer-actions">
                <button class="btn-primary" id="scraper-start-btn" onclick="startScraping()">Start Scraping</button>
                <button class="btn-secondary" id="scraper-cancel-btn" onclick="cancelScraping()" style="display:none;">Cancel</button>
            </div>
        </div>
    </div>
</div>
`;
}

// Inject CSS
function injectCSS() {
    const style = document.createElement("style");
    style.textContent = `
.web-scraper-drawer{position:fixed;top:0;left:0;width:100%;height:100%;z-index:10000;font-family:system-ui}
.drawer-overlay{position:absolute;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);backdrop-filter:blur(4px)}
.drawer-content{position:absolute;right:0;top:0;width:400px;max-width:90vw;height:100%;background:#1e1e1e;box-shadow:-4px 0 20px rgba(0,0,0,0.5);overflow-y:auto;animation:slideIn 0.3s ease}
@keyframes slideIn{from{transform:translateX(100%)}to{transform:translateX(0)}}
.drawer-header{display:flex;justify-content:space-between;align-items:center;padding:20px;border-bottom:1px solid #333}
.drawer-header h2{margin:0;color:#fff;font-size:20px;font-weight:600}
.drawer-close{background:none;border:none;color:#fff;font-size:32px;cursor:pointer;padding:0;width:32px;height:32px;line-height:1}
.drawer-close:hover{color:#ff6b6b}
.drawer-body{padding:20px}
.form-group{margin-bottom:20px}
.form-group label{display:block;color:#ccc;margin-bottom:8px;font-size:14px;font-weight:500}
.form-group input,.form-group select{width:100%;padding:10px;background:#2a2a2a;border:1px solid #444;border-radius:6px;color:#fff;font-size:14px;box-sizing:border-box}
.form-group input:focus,.form-group select:focus{outline:none;border-color:#4a9eff}
.form-group input[type="checkbox"]{width:18px;height:18px;cursor:pointer;accent-color:#4a9eff}
.form-group small{display:block;margin-top:4px;color:#888;font-size:11px;line-height:1.4}
.form-group small a{color:#4a9eff;text-decoration:none}
.form-group small a:hover{text-decoration:underline}
.form-row{display:flex;gap:15px}
.form-row .form-group{flex:1}
.progress-container{margin:20px 0;padding:15px;background:#2a2a2a;border-radius:8px;border:1px solid #444}
.progress-bar{width:100%;height:8px;background:#1a1a1a;border-radius:4px;overflow:hidden;margin-bottom:10px}
.progress-fill{height:100%;background:linear-gradient(90deg,#4a9eff,#6bc4ff);transition:width 0.3s ease;width:0%}
.progress-text{color:#fff;font-size:14px;margin-bottom:5px}
.progress-stats{color:#aaa;font-size:12px}
.drawer-actions{display:flex;gap:10px;margin-top:30px}
.btn-primary,.btn-secondary{padding:12px 24px;border:none;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer;transition:all 0.2s}
.btn-primary{background:#4a9eff;color:#fff}
.btn-primary:hover{background:#3a8eef}
.btn-primary:disabled{background:#555;cursor:not-allowed}
.btn-secondary{background:#555;color:#fff}
.btn-secondary:hover{background:#666}
#webscraper-gallery::-webkit-scrollbar{width:6px}
#webscraper-gallery::-webkit-scrollbar-track{background:#1a1a1a;border-radius:3px}
#webscraper-gallery::-webkit-scrollbar-thumb{background:#444;border-radius:3px}
#webscraper-gallery::-webkit-scrollbar-thumb:hover{background:#555}
`;
    document.head.appendChild(style);
}

// Open drawer
function openWebScraperDrawer() {
    const drawer = document.getElementById(DRAWER_ID);
    if (!drawer) {
        document.body.insertAdjacentHTML("beforeend", createDrawerHTML());
        injectCSS();
        
        // Load saved API keys
        setTimeout(() => {
            const sourceSelect = document.getElementById("scraper-source");
            const apiKeyInput = document.getElementById("scraper-api-key");
            
            function updateApiKeyPlaceholder() {
                const source = sourceSelect.value;
                const savedKey = localStorage.getItem(`api_key_${source}`);
                if (savedKey) {
                    apiKeyInput.value = savedKey;
                } else {
                    apiKeyInput.value = "";
                }
                
                const sourceInfo = document.getElementById("source-info");
                const helpText = document.getElementById("api-key-help");
                
                // Update placeholder, help text, and source info based on selection
                if (source === "freepik") {
                    apiKeyInput.placeholder = "Enter your Freepik API key";
                    if (helpText) {
                        helpText.innerHTML = 'Get your API key from <a href="https://www.freepik.com/developers/dashboard/api-key" target="_blank" style="color: #4a9eff;">Freepik Developers</a>';
                    }
                    if (sourceInfo) {
                        sourceInfo.innerHTML = '⚠️ Freepik free tier only provides <b>preview size</b> images (~626px). Premium required for full resolution.';
                        sourceInfo.style.color = '#ff9800';
                    }
                } else if (source === "pixabay") {
                    apiKeyInput.placeholder = "Enter your Pixabay API key";
                    if (helpText) {
                        helpText.innerHTML = 'Get your API key from <a href="https://pixabay.com/api/docs/" target="_blank" style="color: #4a9eff;">Pixabay API Docs</a> (free!)';
                    }
                    if (sourceInfo) {
                        sourceInfo.innerHTML = 'Pixabay provides medium resolution images (~1280px) for free.';
                        sourceInfo.style.color = '#888';
                    }
                } else if (source === "unsplash") {
                    apiKeyInput.placeholder = "Enter your Unsplash API key";
                    if (helpText) {
                        helpText.innerHTML = '⭐ Get your FREE API key from <a href="https://unsplash.com/developers" target="_blank" style="color: #4a9eff;">Unsplash Developers</a>';
                    }
                    if (sourceInfo) {
                        sourceInfo.innerHTML = '⭐ Unsplash provides <b>FREE high-resolution</b> images (2000-4000px)! Best for quality.';
                        sourceInfo.style.color = '#4caf50';
                    }
                }
            }
            
            sourceSelect.addEventListener("change", updateApiKeyPlaceholder);
            updateApiKeyPlaceholder();
        }, 100);
    }
    document.getElementById(DRAWER_ID).style.display = "block";
}

// Close drawer
function closeWebScraperDrawer() {
    const drawer = document.getElementById(DRAWER_ID);
    if (drawer) drawer.style.display = "none";
    if (statusInterval) {
        clearInterval(statusInterval);
        statusInterval = null;
    }
}

// Start scraping
async function startScraping() {
    const query = document.getElementById("scraper-query").value.trim();
    if (!query) {
        alert("Please enter a search query");
        return;
    }
    
    const source = document.getElementById("scraper-source").value;
    const apiKey = document.getElementById("scraper-api-key").value.trim();
    
    if (!apiKey) {
        alert(`Please enter your ${source} API key`);
        return;
    }
    
    // Save API key to localStorage
    localStorage.setItem(`api_key_${source}`, apiKey);
    
    const params = {
        query,
        source: source,
        api_key: apiKey,
        category: document.getElementById("scraper-category").value,
        min_width: parseInt(document.getElementById("scraper-min-width").value),
        min_height: parseInt(document.getElementById("scraper-min-height").value),
        aspect_ratio: document.getElementById("scraper-aspect-ratio").value,
        max_images: parseInt(document.getElementById("scraper-max-images").value),
        tags: document.getElementById("scraper-tags").value.split(",").map(t => t.trim()).filter(t => t),
        exclude_ai: document.getElementById("scraper-exclude-ai").checked,
        photos_only: document.getElementById("scraper-photos-only").checked
    };
    
    try {
        const response = await fetch("/webscraper/start", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(params)
        });
        const data = await response.json();
        
        if (data.success) {
            currentSessionId = data.session_id;
            document.getElementById("scraper-progress").style.display = "block";
            document.getElementById("scraper-start-btn").disabled = true;
            document.getElementById("scraper-cancel-btn").style.display = "block";
            startStatusPolling();
        } else {
            alert("Error: " + (data.error || "Failed to start scraping"));
        }
    } catch (error) {
        alert("Error: " + error.message);
    }
}

// Cancel scraping
async function cancelScraping() {
    if (!currentSessionId) return;
    
    try {
        await fetch(`/webscraper/cancel/${currentSessionId}`, {method: "POST"});
        if (statusInterval) {
            clearInterval(statusInterval);
            statusInterval = null;
        }
        document.getElementById("scraper-start-btn").disabled = false;
        document.getElementById("scraper-cancel-btn").style.display = "none";
    } catch (error) {
        console.error("Error cancelling:", error);
    }
}

// Poll for status updates
function startStatusPolling() {
    if (statusInterval) clearInterval(statusInterval);
    
    statusInterval = setInterval(async () => {
        if (!currentSessionId) return;
        
        try {
            const response = await fetch(`/webscraper/status/${currentSessionId}`);
            const status = await response.json();
            
            if (status.error) {
                clearInterval(statusInterval);
                return;
            }
            
            updateProgress(status);
            
                if (status.status === "completed" || status.status === "error" || status.status === "cancelled") {
                clearInterval(statusInterval);
                document.getElementById("scraper-start-btn").disabled = false;
                document.getElementById("scraper-cancel-btn").style.display = "none";
                
                if (status.status === "completed") {
                    // Refresh image gallery when scraping completes
                    if (window.refreshImageGallery) {
                        setTimeout(() => window.refreshImageGallery(), 1000);
                    }
                }
            }
        } catch (error) {
            console.error("Error polling status:", error);
        }
    }, 1000);
}

// Update progress UI
function updateProgress(status) {
    const fill = document.getElementById("progress-fill");
    const text = document.getElementById("progress-text");
    const stats = document.getElementById("progress-stats");
    
    if (fill) fill.style.width = status.progress + "%";
    if (text) text.textContent = status.current_step || "Processing...";
    if (stats) {
        stats.textContent = `Images: ${status.scraped_images || 0} / ${status.total_images || 0}`;
    }
}

// Register sidebar tab for Web Scraper (only once to prevent duplicates)
if (!app.extensionManager.sidebarTabs || !app.extensionManager.sidebarTabs.find(t => t.id === "webscraper")) {
    app.extensionManager.registerSidebarTab({
        id: "webscraper",
        icon: "pi pi-download",
        title: "Web Scraper",
        tooltip: "Web Image Scraper - Scrape images from Pixabay, Unsplash, Freepik",
        type: "custom",
        render: (el) => {
        // Create container
        const container = document.createElement('div');
        container.style.padding = '20px';
        container.style.height = '100%';
        container.style.overflowY = 'auto';
        
        // Title
        const title = document.createElement('h2');
        title.textContent = 'Web Image Scraper';
        title.style.marginTop = '0';
        title.style.color = '#fff';
        container.appendChild(title);
        
        // Description
        const desc = document.createElement('p');
        desc.textContent = 'Scrape high-resolution images from Pixabay, Unsplash, and Freepik with customizable parameters.';
        desc.style.color = '#aaa';
        desc.style.marginBottom = '20px';
        container.appendChild(desc);
        
        // Add node button (opens drawer automatically)
        const addNodeBtn = document.createElement('button');
        addNodeBtn.textContent = 'Add Web Scraper Node';
        addNodeBtn.style.width = '100%';
        addNodeBtn.style.padding = '12px';
        addNodeBtn.style.background = '#4a9eff';
        addNodeBtn.style.color = '#fff';
        addNodeBtn.style.border = 'none';
        addNodeBtn.style.borderRadius = '6px';
        addNodeBtn.style.cursor = 'pointer';
        addNodeBtn.style.fontSize = '14px';
        addNodeBtn.style.fontWeight = '600';
        addNodeBtn.style.marginBottom = '20px';
        addNodeBtn.onmouseover = () => addNodeBtn.style.background = '#3a8eef';
        addNodeBtn.onmouseout = () => addNodeBtn.style.background = '#4a9eff';
        addNodeBtn.onclick = () => {
            const node = LiteGraph.createNode("WebScraper");
            if (node) {
                app.graph.add(node);
                node.pos = [app.canvas.graph_mouse[0], app.canvas.graph_mouse[1]];
                app.graph.setDirtyCanvas(true, true);
                // Open drawer after adding node
                setTimeout(() => openWebScraperDrawer(), 100);
            } else {
                // If node creation fails, just open drawer
                openWebScraperDrawer();
            }
        };
        container.appendChild(addNodeBtn);
        
        // Image Library Section
        const librarySection = document.createElement('div');
        librarySection.style.marginTop = '30px';
        librarySection.style.padding = '15px';
        librarySection.style.background = '#2a2a2a';
        librarySection.style.borderRadius = '8px';
        librarySection.style.border = '1px solid #444';
        
        const libraryTitle = document.createElement('h3');
        libraryTitle.textContent = 'Image Library';
        libraryTitle.style.color = '#fff';
        libraryTitle.style.marginTop = '0';
        libraryTitle.style.marginBottom = '10px';
        libraryTitle.style.fontSize = '16px';
        librarySection.appendChild(libraryTitle);
        
        // Help text
        const helpText = document.createElement('div');
        helpText.innerHTML = '<small style="color: #888;">Click <b>Use Image</b> to add a node with that specific image selected. Each image shows its index number (#0, #1, etc.).</small>';
        helpText.style.marginBottom = '15px';
        librarySection.appendChild(helpText);
        
        // Search controls
        const searchControls = document.createElement('div');
        searchControls.style.marginBottom = '15px';
        
        const searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.placeholder = 'Search images...';
        searchInput.style.width = '100%';
        searchInput.style.padding = '8px';
        searchInput.style.background = '#1a1a1a';
        searchInput.style.border = '1px solid #444';
        searchInput.style.borderRadius = '4px';
        searchInput.style.color = '#fff';
        searchInput.style.marginBottom = '10px';
        searchInput.style.boxSizing = 'border-box';
        searchControls.appendChild(searchInput);
        
        const categorySelect = document.createElement('select');
        categorySelect.style.width = '100%';
        categorySelect.style.padding = '8px';
        categorySelect.style.background = '#1a1a1a';
        categorySelect.style.border = '1px solid #444';
        categorySelect.style.borderRadius = '4px';
        categorySelect.style.color = '#fff';
        categorySelect.style.marginBottom = '10px';
        categorySelect.style.boxSizing = 'border-box';
        categorySelect.innerHTML = '<option value="">All Categories</option>';
        searchControls.appendChild(categorySelect);
        
        const buttonRow = document.createElement('div');
        buttonRow.style.display = 'flex';
        buttonRow.style.gap = '8px';
        
        const refreshBtn = document.createElement('button');
        refreshBtn.textContent = 'Refresh';
        refreshBtn.style.flex = '1';
        refreshBtn.style.padding = '8px';
        refreshBtn.style.background = '#555';
        refreshBtn.style.color = '#fff';
        refreshBtn.style.border = 'none';
        refreshBtn.style.borderRadius = '4px';
        refreshBtn.style.cursor = 'pointer';
        refreshBtn.style.fontSize = '12px';
        refreshBtn.onmouseover = () => refreshBtn.style.background = '#666';
        refreshBtn.onmouseout = () => refreshBtn.style.background = '#555';
        buttonRow.appendChild(refreshBtn);
        
        const debugBtn = document.createElement('button');
        debugBtn.textContent = 'Debug';
        debugBtn.style.flex = '1';
        debugBtn.style.padding = '8px';
        debugBtn.style.background = '#444';
        debugBtn.style.color = '#fff';
        debugBtn.style.border = 'none';
        debugBtn.style.borderRadius = '4px';
        debugBtn.style.cursor = 'pointer';
        debugBtn.style.fontSize = '12px';
        debugBtn.onmouseover = () => debugBtn.style.background = '#555';
        debugBtn.onmouseout = () => debugBtn.style.background = '#444';
        debugBtn.onclick = async () => {
            try {
                const response = await fetch('/webscraper/library/debug');
                const data = await response.json();
                console.log('Library Debug Info:', data);
                
                let message = `Total images in database: ${data.total_images}\n`;
                message += `DB exists: ${data.db_exists}\n`;
                message += `Library dir exists: ${data.library_dir_exists}\n`;
                message += `Categories: ${data.categories?.join(', ') || 'None'}\n\n`;
                message += `DB Path: ${data.db_path}\n`;
                message += `Library Dir: ${data.library_dir}\n\n`;
                
                if (data.sample_images && data.sample_images.length > 0) {
                    message += `Sample images:\n`;
                    data.sample_images.forEach(img => {
                        message += `- ${img.filename} (exists: ${img.file_exists})\n`;
                    });
                }
                
                message += '\nCheck console for full details.';
                alert(message);
            } catch (error) {
                console.error('Debug error:', error);
                alert('Error checking database. See console for details.');
            }
        };
        
        // Add test button
        const testBtn = document.createElement('button');
        testBtn.textContent = 'Test DB';
        testBtn.style.width = '100%';
        testBtn.style.padding = '8px';
        testBtn.style.background = '#666';
        testBtn.style.color = '#fff';
        testBtn.style.border = 'none';
        testBtn.style.borderRadius = '4px';
        testBtn.style.cursor = 'pointer';
        testBtn.style.fontSize = '12px';
        testBtn.style.marginTop = '8px';
        testBtn.onmouseover = () => testBtn.style.background = '#777';
        testBtn.onmouseout = () => testBtn.style.background = '#666';
        testBtn.onclick = async () => {
            try {
                const response = await fetch('/webscraper/library/test-add', {method: 'POST'});
                const data = await response.json();
                console.log('Test Add Result:', data);
                if (data.success) {
                    alert(`Test image added successfully!\n\nImage path: ${data.image_path}\nImage exists: ${data.image_exists}\n\nClick Refresh to see it.`);
                    setTimeout(() => loadImages(), 500);
                } else {
                    alert(`Failed to add test image:\n${data.error || 'Unknown error'}\n\nCheck console for details.`);
                }
            } catch (error) {
                console.error('Test add error:', error);
                alert('Error testing database. See console for details.');
            }
        };
        searchControls.appendChild(testBtn);
        buttonRow.appendChild(debugBtn);
        
        searchControls.appendChild(buttonRow);
        
        librarySection.appendChild(searchControls);
        
        // Image gallery grid
        const galleryGrid = document.createElement('div');
        galleryGrid.id = 'webscraper-gallery';
        galleryGrid.style.display = 'grid';
        galleryGrid.style.gridTemplateColumns = 'repeat(2, 1fr)';
        galleryGrid.style.gap = '10px';
        galleryGrid.style.maxHeight = '600px';
        galleryGrid.style.overflowY = 'auto';
        galleryGrid.style.overflowX = 'hidden';
        galleryGrid.style.marginTop = '15px';
        galleryGrid.style.paddingRight = '5px';
        librarySection.appendChild(galleryGrid);
        
        // Loading indicator
        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'gallery-loading';
        loadingDiv.textContent = 'Loading images...';
        loadingDiv.style.color = '#aaa';
        loadingDiv.style.textAlign = 'center';
        loadingDiv.style.padding = '20px';
        loadingDiv.style.display = 'none';
        galleryGrid.appendChild(loadingDiv);
        
        container.appendChild(librarySection);
        
        // Load categories and images
        async function loadCategories() {
            try {
                const response = await fetch('/webscraper/library/categories');
                const data = await response.json();
                if (data.success) {
                    categorySelect.innerHTML = '<option value="">All Categories</option>';
                    data.categories.forEach(cat => {
                        const option = document.createElement('option');
                        option.value = cat;
                        option.textContent = cat;
                        categorySelect.appendChild(option);
                    });
                }
            } catch (error) {
                console.error('Error loading categories:', error);
            }
        }
        
        async function loadImages() {
            const loading = document.getElementById('gallery-loading');
            loading.style.display = 'block';
            galleryGrid.innerHTML = '';
            galleryGrid.appendChild(loading);
            
            try {
                const params = new URLSearchParams();
                if (searchInput.value.trim()) {
                    params.append('search_query', searchInput.value.trim());
                }
                if (categorySelect.value) {
                    params.append('category', categorySelect.value);
                }
                params.append('limit', '50');
                
                const response = await fetch(`/webscraper/library/images?${params}`);
                const data = await response.json();
                
                loading.style.display = 'none';
                
                console.log('Library API response:', data);
                
                if (data.success && data.images && data.images.length > 0) {
                    data.images.forEach((img, imageIdx) => {
                        const imgCard = document.createElement('div');
                        imgCard.style.position = 'relative';
                        imgCard.style.background = '#1a1a1a';
                        imgCard.style.borderRadius = '4px';
                        imgCard.style.overflow = 'hidden';
                        imgCard.style.cursor = 'pointer';
                        imgCard.style.border = '2px solid transparent';
                        imgCard.style.display = 'flex';
                        imgCard.style.alignItems = 'center';
                        imgCard.style.justifyContent = 'center';
                        imgCard.style.minHeight = '150px';
                        imgCard.style.maxHeight = '300px';
                        imgCard.onmouseover = () => imgCard.style.borderColor = '#4a9eff';
                        imgCard.onmouseout = () => imgCard.style.borderColor = 'transparent';
                        
                        const imgElement = document.createElement('img');
                        imgElement.style.width = '100%';
                        imgElement.style.height = 'auto';
                        imgElement.style.maxHeight = '300px';
                        imgElement.style.objectFit = 'contain';
                        imgElement.style.display = 'block';
                        
                        // Construct image URL - use our custom endpoint for reliable serving
                        imgElement.src = `/webscraper/library/image/${img.id}`;
                        
                        imgElement.onerror = () => {
                            imgElement.style.display = 'none';
                            const errorDiv = document.createElement('div');
                            errorDiv.textContent = 'Image not found';
                            errorDiv.style.color = '#666';
                            errorDiv.style.padding = '10px';
                            errorDiv.style.textAlign = 'center';
                            errorDiv.style.fontSize = '11px';
                            imgCard.appendChild(errorDiv);
                        };
                        
                        imgCard.appendChild(imgElement);
                        
                        // Add index badge
                        const indexBadge = document.createElement('div');
                        indexBadge.textContent = `#${imageIdx}`;
                        indexBadge.style.position = 'absolute';
                        indexBadge.style.top = '5px';
                        indexBadge.style.left = '5px';
                        indexBadge.style.background = 'rgba(0,0,0,0.7)';
                        indexBadge.style.color = '#fff';
                        indexBadge.style.padding = '2px 6px';
                        indexBadge.style.borderRadius = '3px';
                        indexBadge.style.fontSize = '10px';
                        indexBadge.style.fontWeight = 'bold';
                        imgCard.appendChild(indexBadge);
                        
                        // Add hover overlay with "Use Image" button
                        const overlay = document.createElement('div');
                        overlay.style.position = 'absolute';
                        overlay.style.top = '0';
                        overlay.style.left = '0';
                        overlay.style.width = '100%';
                        overlay.style.height = '100%';
                        overlay.style.background = 'rgba(0, 0, 0, 0.7)';
                        overlay.style.display = 'none';
                        overlay.style.alignItems = 'center';
                        overlay.style.justifyContent = 'center';
                        overlay.style.flexDirection = 'column';
                        overlay.style.gap = '8px';
                        overlay.style.borderRadius = '4px';
                        
                        const useBtn = document.createElement('button');
                        useBtn.textContent = 'Use Image';
                        useBtn.style.padding = '6px 12px';
                        useBtn.style.background = '#4a9eff';
                        useBtn.style.color = '#fff';
                        useBtn.style.border = 'none';
                        useBtn.style.borderRadius = '4px';
                        useBtn.style.cursor = 'pointer';
                        useBtn.style.fontSize = '11px';
                        useBtn.style.fontWeight = '600';
                        useBtn.onmouseover = () => useBtn.style.background = '#3a8eef';
                        useBtn.onmouseout = () => useBtn.style.background = '#4a9eff';
                        useBtn.onclick = (e) => {
                            e.stopPropagation();
                            // Create LoadImageFromLibrary node with this specific image selected
                            const node = LiteGraph.createNode("LoadImageFromLibrary");
                            if (node) {
                                app.graph.add(node);
                                node.pos = [app.canvas.graph_mouse[0], app.canvas.graph_mouse[1]];
                                
                                // Set the image_index to select this specific image
                                // Also set selection_mode to "index" so it uses the index
                                const widgets = node.widgets || [];
                                for (const widget of widgets) {
                                    if (widget.name === 'image_index') {
                                        widget.value = imageIdx;  // Set to clicked image's index
                                    }
                                    if (widget.name === 'selection_mode') {
                                        widget.value = 'index';  // Use index mode
                                    }
                                    if (widget.name === 'category' && img.category) {
                                        widget.value = img.category;
                                    }
                                    if (widget.name === 'search_query' && searchInput.value.trim()) {
                                        widget.value = searchInput.value.trim();
                                    }
                                }
                                
                                app.graph.setDirtyCanvas(true, true);
                                console.log(`Created node with image_index=${imageIdx} for image: ${img.filename}`);
                            }
                        };
                        
                        const previewBtn = document.createElement('button');
                        previewBtn.textContent = 'Preview';
                        previewBtn.style.padding = '6px 12px';
                        previewBtn.style.background = '#555';
                        previewBtn.style.color = '#fff';
                        previewBtn.style.border = 'none';
                        previewBtn.style.borderRadius = '4px';
                        previewBtn.style.cursor = 'pointer';
                        previewBtn.style.fontSize = '11px';
                        previewBtn.style.fontWeight = '600';
                        previewBtn.onmouseover = () => previewBtn.style.background = '#666';
                        previewBtn.onmouseout = () => previewBtn.style.background = '#555';
                        previewBtn.onclick = (e) => {
                            e.stopPropagation();
                            showImagePreview(img);
                        };
                        
                        overlay.appendChild(useBtn);
                        overlay.appendChild(previewBtn);
                        imgCard.appendChild(overlay);
                        
                        // Show overlay on hover
                        imgCard.onmouseenter = () => overlay.style.display = 'flex';
                        imgCard.onmouseleave = () => overlay.style.display = 'none';
                        
                        galleryGrid.appendChild(imgCard);
                    });
                } else {
                    const noImages = document.createElement('div');
                    let message = 'No images found';
                    if (data.success && data.count === 0) {
                        message = 'No images found in library. Scrape some images first!';
                    } else if (!data.success) {
                        message = `Error: ${data.error || 'Failed to load images'}`;
                    }
                    noImages.textContent = message;
                    noImages.style.color = '#666';
                    noImages.style.textAlign = 'center';
                    noImages.style.padding = '20px';
                    noImages.style.fontSize = '12px';
                    galleryGrid.appendChild(noImages);
                }
            } catch (error) {
                loading.style.display = 'none';
                const errorDiv = document.createElement('div');
                errorDiv.textContent = 'Error loading images';
                errorDiv.style.color = '#ff6b6b';
                errorDiv.style.textAlign = 'center';
                errorDiv.style.padding = '20px';
                galleryGrid.appendChild(errorDiv);
                console.error('Error loading images:', error);
            }
        }
        
        // Event listeners
        refreshBtn.onclick = loadImages;
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') loadImages();
        });
        categorySelect.onchange = loadImages;
        
        // Initial load
        loadCategories();
        loadImages();
        
        // Store loadImages function globally so it can be called when scraping completes
        window.refreshImageGallery = loadImages;
        
        el.appendChild(container);
    }
    });
}

// Register node with drawer trigger
app.registerExtension({
    name: "WebScraper",
    async setup() {
        // Add button to WebScraper node
        const node = LiteGraph.createNode("WebScraper");
        if (node) {
            node.onAdded = function() {
                const button = this.addWidget("button", "Open Scraper", null, () => {
                    openWebScraperDrawer();
                });
            };
        }
    },
    nodeCreated(node) {
        if (node.type === "WebScraper") {
            // Add button to open drawer
            setTimeout(() => {
                const button = node.addWidget("button", "Open Scraper", null, () => {
                    openWebScraperDrawer();
                });
            }, 100);
        }
    }
});

// Show image preview in lightbox
function showImagePreview(imageData) {
    // Create lightbox overlay
    const lightbox = document.createElement('div');
    lightbox.id = 'webscraper-lightbox';
    lightbox.style.position = 'fixed';
    lightbox.style.top = '0';
    lightbox.style.left = '0';
    lightbox.style.width = '100%';
    lightbox.style.height = '100%';
    lightbox.style.background = 'rgba(0, 0, 0, 0.9)';
    lightbox.style.zIndex = '20000';
    lightbox.style.display = 'flex';
    lightbox.style.alignItems = 'center';
    lightbox.style.justifyContent = 'center';
    lightbox.style.cursor = 'pointer';
    lightbox.onclick = () => lightbox.remove();
    
    const content = document.createElement('div');
    content.style.position = 'relative';
    content.style.maxWidth = '90%';
    content.style.maxHeight = '90%';
    content.style.cursor = 'default';
    content.onclick = (e) => e.stopPropagation();
    
    const img = document.createElement('img');
    img.src = `/webscraper/library/image/${imageData.id}`;
    img.style.maxWidth = '100%';
    img.style.maxHeight = '90vh';
    img.style.objectFit = 'contain';
    img.style.borderRadius = '8px';
    
    const info = document.createElement('div');
    info.style.color = '#fff';
    info.style.marginTop = '15px';
    info.style.textAlign = 'center';
    info.style.fontSize = '14px';
    info.innerHTML = `
        <div><strong>${imageData.filename || 'Image'}</strong></div>
        ${imageData.category ? `<div style="color: #aaa; margin-top: 5px;">Category: ${imageData.category}</div>` : ''}
        ${imageData.tags ? `<div style="color: #aaa; margin-top: 5px;">Tags: ${imageData.tags}</div>` : ''}
        <div style="color: #888; margin-top: 10px; font-size: 12px;">Click outside to close</div>
    `;
    
    const closeBtn = document.createElement('button');
    closeBtn.textContent = '×';
    closeBtn.style.position = 'absolute';
    closeBtn.style.top = '-40px';
    closeBtn.style.right = '0';
    closeBtn.style.background = 'none';
    closeBtn.style.border = 'none';
    closeBtn.style.color = '#fff';
    closeBtn.style.fontSize = '36px';
    closeBtn.style.cursor = 'pointer';
    closeBtn.style.width = '40px';
    closeBtn.style.height = '40px';
    closeBtn.style.lineHeight = '1';
    closeBtn.onclick = () => lightbox.remove();
    closeBtn.onmouseover = () => closeBtn.style.color = '#ff6b6b';
    closeBtn.onmouseout = () => closeBtn.style.color = '#fff';
    
    content.appendChild(closeBtn);
    content.appendChild(img);
    content.appendChild(info);
    lightbox.appendChild(content);
    
    document.body.appendChild(lightbox);
    
    // Close on Escape key
    const escapeHandler = (e) => {
        if (e.key === 'Escape') {
            lightbox.remove();
            document.removeEventListener('keydown', escapeHandler);
        }
    };
    document.addEventListener('keydown', escapeHandler);
}

// Make functions globally available
window.openWebScraperDrawer = openWebScraperDrawer;
window.closeWebScraperDrawer = closeWebScraperDrawer;
window.startScraping = startScraping;
window.cancelScraping = cancelScraping;
window.showImagePreview = showImagePreview;
