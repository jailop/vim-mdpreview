" autoload/mdpreview.vim - Core functionality

let s:server_running = 0
let s:server_job = v:null
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
  
  " Check if job start failed (in nvim, jobstart returns -1 on error)
  if has('nvim')
    if s:server_job <= 0
      echohl ErrorMsg
      echo "MdPreview: Failed to start preview server"
      echohl None
      return
    endif
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
  let s:server_job = v:null
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
  " Log function call
  let l:logfile = expand('~/.vim/mdpreview_vim.log')
  
  " Check actual job status, not the flag
  let l:job_alive = s:is_job_alive()
  call writefile([strftime('%Y-%m-%d %H:%M:%S') . ' - mdpreview#update() called, server_running=' . s:server_running . ', job_alive=' . string(l:job_alive)], l:logfile, 'a')
  
  if !l:job_alive
    call writefile([strftime('%Y-%m-%d %H:%M:%S') . ' - Job not alive, returning'], l:logfile, 'a')
    return
  endif
  
  " Update the flag if job is alive but flag says otherwise
  if !s:server_running && l:job_alive
    let s:server_running = 1
  endif
  
  let l:content = join(getline(1, '$'), "\n")
  let l:filepath = expand('%:p')
  
  " Get cursor position and calculate scroll percentage
  let l:cursor_line = line('.')
  let l:total_lines = line('$')
  let l:scroll_percent = (l:cursor_line * 100.0) / l:total_lines
  
  " Send content to server
  call s:send_update(l:content, l:filepath, l:scroll_percent)
endfunction

function! mdpreview#refresh() abort
  call mdpreview#update()
endfunction

function! mdpreview#debounced_update() abort
  " Check actual job status
  if !s:is_job_alive()
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

function! mdpreview#debug_status() abort
  " Check actual job status first
  let l:job_alive = s:is_job_alive()
  
  echo "Server running flag: " . s:server_running
  echo "Job actually alive: " . string(l:job_alive)
  
  if s:server_job isnot v:null
    if has('nvim')
      try
        let l:pid = jobpid(s:server_job)
        echo "Server job: process " . l:pid . " (nvim)"
      catch
        echo "Server job: invalid"
      endtry
    else
      try
        let l:job_status = job_status(s:server_job)
        echo "Server job: " . l:job_status . " (vim)"
      catch
        echo "Server job: invalid"
      endtry
    endif
  else
    echo "Server job: not started"
  endif
  
  echo "Update timer: " . s:update_timer
  echo "Current file: " . s:current_file
  echo "Port: " . g:mdpreview_port
  echo "WS Port: " . g:mdpreview_ws_port
  
  " Show log files
  echo "Vim log: ~/.vim/mdpreview_vim.log"
  echo "Server log: ~/.vim/mdpreview_server.log"
  
  " Try to send an update now
  if l:job_alive
    echo "Forcing update..."
    call mdpreview#update()
  else
    echo "Server not running!"
  endif
  
  " Show last few lines from logs
  echo "\n=== Last 5 lines from vim log ==="
  let l:vim_log = expand('~/.vim/mdpreview_vim.log')
  if filereadable(l:vim_log)
    let l:lines = readfile(l:vim_log)
    for line in l:lines[-5:]
      echo line
    endfor
  else
    echo "Log file not found"
  endif
  
  echo "\n=== Last 10 lines from server log ==="
  let l:server_log = expand('~/.vim/mdpreview_server.log')
  if filereadable(l:server_log)
    let l:lines = readfile(l:server_log)
    for line in l:lines[-10:]
      echo line
    endfor
  else
    echo "Log file not found"
  endif
endfunction

" Private functions
function! s:open_browser_and_update(timer) abort
  let l:url = 'http://localhost:' . g:mdpreview_port
  
  " Open browser
  call s:open_browser(l:url)
  
  " Log browser opening
  let l:logfile = expand('~/.vim/mdpreview_vim.log')
  call writefile([strftime('%Y-%m-%d %H:%M:%S') . ' - Opening browser: ' . l:url], l:logfile, 'a')
  
  " Send initial content
  call timer_start(500, function('s:do_update'))
endfunction

function! s:do_update(timer) abort
  call mdpreview#update()
endfunction

function! s:send_update(content, filepath, scroll_percent) abort
  let l:url = 'http://localhost:' . g:mdpreview_port . '/update'
  
  " Log to file
  let l:logfile = expand('~/.vim/mdpreview_vim.log')
  call writefile([strftime('%Y-%m-%d %H:%M:%S') . ' - Sending update: ' . len(a:content) . ' bytes, filepath=' . a:filepath . ', scroll=' . a:scroll_percent . '%'], l:logfile, 'a')
  
  " Prepare JSON data with wiki-links, LaTeX options, and scroll position
  let l:data = {
        \ 'content': a:content,
        \ 'filepath': a:filepath,
        \ 'enable_wikilinks': g:mdpreview_enable_wikilinks,
        \ 'enable_latex': g:mdpreview_enable_latex,
        \ 'scroll_percent': a:scroll_percent
        \ }
  let l:json = json_encode(l:data)
  
  " Create temporary file for POST data
  let l:tmpfile = tempname()
  call writefile([l:json], l:tmpfile)
  
  " Send via curl
  if executable('curl')
    let l:cmd = 'curl -s -X POST -H "Content-Type: application/json" -d @' 
          \ . shellescape(l:tmpfile) . ' ' . l:url . ' 2>&1'
    let l:output = system(l:cmd)
    call writefile([strftime('%Y-%m-%d %H:%M:%S') . ' - curl output: ' . l:output], l:logfile, 'a')
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
  " Log stderr to file instead of showing as errors
  let l:logfile = expand('~/.vim/mdpreview_server.log')
  if type(a:data) == v:t_list
    for line in a:data
      if !empty(line)
        call writefile([strftime('%Y-%m-%d %H:%M:%S') . ' - ' . line], l:logfile, 'a')
      endif
    endfor
  elseif type(a:data) == v:t_string && !empty(a:data)
    call writefile([strftime('%Y-%m-%d %H:%M:%S') . ' - ' . a:data], l:logfile, 'a')
  endif
endfunction

function! s:is_job_alive() abort
  if s:server_job is v:null
    return 0
  endif
  
  if has('nvim')
    try
      let l:pid = jobpid(s:server_job)
      return l:pid > 0
    catch
      return 0
    endtry
  else
    try
      let l:job_status = job_status(s:server_job)
      return l:job_status == 'run'
    catch
      return 0
    endtry
  endif
endfunction

function! s:on_server_exit(job_id, status, ...) abort
  " Log the exit event but don't change the flag
  " The flag will be checked dynamically by s:is_job_alive()
  let l:logfile = expand('~/.vim/mdpreview_server.log')
  call writefile([strftime('%Y-%m-%d %H:%M:%S') . ' - Server exit callback: status=' . a:status], l:logfile, 'a')
  
  " Only show error if server actually died
  if !s:is_job_alive()
    let s:server_running = 0
    if a:status != 0
      echohl WarningMsg
      echo "MdPreview: Server exited with status " . a:status
      echohl None
    endif
  endif
endfunction
