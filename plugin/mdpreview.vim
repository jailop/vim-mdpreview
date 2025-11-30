" mdpreview.vim - Markdown Preview Plugin
" Maintainer: Data Inquiry
" Version: 1.0.0

if exists('g:loaded_mdpreview')
  finish
endif
let g:loaded_mdpreview = 1

" Default configuration
let g:mdpreview_port = get(g:, 'mdpreview_port', 8765)
let g:mdpreview_auto_start = get(g:, 'mdpreview_auto_start', 0)
let g:mdpreview_refresh_on_save = get(g:, 'mdpreview_refresh_on_save', 1)
let g:mdpreview_refresh_on_change = get(g:, 'mdpreview_refresh_on_change', 0)
let g:mdpreview_debounce_delay = get(g:, 'mdpreview_debounce_delay', 300)
let g:mdpreview_browser = get(g:, 'mdpreview_browser', '')
let g:mdpreview_enable_wikilinks = get(g:, 'mdpreview_enable_wikilinks', 1)
let g:mdpreview_enable_latex = get(g:, 'mdpreview_enable_latex', 1)

" Commands
command! MdPreview call mdpreview#start()
command! MdPreviewStop call mdpreview#stop()
command! MdPreviewRefresh call mdpreview#refresh()
command! MdPreviewToggle call mdpreview#toggle()

" Auto-commands for markdown files
augroup mdpreview
  autocmd!
  if g:mdpreview_auto_start
    autocmd FileType markdown call mdpreview#auto_start()
  endif
  if g:mdpreview_refresh_on_save
    autocmd BufWritePost *.md call mdpreview#update()
  endif
  if g:mdpreview_refresh_on_change
    autocmd TextChanged,TextChangedI *.md call mdpreview#debounced_update()
  endif
  autocmd VimLeavePre * call mdpreview#cleanup()
augroup END
