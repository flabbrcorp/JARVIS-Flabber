# probe_model.ps1 - READ-ONLY. Asks the two usual local model servers what they are running.
# Run from the JARVIS folder:  powershell -ExecutionPolicy Bypass -File .\probe_model.ps1

Write-Output "=== Ollama (port 11434) ==="
try {
  $r = Invoke-RestMethod -Uri 'http://localhost:11434/api/tags' -TimeoutSec 5 -ErrorAction Stop
  if ($r.models.Count -eq 0) { Write-Output "REACHABLE, but no models listed" }
  foreach ($m in $r.models) { Write-Output ("MODEL: " + $m.name) }
} catch {
  Write-Output ("NOT REACHABLE: " + $_.Exception.Message)
}

Write-Output ""
Write-Output "=== OpenAI-style server (port 1234, e.g. LM Studio) ==="
try {
  $r = Invoke-RestMethod -Uri 'http://localhost:1234/v1/models' -TimeoutSec 5 -ErrorAction Stop
  if ($r.data.Count -eq 0) { Write-Output "REACHABLE, but no models listed" }
  foreach ($m in $r.data) { Write-Output ("MODEL: " + $m.id) }
} catch {
  Write-Output ("NOT REACHABLE: " + $_.Exception.Message)
}

Write-Output ""
Write-Output "=== Anything else listening on common local ports? ==="
foreach ($p in 8080, 8000, 5000, 5001, 3000, 7860, 11435, 8188) {
  $t = Test-NetConnection -ComputerName localhost -Port $p -WarningAction SilentlyContinue
  if ($t.TcpTestSucceeded) { Write-Output ("OPEN: " + $p) }
}
Write-Output "Done."
