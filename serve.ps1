# Tiny static file server on http://localhost:3000
# Serves files from the .\site folder. Press Ctrl+C to stop.

$ErrorActionPreference = 'Stop'
$root = Join-Path $PSScriptRoot 'site'
$port = if ($env:PORT) { $env:PORT } else { '3000' }
$prefix = "http://localhost:$port/"

$mime = @{
  '.html' = 'text/html; charset=utf-8'
  '.htm'  = 'text/html; charset=utf-8'
  '.css'  = 'text/css; charset=utf-8'
  '.js'   = 'application/javascript; charset=utf-8'
  '.json' = 'application/json; charset=utf-8'
  '.svg'  = 'image/svg+xml'
  '.png'  = 'image/png'
  '.jpg'  = 'image/jpeg'
  '.jpeg' = 'image/jpeg'
  '.gif'  = 'image/gif'
  '.ico'  = 'image/x-icon'
  '.txt'  = 'text/plain; charset=utf-8'
}

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add($prefix)
$listener.Start()
Write-Host "Serving $root at $prefix"
Write-Host "Press Ctrl+C to stop."

try {
  while ($listener.IsListening) {
    $ctx = $listener.GetContext()
    $req = $ctx.Request
    $res = $ctx.Response

    $path = [System.Uri]::UnescapeDataString($req.Url.AbsolutePath)
    if ($path -eq '/' -or $path -eq '') { $path = '/index.html' }
    $full = Join-Path $root ($path.TrimStart('/'))

    try {
      if ((Test-Path $full -PathType Container)) {
        $full = Join-Path $full 'index.html'
      }
      if (Test-Path $full -PathType Leaf) {
        $ext = [System.IO.Path]::GetExtension($full).ToLowerInvariant()
        $ct = if ($mime.ContainsKey($ext)) { $mime[$ext] } else { 'application/octet-stream' }
        $bytes = [System.IO.File]::ReadAllBytes($full)
        $res.ContentType = $ct
        $res.ContentLength64 = $bytes.Length
        $res.OutputStream.Write($bytes, 0, $bytes.Length)
        Write-Host "200 $path"
      } else {
        $res.StatusCode = 404
        $body = [Text.Encoding]::UTF8.GetBytes("404 Not Found: $path")
        $res.OutputStream.Write($body, 0, $body.Length)
        Write-Host "404 $path"
      }
    } catch {
      $res.StatusCode = 500
      $msg = [Text.Encoding]::UTF8.GetBytes("500 $($_.Exception.Message)")
      $res.OutputStream.Write($msg, 0, $msg.Length)
      Write-Host "500 $path - $($_.Exception.Message)"
    } finally {
      $res.Close()
    }
  }
} finally {
  $listener.Stop()
  $listener.Close()
}
