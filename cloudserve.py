#!/usr/bin/env python3
"""
CloudServe - A better alternative to SimpleHTTPServer
Features: File upload/download, directory browsing, Cloudflare Tunnel integration
"""

import os
import sys
import re
import json
import shutil
import zipfile
import argparse
import mimetypes
import subprocess
import threading
import platform
import socket
import urllib.request
from pathlib import Path
from datetime import datetime
from functools import wraps
from io import BytesIO

try:
    from flask import (
        Flask, request, send_file, render_template,
        jsonify, redirect, url_for, Response, abort
    )
    from werkzeug.utils import secure_filename
except ImportError:
    print("[!] Flask not found. Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "werkzeug", "-q"])
    from flask import (
        Flask, request, send_file, render_template,
        jsonify, redirect, url_for, Response, abort
    )
    from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # 10GB

CONFIG = {
    "root_dir": os.getcwd(),
    "allow_upload": True,
    "allow_delete": False,
    "auth_user": None,
    "auth_pass": None,
    "tunnel_url": None,
    "tunnel_process": None,
    "tunnel_log": [],          # rolling log lines from cloudflared
    "tunnel_status": "stopped", # stopped | starting | running | error
    "port": None,
    "host": "0.0.0.0",
    "readonly": False,
}


def find_free_port(preferred=None):
    """Return a free TCP port. Try preferred first, else pick random."""
    if preferred:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", preferred))
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                return preferred
            except OSError:
                pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def check_auth(username, password):
    return username == CONFIG["auth_user"] and password == CONFIG["auth_pass"]

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if CONFIG["auth_user"] is None:
            return f(*args, **kwargs)
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return Response(
                "Authentication required.", 401,
                {"WWW-Authenticate": 'Basic realm="CloudServe"'}
            )
        return f(*args, **kwargs)
    return decorated


def safe_path(rel_path):
    root = Path(CONFIG["root_dir"]).resolve()
    target = (root / rel_path).resolve()
    if not str(target).startswith(str(root)):
        abort(403)
    return target

def human_size(size_bytes):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"

def get_file_info(path: Path):
    stat = path.stat()
    return {
        "name": path.name,
        "is_dir": path.is_dir(),
        "size": stat.st_size if path.is_file() else 0,
        "size_human": human_size(stat.st_size) if path.is_file() else "—",
        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
        "ext": path.suffix.lower().lstrip(".") if path.is_file() else "",
        "mime": mimetypes.guess_type(str(path))[0] or "application/octet-stream",
    }

def list_directory(rel_path=""):
    target = safe_path(rel_path)
    if not target.is_dir():
        abort(404)
    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            try:
                items.append(get_file_info(entry))
            except PermissionError:
                pass
    except PermissionError:
        abort(403)

    parts = Path(rel_path).parts if rel_path else []
    breadcrumbs = [{"name": "~", "path": ""}]
    cum = ""
    for p in parts:
        cum = cum + "/" + p if cum else p
        breadcrumbs.append({"name": p, "path": cum})

    return {
        "items": items,
        "path": rel_path,
        "breadcrumbs": breadcrumbs,
        "tunnel_url": CONFIG.get("tunnel_url"),
        "tunnel_status": CONFIG.get("tunnel_status", "stopped"),
        "allow_upload": CONFIG["allow_upload"] and not CONFIG["readonly"],
        "allow_delete": CONFIG["allow_delete"] and not CONFIG["readonly"],
        "server_port": CONFIG["port"],
    }


@app.route("/")
@requires_auth
def index():
    return render_template("index.html", **list_directory(""))

@app.route("/browse/", defaults={"rel_path": ""})
@app.route("/browse/<path:rel_path>")
@requires_auth
def browse(rel_path):
    target = safe_path(rel_path)
    if target.is_file():
        return redirect(url_for("download_file", rel_path=rel_path))
    return render_template("index.html", **list_directory(rel_path))

@app.route("/download/<path:rel_path>")
@requires_auth
def download_file(rel_path):
    target = safe_path(rel_path)
    if not target.is_file():
        abort(404)
    return send_file(str(target), as_attachment=True, download_name=target.name)

@app.route("/view/<path:rel_path>")
@requires_auth
def view_file(rel_path):
    target = safe_path(rel_path)
    if not target.is_file():
        abort(404)
    mime, _ = mimetypes.guess_type(str(target))
    return send_file(str(target), mimetype=mime or "application/octet-stream")

@app.route("/zip/<path:rel_path>")
@requires_auth
def zip_directory(rel_path):
    target = safe_path(rel_path)
    if not target.is_dir():
        abort(404)
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in target.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(target))
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f"{target.name}.zip",
                     mimetype="application/zip")

