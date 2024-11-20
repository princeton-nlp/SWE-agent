_print() {
    local CURRENT_FILE=$(_read_env "CURRENT_FILE")
    local CURRENT_LINE=$(_read_env "CURRENT_LINE")
    local WINDOW=$(_read_env "WINDOW")

    local total_lines=$(awk 'END {print NR}' "$CURRENT_FILE")
    echo "[File: $(realpath "$CURRENT_FILE") ($total_lines lines total)]"
    lines_above=$((CURRENT_LINE - WINDOW / 2 - 1))
    lines_above=$((lines_above < 0 ? 0 : lines_above))
    if [ $lines_above -gt 0 ]; then
        echo "($lines_above more lines above)"
    fi
    start_line=$((CURRENT_LINE - WINDOW / 2))
    start_line=$((start_line < 1 ? 1 : start_line))
    end_line=$((CURRENT_LINE + WINDOW / 2))
    end_line=$((end_line > total_lines ? total_lines : end_line))
    sed -n "$start_line,$end_line p" "$CURRENT_FILE" | nl -v $start_line -s':' -b a -n ln -w1
    lines_below=$((total_lines - CURRENT_LINE - WINDOW / 2))
    lines_below=$((lines_below < 0 ? 0 : lines_below))
    if [ $lines_below -gt 0 ]; then
        echo "($lines_below more lines below)"
    fi
}

_constrain_line() {
    local CURRENT_FILE=$(_read_env CURRENT_FILE)
    local CURRENT_LINE=$(_read_env CURRENT_LINE)
    local WINDOW=$(_read_env WINDOW)

    if [ -z "$CURRENT_FILE" ]
    then
        echo "No file open. Use the open command first."
        return
    fi
    local max_line=$(awk 'END {print NR}' "$CURRENT_FILE")
    local half_window=$((WINDOW / 2))
    # First ensure line number isn't too large (min of current_line and max_line - half_window)
    if ((CURRENT_LINE > max_line - half_window)); then
        CURRENT_LINE=$((max_line - half_window))
    fi
    # Then ensure line number isn't too small (max of current_line and half_window)
    if ((CURRENT_LINE < half_window)); then
        CURRENT_LINE=$((half_window))
    fi
    _write_env CURRENT_LINE $CURRENT_LINE
}

_scroll_warning_message() {
    # Warn the agent if we scroll too many times
    # Message will be shown if scroll is called more than WARN_AFTER_SCROLLING_TIMES (default 3) times
    # Initialize variable if it's not set
    local SCROLL_COUNT=$(_read_env SCROLL_COUNT 0)
    # Reset if the last command wasn't about scrolling
    if [ "$LAST_ACTION" != "scroll_up" ] && [ "$LAST_ACTION" != "scroll_down" ]; then
        _write_env SCROLL_COUNT 0
    fi
    # Increment because we're definitely scrolling now
    _write_env SCROLL_COUNT $(($SCROLL_COUNT + 1))
    if [ $SCROLL_COUNT -ge ${WARN_AFTER_SCROLLING_TIMES:-3} ]; then
        echo ""
        echo "WARNING: Scrolling many times in a row is very inefficient."
        echo "If you know what you are looking for, use \`search_file <pattern>\` instead."
        echo ""
    fi
}