# Jarvis

Jarvis is a Windows desktop assistant for local models. The repository contains the current desktop app, the legacy Python agent and API, the bridge, the memory experiments, and the development journal.

- [Desktop setup and usage](jarvis/desktop/README.md) starts with Python 3.13, the desktop requirements, and a local Ollama installation. Launch [Jarvis Desktop.pyw](<jarvis/Jarvis Desktop.pyw>) and use **Import GGUF** for an existing local model. [Desktop settings](jarvis/config/desktop.json) define the loopback port and paths relative to the repository root.
- [Development journal](development/README.md) links the current state, open issues, decisions, and agent notes. Start here when handing work to another AI. The journal documents the original Windows paths and local evidence, which may need adjustment in a fresh clone.
- The legacy agent uses [jarvis.env.example](jarvis/jarvis.env.example) as a starting point for a local jarvis.env. Set the endpoint and model for your machine. The [bridge](jarvis-bridge/jarvis_bridge.py) also accepts JARVIS_ROOT and JARVIS_PYTHON to locate the project and Python.

Model weights, local credentials, live memory databases, conversation exports, caches, and compiled launchers are excluded. Existing local models can be registered with Ollama on the machine that runs Jarvis.

