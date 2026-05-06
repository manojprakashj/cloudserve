<div align="center">


**A modern, hackable file server with Cloudflare Tunnel support**

A better alternative to `python -m http.server` and `updog`

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue?style=flat-square&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.x-black?style=flat-square&logo=flask)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey?style=flat-square)]()

</div>

---

## What is CloudServe?

CloudServe is a single file Python HTTP file server built for pentesters, CTF players, developers, and anyone who needs to quickly share files over a network. It runs on a **random free port by default** (no port conflicts), has a clean white minimal web UI, and can expose itself to the internet in seconds via a **Cloudflare Quick Tunnel** no account, no registration required.

---

## Features

| | Feature | Details |
|---|---|---|
| 📁 | **Directory browsing** | Clean minimal UI with file type icons, sortable columns |
| ⬆️ | **File upload** | Drag-and-drop anywhere on the page or click to browse, with progress bar |
| ⬇️ | **File download** | Direct download per file or download entire folder as `.zip` |
| ☁️ | **Cloudflare Tunnel** | One-click public URL no account needed, auto-installs `cloudflared` |
| 🎛️ | **Tunnel control panel** | Start / Stop / Restart tunnel live from the browser, with live log viewer |
| 🔒 | **HTTP Basic Auth** | Protect with `--auth user:pass` |
| 🔍 | **Live file filter** | Instant client-side search/filter by filename |
| 📂 | **New folder** | Create directories from the web UI |
| 🗑️ | **Optional delete** | Enable with `--delete` flag |
| 🔐 | **Read-only mode** | `--readonly` disables all writes |
| 🔗 | **Copy link** | One-click copy of direct download URL to clipboard |
| 🖱️ | **Context menu** | Right-click any file or folder for quick actions |
| 🎲 | **Random port** | Picks a free port automatically no conflicts, no guessing |
| 📦 | **Single file** | Just `cloudserve.py` + a `templates/` folder. No bloat. |

---

<img width="1482" height="756" alt="image" src="https://github.com/user-attachments/assets/9b7d1ac7-9926-4b7e-a445-8bd23f46bf9d" />


<img width="1562" height="873" alt="image" src="https://github.com/user-attachments/assets/4ebb0a75-39e7-47e5-a920-058aa373687d" />


<img width="1563" height="866" alt="image" src="https://github.com/user-attachments/assets/f705b111-a9aa-486f-a8da-793f666db4b4" />


<img width="1566" height="870" alt="image" src="https://github.com/user-attachments/assets/cdf1cfdb-1ee3-45ae-a961-9f5ca2b8a73a" />



## Quick Start

```bash
# Clone
git clone https://github.com/yourname/cloudserve.git
cd cloudserve

# Install dependency
pip install flask

# Run
python3 cloudserve.py
```

That's it. A browser tab opens automatically.

---

## Installation

### As a global command (recommended)

```bash
# Method 1 copy to PATH (works everywhere, no venv)
chmod +x cloudserve.py
sudo cp cloudserve.py /usr/local/bin/cloudserve

# Method 2 pip editable install
pip install -e .

# Method 3 pipx (cleanest isolation)
pipx install .

# Method 4 shell alias
echo 'alias cloudserve="python3 /path/to/cloudserve/cloudserve.py"' >> ~/.bashrc
source ~/.bashrc
```

After any of the above, just run:

```bash
cloudserve
cloudserve /tmp/files --tunnel
cloudserve --auth admin:secret --delete
```

### Dependencies

```
Python 3.7+
flask >= 2.3.0
werkzeug >= 2.3.0
```

Flask is auto-installed on first run if missing.

---

## Usage

```
usage: cloudserve [-h] [-p PORT] [--host HOST] [--tunnel] [--no-upload]
                  [--delete] [--readonly] [--auth USER:PASS]
                  [--no-browser] [directory]

positional arguments:
  directory          Directory to serve (default: current directory)

options:
  -h, --help         Show this help message and exit
  -p, --port PORT    Port to listen on (default: random free port)
  --host HOST        Interface to bind to (default: 0.0.0.0)
  --tunnel           Start a Cloudflare Quick Tunnel on launch
  --no-upload        Disable file uploads
  --delete           Enable file deletion (disabled by default)
  --readonly         Read-only mode disables upload, delete, mkdir
  --auth USER:PASS   Protect with HTTP Basic Auth
  --no-browser       Don't auto-open browser on start
```

---

## Examples

```bash
# Serve current directory on a random free port
cloudserve

# Serve a specific folder on a fixed port
cloudserve -p 9000 /tmp/files

# Instantly share with the internet (no account needed)
cloudserve --tunnel

# Share with auth + public tunnel (pentest / CTF exfil)
cloudserve /tmp/loot --tunnel --auth hacker:s3cr3t

# Full access server (upload + delete enabled)
cloudserve --delete /tmp/drop

# Read-only public share
cloudserve --readonly /srv/public

# LAN only (don't bind to all interfaces)
cloudserve --host 127.0.0.1

# Serve without opening browser (headless / server mode)
cloudserve --no-browser /data
```

---

