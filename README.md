# Vim Markdown Preview Plugin

Live markdown preview in your browser with automatic refresh, wiki-links, LaTeX formulas, and syntax highlighting.

## Features

### Phase 1 - Basic Features ✅
- ✅ Basic markdown rendering (tables, lists, code blocks, etc.)
- ✅ Live preview in browser
- ✅ WebSocket auto-refresh
- ✅ Manual and auto-update on save
- ✅ HTTP server with Python backend
- ✅ GitHub-style rendering

### Phase 2 - Extended Features ✅
- ✅ **Wiki-Links**: `[[note]]` and `[[note|display text]]`
- ✅ **File Inclusion**: `[[!file]]` and `[[!file|title]]`
- ✅ **LaTeX Formulas**: Inline `$E=mc^2$` and display `$$...$$`
- ✅ **Syntax Highlighting**: Code blocks with highlight.js
- ✅ KaTeX integration for beautiful math rendering
- ✅ Circular inclusion detection
- ✅ Error handling and graceful fallbacks

### Phase 3 - Performance Optimizations ✅
- ✅ **Debounced Updates**: Client and server-side debouncing (300ms default)
- ✅ **Incremental Rendering**: Content hash-based caching (2400x faster for cached content)
- ✅ **Cached File Inclusions**: Modification time-based caching (80% faster for repeated includes)
- ✅ **Performance Monitoring**: `/stats` endpoint for monitoring cache performance
- ✅ **Memory Management**: Bounded caches with automatic eviction
- ✅ **Position Sync**: Preview scrolls automatically to match cursor position in Vim

See [PERFORMANCE.md](PERFORMANCE.md) and [POSITION_SYNC.md](POSITION_SYNC.md) for detailed documentation.

## Installation

### Requirements

- Vim 8+ or Neovim 0.5+
- Python 3.7+
- `curl` command

### Install Python Dependencies

```bash
pip3 install -r requirements.txt
```

Or manually:

```bash
pip3 install markdown websockets
```

**Note**: The plugin uses the standard `markdown` library which is widely available and supports most features including tables, code blocks, and more. PyMD4C was listed as an optional dependency for advanced features like wiki-links, but it's not required - the plugin works perfectly with the standard markdown library.

### Install Plugin

#### Using vim-plug

Add to your `.vimrc`:

```vim
Plug 'datainquiry/vim-preview'
```

#### Manual Installation

Copy files to your Vim directory:

```bash
cp -r plugin autoload server templates ~/.vim/
```

Or for Neovim:

```bash
cp -r plugin autoload server templates ~/.config/nvim/
```

## Usage

### Basic Commands

- `:MdPreview` - Start preview server and open browser
- `:MdPreviewStop` - Stop preview server
- `:MdPreviewRefresh` - Manually refresh preview
- `:MdPreviewToggle` - Toggle preview on/off

### Quick Start

1. Open a markdown file in Vim
2. Run `:MdPreview`
3. Browser opens automatically with live preview
4. Edit and save - preview updates automatically
5. Move your cursor - preview scrolls to match your position

### Position Sync

The preview automatically scrolls to match your cursor position in Vim:
- Move to different sections and watch the preview follow
- No manual scrolling needed to find what you're editing
- Smooth scrolling for a natural experience

See [POSITION_SYNC.md](POSITION_SYNC.md) for technical details.

## Configuration

Add to your `.vimrc` or `init.vim`:

```vim
" HTTP server port (default: 8765)
let g:mdpreview_port = 8765

" WebSocket server port (default: 8766)
let g:mdpreview_ws_port = 8766

" Auto-start preview when opening markdown files (default: 0)
let g:mdpreview_auto_start = 0

" Refresh on save (default: 1)
let g:mdpreview_refresh_on_save = 1

" Refresh while typing with debouncing (default: 0)
" Recommended: 1 for live editing experience
let g:mdpreview_refresh_on_change = 0

" Debounce delay in ms for auto-refresh (default: 300)
" Lower = faster updates but more CPU usage
" Higher = less CPU usage but slower updates
let g:mdpreview_debounce_delay = 300

" Custom browser command (empty = auto-detect)
let g:mdpreview_browser = ''
" Examples:
" let g:mdpreview_browser = 'firefox'
" let g:mdpreview_browser = 'google-chrome'

" Enable wiki-links [[link]] (default: 1)
let g:mdpreview_enable_wikilinks = 1

" Enable LaTeX formulas $...$ (default: 1)
let g:mdpreview_enable_latex = 1
```

### Performance Tips

- **For active editing**: Enable `g:mdpreview_refresh_on_change = 1` with default debounce (300ms)
- **For battery life**: Use `g:mdpreview_refresh_on_save = 1` only
- **For large documents**: Increase `g:mdpreview_debounce_delay` to 500ms or higher
- **For rapid feedback**: Decrease to 150ms (may increase CPU usage)

The plugin uses intelligent caching to make repeated renders nearly instant. See [PERFORMANCE.md](PERFORMANCE.md) for details.

## Feature Examples

### Wiki-Links

```markdown
Link to another note: [[my-note]]
Link with custom text: [[my-note|Click here]]
```

### File Inclusion

```markdown
Include another file: [[!other-file]]
Include with title: [[!other-file|Custom Title]]
```

### LaTeX Formulas

```markdown
Inline math: $E = mc^2$

Display math:
$$
\int_a^b f(x) dx = F(b) - F(a)
$$
```

### Syntax Highlighting

````markdown
```python
def hello():
    print("Hello, world!")
```
````

## How It Works

1. **Vim Plugin**: Monitors buffer changes and sends markdown content
2. **Python Server**: Converts markdown to HTML using `markdown` library
3. **WebSocket**: Pushes updates to browser in real-time
4. **Browser**: Auto-refreshes with smooth animations

## Architecture

```
┌─────────────┐
│     Vim     │
│   Buffer    │
└──────┬──────┘
       │ HTTP POST
       ▼
┌─────────────────┐      WebSocket     ┌──────────────┐
│  Python Server  │◄──────────────────►│   Browser    │
│  - md → HTML    │                    │   Preview    │
│  - WebSocket    │                    └──────────────┘
└─────────────────┘
```

## Troubleshooting

### Server won't start

- Check Python 3 is installed: `python3 --version`
- Install dependencies: `pip3 install markdown websockets`
- Check port is not in use: `lsof -i :8765`

### Browser doesn't open

- Set custom browser: `let g:mdpreview_browser = 'firefox'`
- Manually open: `http://localhost:8765`

### Preview not updating

- Check `curl` is installed: `which curl`
- Run `:MdPreviewRefresh` manually
- Check Vim messages: `:messages`

## Development Status

### Phase 1 ✅ Complete

- [x] Project structure
- [x] VimScript plugin skeleton
- [x] Python HTTP server with WebSocket
- [x] Basic markdown conversion
- [x] HTML template with auto-refresh
- [x] Browser auto-open
- [x] Update on save
- [x] Manual commands

### Phase 2 ✅ Complete

- [x] Wiki-link support `[[note]]`
- [x] File inclusion `[[!file]]`
- [x] LaTeX formulas with KaTeX
- [x] Syntax highlighting
- [x] Debounced auto-update
- [x] Circular inclusion detection
- [x] Error handling

### Phase 3 (Future)

- [ ] Themes (light/dark/sepia)
- [ ] Scroll synchronization
- [ ] Export to HTML/PDF
- [ ] Advanced wiki-link navigation
- [ ] Table of contents generation

## License

MIT License

## Contributing

Issues and pull requests welcome!
