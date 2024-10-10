_debug_command() {
    echo "<<INTERACTIVE||$@||INTERACTIVE>>"
}


# @yaml
# signature: dummy_start
# docstring:
dummy_start() {
    _debug_command "SESSION=dummy"
    _debug_command "START"
}

# @yaml
# signature: dummy_stop
# docstring:
dummy_stop() {
    _debug_command "SESSION=dummy"
    _debug_command "stop"
    _debug_command "STOP"
}

# @yaml
# signature: dummy_send <input>
# docstring:
dummy_send() {
    _debug_command "SESSION=dummy"
    _debug_command "send $@"
}