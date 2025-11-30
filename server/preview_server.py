#!/usr/bin/env python3
"""
Markdown Preview Server
Provides HTTP server with WebSocket for live markdown preview
Phase 2: With wiki-links, LaTeX, and enhanced features
Performance Optimized: With debouncing, caching, and incremental rendering
"""

import sys
import argparse
import asyncio
import json
import mimetypes
import time
import logging
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread, Lock
import websockets

# Setup logging
LOG_FILE = Path.home() / '.vim' / 'mdpreview.log'
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger('mdpreview')

# Import our enhanced processor
try:
    from markdown_processor import MarkdownProcessor
    HAS_PROCESSOR = True
    logger.info("Loaded MarkdownProcessor successfully")
except ImportError as e:
    HAS_PROCESSOR = False
    logger.warning(f"markdown_processor not found: {e}. Using fallback.")
    
    # Fallback: Try basic markdown library
    try:
        import markdown
        HAS_MARKDOWN = True
        logger.info("Loaded basic markdown library")
    except ImportError as e:
        HAS_MARKDOWN = False
        logger.error(f"markdown library not found: {e}. Install with: pip3 install markdown")

class PreviewServer:
    def __init__(self, port=8765, base_path='.'):
        logger.info(f"Initializing PreviewServer on port {port}, base_path={base_path}")
        self.port = port
        self.base_path = Path(base_path).resolve()
        self.current_html = ""
        self.clients = set()
        self.http_server = None
        self.ws_server = None
        self.loop = None  # Will be set to the asyncio event loop
        
        # Initialize the enhanced markdown processor
        if HAS_PROCESSOR:
            self.processor = MarkdownProcessor(base_path)
            logger.info("Using MarkdownProcessor")
        else:
            self.processor = None
            logger.info("Using fallback processor")
        
        # Debouncing state
        self._debounce_task = None
        self._debounce_delay = 0.3  # 300ms debounce
        self._pending_update = None
        self._update_lock = Lock()
        
        # Performance monitoring
        self._update_count = 0
        self._total_processing_time = 0.0
        self._cache_hits = 0
        
    async def websocket_handler(self, websocket):
        """Handle WebSocket connections"""
        logger.info(f"New WebSocket connection from {websocket.remote_address}")
        self.clients.add(websocket)
        try:
            # Send current content immediately
            if self.current_html:
                logger.debug(f"Sending current HTML ({len(self.current_html)} bytes) to new client")
                message = json.dumps({'html': self.current_html, 'scroll_percent': None})
                await websocket.send(message)
            else:
                logger.debug("No current HTML to send to new client")
            
            # Keep connection open
            await websocket.wait_closed()
        except Exception as e:
            logger.error(f"WebSocket error: {e}", exc_info=True)
        finally:
            logger.info(f"WebSocket connection closed from {websocket.remote_address}")
            self.clients.remove(websocket)
    
    async def broadcast_update(self, html, scroll_percent=None):
        """Send update to all connected clients"""
        logger.debug(f"Broadcasting update to {len(self.clients)} clients ({len(html)} bytes, scroll={scroll_percent}%)")
        self.current_html = html
        if self.clients:
            # Create message with HTML and optional scroll position
            message = {
                'html': html,
                'scroll_percent': scroll_percent
            }
            message_str = json.dumps(message)
            
            results = await asyncio.gather(
                *[client.send(message_str) for client in self.clients],
                return_exceptions=True
            )
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to send to client {i}: {result}")
    
    def process_markdown(self, content, filepath='', enable_wikilinks=True, enable_latex=True):
        """Convert markdown to HTML with all features and performance tracking"""
        start_time = time.time()
        logger.debug(f"Processing markdown: {len(content)} bytes, filepath={filepath}")
        
        try:
            if self.processor:
                # Use enhanced processor with wiki-links and LaTeX
                logger.debug("Using MarkdownProcessor")
                html = self.processor.convert(content, enable_wikilinks, enable_latex)
                self._cache_hits += 1 if self.processor._last_hash in self.processor._content_cache else 0
            elif HAS_MARKDOWN:
                # Fallback to basic markdown library
                logger.debug("Using basic markdown library")
                md = markdown.Markdown(extensions=[
                    'markdown.extensions.tables',
                    'markdown.extensions.fenced_code',
                    'markdown.extensions.codehilite',
                    'markdown.extensions.nl2br',
                    'markdown.extensions.sane_lists',
                    'markdown.extensions.toc',
                ])
                html = md.convert(content)
            else:
                # Simple fallback conversion
                logger.warning("Using simple fallback conversion")
                html = '<p>' + content.replace('\n\n', '</p><p>').replace('\n', '<br>') + '</p>'
            
            # Track performance
            processing_time = time.time() - start_time
            self._total_processing_time += processing_time
            self._update_count += 1
            
            logger.info(f"Markdown processed in {processing_time:.3f}s ({len(html)} bytes HTML)")
            return html
        except Exception as e:
            logger.error(f"Error processing markdown: {e}", exc_info=True)
            return f"<p style='color: red;'>Error processing markdown: {e}</p>"
    
    async def queue_update(self, content, filepath='', enable_wikilinks=True, enable_latex=True, scroll_percent=None):
        """Queue an update with debouncing"""
        logger.debug(f"Queuing update: {len(content)} bytes, scroll={scroll_percent}%")
        with self._update_lock:
            # Store pending update
            self._pending_update = (content, filepath, enable_wikilinks, enable_latex, scroll_percent)
            
            # Cancel existing debounce task
            if self._debounce_task and not self._debounce_task.done():
                logger.debug("Cancelling previous debounce task")
                self._debounce_task.cancel()
            
            # Create new debounce task
            self._debounce_task = asyncio.create_task(self._debounced_update())
    
    async def _debounced_update(self):
        """Execute update after debounce delay"""
        try:
            logger.debug(f"Debouncing for {self._debounce_delay}s")
            await asyncio.sleep(self._debounce_delay)
            
            with self._update_lock:
                if self._pending_update:
                    content, filepath, enable_wikilinks, enable_latex, scroll_percent = self._pending_update
                    self._pending_update = None
                    logger.info(f"Executing debounced update (scroll={scroll_percent}%)")
                    
                    # Process and broadcast
                    html = self.process_markdown(content, filepath, enable_wikilinks, enable_latex)
                    await self.broadcast_update(html, scroll_percent)
        except asyncio.CancelledError:
            # Task was cancelled, this is expected
            logger.debug("Debounce task cancelled")
            pass
        except Exception as e:
            logger.error(f"Error in debounced update: {e}", exc_info=True)
    
    def get_stats(self):
        """Get performance statistics"""
        avg_time = (self._total_processing_time / self._update_count) if self._update_count > 0 else 0
        stats = {
            'updates': self._update_count,
            'avg_processing_time_ms': avg_time * 1000,
            'total_time_s': self._total_processing_time,
            'cache_hits': self._cache_hits
        }
        
        if self.processor and hasattr(self.processor, 'wikilink_processor'):
            wl_stats = self.processor.wikilink_processor.get_cache_stats()
            stats['file_cache'] = wl_stats
        
        return stats
    
    def get_template_html(self):
        """Get HTML template"""
        template_path = Path(__file__).parent.parent / 'templates' / 'preview.html'
        if template_path.exists():
            return template_path.read_text()
        else:
            # Inline template
            return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Markdown Preview</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #fff;
            padding: 20px;
            max-width: 900px;
            margin: 0 auto;
        }
        #content {
            animation: fadeIn 0.3s;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        h1, h2, h3, h4, h5, h6 {
            margin: 1.5em 0 0.5em 0;
            font-weight: 600;
            line-height: 1.25;
        }
        h1 { font-size: 2em; border-bottom: 2px solid #eaecef; padding-bottom: 0.3em; }
        h2 { font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
        h3 { font-size: 1.25em; }
        p { margin: 1em 0; }
        a { color: #0366d6; text-decoration: none; }
        a:hover { text-decoration: underline; }
        code {
            background: #f6f8fa;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
            font-size: 85%;
        }
        pre {
            background: #f6f8fa;
            padding: 16px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 1em 0;
        }
        pre code {
            background: none;
            padding: 0;
            font-size: 100%;
        }
        blockquote {
            border-left: 4px solid #dfe2e5;
            padding: 0 1em;
            color: #6a737d;
            margin: 1em 0;
        }
        ul, ol { margin: 1em 0; padding-left: 2em; }
        li { margin: 0.25em 0; }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }
        th, td {
            border: 1px solid #dfe2e5;
            padding: 8px 12px;
            text-align: left;
        }
        th {
            background: #f6f8fa;
            font-weight: 600;
        }
        img { max-width: 100%; height: auto; }
        hr {
            border: 0;
            border-top: 2px solid #eaecef;
            margin: 2em 0;
        }
        .status {
            position: fixed;
            top: 10px;
            right: 10px;
            padding: 5px 10px;
            background: #28a745;
            color: white;
            border-radius: 4px;
            font-size: 12px;
            opacity: 0;
            transition: opacity 0.3s;
        }
        .status.show { opacity: 1; }
        .status.error { background: #dc3545; }
    </style>
</head>
<body>
    <div class="status" id="status">Connected</div>
    <div id="content"></div>
    
    <script>
        let ws = null;
        let reconnectTimer = null;
        
        function connect() {
            // WebSocket runs on HTTP port + 1
            const httpPort = parseInt(window.location.port) || 8765;
            const wsPort = httpPort + 1;
            ws = new WebSocket('ws://localhost:' + wsPort + '/ws');
            
            ws.onopen = function() {
                showStatus('Connected', false);
            };
            
            ws.onmessage = function(event) {
                document.getElementById('content').innerHTML = event.data;
                showStatus('Updated', false);
            };
            
            ws.onerror = function(error) {
                showStatus('Connection error', true);
            };
            
            ws.onclose = function() {
                showStatus('Disconnected', true);
                // Attempt to reconnect after 2 seconds
                reconnectTimer = setTimeout(connect, 2000);
            };
        }
        
        function showStatus(message, isError) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status show' + (isError ? ' error' : '');
            setTimeout(() => {
                status.className = 'status';
            }, 2000);
        }
        
        connect();
    </script>
</body>
</html>"""

class RequestHandler(BaseHTTPRequestHandler):
    server_instance = None
    
    def log_message(self, format, *args):
        """Custom logging to use our logger"""
        logger.debug(f"HTTP {format % args}")
    
    def do_GET(self):
        """Handle GET requests"""
        logger.debug(f"GET {self.path}")
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html = self.server_instance.get_template_html()
            self.wfile.write(html.encode())
            logger.info(f"Served template HTML ({len(html)} bytes)")
        else:
            self.send_response(404)
            self.end_headers()
            logger.warning(f"404: {self.path}")
    
    def do_POST(self):
        """Handle POST requests for content updates"""
        logger.debug(f"POST {self.path}")
        if self.path == '/update':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode())
                content = data.get('content', '')
                filepath = data.get('filepath', '')
                enable_wikilinks = data.get('enable_wikilinks', True)
                enable_latex = data.get('enable_latex', True)
                scroll_percent = data.get('scroll_percent', None)
                
                logger.info(f"Update request: {len(content)} bytes, filepath={filepath}, scroll={scroll_percent}%")
                
                # Schedule update in the asyncio loop
                if self.server_instance.loop:
                    asyncio.run_coroutine_threadsafe(
                        self.server_instance.queue_update(
                            content, filepath, enable_wikilinks, enable_latex, scroll_percent
                        ),
                        self.server_instance.loop
                    )
                else:
                    logger.error("No event loop available!")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = json.dumps({'status': 'ok'})
                self.wfile.write(response.encode())
                
            except Exception as e:
                logger.error(f"Error processing update request: {e}", exc_info=True)
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = json.dumps({'status': 'error', 'message': str(e)})
                self.wfile.write(response.encode())
        elif self.path == '/stats':
            # Performance statistics endpoint
            try:
                stats = self.server_instance.get_stats()
                logger.debug(f"Stats request: {stats}")
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = json.dumps(stats, indent=2)
                self.wfile.write(response.encode())
            except Exception as e:
                logger.error(f"Error getting stats: {e}", exc_info=True)
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = json.dumps({'status': 'error', 'message': str(e)})
                self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()

async def start_websocket_server(server, ws_port):
    """Start WebSocket server"""
    # Set the event loop reference
    server.loop = asyncio.get_event_loop()
    logger.info(f"Starting WebSocket server on port {ws_port}")
    
    async def handler(websocket):
        logger.debug(f"WebSocket handler called for {websocket.remote_address}")
        await server.websocket_handler(websocket)
    
    try:
        async with websockets.serve(handler, 'localhost', ws_port):
            logger.info(f"WebSocket server listening on ws://localhost:{ws_port}")
            await asyncio.Future()  # run forever
    except Exception as e:
        logger.error(f"WebSocket server error: {e}", exc_info=True)
        raise

def start_http_server(server, port):
    """Start HTTP server"""
    RequestHandler.server_instance = server
    httpd = HTTPServer(('localhost', port), RequestHandler)
    logger.info(f"HTTP server started on http://localhost:{port}")
    print(f"Server started on http://localhost:{port}", flush=True)
    httpd.serve_forever()

def main():
    parser = argparse.ArgumentParser(description='Markdown Preview Server')
    parser.add_argument('--port', type=int, default=8765, help='HTTP server port')
    parser.add_argument('--ws-port', type=int, default=8766, help='WebSocket server port')
    parser.add_argument('--base', type=str, default='.', help='Base directory')
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info(f"Starting Markdown Preview Server")
    logger.info(f"HTTP port: {args.port}, WebSocket port: {args.ws_port}")
    logger.info(f"Base path: {args.base}")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info("="*60)
    
    server = PreviewServer(port=args.port, base_path=args.base)
    
    # Start HTTP server in a thread
    http_thread = Thread(target=start_http_server, args=(server, args.port), daemon=True)
    http_thread.start()
    
    # Start WebSocket server on separate port
    try:
        asyncio.run(start_websocket_server(server, args.ws_port))
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        print("\nServer stopped", flush=True)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        print(f"Error: {e}", flush=True)

if __name__ == '__main__':
    main()
