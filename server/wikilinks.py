#!/usr/bin/env python3
"""
Wiki-link and File Inclusion Processor
Handles [[link]], [[link|text]], [[!file]], and [[!file|title]] patterns
Performance optimized with file content caching
"""

import re
import hashlib
import time
from pathlib import Path
from typing import Tuple, Optional, Dict


class WikiLinkProcessor:
    def __init__(self, base_path: str = '.'):
        self.base_path = Path(base_path).resolve()
        self.included_files = set()  # Track to prevent circular inclusions
        
        # File content cache: filepath -> (mtime, content)
        self._file_cache: Dict[Path, Tuple[float, str]] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
    def process(self, markdown_text: str) -> str:
        """
        Process wiki-links and inclusions in markdown text
        Returns modified markdown with inclusions expanded
        """
        # First, handle file inclusions (before markdown conversion)
        result = self.process_inclusions(markdown_text)
        
        # Wiki-links will be handled after markdown conversion
        return result
    
    def process_inclusions(self, markdown_text: str) -> str:
        """
        Process [[!file]] and [[!file|title]] inclusions
        Expands file content inline before markdown conversion
        Uses cached file contents when available
        """
        # Pattern: [[!target]] or [[!target|title]]
        pattern = r'\[\[!([^\]|]+)(?:\|([^\]]+))?\]\]'
        
        def replace_inclusion(match):
            target = match.group(1).strip()
            title = match.group(2).strip() if match.group(2) else target
            
            # Resolve file path
            resolved_path = self.resolve_file_path(target)
            
            if not resolved_path:
                return self.format_inclusion_error(target, "File not found")
            
            # Check for circular inclusion
            if resolved_path in self.included_files:
                return self.format_inclusion_error(target, "Circular inclusion detected")
            
            # Read file content with caching
            try:
                content = self._read_file_cached(resolved_path)
                
                # Track inclusion
                self.included_files.add(resolved_path)
                
                # Format the inclusion with a title
                result = f'\n\n<div class="included-content">\n'
                result += f'<div class="inclusion-title">{title}</div>\n\n'
                result += content
                result += '\n\n</div>\n\n'
                
                return result
                
            except Exception as e:
                return self.format_inclusion_error(target, f"Cannot read file: {str(e)}")
        
        return re.sub(pattern, replace_inclusion, markdown_text)
    
    def _read_file_cached(self, filepath: Path) -> str:
        """
        Read file with caching based on modification time
        Returns cached content if file hasn't changed
        """
        try:
            current_mtime = filepath.stat().st_mtime
            
            # Check cache
            if filepath in self._file_cache:
                cached_mtime, cached_content = self._file_cache[filepath]
                if cached_mtime == current_mtime:
                    self._cache_hits += 1
                    return cached_content
            
            # Read file and update cache
            self._cache_misses += 1
            content = filepath.read_text(encoding='utf-8')
            self._file_cache[filepath] = (current_mtime, content)
            
            # Limit cache size
            if len(self._file_cache) > 50:
                # Remove oldest entries (simple FIFO)
                oldest_keys = list(self._file_cache.keys())[:-50]
                for key in oldest_keys:
                    del self._file_cache[key]
            
            return content
            
        except Exception as e:
            raise e
    
    def process_wikilink_html(self, html: str) -> str:
        """
        Process wiki-link tags in HTML output
        Handles both md4c's <x-wikilink> tags and raw [[...]] syntax
        """
        # First, handle md4c output: <x-wikilink data-target="link">link</x-wikilink>
        # Convert to: <a href="wiki:link" class="wiki-link">link</a>
        pattern1 = r'<x-wikilink data-target="([^"]+)">([^<]+)</x-wikilink>'
        
        def replace_md4c_link(match):
            target = match.group(1)
            text = match.group(2)
            return f'<a href="wiki:{target}" class="wiki-link" data-target="{target}">{text}</a>'
        
        html = re.sub(pattern1, replace_md4c_link, html)
        
        # Second, handle raw [[...]] syntax from markdown library
        # Pattern: [[target]] or [[target|text]]
        pattern2 = r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'
        
        def replace_bracket_link(match):
            target = match.group(1).strip()
            text = match.group(2).strip() if match.group(2) else target
            return f'<a href="wiki:{target}" class="wiki-link" data-target="{target}">{text}</a>'
        
        html = re.sub(pattern2, replace_bracket_link, html)
        
        return html
    
    def resolve_file_path(self, target: str) -> Optional[Path]:
        """
        Resolve a wiki-link target to an actual file path
        Tries .md, .markdown, and exact name
        """
        # Try different extensions
        extensions = ['.md', '.markdown', '']
        
        for ext in extensions:
            file_path = self.base_path / f"{target}{ext}"
            if file_path.exists() and file_path.is_file():
                return file_path
        
        return None
    
    def format_inclusion_error(self, target: str, error_msg: str) -> str:
        """Format an error message for failed inclusion"""
        return (
            f'\n\n<div class="inclusion-error">\n'
            f'<strong>Inclusion Error:</strong> {error_msg}: {target}\n'
            f'</div>\n\n'
        )
    
    def clear_inclusion_cache(self):
        """Clear the inclusion tracking (call for each new document)"""
        self.included_files.clear()
    
    def clear_file_cache(self):
        """Clear the file content cache"""
        self._file_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for monitoring"""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        return {
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'total': total,
            'hit_rate': hit_rate,
            'cache_size': len(self._file_cache)
        }
