#!/usr/bin/env bash
set -e

echo "🚀 Installing ServerStriker..."

apt update -y
apt install -y python3 python3-pip git

INSTALL_DIR="/opt/serverstriker"

# If running via curl|bash, repo isn't cloned yet.
# So: if this script is run inside a cloned repo, copy files from current dir.
# If not, instruct user to clone first.
if [ ! -f "./serverstriker.py" ]; then
  echo "❌ serverstriker.py not found in current directory."
  echo "✅ Run:"
  echo "   git clone <YOUR_REPO_URL> && cd serverstriker && sudo ./install.sh"
  exit 1
fi

mkdir -p "$INSTALL_DIR"
cp -r ./* "$INSTALL_DIR"

# deps
pip3 install --upgrade pip
pip3 install psutil requests

# Make executable + symlink as command
chmod +x "$INSTALL_DIR/serverstriker.py"
ln -sf "$INSTALL_DIR/serverstriker.py" /usr/local/bin/ServerStriker

# Config dir
mkdir -p /etc/serverstriker

# systemd
cp "$INSTALL_DIR/serverstriker.service" /etc/systemd/system/serverstriker.service
systemctl daemon-reload
systemctl enable serverstriker

echo ""
echo "✅ Installed."
echo "Next:"
echo "  1) ServerStriker -init"
echo "  2) sudo systemctl start serverstriker"
echo "  3) sudo systemctl status serverstriker"
echo ""
