#!/bin/sh
# uv manages Python and the project environment on Linux and macOS.
cd "$(dirname "$0")" || exit 1
STRATA_UV_EXE="$(command -v uv 2>/dev/null || true)"
if [ -z "$STRATA_UV_EXE" ] && [ -x "$HOME/.local/bin/uv" ]; then
  STRATA_UV_EXE="$HOME/.local/bin/uv"
fi
if [ -z "$STRATA_UV_EXE" ] && [ -x "$PWD/.uv/uv" ]; then
  STRATA_UV_EXE="$PWD/.uv/uv"
fi
if [ -z "$STRATA_UV_EXE" ]; then
  echo "Installing uv into this Strata folder ..."
  mkdir -p .uv || exit 1
  curl -fsSL --retry 3 https://astral.sh/uv/install.sh -o .uv/install.sh || exit 1
  UV_INSTALL_DIR="$PWD/.uv" UV_NO_MODIFY_PATH=1 sh .uv/install.sh || exit 1
  STRATA_UV_EXE="$PWD/.uv/uv"
fi
export STRATA_UV_EXE
# On NixOS a standalone interpreter can load the native libraries from wheels.
if grep -qi '^ID=nixos' /etc/os-release 2>/dev/null; then
  UV_PYTHON_PREFERENCE=only-managed
  export UV_PYTHON_PREFERENCE
fi
exec "$STRATA_UV_EXE" run --locked --no-dev python setup.py "$@"
