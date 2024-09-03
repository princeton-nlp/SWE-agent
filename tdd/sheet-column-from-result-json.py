import json
import sys
from instances import instance_id_list

def main():
    if len(sys.argv) != 2:
        print("Usage: python gen-column.py <json_file_path>")
        sys.exit(1)

    json_file_path = sys.argv[1]

    try:
        with open(json_file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: File '{json_file_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in file '{json_file_path}'.")
        sys.exit(1)

    resolved_ids = set(data.get('resolved_ids', []))
    unresolved_ids = set(data.get('unresolved_ids', []))
    error_ids = set(data.get('error_ids', []))
    empty_patch_ids = set(data.get('empty_patch_ids', []))

    for instance_id in instance_id_list:
        if instance_id in resolved_ids:
            status = 'resolved'
        elif instance_id in unresolved_ids:
            status = 'unresolved'
        elif instance_id in error_ids:
            status = 'error'
        elif instance_id in empty_patch_ids:
            status = 'empty_patch'
        else:
            status = '(missing)'
        
        print(status)

if __name__ == "__main__":
    main()
