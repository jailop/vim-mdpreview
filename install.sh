#!/bin/bash
# Install script for vim-markdown-preview plugin

set -e

echo "Installing Vim Markdown Preview Plugin..."

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3.6+"
    exit 1
fi

echo "✓ Python 3 found"

# Check pip3
if ! command -v pip3 &> /dev/null; then
    echo "Warning: pip3 not found. You may need to install Python dependencies manually."
else
    echo "Installing Python dependencies..."
    pip3 install --user markdown websockets
    echo "✓ Python dependencies installed"
fi

# Check curl
if ! command -v curl &> /dev/null; then
    echo "Warning: curl not found. Install curl for full functionality."
else
    echo "✓ curl found"
fi

# Determine Vim directory
if [ -d "$HOME/.config/nvim" ]; then
    VIM_DIR="$HOME/.config/nvim"
    echo "Installing for Neovim at $VIM_DIR"
elif [ -d "$HOME/.vim" ]; then
    VIM_DIR="$HOME/.vim"
    echo "Installing for Vim at $VIM_DIR"
else
    echo "Creating Vim directory at $HOME/.vim"
    mkdir -p "$HOME/.vim"
    VIM_DIR="$HOME/.vim"
fi

# Copy plugin files
echo "Copying plugin files..."
mkdir -p "$VIM_DIR/plugin"
mkdir -p "$VIM_DIR/autoload"
mkdir -p "$VIM_DIR/server"

cp plugin/mdpreview.vim "$VIM_DIR/plugin/"
cp autoload/mdpreview.vim "$VIM_DIR/autoload/"
cp -r server/* "$VIM_DIR/server/"
chmod +x "$VIM_DIR/server/preview_server.py"

echo "✓ Plugin files copied"

# Create doc directory if needed
if [ -f "doc/mdpreview.txt" ]; then
    mkdir -p "$VIM_DIR/doc"
    cp doc/mdpreview.txt "$VIM_DIR/doc/"
    echo "✓ Documentation copied"
fi

echo ""
echo "Installation complete! 🎉"
echo ""
echo "Usage:"
echo "  1. Open a markdown file in Vim"
echo "  2. Run :MdPreview"
echo "  3. Browser opens with live preview"
echo ""
echo "Commands:"
echo "  :MdPreview        - Start preview"
echo "  :MdPreviewStop    - Stop preview"
echo "  :MdPreviewRefresh - Refresh preview"
echo ""
echo "Configuration (add to .vimrc):"
echo "  let g:mdpreview_port = 8765"
echo "  let g:mdpreview_refresh_on_save = 1"
echo ""
