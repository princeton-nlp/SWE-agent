_connect_command() {
    echo "<<INTERACTIVE||$@||INTERACTIVE>>"
}

# @yaml
# signature: connect_start <server_address> <port>
# docstring: Starts a new interactive connection to the server address and port.
# arguments:
#   server_address:
#     type: string
#     description: the server address to initiate connection to
#     required: true
#   port:
#     type: int
#     description: desired port for connection
#     required: true
connect_start() {
    if [ -z "$1" ] || [ -z "$2" ]
    then
        echo "Usage: connect_start <server_address> <port>"
        return
    fi
    _connect_command "SESSION=connect"
    _connect_command "START"
    _connect_command "connect $1 $2"
    export INTERACTIVE_SESSION="connect $@"
}

# @yaml
# signature: connect_sendline [<line>]
# docstring: Sends a line with unicode/hexadecimal values to the connection. Sending hexadecimal bytes should be done using \x<hh> where hh stands for the sepecific byte you want to send.
# arguments:
#   line:
#     type: string
#     description: The line to send to the connection
#     required: false
connect_sendline() {
    _connect_command "SESSION=connect"
    _connect_command 'sendline '$@
}

# @yaml
# signature: connect_exec <command>
# docstring: Executes arbitrary connect command in connect session.
# arguments:
#   command:
#     type: string
#     description: command to execute (wrap in single quotes to avoid shell escaping and substitution)
#     required: true
connect_exec() {
    if [ -z "$1" ]
    then
        echo "Usage: connect_exec <command>"
        return
    fi
    _connect_command "SESSION=connect"
    _connect_command "$@"
}

# @yaml
# signature: connect_stop
# docstring: Stops the current connect session.
connect_stop() {
    _connect_command "SESSION=connect"
    _connect_command "quit"
    _connect_command "STOP"
    unset INTERACTIVE_SESSION
}
