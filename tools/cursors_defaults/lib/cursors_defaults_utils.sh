#!/usr/bin/env bash

_reset_cursors() {
    _write_env START_CURSOR 1
    _write_env END_CURSOR 1
}

_constrain_cursors() {
    # constrain the cursors to be within the bounds of the file [0, total_lines+1]
    local CURRENT_FILE=$(_read_env CURRENT_FILE)
    local CURRENT_LINE=$(_read_env CURRENT_LINE)
    local WINDOW=$(_read_env WINDOW)
    local OVERLAP=$(_read_env OVERLAP)
    local START_CURSOR=$(_read_env START_CURSOR)
    local END_CURSOR=$(_read_env END_CURSOR)

    local total_lines=$(awk 'END {print NR}' "$CURRENT_FILE")
    total_lines=$((total_lines < 1 ? 1 : total_lines))  # if the file is empty, set total_lines to 1
    local start_line=$((CURRENT_LINE - WINDOW / 2))
    local end_line=$((CURRENT_LINE + WINDOW / 2))
    start_line=$((start_line < 1 ? 1 : start_line))
    end_line=$((end_line > total_lines ? total_lines : end_line))
    local warning_string=""
    if [ "$START_CURSOR" -lt "$start_line" ]; then
        warning_string+="START_CURSOR moved to $start_line\n"
        START_CURSOR=$start_line
    elif [ "$START_CURSOR" -gt "$end_line" ]; then
        START_CURSOR=$end_line
        warning_string+="START_CURSOR moved to $end_line\n"
    fi
    if [ "$END_CURSOR" -lt "$start_line" ]; then
        warning_string+="END_CURSOR moved to $start_line\n"
        END_CURSOR=$start_line
    elif [ "$END_CURSOR" -gt "$end_line" ]; then
        warning_string+="END_CURSOR moved to $end_line\n"
        END_CURSOR=$end_line
    fi
    echo "$warning_string"
    echo $START_CURSOR $END_CURSOR
    _write_env START_CURSOR $START_CURSOR
    _write_env END_CURSOR $END_CURSOR
}

_print() {
    local CURRENT_FILE=$(_read_env CURRENT_FILE)
    local CURRENT_LINE=$(_read_env CURRENT_LINE)
    local WINDOW=$(_read_env WINDOW)
    local OVERLAP=$(_read_env OVERLAP)
    local START_CURSOR=$(_read_env START_CURSOR)
    local END_CURSOR=$(_read_env END_CURSOR)

    local cursor_warning=$(_constrain_cursors)
    local cursor_values=$(echo "$cursor_warning" | tail -n 1)
    cursor_warning=$(echo "$cursor_warning" | head -n -1)
    _write_env START_CURSOR $(echo "$cursor_values" | awk '{print $1}')
    _write_env END_CURSOR $(echo "$cursor_values" | awk '{print $2}')
    local total_lines=$(awk 'END {print NR}' $CURRENT_FILE)
    echo "[File: $(realpath "$CURRENT_FILE") ($total_lines lines total)]"
    local start_line=$((CURRENT_LINE - WINDOW / 2))
    local end_line=$((CURRENT_LINE + WINDOW / 2))
    start_line=$((start_line < 1 ? 1 : start_line))
    end_line=$((end_line > total_lines ? total_lines : end_line))
    local lines=()
    local i=0
    while IFS= read -r line; do
        lines[i++]="$line"
    done < <(awk -v start="$start_line" -v end="$end_line" 'NR>=start && NR<=end {print}' "$CURRENT_FILE")
    local num_lines=${#lines[@]}
    if [ $start_line -gt 1 ]; then
        echo "($((start_line - 1)) more lines above)"
    fi
    for ((i=0; i<num_lines+1; i++)) do
        local line_number=$((start_line + i))
        if [ $line_number -eq $START_CURSOR ]
        then
            echo $START_CURSOR_MARK
        fi
        # if i in [0, num_lines-1] then print the line number and the line
        if [ $i -ge 0 ] && [ $i -lt $num_lines ]
        then
            echo "$line_number:${lines[i]}"
        fi
        if [ $line_number -eq $END_CURSOR ]
        then
            echo $END_CURSOR_MARK
        fi
    done
    lines_below=$((total_lines - start_line - num_lines))
    lines_below=$((lines_below > 0 ? lines_below : 0))
    if [ $lines_below -gt 0 ]; then
        echo "($lines_below more lines below)"
    fi
    if [ -n "$cursor_warning" ]; then
        echo -e "$cursor_warning"
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