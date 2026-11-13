# Roblox Studio — Combat-Readiness Checklist

Goal: let Jarvis open a local place and run build/iterate scripts unattended.

## Status (2026-10-28)
- ✅ Roblox Studio installed. Path: `C:\Users\flab\AppData\Local\Roblox\Versions\version-76e1a02649ad4f35\RobloxStudioBeta.exe`
- ✅ CLI works: `--task EditFile --localPlaceFile <path>`, `--task RunScript --runScriptFile <path> --outputFile <path> --quitAfterExecution`, `--api <path>`.
- ✅ `RobloxController.ps1` written (Open-Project / Run-Script / Dump-API / New-Auth).
- ❌ **Not logged into Roblox** — no `.ROBLOSECURITY` token in `%APPDATA%`.
- ❌ API dump not done yet.

## What "go nap" requires (order matters)
1. **Log in** — run the Quick Login flow in `New-Auth.ps1` once → produces `C:\Users\flab\AppData\ROBLOSECURITY`. (Needs your creds — do it once, then I don't.)
2. **Dump the API** — Jarvis runs `Dump-API` → writes full Roblox Luau API surface to `roblox-api.json`. Then Jarvis has the full function reference and doesn't need to web-search during builds.
3. **Point at a place** — a local place file (`*.rbxl`) on disk. Jarvis opens it with `Open-Project` and builds from there.

## Notes
- Studio is a GUI app → it opens a window on your PC. It runs on your machine, not headless in the cloud.
- `--api` gives the full API surface (no third-party module needed).
- No third-party PowerShell module is required; the exe CLI is enough.
