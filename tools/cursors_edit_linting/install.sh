source /root/tools/cursors_defaults/lib/utils.sh

if [ -z "$WINDOW" ]; then
    echo "Error: WINDOW not set"
    exit 1
fi
if [ -z "$OVERLAP" ]; then
    echo "Error: OVERLAP not set"
    exit 1
fi

_write_env CURRENT_FILE "${CURRENT_FILE:-}"
_write_env CURRENT_LINE "${CURRENT_LINE:-0}"
_write_env WINDOW "$WINDOW"
_write_env OVERLAP "$OVERLAP"
