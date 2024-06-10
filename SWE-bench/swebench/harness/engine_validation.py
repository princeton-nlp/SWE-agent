import argparse, os

from multiprocessing import Pool, cpu_count
from swebench.harness.constants import PatchType
from swebench.harness.context_manager import TaskEnvContextManager, TestbedContextManager
from swebench.harness.utils import get_instances, split_instances, DotDict


SKIP_INSTANCES = {"pytest-dev/pytest": ["6387", "7956", "3805"]}


def validate_args(args):
    """
    Validation for command line arguments
    """
    if not os.path.exists(args.instances_path):
        raise ValueError(f"Could not find instances file at {args.instances_path}")
    if not os.path.exists(args.log_dir):
        raise ValueError(f"Could not find log directory at {args.log_dir}")

    # If value is provided, check that the paths exist
    if args.path_conda is not None and not os.path.exists(args.path_conda):
        raise ValueError(f"Could not find conda installation at {args.path_conda}")
    if args.testbed is not None and not os.path.exists(args.testbed):
        raise ValueError(f"Could not find testbed at {args.testbed}")
    if args.temp_dir is not None and not os.path.exists(args.temp_dir):
        raise ValueError(f"Could not find temporary directory at {args.temp_dir}")

    # If value is provided, check that it is valid
    if args.timeout is not None and args.timeout < 0:
        raise ValueError(f"Timeout must be a positive integer")
    if args.num_workers is not None and args.num_workers < 1:
        raise ValueError(f"Number of workers must be a positive integer")


def verify_task_instances(data: dict):
    """
    Sets up task environment context manager. Each task instance is then
    installed and validated within the context manager.

    Args:
        data: Dict containing task instances and other data
            task_instances: List of task instances
            + setup_testbed args
    """
    data_dict = DotDict(data)
    for task_instance in data_dict.task_instances:
        with TaskEnvContextManager(
            task_instance,
            data_dict.testbed,
            data_dict.venv,
            data_dict.log_dir,
            data_dict.conda_path,
            verbose=data_dict.verbose,
            timeout=data_dict.timeout,
            log_suffix=data_dict.log_suffix,
        ) as tcm:
            if (
                task_instance["repo"] in SKIP_INSTANCES
                and task_instance["pull_number"]
                in SKIP_INSTANCES[task_instance["repo"]]
            ):
                continue
            if (
                not tcm.reset_task_env(task_instance)
                or not tcm.run_install_task(task_instance)
                or not tcm.apply_patch(task_instance["test_patch"], patch_type=PatchType.PATCH_TEST.value)
                or not tcm.run_tests_task(task_instance)
                or not tcm.apply_patch(task_instance["patch"], patch_type=PatchType.PATCH_GOLD.value)
                or not tcm.run_tests_task(task_instance)
            ):
                continue


def setup_testbed(data: dict):
    """
    Creates testbed context manager and runs verify_task_instances in parallel

    Args:
        data: Dict containing task instances and other data
        conda_link: URL to conda installation to use
        task_instances: List of task instances
        log_dir: Path to log directory
        path_conda: Path to miniconda3 or anaconda installation
        testbed: Path to testbed directory
        temp_dir: Path to temporary directory for storing virtual envs
        timeout: Timeout (seconds) for testing script execution
        verbose: Verbose mode
    """
    data_dict = DotDict(data)
    with TestbedContextManager(
        data_dict.task_instances,
        data_dict.log_dir,
        conda_link=data_dict.conda_link,
        path_conda=data_dict.path_conda,
        testbed=data_dict.testbed,
        temp_dir=data_dict.temp_dir,
        timeout=data_dict.timeout,
        verbose=data_dict.verbose,
    ) as tcm:
        distributed_task_list = tcm.get_distributed_tasks()
        for task_list in distributed_task_list:
            print(
                f"{task_list['testbed']}: {len(task_list['task_instances'])} instances"
            )

        if len(distributed_task_list) == 1:
            data_dict.func(distributed_task_list[0])
            return

        pool = Pool(processes=len(distributed_task_list))
        pool.map(data_dict.func, distributed_task_list)
        pool.close()
        pool.join()


def main(args):
    """
    Splits task instances into multiple groups if num_workers > 1
    """
    if args.num_workers is None:
        args.num_workers = cpu_count()

    task_instances = get_instances(args.instances_path)
    task_instances_groups = split_instances(task_instances, args.num_workers)

    data_groups = [
        {
            "task_instances": g,
            "func": verify_task_instances,
            **vars(args),
        }
        for g in task_instances_groups
    ]

    for group in data_groups:
        del group["instances_path"]

    if args.num_workers == 1:
        setup_testbed(data_groups[0])
        return

    pool = Pool(processes=args.num_workers)
    pool.map(setup_testbed, data_groups)
    pool.close()
    pool.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances_path", type=str, help="Path to candidate task instances file", required=True)
    parser.add_argument("--log_dir", type=str, help="Path to log directory", required=True)
    parser.add_argument("--conda_link", type=str, default=None, help="(Optional) URL to conda installation to use")
    parser.add_argument("--log_suffix", type=str, default=None, help="(Optional) Suffix to append to log file names")
    parser.add_argument("--path_conda", type=str, help="(Optional) Path to miniconda3 or anaconda installation")
    parser.add_argument("--testbed", type=str, help="(Optional) Path to testbed directory")
    parser.add_argument("--temp_dir", type=str, help="(Optional) Path to temporary directory for storing virtual envs")
    parser.add_argument("--timeout", type=int, default=None, help="(Optional) Timeout (seconds) for testing script execution")
    parser.add_argument("--verbose", action="store_true", help="(Optional) Verbose mode")
    parser.add_argument("--num_workers", type=int, default=None, help="(Optional) Number of workers")
    args = parser.parse_args()
    validate_args(args)
    main(args)
