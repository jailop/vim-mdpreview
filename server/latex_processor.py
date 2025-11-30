#!/usr/bin/env python3
"""
LaTeX Formula Processor
Converts md4c LaTeX output to KaTeX-friendly format
"""

import re


class LaTeXProcessor:
    def __init__(self):
        pass
    
    def process(self, html: str) -> str:
        """
        Process LaTeX formulas in HTML output
        Converts md4c <x-equation> tags to KaTeX format
        """
        # md4c outputs:
        # - Block formulas: <x-equation type="display">...</x-equation>
        # - Inline formulas: <x-equation>...</x-equation>
        
        # Convert block formulas to $$...$$
        html = re.sub(
            r'<x-equation type="display">([^<]*)</x-equation>',
            r'$$\1$$',
            html
        )
        
        # Convert inline formulas to $...$
        html = re.sub(
            r'<x-equation>([^<]*)</x-equation>',
            r'$\1$',
            html
        )
        
        return html
