#!/usr/bin/env python3
"""
Wiki-link and File Inclusion Processor
Handles [[link]], [[link|text]], [[!file]], and [[!file|title]] patterns
"""

import re
from pathlib import Path
from typing import Tuple, Optional


class WikiLinkProcessor:
    def __init__(self, base_path: str = '.'):
        self.base_path = Path(base_path).resolve()
        self.included_files = set()  # Track to prevent circular inclusions
        
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
            
            # Read file content
            try:
                content = resolved_path.read_text(encoding='utf-8')
                
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
    
    def process_wikilink_html(self, html: str) -> str:
        """
        Process wiki-link tags in HTML output from md4c
        Converts <x-wikilink> tags to proper HTML links
        """
        # md4c outputs: <x-wikilink data-target="link">link</x-wikilink>
        # Convert to: <a href="wiki:link" class="wiki-link">link</a>
        pattern = r'<x-wikilink data-target="([^"]+)">([^<]+)</x-wikilink>'
        
        def replace_link(match):
            target = match.group(1)
            text = match.group(2)
            return f'<a href="wiki:{target}" class="wiki-link" data-target="{target}">{text}</a>'
        
        return re.sub(pattern, replace_link, html)
    
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
