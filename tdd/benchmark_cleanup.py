import os

# List of instances to delete
instances = [
    "django__django-13410",
    "django__django-13786",
    "django__django-14122",
    "django__django-14315",
    "django__django-14373",
    "django__django-14999",
    "django__django-15037",
    "django__django-16136",
    "django__django-16454",
    "django__django-9296",
    "psf__requests-2317",
    "pydata__xarray-4075",
    "pydata__xarray-4629",
    "pydata__xarray-6744",
    "pylint-dev__pylint-4604",
    "pytest-dev__pytest-5840",
    "pytest-dev__pytest-6197",
    "scikit-learn__scikit-learn-10297",
    "scikit-learn__scikit-learn-10844",
    "scikit-learn__scikit-learn-14141",
    "scikit-learn__scikit-learn-14629",
    "scikit-learn__scikit-learn-25102",
    "scikit-learn__scikit-learn-26194",
    "sympy__sympy-14531",
    "sympy__sympy-14976",
    "sympy__sympy-15875",
    "sympy__sympy-16766",
    "sympy__sympy-18211",
    "sympy__sympy-19637",
    "sympy__sympy-22080",
    "sympy__sympy-24539"
]

def delete_trajectory_files(base_path):
    deleted_count = 0
    for folder in os.listdir(base_path):
        folder_path = os.path.join(base_path, folder)
        if os.path.isdir(folder_path):
            for instance in instances:
                file_path = os.path.join(folder_path, f"{instance}.traj")
                if os.path.isfile(file_path):
                   try:
                       os.remove(file_path)
                       print(f"Deleted: {file_path}")
                       deleted_count += 1
                   except Exception as e:
                       print(f"Error deleting {file_path}: {e}")
    
    print(f"Total files deleted: {deleted_count}")

if __name__ == "__main__":
    user = os.environ.get('USER')
    if not user:
        print("Error: Unable to get USER environment variable.")
    else:
        base_path = f"trajectories/{user}"
        if os.path.exists(base_path):
            delete_trajectory_files(base_path)
        else:
            print(f"Error: The path {base_path} does not exist.")
