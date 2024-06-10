import argparse, glob, json, logging, os, re, requests, subprocess, sys

from multiprocessing import Pool, Manager

from swebench.versioning.constants import (
    SWE_BENCH_URL_RAW,
    MAP_REPO_TO_VERSION_PATHS,
    MAP_REPO_TO_VERSION_PATTERNS,
)
from swebench.versioning.utils import get_instances, split_instances

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


INSTALL_CMD = {
    "pytest-dev/pytest": "pip install -e .",
    "matplotlib/matplotlib": "python -m pip install -e .",
    "pydata/xarray": "pip install -e .",
}


def _find_version_in_text(text: str, instance: dict) -> str:
    """
    Helper function for applying regex patterns to look for versions in text

    Args:
        text (str): Text to search
        instance (dict): Instance to find version for
    Returns:
        str: Version text, if found
    """
    # Remove comments
    pattern = r'""".*?"""'
    text = re.sub(pattern, '', text, flags=re.DOTALL)
    # Search through all patterns
    for pattern in MAP_REPO_TO_VERSION_PATTERNS[instance["repo"]]:
        matches = re.search(pattern, text)
        if matches is not None:
            print(instance['repo'])
            if instance['repo'] == 'pyvista/pyvista':
                text = matches.group(0)
                text = text.split('=')[-1].strip() if '=' in text else text.strip()
                text = '.'.join(text.split(','))
                return text
            return str(matches.group(1)).replace(" ", "")


def get_version(instance, is_build=False, path_repo=None):
    """
    Function for looking up the version of a task instance.

    If is_build is True, then the version is looked up by 1. building the repo
    at the instance's base commit, 2. activating the conda environment, and 3.
    looking for the version according to a predefined list of paths.

    Otherwise, the version is looked up by searching GitHub at the instance's
    base commit for the version according to a predefined list of paths.

    Args:
        instance (dict): Instance to find version for
        is_build (bool): Whether to build the repo and look for the version
        path_repo (str): Path to repo to build
    Returns:
        str: Version text, if found
    """
    keep_major_minor = lambda x, sep: ".".join(x.strip().split(sep)[:2])
    paths_to_version = MAP_REPO_TO_VERSION_PATHS[instance["repo"]]
    version = None
    for path_to_version in paths_to_version:
        init_text = None
        if is_build and path_repo is not None:
            version_path_abs = os.path.join(path_repo, path_to_version)
            if os.path.exists(version_path_abs):
                logger.info(f"Found version file at {path_to_version}")
                with open(path_to_version) as f:
                    init_text = f.read()
        else:
            url = os.path.join(
                SWE_BENCH_URL_RAW,
                instance["repo"],
                instance["base_commit"],
                path_to_version,
            )
            init_text = requests.get(url).text
        version = _find_version_in_text(init_text, instance)
        if version is not None:
            if "." in version:
                version = keep_major_minor(version, ".")
            if "," in version:
                version = keep_major_minor(version, ",")
            version = re.sub(r"[^0-9\.]", "", version)
            return version
    return version


def map_version_to_task_instances(task_instances: list) -> dict:
    """
    Create a map of version key to list of task instances

    Args:
        task_instances (list): List of task instances
    Returns:
        dict: Map of version key to list of task instances
    """
    return_map = {}
    if "version" in task_instances[0]:
        for instance in task_instances:
            version = instance["version"]
            if version not in return_map:
                return_map[version] = []
            return_map[version].append(instance)
        return return_map
    for instance in task_instances:
        version = get_version(instance)
        if version not in return_map:
            return_map[version] = []
        return_map[version].append(instance)
    return return_map


