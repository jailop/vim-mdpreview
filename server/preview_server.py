#!/usr/bin/env python3
"""
Markdown Preview Server
Provides HTTP server with WebSocket for live markdown preview
Phase 2: With wiki-links, LaTeX, and enhanced features
"""

import sys
import argparse
import asyncio
import json
import mimetypes
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import websockets

# Import our enhanced processor
try:
    from markdown_processor import MarkdownProcessor
    HAS_PROCESSOR = True
except ImportError:
    HAS_PROCESSOR = False
    print("Warning: markdown_processor not found. Using fallback.", file=sys.stderr)
    
    # Fallback: Try basic markdown library
    try:
        import markdown
        HAS_MARKDOWN = True
    except ImportError:
        HAS_MARKDOWN = False
        print("Warning: markdown library not found. Install with: pip3 install markdown", file=sys.stderr)

class PreviewServer:
    def __init__(self, port=8765, base_path='.'):
        self.port = port
        self.base_path = Path(base_path).resolve()
        self.current_html = ""
        self.clients = set()
        self.http_server = None
        self.ws_server = None
        
        # Initialize the enhanced markdown processor
        if HAS_PROCESSOR:
            self.processor = MarkdownProcessor(base_path)
        else:
            self.processor = None
        
    async def websocket_handler(self, websocket, path):
        """Handle WebSocket connections"""
        self.clients.add(websocket)
        try:
            # Send current content immediately
            if self.current_html:
                await websocket.send(self.current_html)
            
            # Keep connection open
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)
    
    async def broadcast_update(self, html):
        """Send update to all connected clients"""
        self.current_html = html
        if self.clients:
            await asyncio.gather(
                *[client.send(html) for client in self.clients],
                return_exceptions=True
            )
    
    def process_markdown(self, content, filepath='', enable_wikilinks=True, enable_latex=True):
        """Convert markdown to HTML with all features"""
        if self.processor:
            # Use enhanced processor with wiki-links and LaTeX
            html = self.processor.convert(content, enable_wikilinks, enable_latex)
        elif HAS_MARKDOWN:
            # Fallback to basic markdown library
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
            html = '<p>' + content.replace('\n\n', '</p><p>').replace('\n', '<br>') + '</p>'
        
        return html
    
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
            const wsPort = window.location.port || 8765;
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
        """Suppress default logging"""
        pass
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html = self.server_instance.get_template_html()
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests for content updates"""
        if self.path == '/update':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode())
                content = data.get('content', '')
                filepath = data.get('filepath', '')
                enable_wikilinks = data.get('enable_wikilinks', True)
                enable_latex = data.get('enable_latex', True)
                
                # Process markdown with options
                html = self.server_instance.process_markdown(
                    content, filepath, enable_wikilinks, enable_latex
                )
                
                # Broadcast to WebSocket clients
                asyncio.run(self.server_instance.broadcast_update(html))
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = json.dumps({'status': 'ok'})
                self.wfile.write(response.encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = json.dumps({'status': 'error', 'message': str(e)})
                self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()

async def start_websocket_server(server, port):
    """Start WebSocket server"""
    async with websockets.serve(server.websocket_handler, 'localhost', port):
        await asyncio.Future()  # run forever

def start_http_server(server, port):
    """Start HTTP server"""
    RequestHandler.server_instance = server
    httpd = HTTPServer(('localhost', port), RequestHandler)
    print(f"Server started on http://localhost:{port}", flush=True)
    httpd.serve_forever()

def main():
    parser = argparse.ArgumentParser(description='Markdown Preview Server')
    parser.add_argument('--port', type=int, default=8765, help='Server port')
    parser.add_argument('--base', type=str, default='.', help='Base directory')
    args = parser.parse_args()
    
    server = PreviewServer(port=args.port, base_path=args.base)
    
    # Start HTTP server in a thread
    http_thread = Thread(target=start_http_server, args=(server, args.port), daemon=True)
    http_thread.start()
    
    # Start WebSocket server
    try:
        asyncio.run(start_websocket_server(server, args.port))
    except KeyboardInterrupt:
        print("\nServer stopped", flush=True)

if __name__ == '__main__':
    main()
