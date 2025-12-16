#!/usr/bin/env bash
set -e

echo "🚀 Installing ServerStriker..."

# -----------------------------
# Check OS
# -----------------------------
if ! command -v apt >/dev/null 2>&1; then
  echo "❌ This installer supports Debian/Ubuntu systems only."
  exit 1
fi

# -----------------------------
# Check Python
# -----------------------------
if ! command -v python3 >/dev/null 2>&1; then
  echo "🐍 Python3 not found. Installing..."
  apt update -y
  apt install -y python3
else
  echo "✅ Python3 found: $(python3 --version)"
fi

# -----------------------------
# Check pip
# -----------------------------
if ! command -v pip3 >/dev/null 2>&1; then
  echo "📦 pip3 not found. Installing..."
  apt install -y python3-pip
else
  echo "✅ pip3 found"
fi

# -----------------------------
# Install git (needed for repo clone workflows)
# -----------------------------
if ! command -v git >/dev/null 2>&1; then
  echo "📦 Installing git..."
  apt install -y git
fi

INSTALL_DIR="/opt/serverstriker"

# -----------------------------
# Validate repo files
# -----------------------------
if [ ! -f "./main.py" ] && [ ! -f "./serverstriker.py" ]; then
  echo "❌ serverstriker main file not found."
  echo "✅ Run:"
  echo "   git clone <YOUR_REPO_URL>"
  echo "   cd serverstriker"
  echo "   sudo ./install.sh"
  exit 1
fi

# Normalize filename (support main.py or serverstriker.py)
APP_FILE="serverstriker.py"
if [ -f "./main.py" ]; then
  APP_FILE="main.py"
fi

# -----------------------------
# Install application
# -----------------------------
echo "📂 Installing to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -r ./* "$INSTALL_DIR"

# -----------------------------
# Python dependencies
# -----------------------------
echo "📦 Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install psutil requests

# -----------------------------
# Make executable + CLI alias
# -----------------------------
chmod +x "$INSTALL_DIR/$APP_FILE"
ln -sf "$INSTALL_DIR/$APP_FILE" /usr/local/bin/serverstriker

# -----------------------------
# Config directory
# -----------------------------
mkdir -p /etc/serverstriker

# -----------------------------
# systemd service
# -----------------------------
if [ ! -f "$INSTALL_DIR/serverstriker.service" ]; then
  echo "❌ serverstriker.service not found."
  exit 1
fi

cp "$INSTALL_DIR/serverstriker.service" /etc/systemd/system/serverstriker.service
systemctl daemon-reload
systemctl enable serverstriker

echo ""
echo "✅ serverstriker installed successfully!"
echo ""
echo "Next steps:"
echo "  1) serverstriker -init"
echo "  2) sudo systemctl start serverstriker"
echo "  3) sudo systemctl status serverstriker"
echo ""
