import subprocess
from pathlib import Path
from typing import Any

import rich

from run import ScriptArguments, logger
from sweagent.agent.agents import Agent
from sweagent.environment.swe_env import SWEEnv
from sweagent.main.hooks.abstract import MainHook


class SaveApplyPatchHook(MainHook):
    """This hook saves patches to a separate directory and optionally applies them to a local repository."""

    def on_init(self, *, args: ScriptArguments, agent: Agent, env: SWEEnv, traj_dir: Path):
        self._traj_dir = traj_dir
        self._apply_patch_locally = args.actions.apply_patch_locally
        self._instance = None

    def on_instance_start(self, *, index: int, instance: dict[str, Any]):
        self._instance = instance

    def on_instance_completed(self, *, info, trajectory):
        assert self._instance is not None  # mypy
        instance_id = self._instance["instance_id"]
        patch_path = self._save_patch(instance_id, info)
        if patch_path:
            if not self._apply_patch_locally:
                return
            if not self._is_promising_patch(info):
                return
            assert self._instance  # mypy
            if self._instance["repo_type"] != "local":
                return
            local_dir = Path(self._instance["repo"])
            self._apply_patch(patch_path, local_dir)

    @staticmethod
    def _print_patch_message(patch_output_file: Path):
        console = rich.console.Console()
        msg = [
            "SWE-agent has produced a patch that it believes will solve the issue you submitted!",
            "Use the code snippet below to inspect or apply it!",
        ]
        panel = rich.panel.Panel.fit(
            "\n".join(msg),
            title="🎉 Submission successful 🎉",
        )
        console.print(panel)
        content = [
            "```bash",
            "# The patch has been saved to your local filesystem at:",
            f"PATCH_FILE_PATH='{patch_output_file.resolve()}'",
            "# Inspect it:",
            'cat "${PATCH_FILE_PATH}"',
            "# Apply it to a local repository:",
            "cd <your local repo root>",
            'git apply "${PATCH_FILE_PATH}"',
            "```",
        ]
        console.print(rich.markdown.Markdown("\n".join(content)))

    def _save_patch(self, instance_id: str, info) -> Path | None:
        """Create patch files that can be applied with `git am`.

        Returns:
            The path to the patch file, if it was saved. Otherwise, returns None.
        """
        patch_output_dir = self._traj_dir / "patches"
        patch_output_dir.mkdir(exist_ok=True, parents=True)
        patch_output_file = patch_output_dir / f"{instance_id}.patch"
        if info.get("submission") is None:
            logger.info("No patch to save.")
            return None
        model_patch = info["submission"]
        patch_output_file.write_text(model_patch)
        if self._is_promising_patch(info):
            # Only print big congratulations if we actually believe
            # the patch will solve the issue
            self._print_patch_message(patch_output_file)
        return patch_output_file

    def _apply_patch(self, patch_file: Path, local_dir: Path) -> None:
        """Apply a patch to a local directory."""

        assert local_dir.is_dir()
        assert patch_file.exists()
        # The resolve() is important, because we're gonna run the cmd
        # somewhere else
        cmd = ["git", "apply", str(patch_file.resolve())]
        try:
            subprocess.run(cmd, cwd=local_dir, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to apply patch {patch_file} to {local_dir}: {e}")
            return
        logger.info(f"Applied patch {patch_file} to {local_dir}")
