#!/usr/bin/env bash
# CloudServe installer
set -e

echo ""
echo "  ██████╗██╗      ██████╗ ██╗   ██╗██████╗ "
echo " ██╔════╝██║     ██╔═══██╗██║   ██║██╔══██╗"
echo " ██║     ██║     ██║   ██║██║   ██║██║  ██║"
echo " ╚██████╗███████╗╚██████╔╝╚██████╔╝██████╔╝"
echo "  ╚═════╝╚══════╝ ╚═════╝  ╚═════╝ ╚═════╝ "
echo ""

echo "[*] Installing Python dependencies..."
pip install flask werkzeug -q

echo "[*] Making cloudserve.py executable..."
chmod +x cloudserve.py

# Optional: install to PATH
read -p "[?] Install to /usr/local/bin/cloudserve? (y/N) " answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
    # Create wrapper that sets correct template path
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cat > /tmp/cloudserve_wrapper << EOF
#!/usr/bin/env bash
export FLASK_TEMPLATE_DIR="$SCRIPT_DIR/templates"
exec python3 "$SCRIPT_DIR/cloudserve.py" "\$@"
EOF
    chmod +x /tmp/cloudserve_wrapper
    sudo mv /tmp/cloudserve_wrapper /usr/local/bin/cloudserve
    echo "[+] Installed to /usr/local/bin/cloudserve"
fi

echo ""
echo "[+] Done! Usage:"
echo "    python3 cloudserve.py               # serve current dir"
echo "    python3 cloudserve.py --tunnel      # with Cloudflare tunnel"
echo "    python3 cloudserve.py --help        # all options"
echo ""
