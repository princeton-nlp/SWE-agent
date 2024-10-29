# Add semantic search command
semantic_search() {
    if [ $# -eq 1 ]; then
        local search_query="$1"
        local dir="./"
    elif [ $# -eq 2 ]; then
        local search_query="$1"
        if [ -d "$2" ]; then
            local dir="$2"
        else
            echo "Directory $2 not found"
            return
        fi
    else
        echo "Usage: semantic_search <search_query> [<dir>]"
        return
    fi

    dir=$(realpath "$dir")

    # Call Python script that handles the semantic search
    python3 config/commands/_semantic_search.py "$search_query" "$dir"
}