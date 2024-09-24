# @yaml
# signature: submit '<flag>'
# docstring: submits your current flag and terminates the session, you should be aware to properly escape the flag as this is a bash command and to put your flag under single quotes.
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

    echo -n "<<SUBMISSION||"
    echo -n "$@"
    echo "||SUBMISSION>>"
}