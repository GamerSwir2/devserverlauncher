#!/bin/bash

INSTALL_DIR="$HOME/.local/share/m1pplauncher-files"
BIN_DIR="$HOME/.local/bin"
DESKTOP_FILE="$HOME/.local/share/applications/m1pplauncher.desktop"
ICON_PATH="$HOME/.local/share/m1pplauncher-files/m1pplauncher.png"

TAR_URL="https://github.com/M1PPosuDEV/m1pplauncher/releases/download/0.3alpha/m1pplauncher-linux.tar.gz"

m1pplauncher-uninstall

install_deps() {
    echo "Installing mono-complete..."

    if command -v apt-get &> /dev/null; then
        echo "Detected APT (Debian/Ubuntu)"
        sudo apt-get update
        sudo apt-get install -y mono-complete zenity

    elif command -v dnf &> /dev/null; then
        echo "Detected DNF (Fedora/RHEL 8+)"
        sudo dnf install -y mono-complete zenity

    elif command -v zypper &> /dev/null; then
        echo "Detected Zypper (openSUSE)"
        sudo zypper addrepo https://download.mono-project.com/repo/opensuse-stable.repo
        sudo zypper refresh
        sudo zypper install -y mono-complete zenity

    elif command -v pacman &> /dev/null; then
        echo "Detected Pacman (Arch Linux)"
        sudo pacman -S --noconfirm mono zenity

    else
        echo "IMPORTANT: Unsupported package manager or distribution. You will need to install mono and zenity on your system."
    fi

}

install_deps

if ! command -v curl &>/dev/null; then
  echo "ERROR: curl is not installed."
  exit 1
fi

if ! command -v tar &>/dev/null; then
  echo "ERROR: tar is not installed."
  exit 1
fi

mkdir -p "$INSTALL_DIR"

echo "Downloading the tar file..."
curl -L "$TAR_URL" -o "$INSTALL_DIR/file.tar.gz"

echo "Unpacking the tar file..."
tar -xvzf "$INSTALL_DIR/file.tar.gz" -C "$INSTALL_DIR"

if [ $? -ne 0 ]; then
  echo "Failed to unpack the tar file. Exiting..."
  exit 1
fi

rm "$INSTALL_DIR/file.tar.gz"

echo "Creating the uninstall script..."
cat <<EOL > "$BIN_DIR/m1pplauncher-uninstall"
#!/bin/bash
echo "Uninstalling M1PPLauncher..."
rm -rf "$INSTALL_DIR"
rm -f "$DESKTOP_FILE"
rm -f "$BIN_DIR/m1pplauncher-uninstall"
echo "Uninstallation completed."
EOL

chmod +x "$BIN_DIR/m1pplauncher-uninstall"

echo "Creating the .desktop file..."
cat <<EOL > "$DESKTOP_FILE"
[Desktop Entry]
Version=0.3
Name=M1PP Launcher
Comment=Launch M1PP Launcher
Exec=$INSTALL_DIR/m1pplauncher
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Utility;
EOL

echo "Installation completed successfully!"
