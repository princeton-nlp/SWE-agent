_print() {
    local CURRENT_FILE=$(_read_env "CURRENT_FILE")
    local CURRENT_LINE=$(_read_env "CURRENT_LINE")
    local WINDOW=$(_read_env "WINDOW")

    local total_lines=$(awk 'END {print NR}' "$CURRENT_FILE")
    echo "[File: $(realpath "$CURRENT_FILE") ($total_lines lines total)]"
    lines_above=$(jq -n "$CURRENT_LINE - $WINDOW/2" | jq '[0, .] | max | floor')
    lines_below=$(jq -n "$total_lines - $CURRENT_LINE - $WINDOW/2" | jq '[0, .] | max | round')
    if [ $lines_above -gt 0 ]; then
        echo "($lines_above more lines above)"
    fi
    cat "$CURRENT_FILE" | grep -n $ | head -n $(jq -n "[$CURRENT_LINE + $WINDOW/2, $WINDOW/2] | max | floor") | tail -n $(jq -n "$WINDOW")
    if [ $lines_below -gt 0 ]; then
        echo "($lines_below more lines below)"
    fi
}

_constrain_line() {
    local CURRENT_FILE=$(_read_env "CURRENT_FILE")
    local CURRENT_LINE=$(_read_env "CURRENT_LINE")
    local WINDOW=$(_read_env "WINDOW")

    if [ -z "$CURRENT_FILE" ]
    then
        echo "No file open. Use the open command first."
        return
    fi
    local max_line=$(awk 'END {print NR}' "$CURRENT_FILE")
    local half_window=$(jq -n "$WINDOW/2" | jq 'floor')
    export CURRENT_LINE=$(jq -n "[$CURRENT_LINE, $max_line - $half_window] | min")
    export CURRENT_LINE=$(jq -n "[$CURRENT_LINE, $half_window] | max")
    _write_env "CURRENT_LINE" "$CURRENT_LINE"
}