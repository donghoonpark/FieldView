#!/bin/bash
set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
  echo "This script must be run as root (e.g., with sudo)." >&2
  exit 1
fi

apt-get update
apt-get install -y \
  libegl1 \
  libxkbcommon-x11-0 \
  libdbus-1-3 \
  libxcb-icccm4 \
  libxcb-image0 \
  libxcb-keysyms1 \
  libxcb-randr0 \
  libxcb-render-util0 \
  libxcb-xinerama0 \
  libxcb-xinput0 \
  libxcb-xfixes0 \
  x11-utils \
  libxcb-cursor0 \
  libfontconfig1 \
  libglib2.0-0 \
  libgl1