@app.route("/upload", methods=["POST"])
@requires_auth
def upload():
    if CONFIG["readonly"] or not CONFIG["allow_upload"]:
        return jsonify({"error": "Uploads disabled"}), 403
    rel_path = request.form.get("path", "")
    target_dir = safe_path(rel_path)
    if not target_dir.is_dir():
        return jsonify({"error": "Invalid directory"}), 400
    uploaded, errors = [], []
    for f in request.files.getlist("files"):
        if f.filename:
            fname = secure_filename(f.filename)
            dest = target_dir / fname
            if dest.exists():
                stem, suffix = dest.stem, dest.suffix
                counter = 1
                while dest.exists():
                    dest = target_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            try:
                f.save(str(dest))
                uploaded.append(fname)
            except Exception as e:
                errors.append(str(e))
    return jsonify({"uploaded": uploaded, "errors": errors})

@app.route("/delete", methods=["POST"])
@requires_auth
def delete():
    if CONFIG["readonly"] or not CONFIG["allow_delete"]:
        return jsonify({"error": "Delete disabled"}), 403
    data = request.get_json()
    rel_path = data.get("path", "")
    target = safe_path(rel_path)
    root = Path(CONFIG["root_dir"]).resolve()
    if target == root:
        return jsonify({"error": "Cannot delete root"}), 403
    try:
        shutil.rmtree(target) if target.is_dir() else target.unlink()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/mkdir", methods=["POST"])
@requires_auth
def mkdir():
    if CONFIG["readonly"]:
        return jsonify({"error": "Read-only mode"}), 403
    data = request.get_json()
    name = secure_filename(data.get("name", ""))
    if not name:
        return jsonify({"error": "Invalid name"}), 400
    target = safe_path(os.path.join(data.get("path", ""), name))
    try:
        target.mkdir(parents=True, exist_ok=True)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status")
def api_status():
    return jsonify({
        "root": CONFIG["root_dir"],
        "port": CONFIG["port"],
        "tunnel_url": CONFIG.get("tunnel_url"),
        "tunnel_status": CONFIG.get("tunnel_status", "stopped"),
        "tunnel_log": CONFIG.get("tunnel_log", [])[-20:],
        "allow_upload": CONFIG["allow_upload"],
        "allow_delete": CONFIG["allow_delete"],
        "readonly": CONFIG["readonly"],
    })

@app.route("/api/tunnel/start", methods=["POST"])
def tunnel_start():
    if CONFIG.get("tunnel_status") == "running":
        return jsonify({"url": CONFIG["tunnel_url"], "status": "already_running"})
    if CONFIG.get("tunnel_status") == "starting":
        return jsonify({"status": "starting"})
    # Start in background thread so we can return immediately
    threading.Thread(target=_do_start_tunnel, daemon=True).start()
    return jsonify({"status": "starting"})

@app.route("/api/tunnel/stop", methods=["POST"])
def tunnel_stop():
    stop_cloudflare_tunnel()
    return jsonify({"status": "stopped"})

@app.route("/api/tunnel/restart", methods=["POST"])
def tunnel_restart():
    stop_cloudflare_tunnel()
    threading.Thread(target=_do_start_tunnel, daemon=True).start()
    return jsonify({"status": "starting"})

@app.route("/api/tunnel/status")
def tunnel_status_api():
    return jsonify({
        "status": CONFIG.get("tunnel_status", "stopped"),
        "url": CONFIG.get("tunnel_url"),
        "log": CONFIG.get("tunnel_log", [])[-30:],
    })

def _do_start_tunnel():
    """Background task that actually starts the tunnel."""
    CONFIG["tunnel_status"] = "starting"
    CONFIG["tunnel_log"] = []
    CONFIG["tunnel_url"] = None
    url = start_cloudflare_tunnel(CONFIG["port"])
    if not url:
        CONFIG["tunnel_status"] = "error"


