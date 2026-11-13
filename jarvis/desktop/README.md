# Jarvis Desktop

On this PC, double-click **Jarvis Desktop.pyw** in the Jarvis folder. Jarvis starts its own local Ollama server as needed.
Pick a model from the top bar. The next message uses that model and keeps the current
chat's history. Enter sends, Shift+Enter adds a line, and Ctrl+N opens a new chat.
Use Import GGUF to register an existing local model with Ollama.

Open **Memory** in the sidebar to save a short fact or preference. Choose
**When relevant** for topic-specific information or **Every chat** for a
standing preference. Select an existing entry to correct or forget it.
After a reply, the status line lists the memories included in its prompt.
In chat, send a short statement such as `Remember that I prefer concise replies.`
or `Save to memory: My project is called Atlas.` Desktop saves it as a relevant note
and confirms the result in the transcript. `Save my name (Flab) in your memories.`
saves a standing note. Use the Memory sidebar to edit a note or change its scope.

The desktop database is `D:\AI_JARVIS\data\desktop.sqlite3`.
The Windows launcher uses `%LOCALAPPDATA%\Jarvis\desktop-venv`. To recreate the
environment, install Python 3.13 and run from this checkout:

```powershell
$jarvisRuntime = Join-Path $env:LOCALAPPDATA 'Jarvis\desktop-venv'
py -3.13 -m venv $jarvisRuntime
& (Join-Path $jarvisRuntime 'Scripts\python.exe') -m pip install -r desktop/requirements.txt
```

Desktop history and model selection live in the chat service. The Ollama adapter
uses loopback and bypasses proxy settings. This release supports local text chat.

