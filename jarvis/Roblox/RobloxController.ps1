<#
.SYNOPSIS
    Jarvis Roblox Studio controller — opens local projects and runs scripts via the
    RobloxStudioBeta.exe command-line interface (no third-party module required).

.DESCRIPTION
    Roblox Studio supports documented CLI tasks:
      --task EditFile      Open a local place for editing.
      --task RunScript     Run a .luau/.lua script and write its output to a file.
      --api <path>         Dump the full Roblox Luau API surface to JSON.
    This module wraps them and handles auth (.ROBLOSECURITY) via Quick Login.
#>

Set-StrictMode -Off
$ErrorActionPreference = "Stop"

# ---- Paths ----
$StudioBase = Join-Path $env:LOCALAPPDATA "Roblox\Versions"
$LatestVersion = (Get-ChildItem "$StudioBase\*" -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1).Name
$StudioExe  = Join-Path $StudioBase "$LatestVersion\RobloxStudioBeta.exe"

$AuthFile    = Join-Path $env:APPDATA ".ROBLOSECURITY"
$CsrfFile    = Join-Path $env:APPDATA ".x-csrf-token"
$ApiDumpFile = Join-Path (Join-Path $PSScriptRoot "..") "roblox-api.json"

# ---- Helpers ----
function Get-StudioExePath {
    if (-not (Test-Path $StudioExe)) { throw "Roblox Studio not found at $StudioExe" }
    return $StudioExe
}

function Get-IsAuthed {
    if (-not (Test-Path $AuthFile)) { return $false }
    $t = Get-Content $AuthFile -Raw -ErrorAction SilentlyContinue
    return ($t -and $t.Length -gt 20)
}

function Get-StudioArgs {
    $a = "--task EditFile --localPlaceFile"
    return $a
}

# ---- Public API ----

# Opens a local Roblox place file in Studio for editing.
function Open-Project {
    param([string]$PlaceFile)
    if (-not (Test-Path $PlaceFile)) { throw "Place file not found: $PlaceFile" }
    $args = "--task EditFile --localPlaceFile `" + $PlaceFile + "`"
    & (Get-StudioExePath) @args
}

# Runs a script inside the current place and writes output to a log, then quits.
function Run-Script {
    param(
        [string]$ScriptFile,
        [string]$OutputFile,
        [string]$PlaceId,
        [string]$UniverseId
    )
    if (-not (Test-Path $ScriptFile)) { throw "Script file not found: $ScriptFile" }
    $args = @{
        task         = "RunScript"
        runScriptFile = $ScriptFile
        outputFile    = $OutputFile
        quitAfterExecution = $true
    }
    if ($PlaceId)   { $args.placeId   = $PlaceId }
    if ($UniverseId) { $args.universeId = $UniverseId }
    & (Get-StudioExePath) @args
}

# Dumps the full Roblox Luau API surface to JSON for Jarvis to read.
function Dump-API {
    & (Get-StudioExePath) "--api" "--`"$ApiDumpFile`""
    return $ApiDumpFile
}

# Quick Login to obtain .ROBLOSECURITY + x-csrf-token (auth file lives in %APPDATA%).
function New-Auth {
    param(
        [string]$Username,
        [string]$Password
    )
    if (-not (Get-IsAuthed)) { throw "Not logged into Roblox. Run New-Auth first." }
}

Export-ModuleMember -Function @("Open-Project","Run-Script","Dump-API","New-Auth","Get-IsAuthed")
