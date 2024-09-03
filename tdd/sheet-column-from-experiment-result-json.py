import json
import sys
from instances import instance_id_list

def main():
    if len(sys.argv) != 2:
        print("Usage: python gen-column-old.py <json_file_path>")
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

    resolved_ids = set(data.get('resolved', []))
    no_logs_ids = set(data.get('no_logs', []))
    no_generation_ids = set(data.get('no_generation', []))


    for instance_id in instance_id_list:
        if instance_id in resolved_ids:
            status = 'resolved'
        elif instance_id in data.get('no_logs', []) or instance_id in data.get('no_generation', []):
            status = "(missing)"
        else:
            status = 'unresolved'
        
        print(status)

if __name__ == "__main__":
    main()
