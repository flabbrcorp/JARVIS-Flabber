Write-Output "=== Write to Documents? (policy allows, workspace blocks?) ==="
try {
  Set-Content -Path 'C:\Users\flab\Documents\__jarvis_probe.txt' -Value 'probe' -Encoding utf8 -ErrorAction Stop
  Write-Output "WRITE OK"
  Remove-Item 'C:\Users\flab\Documents\__jarvis_probe.txt' -ErrorAction SilentlyContinue
} catch {
  Write-Output ("WRITE BLOCKED: " + $_.Exception.Message)
}

Write-Output "=== Read from Documents? (policy allows, workspace blocks?) ==="
try {
  $c = Invoke-WebRequest -Uri 'file://C:/Users/flab/Documents/bus/crowd_runner%20(2).html' -UseBasicParsing -TimeoutSec 10
  Write-Output ("READ OK HTTP " + $c.StatusCode)
} catch {
  Write-Output ("READ BLOCKED: " + $_.Exception.Message)
}
