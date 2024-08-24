_debug_command() {
    echo "<<INTERACTIVE_GDB||$@||INTERACTIVE_GDB>>"
}

# @yaml
# signature: debug_start <binary> [<args>]
# docstring: Starts a debug session with the given binary.
# arguments:
#   binary:
#     type: string
#     description: the path to the binary to debug
#     required: true
#   args:
#     type: string
#     description: optional command-line arguments for the binary
#     required: false
debug_start() {
    if [ -z "$1" ]
    then
        echo "Usage: debug_start <binary>"
        return
    fi
    if [ ! -x "$1" ]
    then
        echo "Error: File $1 does not exist, or is not executable"
        return
    fi
    fp=$(realpath $1)
    _debug_command "START"
    _debug_command "file $fp"
    _debug_command "starti"
}

# @yaml
# signature: debug_add_breakpoint <breakpoint>
# docstring: Adds a breakpoint in the debug session
# arguments:
#   breakpoint:
#     type: string
#     description: The breakpoint location, which may be a function name, address, or filename and line number.
#     required: true
debug_add_breakpoint() {
    if [ -z "$1" ]
    then
        echo "Usage: debug_add_breakpoint <breakpoint>"
        return
    fi
    _debug_command 'break '$1
}

# @yaml
# signature: debug_continue
# docstring: Continues the program execution in the debug session.
debug_continue() {
    _debug_command 'continue'
}

# @yaml
# signature: debug_step [number]
# docstring: Steps number of instructions in the debug session.
# arguments:
#   number:
#     type: integer
#     description: number of instructions to step (default is 1)
#     required: false
debug_step() {
    if [ -z "$1" ]
    then
        _debug_command 'stepi'
    elif [[ (("$1" -eq "$1") && ("$1" -gt "0")) ]] # Check if integer and positive
    then
        _debug_command 'stepi '$1
    else
        echo "Please provide a positive integer for number of instructions."
        echo "Usage: debug_step [number]"
    fi
}

# @yaml
# signature: debug_exec <command>
# docstring: Executes arbitrary gdb command in debug session.
# arguments:
#   command:
#     type: string
#     description: command to execute
#     required: true
debug_exec() {
    if [ -z "$1" ]
    then
        echo "Usage: debug_exec <command>"
        return
    fi
    _debug_command "$1"
}

# @yaml
# signature: debug_stop
# docstring: Stops the current debug session.
debug_stop() {
    _debug_command "quit"
    _debug_command "STOP"
}
