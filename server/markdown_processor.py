#!/usr/bin/env python3
"""
Enhanced Markdown Processor
Uses md4c for parsing with extensions, processes wiki-links and LaTeX
Performance optimized with caching and incremental updates
"""

import re
import hashlib
from pathlib import Path
from typing import Optional, Dict, Tuple
from functools import lru_cache

# Try md4c first (best option)
try:
    import md4c
    HAS_MD4C = True
except ImportError:
    HAS_MD4C = False

# Fallback to markdown library
try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

from wikilinks import WikiLinkProcessor
from latex_processor import LaTeXProcessor


class MarkdownProcessor:
    def __init__(self, base_path: str = '.'):
        self.base_path = Path(base_path).resolve()
        self.wikilink_processor = WikiLinkProcessor(base_path)
        self.latex_processor = LaTeXProcessor()
        
        # Performance caches
        self._content_cache: Dict[str, Tuple[str, str]] = {}  # hash -> (content, html)
        self._last_hash: Optional[str] = None
        self._incremental_enabled = True
        
    def convert(self, markdown_text: str, enable_wikilinks: bool = True, 
                enable_latex: bool = True, force: bool = False) -> str:
        """
        Convert markdown to HTML with all extensions
        Uses content hash for caching to avoid redundant processing
        """
        # Calculate content hash for cache lookup
        content_hash = self._hash_content(markdown_text, enable_wikilinks, enable_latex)
        
        # Check cache unless forced
        if not force and self._incremental_enabled:
            if content_hash == self._last_hash and content_hash in self._content_cache:
                # Return cached result
                return self._content_cache[content_hash][1]
        
        # Clear inclusion cache for each new document
        self.wikilink_processor.clear_inclusion_cache()
        
        # Step 1: Process file inclusions (before markdown conversion)
        if enable_wikilinks:
            markdown_text = self.wikilink_processor.process(markdown_text)
        
        # Step 2: Convert markdown to HTML
        html = self.markdown_to_html(markdown_text, enable_wikilinks, enable_latex)
        
        # Step 3: Process wiki-link tags in HTML
        if enable_wikilinks:
            html = self.wikilink_processor.process_wikilink_html(html)
        
        # Step 4: Process LaTeX tags
        if enable_latex:
            html = self.latex_processor.process(html)
        
        # Update cache
        self._content_cache[content_hash] = (markdown_text, html)
        self._last_hash = content_hash
        
        # Limit cache size to avoid memory bloat
        if len(self._content_cache) > 10:
            # Keep only the most recent 10 entries
            oldest_keys = list(self._content_cache.keys())[:-10]
            for key in oldest_keys:
                del self._content_cache[key]
        
        return html
    
    def _hash_content(self, text: str, enable_wikilinks: bool, enable_latex: bool) -> str:
        """Generate hash of content and settings for cache key"""
        content = f"{text}|{enable_wikilinks}|{enable_latex}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear the conversion cache"""
        self._content_cache.clear()
        self._last_hash = None
        self.wikilink_processor.clear_inclusion_cache()
    
    def enable_incremental(self, enabled: bool = True):
        """Enable or disable incremental rendering"""
        self._incremental_enabled = enabled
    
    def markdown_to_html(self, text: str, enable_wikilinks: bool = True,
                        enable_latex: bool = True) -> str:
        """
        Convert markdown to HTML using available parser
        """
        if HAS_MD4C:
            return self._convert_with_md4c(text, enable_wikilinks, enable_latex)
        elif HAS_MARKDOWN:
            return self._convert_with_markdown(text)
        else:
            return self._convert_simple(text)
    
    def _convert_with_md4c(self, text: str, enable_wikilinks: bool,
                          enable_latex: bool) -> str:
        """Convert using md4c library (preferred)"""
        # Set up flags
        flags = (
            md4c.MD_FLAG_TABLES |
            md4c.MD_FLAG_STRIKETHROUGH |
            md4c.MD_FLAG_TASKLISTS |
            md4c.MD_FLAG_PERMISSIVEAUTOLINKS |
            md4c.MD_FLAG_PERMISSIVEURLAUTOLINKS |
            md4c.MD_FLAG_PERMISSIVEEMAILAUTOLINKS
        )
        
        if enable_wikilinks:
            flags |= md4c.MD_FLAG_WIKILINKS
        
        if enable_latex:
            flags |= md4c.MD_FLAG_LATEXMATHSPANS
        
        # Convert
        try:
            html = md4c.parse(text, flags)
            return html
        except Exception as e:
            print(f"md4c error: {e}")
            return self._convert_simple(text)
    
    def _convert_with_markdown(self, text: str) -> str:
        """Convert using Python markdown library (fallback)"""
        # Preprocess: Protect LaTeX equations from being touched by markdown
        latex_blocks = []
        
        def save_latex_block(match):
            latex_blocks.append(match.group(0))
            placeholder = f"\n\nLATEXBLOCK{len(latex_blocks)-1}ENDBLOCK\n\n"
            return placeholder
        
        # Protect display math ($$...$$) - must handle multi-line
        text = re.sub(r'\$\$(.*?)\$\$', save_latex_block, text, flags=re.DOTALL)
        
        # Protect inline math ($...$)
        def save_inline_latex(match):
            latex_blocks.append(match.group(0))
            return f"LATEXINLINE{len(latex_blocks)-1}ENDINLINE"
        text = re.sub(r'\$([^\$\n]+?)\$', save_inline_latex, text)
        
        # Convert markdown
        md = markdown.Markdown(extensions=[
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
            'markdown.extensions.codehilite',
            'markdown.extensions.sane_lists',
            'markdown.extensions.toc',
        ])
        html = md.convert(text)
        
        # Restore LaTeX equations
        for i, latex_block in enumerate(latex_blocks):
            html = html.replace(f"<p>LATEXBLOCK{i}ENDBLOCK</p>", latex_block)
            html = html.replace(f"LATEXBLOCK{i}ENDBLOCK", latex_block)
            html = html.replace(f"LATEXINLINE{i}ENDINLINE", latex_block)
        
        return html
    
    def _convert_simple(self, text: str) -> str:
        """Simple fallback conversion (no library available)"""
        # Protect LaTeX equations first
        latex_blocks = []
        def save_latex_block(match):
            latex_blocks.append(match.group(0))
            return f"\n\nLATEXBLOCK{len(latex_blocks)-1}ENDBLOCK\n\n"
        
        # Protect display math ($$...$$)
        html = re.sub(r'\$\$(.*?)\$\$', save_latex_block, text, flags=re.DOTALL)
        
        # Protect inline math ($...$)
        def save_inline_latex(match):
            latex_blocks.append(match.group(0))
            return f"LATEXINLINE{len(latex_blocks)-1}ENDINLINE"
        html = re.sub(r'\$([^\$\n]+?)\$', save_inline_latex, html)
        
        # Headers
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        
        # Bold and italic (before paragraph processing)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # Code
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)
        
        # Paragraphs - split by double newlines or headers/latex blocks
        lines = html.split('\n')
        paragraphs = []
        current_para = []
        
        for line in lines:
            line_stripped = line.strip()
            # Check if line is a header, empty, or LaTeX block
            if (line_stripped == '' or 
                line_stripped.startswith('<h') or 
                'LATEXBLOCK' in line_stripped):
                # Save current paragraph
                if current_para:
                    para_text = ' '.join(current_para)
                    if not para_text.startswith('<h'):
                        para_text = f'<p>{para_text}</p>'
                    paragraphs.append(para_text)
                    current_para = []
                # Add special line
                if line_stripped.startswith('<h') or 'LATEXBLOCK' in line_stripped:
                    paragraphs.append(line_stripped)
            else:
                current_para.append(line_stripped)
        
        # Save last paragraph
        if current_para:
            para_text = ' '.join(current_para)
            paragraphs.append(f'<p>{para_text}</p>')
        
        html = '\n'.join(paragraphs)
        
        # Restore LaTeX equations
        for i, latex_block in enumerate(latex_blocks):
            html = html.replace(f"<p>LATEXBLOCK{i}ENDBLOCK</p>", latex_block)
            html = html.replace(f"LATEXBLOCK{i}ENDBLOCK", latex_block)
            html = html.replace(f"LATEXINLINE{i}ENDINLINE", latex_block)
        
        return html
