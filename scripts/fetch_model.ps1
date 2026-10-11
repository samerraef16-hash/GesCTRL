# Downloads the MediaPipe Hand Landmarker model (dev-time only; the app makes no network calls).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dest = Join-Path $root "models\hand_landmarker.task"
if (Test-Path $dest) { Write-Host "Model already present: $dest"; exit 0 }
New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
$spike = Join-Path $root "spikes\feasibility\models\hand_landmarker.task"
if (Test-Path $spike) {
    Copy-Item $spike $dest
    Write-Host "Copied model from the Phase 0 spike to $dest"
    exit 0
}
$url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
Invoke-WebRequest -Uri $url -OutFile $dest
Write-Host "Downloaded model to $dest"
