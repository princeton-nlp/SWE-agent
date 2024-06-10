import logging, os, platform, subprocess, json

from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
from swebench.harness.constants import (
    APPLY_PATCH_FAIL,
    APPLY_PATCH_PASS,
    DEFAULT_CONDA_LINK,
    INSTALL_FAIL,
    INSTALL_PASS,
    INSTALL_TIMEOUT,
    KEY_INSTANCE_ID,
    KEY_MODEL,
    MAP_REPO_TO_INSTALL,
    MAP_REPO_TO_TEST_FRAMEWORK,
    MAP_REPO_VERSION_TO_CONDA_LINK,
    MAP_VERSION_TO_INSTALL,
    RESET_FAILED,
    TESTS_FAILED,
    TESTS_PASSED,
    TESTS_TIMEOUT,
    TESTS_ERROR,
    PatchType,
)
from swebench.harness.utils import (
    clone_repo,
    get_conda_env_names,
    get_environment_yml,
    get_requirements,
    get_test_directives,
)
from tempfile import TemporaryDirectory
from traceback import format_exc

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s")
logger_testbed = logging.getLogger("testbed")


class LogWrapper:
    def __init__(
        self,
        log_file: str,
        logger: logging.Logger = None,
        prefix: str = None,
    ):
        self.log_file = log_file
        self.logger = logger
        self.prefix = prefix

    def write(
            self,
            message: str,
            mode: str = "a",
            level: int = INFO):
        with open(self.log_file, mode) as f:
            log = f"{self.prefix} {message} \n" if self.prefix \
                is not None else f"{message} \n"
            f.write(log)
        if self.logger is not None:
            self.logger.log(level, message)


class ExecWrapper:
    def __init__(
        self,
        subprocess_args: dict = None,
        logger: LogWrapper = None,
    ):
        self.logger = logger
        if subprocess_args is None:
            self.subprocess_args = {}
        else:
            self.subprocess_args = subprocess_args

    def __call__(self, cmd, raise_error=True, **kwargs):
        try:
            if isinstance(cmd, list):
                self.logger.write(f"Command: {' '.join(cmd)}", level=DEBUG)
            else:
                self.logger.write(f"Command: {cmd}", level=DEBUG)
            combined_args = {**self.subprocess_args, **kwargs}
            self.logger.write(f"Subprocess args: {json.dumps(combined_args)}", level=DEBUG)
            output = subprocess.run(cmd, **combined_args)
            self.logger.write(f"Std. Output:\n{output.stdout}", level=DEBUG)
            if output.stderr:
                self.logger.write(f"Std. Error:\n{output.stderr}", level=DEBUG)
            self.logger.write(f"Return Code: {output.returncode}", level=DEBUG)
            return output
        except subprocess.CalledProcessError as e:
            if raise_error and self.logger is not None:
                self.logger.write(f"Error: {e}", level=ERROR)
                self.logger.write(f"Error stdout: {e.stdout}", level=ERROR)
                if e.stderr:
                    self.logger.write(f"Error stderr: {e.stderr}", level=ERROR)
                self.logger.write(f"Error traceback: {format_exc()}", level=ERROR)
                raise e


