import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import threading
import time


class DevServer:
    def __init__(self, port: int, iframe_port: int):
        self.port = port
        self.iframe_port = iframe_port
        self.app = self._create_app()
        
    def _create_app(self) -> FastAPI:
        app = FastAPI(title="Ubidots Pages Dev Server")
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @app.get("/", response_class=HTMLResponse)
        async def dashboard_preview():
            return self._get_dashboard_html()
            
        @app.get("/health")
        async def health():
            return {"status": "ok", "iframe_port": self.iframe_port}
            
        return app
    
    def _get_dashboard_html(self) -> str:
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ubidots Pages - Development Preview</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f6fa;
        }}
        
        .context-bar {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .logo-section {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        
        .logo {{
            font-size: 20px;
            font-weight: bold;
        }}
        
        .nav {{
            display: flex;
            gap: 24px;
        }}
        
        .nav-item {{
            color: rgba(255,255,255,0.9);
            text-decoration: none;
            padding: 8px 12px;
            border-radius: 4px;
            transition: background-color 0.2s;
        }}
        
        .nav-item:hover {{
            background-color: rgba(255,255,255,0.1);
            color: white;
        }}
        
        .nav-item.active {{
            background-color: rgba(255,255,255,0.2);
            color: white;
        }}
        
        .user-section {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .user-avatar {{
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: rgba(255,255,255,0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        }}
        
        .main-content {{
            padding: 24px;
            height: calc(100vh - 68px);
        }}
        
        .page-container {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            height: 100%;
            overflow: hidden;
            position: relative;
        }}
        
        .page-header {{
            padding: 16px 24px;
            border-bottom: 1px solid #e1e8ed;
            background: #fafbfc;
        }}
        
        .page-title {{
            font-size: 18px;
            font-weight: 600;
            color: #333;
        }}
        
        .page-content {{
            height: calc(100% - 60px);
            position: relative;
        }}
        
        .iframe-container {{
            width: 100%;
            height: 100%;
            position: relative;
        }}
        
        .iframe-placeholder {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #666;
            text-align: center;
            background: #f8f9fa;
        }}
        
        .iframe-placeholder h2 {{
            margin-bottom: 12px;
            color: #333;
        }}
        
        .iframe-placeholder p {{
            margin-bottom: 8px;
            line-height: 1.5;
        }}
        
        .iframe-placeholder code {{
            background: #e9ecef;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
        }}
        
        .custom-page-iframe {{
            width: 100%;
            height: 100%;
            border: none;
            background: white;
        }}
        
        .status-indicator {{
            position: absolute;
            top: 16px;
            right: 24px;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }}
        
        .status-waiting {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .status-connected {{
            background: #d4edda;
            color: #155724;
        }}
    </style>
</head>
<body>
    <div class="context-bar">
        <div class="logo-section">
            <div class="logo">🔷 Ubidots</div>
            <nav class="nav">
                <a href="#" class="nav-item">Dashboard</a>
                <a href="#" class="nav-item">Devices</a>
                <a href="#" class="nav-item">Variables</a>
                <a href="#" class="nav-item">Functions</a>
                <a href="#" class="nav-item active">Custom Pages</a>
                <a href="#" class="nav-item">Analytics</a>
            </nav>
        </div>
        <div class="user-section">
            <span>Developer Mode</span>
            <div class="user-avatar">D</div>
        </div>
    </div>
    
    <div class="main-content">
        <div class="page-container">
            <div class="page-header">
                <h1 class="page-title">Custom Page Development Preview</h1>
                <div id="status" class="status-indicator status-waiting">
                    Waiting for content...
                </div>
            </div>
            <div class="page-content">
                <div class="iframe-container">
                    <div id="placeholder" class="iframe-placeholder">
                        <h2>🚀 Ready for Development!</h2>
                        <p>Your custom page will appear here once you start serving content on:</p>
                        <p><code>http://localhost:{self.iframe_port}</code></p>
                        <br>
                        <p>💡 <strong>Quick Start:</strong></p>
                        <p>1. Create an HTML file in your project</p>
                        <p>2. Serve it on port {self.iframe_port}</p>
                        <p>3. Watch it appear in this iframe!</p>
                        <br>
                        <p>🔄 The page will auto-reload when you make changes</p>
                    </div>
                    <iframe 
                        id="customPageIframe"
                        class="custom-page-iframe"
                        src="http://localhost:{self.iframe_port}"
                        style="display: none;"
                        onload="handleIframeLoad()"
                        onerror="handleIframeError()">
                    </iframe>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let retryCount = 0;
        const maxRetries = 60; // 5 minutes with 5 second intervals
        
        function checkIframeContent() {{
            const iframe = document.getElementById('customPageIframe');
            const placeholder = document.getElementById('placeholder');
            const status = document.getElementById('status');
            
            // Try to load the iframe content
            fetch('http://localhost:{self.iframe_port}')
                .then(response => {{
                    if (response.ok) {{
                        iframe.style.display = 'block';
                        placeholder.style.display = 'none';
                        status.textContent = 'Connected';
                        status.className = 'status-indicator status-connected';
                        return;
                    }}
                    throw new Error('No content available');
                }})
                .catch(() => {{
                    iframe.style.display = 'none';
                    placeholder.style.display = 'flex';
                    status.textContent = 'Waiting for content...';
                    status.className = 'status-indicator status-waiting';
                    
                    retryCount++;
                    if (retryCount < maxRetries) {{
                        setTimeout(checkIframeContent, 5000);
                    }}
                }});
        }}
        
        function handleIframeLoad() {{
            const status = document.getElementById('status');
            status.textContent = 'Connected';
            status.className = 'status-indicator status-connected';
        }}
        
        function handleIframeError() {{
            const iframe = document.getElementById('customPageIframe');
            const placeholder = document.getElementById('placeholder');
            iframe.style.display = 'none';
            placeholder.style.display = 'flex';
        }}
        
        // Start checking for content
        setTimeout(checkIframeContent, 1000);
        
        // Reload iframe every 5 seconds to catch new content
        setInterval(() => {{
            const iframe = document.getElementById('customPageIframe');
            if (iframe.style.display !== 'none') {{
                iframe.src = iframe.src;
            }}
        }}, 5000);
    </script>
</body>
</html>
        """


def start_dev_server(port: int, iframe_port: int):
    server = DevServer(port, iframe_port)
    
    config = uvicorn.Config(
        server.app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False
    )
    
    server_instance = uvicorn.Server(config)
    server_instance.run()