#!/bin/bash
# Install REA (https://github.com/morluto/rea) and Hopper on an Apple-silicon Mac for firmware
# analysis. Idempotent. Official sources only: nodejs.org, the rea-agents npm package and the
# Hopper download that `rea setup` verifies. See docs/how-to/set-up-rea-and-hopper.md.
set -euo pipefail

NODE_VERSION=24.22.3
NODE_SHA256=ff6e17d4874b76d272212b908cc020d6e815fba5a6c7eaaa06add725840307fd
REA_VERSION=6.10.1
PREFIX="${REA_NODE_PREFIX:-$HOME/.local/share/rea-node}"

[ "$(uname -s)-$(uname -m)" = "Darwin-arm64" ] || { echo "macOS arm64 only" >&2; exit 1; }

# REA refuses Node releases older than its engines range, so keep a private pinned runtime.
if [ "$("$PREFIX/bin/node" --version 2>/dev/null)" != "v$NODE_VERSION" ]; then
  tmp=$(mktemp -d)
  tarball="node-v$NODE_VERSION-darwin-arm64.tar.gz"
  curl -fsSL -o "$tmp/$tarball" "https://nodejs.org/dist/v$NODE_VERSION/$tarball"
  echo "$NODE_SHA256  $tmp/$tarball" | shasum -a 256 -c -
  mkdir -p "$PREFIX"
  tar -xzf "$tmp/$tarball" -C "$PREFIX" --strip-components 1
  rm -rf "$tmp"
fi
export PATH="$PREFIX/bin:$PATH"

if [ "$(rea --version 2>/dev/null)" != "$REA_VERSION" ]; then
  npm install -g --silent "rea-agents@$REA_VERSION"
fi

# Hopper's command-line launcher finds the app through Spotlight.
if ! mdutil -s /System/Volumes/Data | grep -q "Indexing enabled"; then
  sudo -n mdutil -i on /System/Volumes/Data
fi

# Installs Hopper to ~/Applications after checking its signature, registers the REA MCP server
# and skill with every agent client it detects. Exits non-zero while a manual step remains.
rea setup --yes --all-detected --install-hopper --json >/dev/null || true
mdimport "$HOME/Applications/Hopper Disassembler.app" 2>/dev/null || true

rea --version
echo "REA MCP server (stdio): $PREFIX/bin/node $PREFIX/bin/rea mcp"
