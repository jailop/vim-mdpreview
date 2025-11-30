" autoload/mdpreview.vim - Core functionality

let s:server_running = 0
let s:server_job = -1
let s:update_timer = -1
let s:plugin_dir = expand('<sfile>:p:h:h')
let s:current_file = ''

function! mdpreview#start() abort
  if s:server_running
    echo "Preview server already running"
    call mdpreview#update()
    return
  endif
  
  if &filetype != 'markdown'
    echohl WarningMsg
    echo "MdPreview: Not a markdown file"
    echohl None
    return
  endif
  
  let l:server_script = s:plugin_dir . '/server/preview_server.py'
  
  if !executable('python3')
    echohl ErrorMsg
    echo "MdPreview: python3 not found"
    echohl None
    return
  endif
  
  if !filereadable(l:server_script)
    echohl ErrorMsg
    echo "MdPreview: Server script not found at " . l:server_script
    echohl None
    return
  endif
  
  let l:base_path = expand('%:p:h')
  let l:port = g:mdpreview_port
  let l:ws_port = g:mdpreview_ws_port
  let s:current_file = expand('%:p')
  
  " Start server
  if has('nvim')
    let s:server_job = jobstart(['python3', l:server_script, '--port', l:port, '--ws-port', l:ws_port, '--base', l:base_path], {
          \ 'on_stdout': function('s:on_server_output'),
          \ 'on_stderr': function('s:on_server_error'),
          \ 'on_exit': function('s:on_server_exit'),
          \ })
  else
    let s:server_job = job_start(['python3', l:server_script, '--port', l:port, '--ws-port', l:ws_port, '--base', l:base_path], {
          \ 'out_cb': function('s:on_server_output'),
          \ 'err_cb': function('s:on_server_error'),
          \ 'exit_cb': function('s:on_server_exit'),
          \ })
  endif
  
  if s:server_job <= 0
    echohl ErrorMsg
    echo "MdPreview: Failed to start preview server"
    echohl None
    return
  endif
  
  let s:server_running = 1
  echo "MdPreview: Starting server on port " . l:port . "..."
  
  " Wait a moment for server to start, then open browser and send content
  call timer_start(1000, function('s:open_browser_and_update'))
endfunction

function! mdpreview#stop() abort
  if !s:server_running
    echo "Preview server not running"
    return
  endif
  
  " Stop server
  if has('nvim')
    call jobstop(s:server_job)
  else
    call job_stop(s:server_job)
  endif
  
  let s:server_running = 0
  let s:server_job = -1
  echo "MdPreview: Server stopped"
endfunction

function! mdpreview#toggle() abort
  if s:server_running
    call mdpreview#stop()
  else
    call mdpreview#start()
  endif
endfunction

function! mdpreview#update() abort
  if !s:server_running
    return
  endif
  
  let l:content = join(getline(1, '$'), "\n")
  let l:filepath = expand('%:p')
  
  " Send content to server
  call s:send_update(l:content, l:filepath)
endfunction

function! mdpreview#refresh() abort
  call mdpreview#update()
endfunction

function! mdpreview#debounced_update() abort
  if !s:server_running
    return
  endif
  
  " Cancel previous timer
  if s:update_timer != -1
    call timer_stop(s:update_timer)
  endif
  
  " Start new timer
  let s:update_timer = timer_start(g:mdpreview_debounce_delay, function('s:do_update'))
endfunction

function! mdpreview#auto_start() abort
  if g:mdpreview_auto_start && &filetype == 'markdown'
    call mdpreview#start()
  endif
endfunction

function! mdpreview#cleanup() abort
  call mdpreview#stop()
endfunction

" Private functions
function! s:open_browser_and_update(timer) abort
  let l:url = 'http://localhost:' . g:mdpreview_port
  
  " Open browser
  call s:open_browser(l:url)
  
  " Send initial content
  call timer_start(500, function('s:do_update'))
endfunction

function! s:do_update(timer) abort
  call mdpreview#update()
endfunction

function! s:send_update(content, filepath) abort
  let l:url = 'http://localhost:' . g:mdpreview_port . '/update'
  
  " Prepare JSON data with wiki-links and LaTeX options
  let l:data = {
        \ 'content': a:content,
        \ 'filepath': a:filepath,
        \ 'enable_wikilinks': g:mdpreview_enable_wikilinks,
        \ 'enable_latex': g:mdpreview_enable_latex
        \ }
  let l:json = json_encode(l:data)
  
  " Create temporary file for POST data
  let l:tmpfile = tempname()
  call writefile([l:json], l:tmpfile)
  
  " Send via curl
  if executable('curl')
    let l:cmd = 'curl -s -X POST -H "Content-Type: application/json" -d @' 
          \ . shellescape(l:tmpfile) . ' ' . l:url . ' >/dev/null 2>&1'
    call system(l:cmd)
    call delete(l:tmpfile)
  else
    echohl WarningMsg
    echo "MdPreview: curl not found, cannot update preview"
    echohl None
  endif
endfunction

function! s:open_browser(url) abort
  if !empty(g:mdpreview_browser)
    let l:cmd = g:mdpreview_browser . ' ' . shellescape(a:url) . ' &'
    call system(l:cmd)
    return
  endif
  
  " Auto-detect browser
  if has('mac')
    call system('open ' . shellescape(a:url) . ' &')
  elseif has('unix')
    if executable('xdg-open')
      call system('xdg-open ' . shellescape(a:url) . ' >/dev/null 2>&1 &')
    elseif executable('firefox')
      call system('firefox ' . shellescape(a:url) . ' >/dev/null 2>&1 &')
    elseif executable('google-chrome')
      call system('google-chrome ' . shellescape(a:url) . ' >/dev/null 2>&1 &')
    endif
  elseif has('win32') || has('win64')
    call system('start ' . shellescape(a:url))
  endif
endfunction

" Server callbacks
function! s:on_server_output(job_id, data, ...) abort
  if type(a:data) == v:t_list
    for line in a:data
      if !empty(line)
        echo "MdPreview: " . line
      endif
    endfor
  elseif type(a:data) == v:t_string && !empty(a:data)
    echo "MdPreview: " . a:data
  endif
endfunction

function! s:on_server_error(job_id, data, ...) abort
  if type(a:data) == v:t_list
    for line in a:data
      if !empty(line)
        echohl ErrorMsg
        echo "MdPreview error: " . line
        echohl None
      endif
    endfor
  elseif type(a:data) == v:t_string && !empty(a:data)
    echohl ErrorMsg
    echo "MdPreview error: " . a:data
    echohl None
  endif
endfunction

function! s:on_server_exit(job_id, status, ...) abort
  let s:server_running = 0
  if a:status != 0
    echohl WarningMsg
    echo "MdPreview: Server exited with status " . a:status
    echohl None
  endif
endfunction
