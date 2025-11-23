#!/bin/bash
# SamFWTool - ONE CLICK START (GUI)
cd "$(dirname "$0")"

# Find Python with tkinter
PYTHON=""
for p in python3.12 python3.11 python3.10 python3; do
    if command -v $p &>/dev/null && $p -c "import tkinter" 2>/dev/null; then
        PYTHON=$p
        break
    fi
done

# Fallback: try system pythons
if [ -z "$PYTHON" ]; then
    for p in /usr/bin/python3.12 /usr/bin/python3.11 /usr/bin/python3; do
        if [ -x "$p" ] && $p -c "import tkinter" 2>/dev/null; then
            PYTHON=$p
            break
        fi
    done
fi

if [ -z "$PYTHON" ]; then
    echo "ERROR: No Python with tkinter found."
    echo "Install with: sudo apt-get install python3-tk"
    exit 1
fi

# Install all dependencies
DEPS="click tqdm lz4 python-magic rich"
$PYTHON -m pip install -q $DEPS --break-system-packages 2>/dev/null || \
$PYTHON -m pip install -q $DEPS 2>/dev/null || true

export PYTHONPATH="${PWD}:${PYTHONPATH}"

# Check if display is available
if [ -z "$DISPLAY" ] && [ "$(uname)" = "Linux" ]; then
    echo "No display found - running CLI instead"
    echo ""
    $PYTHON -m samfwtool.cli.main "$@"
else
    $PYTHON -m samfwtool.gui.main_gui "$@"
fi