class TestbedContextManager:
    def __init__(
        self,
        task_instances: list,
        log_dir: str,
        conda_link: str = None,
        path_conda: str = None,
        temp_dir: str = None,
        testbed: str = None,
        timeout: int = None,
        verbose: bool = False,
    ):
        """
        Initialize testbed context. Creates temporary directories and groups task instances
        by repo/version.

        Args:
            task_instances (list): List of task instances
            log_dir (str): Path to log directory
            conda_link(str): URL to conda installation to use
            path_conda (str): Path to conda installation
            testbed (str): Path to testbed directory
            verbose (bool): Whether to show logs
            timeout (int): Timeout for actions
            temp_dir (str): Path to temporary directory
        """
        if verbose:
            logger_testbed.setLevel(logging.INFO)
        self.conda_link = conda_link
        self.log_dir = os.path.abspath(log_dir)
        self.old_dir = os.getcwd()
        self.timeout = timeout
        self.verbose = verbose
        self.exec = ExecWrapper(
            subprocess_args={
                "check": True,
                "shell": False,
                "capture_output": False,
                "text": True,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
            },
        )

        # Create log, temp directories if they don't exist
        if not os.path.exists(self.log_dir):
            logger_testbed.info(f"[Testbed] Creating log directory {self.log_dir}")
            os.makedirs(self.log_dir, exist_ok=True)
        if temp_dir is not None and not os.path.exists(temp_dir):
            logger_testbed.info(f"[Testbed] Creating temp directory {temp_dir}")
            os.makedirs(temp_dir, exist_ok=True)
        temp_dir = os.path.abspath(temp_dir) if temp_dir is not None else None

        # Sort task instances by created_at
        self.task_instances = sorted(
            task_instances, key=lambda x: x["created_at"], reverse=True
        )

        # Group repos by repo, then version
        self.task_instances_grouped = {}
        for instance in self.task_instances:
            # Create test command from framework + directives
            test_type = MAP_REPO_TO_TEST_FRAMEWORK[instance["repo"]]
            instance["test_directives"] = get_test_directives(instance)
            instance["test_cmd"] = f"{test_type} {' '.join(instance['test_directives'])}"

            # Group task instances by repo, version
            repo = instance["repo"]
            version = instance["version"] if "version" in instance else None
            if repo not in self.task_instances_grouped:
                self.task_instances_grouped[repo] = {}
            if version not in self.task_instances_grouped[repo]:
                self.task_instances_grouped[repo][version] = []
            self.task_instances_grouped[repo][version].append(instance)
        
        # Check if instances are from single repo/version
        self.is_single_repo_version = len(self.task_instances_grouped) == 1 and \
            len(self.task_instances_grouped) == 1 and \
            len(list(self.task_instances_grouped.values())[0]) == 1
        
        # Create log file for testbed
        log_file_name = "testbed"
        if self.is_single_repo_version:
            key, versions = list(self.task_instances_grouped.items())[0]
            _, repo = key.split("/")
            version = list(versions.keys())[0]
            log_file_name += f"_{repo}_{version}.log"
        else:
            # TODO: Make log file name more intelligible, random 4 digit number for now
            # This random naming is necessary due to parallelized execution
            log_file_name += f"_{os.urandom(24).hex()}.log"

        self.log_file = os.path.join(self.log_dir, log_file_name)
        self.log = LogWrapper(self.log_file, logger=logger_testbed, prefix="[Testbed]")
        self.exec.logger = self.log
        self.log.write(f"Created log file {self.log_file}", mode="w")

        # Get reference set up instances for each repo/version
        self.setup_refs = {}
        for repo, map_version_to_instances in self.task_instances_grouped.items():
            self.log.write(f"Repo {repo}: {len(map_version_to_instances)} versions")

            # Determine instances to use for environment installation
            self.setup_refs[repo] = {}
            for version, instances in map_version_to_instances.items():
                self.log.write(f"\tVersion {version}: {len(instances)} instances")
                # Use the first instance as set up for each version
                self.setup_refs[repo][version] = instances[0]

        # Set up conda path, create in temp directory if None
        if path_conda is not None:
            self.temp_dir_conda = None
            self.path_conda = os.path.abspath(path_conda)
        else:
            self.temp_dir_conda = TemporaryDirectory(dir=temp_dir)
            self.path_conda = self.temp_dir_conda.name
        self.log.write(f"Using conda path {self.path_conda}")

        # Set up testbed path, create in temp directory if None
        if testbed is not None:
            self.temp_dir_work = None
            self.testbed = os.path.abspath(testbed)
        else:
            self.temp_dir_work = TemporaryDirectory(dir=temp_dir)
            self.testbed = self.temp_dir_work.name
        self.log.write(f"Using working directory {self.testbed} for testbed")

        # Remove None versions, versions not in MAP_VERSION_TO_INSTALL
        self._custom_restraints()

    def __enter__(self):
        """
        Set up testbed (conda environments, git repositories)
        """
        # If path_conda not provided, create temporary miniconda3 installation
        is_osx_64 = False
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            is_osx_64 = True
        if self.temp_dir_conda is not None:
            # Set up the paths for Miniconda
            self.path_conda = os.path.join(self.path_conda, "miniconda3")
            os.mkdir(self.path_conda)
            miniconda_sh = os.path.join(self.path_conda, "miniconda.sh")
            self.log.write(f"No conda path provided, creating temporary install in {self.path_conda}...")

            # Download Miniconda installer
            if self.conda_link is not None:
                cmd_line_install_link = self.conda_link
            else:
                cmd_line_install_link = "https://repo.anaconda.com/miniconda/Miniconda3-"

                # Adjust version for evaluation by repo/version
                if self.is_single_repo_version:
                    key, versions = list(self.setup_refs.items())[0]
                    owner, repo = key.split("/")
                    version = list(versions.keys())[0]
                    self.log.write(f"{repo}/{version} instances in a single process")
                    conda_id = MAP_REPO_VERSION_TO_CONDA_LINK.get(repo, {}).get(version, DEFAULT_CONDA_LINK)
                    cmd_line_install_link += conda_id
                    self.log.write(f"{repo}/{version} using Miniconda link: {cmd_line_install_link}")
                else:
                    cmd_line_install_link += DEFAULT_CONDA_LINK
                    self.log.write(f"Multiple repos/versions; using Miniconda link: {cmd_line_install_link}")

                if platform.system() == "Darwin":
                    if is_osx_64:
                        cmd_line_install_link += "-MacOSX-arm64.sh"
                    else:
                        cmd_line_install_link += "-MacOSX-x86_64.sh"
                elif platform.system() == "Linux":
                    if platform.machine() == "aarch64":
                        cmd_line_install_link += "-Linux-aarch64.sh"
                    else:
                        cmd_line_install_link += "-Linux-x86_64.sh"
                else:
                    raise ValueError("Unknown computer platform " + platform.system())

            download_cmd = [
                "wget",
                cmd_line_install_link,
                "-O",
                miniconda_sh,
            ]
            self.exec(download_cmd)

            # Install Miniconda
            install_cmd = ["bash", miniconda_sh, "-b", "-u", "-p", self.path_conda, "&&", "conda", "init", "--all"]
            self.exec(install_cmd)
            if is_osx_64:
                condabin = os.path.join(self.path_conda, "bin", "conda")
                config_cmd = [condabin, "config", "--env", "--set", "subdir", "osx-64"]
                self.exec(config_cmd)

            # Clean up the installer
            os.remove(miniconda_sh)
        self.log.write(f"Using conda path {self.path_conda}")

        # Set up conda executables, get existing environments
        self.path_conda = os.path.abspath(self.path_conda)
        path_activate = os.path.join(self.path_conda, "bin", "activate")
        exec_cmd = os.path.join(self.path_conda, "bin", "conda")
        env_list = get_conda_env_names(exec_cmd)

        # Set up testbed (environment, github repo) for each repo
        for repo, version_to_setup_ref in self.setup_refs.items():
            repo_prefix = repo.replace("/", "__")

            # Run any repo-level installation commands if provided
            if repo in MAP_REPO_TO_INSTALL:
                install_cmd = MAP_REPO_TO_INSTALL[repo]
                self.log.write(f"Running custom install command for {repo}: {install_cmd}")
                self.exec(install_cmd)

            # Create conda environment per version of the repo
            for version, install in MAP_VERSION_TO_INSTALL[repo].items():
                # Skip if none of the task instances are for this version
                if version not in version_to_setup_ref:
                    continue

                # Name for both environment and github repo
                env_name = f"{repo_prefix}__{version}"
                self.log.write(f"Setting up testbed for {env_name}")

                # Clone github per repo/version
                repo_path = os.path.join(self.testbed, env_name)
                if not os.path.exists(repo_path):
                    if clone_repo(repo, repo_path):
                        self.log.write(f"Cloned {repo} to {repo_path}")
                    else:
                        raise Exception(f"Failed to clone {repo} to {repo_path}")
                else:
                    self.log.write(f"Repo for {repo_prefix} version {version} exists: {repo_path}; skipping")

                # Skip if conda environment already exists
                if env_name in env_list:
                    self.log.write(f"Environment {env_name} already exists; skipping")
                    continue

                # Get setup reference instance
                setup_ref_instance = version_to_setup_ref[version]

                # Create conda environment according to install instructinos
                pkgs = install["packages"] if "packages" in install else ""
                if pkgs == "requirements.txt":
                    # Create environment
                    cmd = (
                        f"{exec_cmd} create -n {env_name} python={install['python']} -y"
                    )
                    self.log.write(f"Creating environment {env_name}")
                    self.exec(cmd.split(" "))

                    # Install dependencies
                    path_to_reqs = get_requirements(setup_ref_instance, self.testbed)
                    cmd = f". {path_activate} {env_name} && echo 'activate successful' && pip install -r {path_to_reqs}"
                    self.log.write(f"Installing dependencies for {env_name}; Command: {cmd}")
                    self.exec(cmd, shell=True)
                    os.remove(path_to_reqs)
                elif pkgs == "environment.yml":
                    if "no_use_env" in install and install["no_use_env"]:
                        # Create environment from yml
                        path_to_reqs = get_environment_yml(
                            setup_ref_instance, env_name,
                            save_path=self.testbed
                        )

                        # `conda create` based installation
                        cmd = f"{exec_cmd} create -c conda-forge -n {env_name} python={install['python']} -y"
                        self.log.write(f"Creating environment {env_name}")
                        self.exec(cmd.split(" "))

                        # Install dependencies
                        cmd = f"{exec_cmd} env update -f {path_to_reqs}"
                        self.log.write(f"Installing dependencies for {env_name}; Command: {cmd}")
                        self.exec(cmd.split(" "))
                    else:
                        # Create environment from yml
                        path_to_reqs = get_environment_yml(
                            setup_ref_instance, env_name,
                            save_path=self.testbed,
                            python_version=install["python"]
                        )

                        # `conda env create` based installation
                        cmd = f"{exec_cmd} env create --file {path_to_reqs}"
                        self.log.write(f"Creating environment {env_name}")
                        self.exec(cmd.split(" "))

                    # Remove environment.yml
                    os.remove(path_to_reqs)
                else:
                    # Create environment + install dependencies
                    cmd = f"{exec_cmd} create -n {env_name} python={install['python']} {pkgs} -y"
                    self.log.write(f"Creating environment {env_name}")
                    self.exec(cmd.split(" "))
                
                arch = platform.machine()
                arch_specific_packages = install.get("arch_specific_packages", {}).get(arch, "")
                if arch_specific_packages:
                    cmd = f". {path_activate} {env_name} && conda install {arch_specific_packages} -y"
                    self.log.write(f"Installing arch-specific packages for {env_name}; Command: {cmd}")
                    self.exec(cmd, shell=True)

                # Install additional packages if specified
                if "pip_packages" in install:
                    pip_packages = " ".join(install["pip_packages"])
                    cmd = f". {path_activate} {env_name} && pip install {pip_packages}"
                    self.log.write(f"Installing pip packages for {env_name}; Command: {cmd}")
                    self.exec(cmd, shell=True)

        return self

    def get_distributed_tasks(self) -> list:
        """
        Create task group (instances + keywords) for each repo/version

        Returns:
            list: List of task groups, each group containing task instances
                from the same repo with the same version
        """
        distributed_tasks = []
        for repo, map_version_to_instances in self.task_instances_grouped.items():
            repo_prefix = repo.replace("/", "__")
            for version, instances in map_version_to_instances.items():
                env_name = f"{repo_prefix}__{version}"
                task_set = {
                    "conda_path": self.path_conda,
                    "log_dir": self.log_dir,
                    "task_instances": instances,
                    "testbed": os.path.join(self.testbed, env_name),
                    "timeout": self.timeout,
                    "venv": env_name,
                    "version": version,
                    "verbose": self.verbose,
                }
                distributed_tasks.append(task_set)
        return distributed_tasks

    def _custom_restraints(self):
        """
        Custom restraints per repo
        """
        for repo, group in self.task_instances_grouped.items():
            if None in group:
                self.log.write(f"Removed None version from repo {repo}")
                del group[None]
            versions = list(group.keys())
            for version in versions:
                if version not in MAP_VERSION_TO_INSTALL[repo]:
                    self.log.write((
                        f"Removed {version} version from repo "
                        f"{repo} (Install instructions not given)"
                    ))
                    del group[version]

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.temp_dir_work is not None:
            self.temp_dir_work.cleanup()
        if self.temp_dir_conda is not None:
            self.temp_dir_conda.cleanup()