def get_versions_from_build(data: dict):
    """
    Logic for looking up versions by building the repo at the instance's base
    commit and looking for the version according to repo-specific paths.

    Args:
        data (dict): Dictionary of data for building a repo for any task instance
            in a given list.
    """
    data_tasks, path_repo, conda_env, path_conda, save_path = (
        data["data_tasks"],
        data["path_repo"],
        data["conda_env"],
        data["path_conda"],
        data["save_path"],
    )
    # Activate conda environment and set installation command
    cmd_activate = f"source {os.path.join(path_conda, 'bin/activate')}"
    cmd_source = f"source {os.path.join(path_conda, 'etc/profile.d/conda.sh')}"
    cmd_install = INSTALL_CMD[data_tasks[0]["repo"]]

    # Change directory to repo testbed
    cwd = os.getcwd()
    os.chdir(path_repo)

    for instance in data_tasks[::-1]:
        # Reset repo to base commit
        subprocess.run(
            "git restore .", check=True, shell=True, stdout=subprocess.DEVNULL
        )
        subprocess.run(
            "git reset HEAD .", check=True, shell=True, stdout=subprocess.DEVNULL
        )
        subprocess.run(
            "git clean -fd", shell=True, check=True, stdout=subprocess.DEVNULL
        )
        out_check = subprocess.run(
            f"git -c advice.detachedHead=false checkout {instance['base_commit']}",
            shell=True,
            stdout=subprocess.DEVNULL,
        )
        if out_check.returncode != 0:
            logger.error(f"[{instance['instance_id']}] Checkout failed")
            continue

        # Run installation command in repo
        out_install = subprocess.run(
            f"{cmd_source}; {cmd_activate} {conda_env}; {cmd_install}",
            shell=True,
            stdout=subprocess.DEVNULL,
        )
        if out_install.returncode != 0:
            logger.error(f"[{instance['instance_id']}] Installation failed")
            continue

        # Look up version according to repo-specific paths
        version = get_version(instance, is_build=True, path_repo=path_repo)
        instance["version"] = version
        logger.info(f'For instance {instance["instance_id"]}, version is {version}')

    # Save results
    with open(save_path, "w") as f:
        json.dump(data_tasks, fp=f)
    os.chdir(cwd)


def get_versions_from_web(data: dict):
    """
    Logic for looking up versions by searching GitHub at the instance's base
    commit and looking for the version according to repo-specific paths.

    Args:
        data (dict): Dictionary of data for searching GitHub for any task instance
            in a given list.
    """
    data_tasks, save_path = data["data_tasks"], data["save_path"]
    version_not_found = data["not_found_list"]
    for instance in data_tasks:
        version = get_version(instance)
        if version is not None:
            instance["version"] = version
            logger.info(f'For instance {instance["instance_id"]}, version is {version}')
        elif version_not_found is not None:
            logger.info(f'[{instance["instance_id"]}]: version not found')
            version_not_found.append(instance)
    with open(save_path, "w") as f:
        json.dump(data_tasks, fp=f)


def merge_results(instances_path: str, repo_prefix: str, output_dir: str = None) -> int:
    """
    Helper function for merging JSON result files generated from multiple threads.

    Args:
        instances_path (str): Path to original task instances without versions
        repo_prefix (str): Prefix of result files (repo name)
        output_dir (str): Path to save merged results to
    Returns:
        int: Number of instances in merged results
    """
    # Merge values from result JSON files into a single list
    merged = []
    for task_with_version_path in glob.glob(f"{repo_prefix}_versions_*.json"):
        with open(task_with_version_path) as f:
            task_with_version = json.load(f)
            merged.extend(task_with_version)
        os.remove(task_with_version_path)

    # Save merged results to original task instances file's path with `_versions` suffix
    old_path_file = instances_path.split("/")[-1]
    instances_path_new = f"{old_path_file.split('.')[0]}_versions.json"
    if output_dir is not None:
        instances_path_new = os.path.join(output_dir, instances_path_new)
    with open(f"{instances_path_new}", "w") as f:
        json.dump(merged, fp=f)
    logger.info(f"Saved merged results to {instances_path_new} ({len(merged)} instances)")
    return len(merged)


