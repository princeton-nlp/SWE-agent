#!/bin/bash

# Check if an argument was provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path_to_jsonl_file>"
    exit 1
fi

FILE="$1"

# Check if the file exists and is readable
if [ ! -f "$FILE" ] || [ ! -r "$FILE" ]; then
    echo "Error: File '$FILE' does not exist or is not readable."
    exit 2
fi

# Iterate over each line of the JSONL file
while IFS= read -r line; do
    # Construct command arguments from the JSON map
    # jq -r '. | to_entries | .[] | "--\(.key) \(.value)"' converts each key-value pair in the JSON object
    # into a format suitable for passing to the Python script
    # xargs -n 2 groups them back into pairs to handle as arguments correctly
    ARGS=$(echo "$line" | jq -r '. | to_entries | .[] | "--\(.key) \(.value)"' | xargs -n 2 echo)

    # Execute the Python script with the constructed arguments
    echo $ARGS
    python run.py $ARGS
done < "$FILE"