## Cloudflare Tunnel

CloudServe integrates with [Cloudflare Quick Tunnels](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/) a free service that gives you a public HTTPS URL with **no account, no signup, no configuration**.

### How it works

```
Your machine                Cloudflare Edge            Anyone on the internet
─────────────               ───────────────            ──────────────────────
cloudserve :XXXX  ◄──────►  trycloudflare.com  ◄──────►  https://abc-xyz.trycloudflare.com
```

### Starting the tunnel

**From the CLI:**
```bash
cloudserve --tunnel
```

**From the browser:**  
Click the tunnel pill in the top right corner → click **Start**

### Installing `cloudflared`

CloudServe will attempt to auto-install `cloudflared` on first use. You can also install it manually:

| Platform | Method |
|----------|--------|
| Linux (apt) | `sudo apt install cloudflared` |
| Linux (manual) | `wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared` |
| macOS | `brew install cloudflared` |
| Windows | [Download from Cloudflare](https://developers.cloudflare.com/cloudflared/install/) |

> **Note:** Quick Tunnels are unauthenticated and temporary. Always use `--auth` if serving sensitive files publicly.

---

## Web UI

### File browser
- Click a **folder** to navigate into it
- Click a **file** to download it
- **Breadcrumb** navigation at the top
- **Sort** by name, size, or date modified
- **Live filter** type to filter files instantly

### Upload
- **Drag and drop** files anywhere on the page
- Or click **Upload** → browse for files
- Progress bar for large files
- Duplicate files are auto-renamed (not overwritten)

### Right-click context menu
Right-click any file or folder to get:
- Download / Download as zip
- Copy direct link
- Delete *(only if `--delete` is enabled)*

### Keyboard shortcuts
| Key | Action |
|-----|--------|
| `Esc` | Close any open modal or panel |

---

## API Reference

All endpoints respect HTTP Basic Auth if `--auth` is set.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Root directory listing |
| `GET` | `/browse/<path>` | Browse a subdirectory |
| `GET` | `/download/<path>` | Download a file |
| `GET` | `/view/<path>` | View a file inline in the browser |
| `GET` | `/zip/<path>` | Download a directory as `.zip` |
| `POST` | `/upload` | Upload files `multipart/form-data`, field: `files[]`, `path` |
| `POST` | `/delete` | Delete a file or folder JSON `{"path": "..."}` |
| `POST` | `/mkdir` | Create a folder JSON `{"path": "...", "name": "..."}` |
| `GET` | `/api/status` | Server status as JSON |
| `GET` | `/api/tunnel/status` | Tunnel status + log as JSON |
| `POST` | `/api/tunnel/start` | Start the Cloudflare tunnel |
| `POST` | `/api/tunnel/stop` | Stop the Cloudflare tunnel |
| `POST` | `/api/tunnel/restart` | Restart the Cloudflare tunnel |

### Example: upload via curl

```bash
# Upload a single file
curl -X POST http://localhost:PORT/upload \
  -F "path=" \
  -F "files=@/path/to/file.txt"

# Upload with auth
curl -u admin:secret -X POST http://localhost:PORT/upload \
  -F "path=" \
  -F "files=@shell.php"
```

### Example: check tunnel status

```bash
curl http://localhost:PORT/api/tunnel/status
# {"status": "running", "url": "https://abc-xyz.trycloudflare.com", "log": [...]}
```

---

## Comparison

| Feature | CloudServe | updog | SimpleHTTPServer |
|---------|:----------:|:-----:|:----------------:|
| Upload | ✅ | ✅ | ❌ |
| Download | ✅ | ✅ | ✅ |
| Cloudflare Tunnel | ✅ | ❌ | ❌ |
| Tunnel control panel | ✅ | ❌ | ❌ |
| Zip folder download | ✅ | ❌ | ❌ |
| HTTP Basic Auth | ✅ | ✅ | ❌ |
| File deletion | ✅ | ❌ | ❌ |
| Live search/filter | ✅ | ❌ | ❌ |
| New folder from UI | ✅ | ❌ | ❌ |
| Random free port | ✅ | ❌ | ❌ |
| Copy link button | ✅ | ❌ | ❌ |
| Context menu | ✅ | ❌ | ❌ |
| Read-only mode | ✅ | ❌ | ❌ |
| Single file | ✅ | ✅ | ✅ |
| No size limit | ✅ | ✅ | ✅ |

---

## Security

CloudServe is designed for controlled use. Keep these in mind:

- **Uploads are enabled by default.** Use `--no-upload` or `--readonly` when sharing with untrusted users.
- **Deletion is disabled by default.** Enable with `--delete` only when necessary.
- **Cloudflare Quick Tunnels are public.** Always use `--auth` if serving anything sensitive over a tunnel.
- **Path traversal is prevented** — all paths are resolved and validated against the root directory.
- **No authentication by default** — add `--auth user:pass` when running on a shared or public network.
- Intended for **local network use, CTF scenarios, and pentest engagements**. Not a production web server.



---

<div align="center">
Made for pentesters, CTF players, and anyone tired of <code> python -m http.server </code>
</div>