def find_cloudflared():
    # Check PATH
    for path_dir in os.environ.get("PATH", "").split(os.pathsep):
        for name in ["cloudflared", "cloudflared.exe"]:
            candidate = os.path.join(path_dir, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
    # Check common locations
    candidates = [
        "/usr/local/bin/cloudflared",
        "/usr/bin/cloudflared",
        os.path.expanduser("~/.local/bin/cloudflared"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "cloudflared", "cloudflared.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None

def install_cloudflared():
    system = platform.system()
    machine = platform.machine().lower()
    CONFIG["tunnel_log"].append("[*] cloudflared not found, attempting auto-install...")
    print("[*] Attempting to install cloudflared...")

    if system == "Linux":
        arch = "amd64" if "x86_64" in machine else "arm64" if "aarch64" in machine else "386"
        url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-{arch}"
        dest = os.path.expanduser("~/.local/bin/cloudflared")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        try:
            CONFIG["tunnel_log"].append(f"[*] Downloading cloudflared ({arch})...")
            urllib.request.urlretrieve(url, dest)
            os.chmod(dest, 0o755)
            CONFIG["tunnel_log"].append(f"[+] Installed to {dest}")
            print(f"[+] cloudflared installed to {dest}")
            return dest
        except Exception as e:
            msg = f"[!] Auto-install failed: {e}"
            CONFIG["tunnel_log"].append(msg)
            print(msg)
            return None
    elif system == "Darwin":
        try:
            subprocess.run(["brew", "install", "cloudflared"], check=True)
            return find_cloudflared()
        except Exception:
            CONFIG["tunnel_log"].append("[!] Run: brew install cloudflared")
            return None
    else:
        CONFIG["tunnel_log"].append("[!] Download from: https://developers.cloudflare.com/cloudflared/install/")
        return None

def start_cloudflare_tunnel(port):
    """Start Cloudflare Quick Tunnel. Returns URL or None."""
    binary = find_cloudflared()
    if not binary:
        binary = install_cloudflared()
        if not binary:
            CONFIG["tunnel_status"] = "error"
            CONFIG["tunnel_log"].append("[!] cloudflared not found. Install it first.")
            return None

    CONFIG["tunnel_log"].append(f"[*] Starting tunnel → localhost:{port}")
    print(f"[*] Starting Cloudflare tunnel on port {port}...")

    try:
        # Use --no-autoupdate to avoid update prompts
        # Bind to 127.0.0.1 explicitly so tunnel can reach the local server
        cmd = [binary, "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate"]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        tunnel_url = [None]
        ready_event = threading.Event()

        def read_output():
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                # Keep a rolling log (last 100 lines)
                CONFIG["tunnel_log"].append(line)
                if len(CONFIG["tunnel_log"]) > 100:
                    CONFIG["tunnel_log"] = CONFIG["tunnel_log"][-100:]

                # Extract the public URL — cloudflared prints it in stderr/stdout
                match = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", line)
                if match and not tunnel_url[0]:
                    tunnel_url[0] = match.group(0)
                    CONFIG["tunnel_url"] = tunnel_url[0]
                    CONFIG["tunnel_process"] = proc
                    CONFIG["tunnel_status"] = "running"
                    print(f"\n[+] Tunnel URL: {tunnel_url[0]}\n")
                    ready_event.set()

            # Process ended
            if CONFIG["tunnel_status"] != "stopped":
                CONFIG["tunnel_status"] = "error"
                CONFIG["tunnel_log"].append("[!] cloudflared process exited unexpectedly")

        t = threading.Thread(target=read_output, daemon=True)
        t.start()

        ready_event.wait(timeout=30)

        if not tunnel_url[0]:
            CONFIG["tunnel_status"] = "error"
            CONFIG["tunnel_log"].append("[!] Timeout: could not get tunnel URL in 30s")
            proc.terminate()
            return None

        return tunnel_url[0]

    except Exception as e:
        msg = f"[!] Tunnel error: {e}"
        CONFIG["tunnel_log"].append(msg)
        CONFIG["tunnel_status"] = "error"
        print(msg)
        return None

def stop_cloudflare_tunnel():
    proc = CONFIG.get("tunnel_process")
    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    CONFIG["tunnel_process"] = None
    CONFIG["tunnel_url"] = None
    CONFIG["tunnel_status"] = "stopped"
    CONFIG["tunnel_log"].append("[*] Tunnel stopped.")
    print("[*] Tunnel stopped.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="CloudServe - File server with Cloudflare tunnel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cloudserve                          # Serve current dir on random port
  cloudserve -p 9000 /tmp            # Serve /tmp on port 9000
  cloudserve --tunnel                 # Start with Cloudflare tunnel
  cloudserve --delete                 # Enable file deletion
  cloudserve --auth admin:secret      # Require HTTP basic auth
  cloudserve --readonly               # Serve files read-only
        """
    )
    parser.add_argument("directory", nargs="?", default=os.getcwd(),
                        help="Directory to serve (default: current)")
    parser.add_argument("-p", "--port", type=int, default=None,
                        help="Port to listen on (default: random free port)")
    parser.add_argument("--host", default="0.0.0.0",
                        help="Interface to bind (default: 0.0.0.0)")
    parser.add_argument("--tunnel", action="store_true",
                        help="Start a Cloudflare Quick Tunnel on launch")
    parser.add_argument("--no-upload", action="store_true",
                        help="Disable file uploads")
    parser.add_argument("--delete", action="store_true",
                        help="Enable file deletion")
    parser.add_argument("--readonly", action="store_true",
                        help="Read-only mode")
    parser.add_argument("--auth", metavar="USER:PASS",
                        help="Enable HTTP Basic Auth")
    parser.add_argument("--no-browser", action="store_true",
                        help="Don't open browser on start")
    return parser.parse_args()

def main():
    args = parse_args()

    root = Path(args.directory).resolve()
    if not root.exists():
        print(f"[!] Directory not found: {root}")
        sys.exit(1)

    port = find_free_port(args.port)

    CONFIG["root_dir"] = str(root)
    CONFIG["port"] = port
    CONFIG["host"] = args.host
    CONFIG["allow_upload"] = not args.no_upload
    CONFIG["allow_delete"] = args.delete
    CONFIG["readonly"] = args.readonly

    if args.auth:
        if ":" in args.auth:
            user, pw = args.auth.split(":", 1)
            CONFIG["auth_user"] = user
            CONFIG["auth_pass"] = pw
        else:
            print("[!] Auth format: --auth user:password")
            sys.exit(1)

    print("""


  ░██████  ░██                              ░██   ░██████                                             
 ░██   ░██ ░██                              ░██  ░██   ░██                                            
░██        ░██  ░███████  ░██    ░██  ░████████ ░██          ░███████  ░██░████ ░██    ░██  ░███████  
░██        ░██ ░██    ░██ ░██    ░██ ░██    ░██  ░████████  ░██    ░██ ░███     ░██    ░██ ░██    ░██ 
░██        ░██ ░██    ░██ ░██    ░██ ░██    ░██         ░██ ░█████████ ░██       ░██  ░██  ░█████████ 
 ░██   ░██ ░██ ░██    ░██ ░██   ░███ ░██   ░███  ░██   ░██  ░██        ░██        ░██░██   ░██        
  ░██████  ░██  ░███████   ░█████░██  ░█████░██   ░██████    ░███████  ░██         ░███     ░███████  
  
  by ManojPrakash.

    """)

    print(f"  Root    : {root}")
    print(f"  Address : http://127.0.0.1:{port}")
    print(f"  Upload  : {'disabled (readonly)' if args.readonly else ('yes' if CONFIG['allow_upload'] else 'no')}")
    print(f"  Delete  : {'disabled (readonly)' if args.readonly else ('yes' if CONFIG['allow_delete'] else 'no')}")
    print(f"  Auth    : {'yes (' + CONFIG['auth_user'] + ')' if CONFIG['auth_user'] else 'no'}")
    print()

    if args.tunnel:
        print("[*] Starting Cloudflare tunnel (this may take a few seconds)...")
        tunnel_url = start_cloudflare_tunnel(port)
        if tunnel_url:
            print(f"  Tunnel  : {tunnel_url}\n")
        else:
            print("  [!] Tunnel failed to start. Try from the web UI.\n")

    if not args.no_browser:
        try:
            import webbrowser
            threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
        except Exception:
            pass

    print("  Press Ctrl+C to stop.\n")

    try:
        app.run(host=args.host, port=port, debug=False, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        stop_cloudflare_tunnel()

if __name__ == "__main__":
    main()