logger_taskenv = logging.getLogger("taskenv")


class TaskEnvContextManager:
    def __init__(
        self,
        instance: dict,
        testbed: str,
        venv: str,
        log_dir: str,
        conda_path: str,
        verbose: bool = False,
        timeout: int = None,
        is_eval: bool = False,
        log_suffix: str = None,
    ):
        """
        Sets up execution context for a single task instance

        Args:
            instance (dict): Task instance
            testbed (str): Path to testbed directory
            venv (str): Name of conda environment (should exist in conda_path)
            log_dir (str): Path to log directory
            conda_path (str): Path to conda installation
            verbose (bool): Whether to show logs
            timeout (int): Timeout for actions
            is_eval (bool): Whether this is for evaluating a model on SWE Bench
                (Mainly for logging purposes)
        """
        if verbose:
            logger_taskenv.setLevel(logging.INFO)
        self.instance = instance
        self.conda_path = conda_path
        self.conda_cache_dir = os.path.join(self.conda_path, "cache")
        self.cwd = os.getcwd()
        self.is_eval = is_eval
        self.testbed = testbed
        self.testbed_name = testbed.split("/")[-1]
        self.venv = venv

        # Log file naming
        log_file_name = (
            f"{instance[KEY_INSTANCE_ID]}.{instance[KEY_MODEL]}.eval.log"
            if self.is_eval
            else f"{instance[KEY_INSTANCE_ID]}.log"
        )
        if log_suffix is not None:
            log_file_name = (
                f"{instance[KEY_INSTANCE_ID]}.{instance[KEY_MODEL]}.{log_suffix}.eval.log"
                if self.is_eval
                else f"{instance[KEY_INSTANCE_ID]}.{log_suffix}.log"
            )
        self.log_file = os.path.join(log_dir, log_file_name)
        self.log = LogWrapper(
            self.log_file, logger=logger_taskenv,
            prefix=f"[{self.testbed_name}] [{self.instance[KEY_INSTANCE_ID]}]")

        self.cmd_activate = (
            f". {os.path.join(self.conda_path, 'bin', 'activate')} "
            + f"{self.venv} && echo 'activate successful'"
        )
        self.timeout = timeout

        self.exec = ExecWrapper(
            subprocess_args={
                "check": True,
                "shell": False,
                "capture_output": False,
                "text": True,
                "env": {"CONDA_PKGS_DIRS": self.conda_cache_dir},
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
            },
            logger=self.log,
        )

    def __enter__(self):
        """
        Enter task environment, set up log file
        """
        os.chdir(self.testbed)
        enter_msg = (
            f"Task Metadata:\n\t- "
            f"Instance ID: {self.instance[KEY_INSTANCE_ID]}\n\t- "
            f"Testbed: {self.testbed}\n\t- "
            f"Virtual Env.: {self.venv}"
        )
        if self.is_eval:
            enter_msg += f"\n\t- Evaluation Model: {self.instance[KEY_MODEL]}"
        self.log.write(enter_msg, mode="w")
        return self

    def reset_task_env(self, instance: dict):
        """
        Reset task environment + testbed and checkout base commit of given task instance

        Args:
            instance (dict): Task instance
        Returns:
            bool: True if reset successful, False otherwise
        """
        try:
            # Remove all paths in .gitignore
            if os.path.exists(".gitignore"):
                self.exec(
                    "git ls-files --ignored --exclude-standard -o -z | xargs -0 -r rm -rf".split(),
                    raise_error=False,
                )

            # Reset git repo + checkout base commit
            self.exec("git restore .".split(" "))
            self.exec("git reset HEAD .".split(" "))
            self.exec("git clean -fdx".split(" "))
            self.exec(
                f"git -c advice.detachedHead=false checkout {instance['base_commit']}".split(
                    " "
                )
            )
            self.log.write(f"Reset task environment to {instance['base_commit']}")
            return True
        except Exception as e:
            err_msg = f"{RESET_FAILED}; Failed to reset task environment to {instance['base_commit']}: {e}"
            self.log.write(err_msg, level=ERROR)
            with open(self.log_file, "a") as f:
                f.write(err_msg)
            return False

    def run_install_task(self, instance: dict) -> bool:
        """
        Run installation for task instance

        Args:
            instance (dict): Task instance
        Returns:
            bool: True if installation successful, False otherwise
        """
        # Get installation instructions by repo/version
        specifications = MAP_VERSION_TO_INSTALL[instance["repo"]][instance["version"]]

        # Run pre-install set up if provided
        if "pre_install" in specifications:
            for pre_install in specifications["pre_install"]:
                cmd_pre_install = f"{self.cmd_activate} && {pre_install}"
                self.log.write(f"Running pre-install setup command: {cmd_pre_install}")
                out_pre_install = self.exec(
                    cmd_pre_install, timeout=self.timeout, shell=True
                )
                with open(self.log_file, "a") as f:
                    f.write(f"Pre-installation Command: {cmd_pre_install}\n")
                    f.write(f"Std. Output: {out_pre_install.stdout}\n")
                    if out_pre_install.stderr:
                        f.write(f"Std. Error: {out_pre_install.stderr}\n")
                if out_pre_install.returncode != 0:
                    self.log.write(f"Pre-install setup failed", level=ERROR)
                    with open(self.log_file, "a") as f:
                        f.write(f"\n{INSTALL_FAIL}\n")
                    return False

        # Skip installation if no instructions provided
        if "install" not in specifications:
            return True

        cmd_install = f"{self.cmd_activate} && {specifications['install']}"
        self.log.write(f"Running installation command: {cmd_install}")
        try:
            # Run installation command
            out_install = self.exec(cmd_install, timeout=self.timeout, shell=True)

            if out_install.returncode != 0:
                # Installation failed
                self.log.write(f"Installation failed", level=ERROR)
                with open(self.log_file, "a") as f:
                    f.write(f"\n{INSTALL_FAIL}\n")
                return False

            # Installation successful
            self.log.write(f"Installation successful")
            with open(self.log_file, "a") as f:
                f.write(f"\n{INSTALL_PASS}\n")
            return True
        except subprocess.TimeoutExpired:
            # Installation timed out
            self.log.write(f"Installation timed out", level=ERROR)
            with open(self.log_file, "a") as f:
                f.write(f"\n{INSTALL_TIMEOUT}\n")
            return False
        except Exception as e:
            # Installation failed
            self.log.write(f"Installation failed", level=ERROR)
            with open(self.log_file, "a") as f:
                f.write(f"\n{INSTALL_FAIL}: {e}\n")
            return False

    def apply_patch(
        self, patch: str, patch_type: PatchType = "", revert: bool = False
    ) -> bool:
        """
        Apply patch to task environment

        Args:
            patch (str): Plaintext of patch to apply
            patch_type (str): Type of patch (e.g. "eval", "test")
        Returns:
            bool: True if patch applied successfully, False otherwise
        """
        # If patch is `None`, indicate in log and skip
        if patch is None:
            self.log.write(f"Patch is `None` ({patch_type})")
            with open(self.log_file, "a") as f:
                f.write(f"{APPLY_PATCH_FAIL}; Prediction patch is `None`")
            return False

        # Write patch to temporary patch file in parent directory
        patch_path = os.path.join(
            os.path.dirname(self.testbed.rstrip("/")),
            f"temp_{self.instance[KEY_INSTANCE_ID]}_{patch_type}.patch",
        )
        with open(patch_path, "w") as f:
            f.write(patch)

        # Restore test files before applying if patch_type is 'test'
        if patch_type == PatchType.PATCH_TEST.value:
            for test in self.instance["test_directives"]:
                if os.path.exists(test):
                    self.exec(f"git restore {test}".split(" "))

        # Apply patch to testbed directory
        apply_cmd = (
            f"git apply -v -R {patch_path}" if revert else f"git apply -v {patch_path}"
        )
        out_patch = self.exec(apply_cmd.split(" "), raise_error=False, check=False)
        os.remove(patch_path)

        log_cmd = "Revert" if revert else "Apply"
        if out_patch.returncode != 0:
            # Patch apply failed
            self.log.write(f"{log_cmd} patch failed ({patch_type})", level=ERROR)
            with open(self.log_file, "a") as f:
                f.write(f"{APPLY_PATCH_FAIL}; ({patch_type})\nOutput:\n")
                f.write(out_patch.stdout)
                if out_patch.stderr:
                    f.write(out_patch.stderr)
            return False

        # Patch apply succeeded
        self.log.write(f"{log_cmd} patch successful ({patch_type})")
        with open(self.log_file, "a") as f:
            f.write(f"{APPLY_PATCH_PASS} ({patch_type})\n")
        return True

    def run_tests_task(self, instance: dict):
        """
        Run tests for task instance

        Args:
            instance (dict): Task instance
        Returns:
            bool: True if test script ran successfully, False otherwise
        """
        try:
            # Run test command for task instance
            test_cmd = f"{self.cmd_activate} && {instance['test_cmd']}"
            with open(self.log_file, "a") as f:
                f.write(f"Test Script: {test_cmd};\n")

            # Set environment variables if provided
            specifications = MAP_VERSION_TO_INSTALL[instance["repo"]][instance["version"]]
            if "env_vars_test" in specifications:
                self.exec.subprocess_args["env"].update(specifications["env_vars_test"])

            out_test = self.exec(
                test_cmd, shell=True, timeout=self.timeout, check=False
            )

            # Unset environment variables if provided
            if "env_vars_test" in specifications:
                for key in specifications["env_vars_test"]:
                    del self.exec.subprocess_args["env"][key]

            # Write pass/fail status to log file
            with open(self.log_file, "a") as f:
                if out_test.returncode != 0:
                    f.write(f"\n{TESTS_FAILED}\n")
                else:
                    f.write(f"\n{TESTS_PASSED}\n")

            self.log.write(f"Test script run successful")
            return True
        except subprocess.TimeoutExpired:
            # Test command run timed out
            self.log.write("Test script run timed out", level=ERROR)
            with open(self.log_file, "a") as f:
                f.write(f"{TESTS_TIMEOUT} after {self.timeout} seconds\n")
            return False
        except Exception as e:
            # Test command run failed
            self.log.write(f"Test script run failed", level=ERROR)
            with open(self.log_file, "a") as f:
                f.write(f"{TESTS_ERROR}: {e}")
            return False

    def __exit__(self, exc_type, exc_value, exc_traceback):
        os.chdir(self.cwd)
