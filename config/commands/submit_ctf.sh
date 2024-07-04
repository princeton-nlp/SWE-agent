# @yaml
# signature: submit
# docstring: submits your current flag and terminates the session
# arguments:
#   flag:
#     type: string
#     description: the flag found
#     required: true
submit() {
    if [ -z "$1" ]; then
        echo "Usage: submit <flag>"
        return
    fi

    if [[ "$1" =~ ^HTB\{.*\}$ ]]; then 
        echo "<<SUBMISSION||"
        echo "$1"
        echo "||SUBMISSION>>"
    else
        echo "Error: Flag '$1' does not match the format HTB{...}."
        return
    fi
}