def main(args):
    """
    Main function for looking up versions for task instances.
    """
    # Get task instances + split into groups for each thread
    data_tasks = get_instances(args.instances_path)
    data_task_lists = split_instances(data_tasks, args.num_workers)
    repo_prefix = data_tasks[0]["repo"].replace("/", "__")

    logger.info(
        f"Getting versions for {len(data_tasks)} instances for {data_tasks[0]['repo']}"
    )
    logger.info(
        f"Split instances into {len(data_task_lists)} groups with lengths {[len(x) for x in data_task_lists]}"
    )

    # If retrieval method includes GitHub, then search GitHub for versions via parallel call
    if any([x == args.retrieval_method for x in ["github", "mix"]]):
        manager = Manager()
        shared_result_list = manager.list()
        pool = Pool(processes=args.num_workers)
        pool.map(
            get_versions_from_web,
            [
                {
                    "data_tasks": data_task_list,
                    "save_path": f"{repo_prefix}_versions_{i}.json"
                    if args.retrieval_method == "github"
                    else f"{repo_prefix}_versions_{i}_web.json",
                    "not_found_list": shared_result_list
                    if args.retrieval_method == "mix"
                    else None,
                }
                for i, data_task_list in enumerate(data_task_lists)
            ],
        )
        pool.close()
        pool.join()

        if args.retrieval_method == "github":
            # If retrieval method is just GitHub, then merge results and return
            assert len(data_tasks) == merge_results(
                args.instances_path, repo_prefix, args.output_dir
            )
            return
        elif args.retrieval_method == "mix":
            # Otherwise, remove instances that were found via GitHub from the list
            shared_result_list = list(shared_result_list)
            total_web = len(data_tasks) - len(shared_result_list)
            logger.info(f"Retrieved {total_web} versions from web")
            data_task_lists = split_instances(shared_result_list, args.num_workers)
            logger.info(
                f"Split instances into {len(data_task_lists)} groups with lengths {[len(x) for x in data_task_lists]} for build"
            )

    # Check that all required arguments for installing task instances are present
    assert any([x == args.retrieval_method for x in ["build", "mix"]])
    assert all([x in args for x in ["testbed", "path_conda", "conda_env"]])
    conda_exec = os.path.join(args.path_conda, "bin/conda")

    cwd = os.getcwd()
    os.chdir(args.testbed)
    for x in range(0, args.num_workers):
        # Clone git repo per thread
        testbed_repo_name = f"{repo_prefix}__{x}"
        if not os.path.exists(testbed_repo_name):
            logger.info(
                f"Creating clone of {data_tasks[0]['repo']} at {testbed_repo_name}"
            )
            cmd_clone = (
                f"git clone git@github.com:swe-bench/{repo_prefix} {testbed_repo_name}"
            )
            subprocess.run(cmd_clone, shell=True, check=True, stdout=subprocess.DEVNULL)
        else:
            logger.info(
                f"Repo for {data_tasks[0]['repo']} exists: {testbed_repo_name}; skipping..."
            )
        # Clone conda environment per thread
        conda_env_name = f"{args.conda_env}_clone_{x}"
        if not os.path.exists(os.path.join(args.path_conda, "envs", conda_env_name)):
            logger.info(f"Creating clone of {args.conda_env} at {conda_env_name}")
            cmd_clone_env = f"{conda_exec} create --name {conda_env_name} --clone {args.conda_env} -y"
            subprocess.run(
                cmd_clone_env, shell=True, check=True, stdout=subprocess.DEVNULL
            )
        else:
            logger.info(
                f"Conda clone for thread {x} exists: {conda_env_name}; skipping..."
            )
    os.chdir(cwd)

    # Create pool tasks
    pool_tasks = []
    for i in range(0, args.num_workers):
        testbed_repo_name = f"{repo_prefix}__{i}"
        pool_tasks.append(
            {
                "data_tasks": data_task_lists[i],
                "path_repo": os.path.join(args.testbed, testbed_repo_name),
                "conda_env": f"{args.conda_env}_clone_{i}",
                "path_conda": args.path_conda,
                "save_path": os.path.join(cwd, f"{repo_prefix}_versions_{i}.json"),
            }
        )

    # Parallelized call
    pool = Pool(processes=args.num_workers)
    pool.map(get_versions_from_build, pool_tasks)
    pool.close()
    pool.join()

    # Check that correct number of instances were versioned
    if args.retrieval_method == "mix":
        assert (
            len(data_tasks)
            == merge_results(args.instances_path, repo_prefix, args.output_dir) + total_web
        )
    elif args.retrieval_method == "build":
        assert len(data_tasks) == merge_results(
            args.instances_path, repo_prefix, args.output_dir
        )

    # Remove testbed repo and conda environments
    if args.cleanup:
        cwd = os.getcwd()
        os.chdir(args.testbed)
        for x in range(0, args.num_workers):
            # Remove git repo
            testbed_repo_name = f"{repo_prefix}__{x}"
            subprocess.run(f"rm -rf {testbed_repo_name}", shell=True, check=True)

            # Remove conda environment
            cmd_rm_env = (
                f"{conda_exec} remove --name {args.conda_env}_clone_{x} --all -y"
            )
            subprocess.run(cmd_rm_env, shell=True, check=True)
        os.chdir(cwd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances_path", required=True, type=str, default=None, help="Path to task instances")
    parser.add_argument("--retrieval_method", required=True, choices=["build", "mix", "github"], default="github", help="Method to retrieve versions")
    parser.add_argument("--cleanup", action="store_true", help="Remove testbed repo and conda environments")
    parser.add_argument("--conda_env", type=str, default=None, help="Conda environment to use")
    parser.add_argument("--path_conda", type=str, default=None, help="Path to conda")
    parser.add_argument("--num_workers", type=int, default=1, help="Number of threads to use")
    parser.add_argument("--output_dir", type=str, default=None, help="Path to save results")
    parser.add_argument("--testbed", type=str, default=None, help="Path to testbed repo")
    args = parser.parse_args()
    main(args)
