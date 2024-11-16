source /root/tools/cursors_defaults/lib/utils.sh

# raise error ir any env variables not set
if [ -z "$WINDOW" ]; then
    echo "Error: WINDOW not set"
    exit 1
fi
if [ -z "$OVERLAP" ]; then
    echo "Error: OVERLAP not set"
    exit 1
fi
if [ -z "$CURRENT_LINE" ]; then
    echo "Error: CURRENT_LINE not set"
    exit 1
fi
if [ -z "$CURRENT_FILE" ]; then
    echo "Error: CURRENT_FILE not set"
    exit 1
fi

_write_env "WINDOW" "$WINDOW"
_write_env "OVERLAP" "$OVERLAP"
_write_env "CURRENT_LINE" "$CURRENT_LINE"
_write_env "CURRENT_FILE" "$CURRENT_FILE"
