from __future__ import annotations
import os
from typing import Tuple

from sweagent.utils.log import get_logger
from sweagent.agent.model_cache import json_serialize_file, json_deserialize_file, json_serialize_str, json_deserialize_str, hash_string

ManualTDDInputEnvVar = "MANUAL_TDD_INPUT_DIRECTORY"

logger = get_logger("manual_tdd_input")

class ManualInput:
    base_dir: str | None
    instance_id: str | None
    conversation_path: str | None
    continuation_label: str | None

    def __init__(self, conversation_path: str | None, continuation_label: str | None):
        self.conversation_path = conversation_path
        self.continuation_label = continuation_label
        self.base_dir = None
        if ManualTDDInputEnvVar in os.environ:
            logger.warning("⚠ ManualInput is enabled")
            self.base_dir = os.environ[ManualTDDInputEnvVar]

    def enabled(self) -> bool:
        return self.base_dir is not None
    
    def set_instance_id(self, instance_id: str) -> None:
        self.instance_id = instance_id

    def _get_conversation_dir(self) -> str:
        if self.conversation_path is None:
            return os.path.join(self.base_dir, self.instance_id)
        return os.path.join(self.base_dir, self.instance_id, self.conversation_path)

    def load_continuation_file(self) -> str | None:
        if not self.enabled():
            return None

        try:
            with open(os.path.join(self._get_conversation_dir(), f"{self.continuation_label}.md"), "r") as f:
                return f.read()
        except FileNotFoundError:
            return None

    def save_conversation(self, conversation: list[dict[str, str]], patch: str | None) -> None:
        if not self.enabled():
            return None

        parent_dir = self._get_conversation_dir()

        # if continuation_label is left off, we're storing the root conversation
        if self.continuation_label is None:
            self.continuation_label = "root"

        content = json_serialize_str(conversation)
        hash = hash_string(content)

        new_subdir = os.path.join(parent_dir, f"{self.continuation_label}-{hash}")
        os.makedirs(new_subdir, exist_ok=True)
        
        with open(os.path.join(new_subdir, "conversation.json"), "w") as f:
            f.write(content)

        if patch is not None and patch.strip() != "":
            with open(os.path.join(new_subdir, "patch.diff"), "w") as f:
                f.write(patch)

        subdir_to_print = new_subdir[len(self.base_dir):]
        logger.info(f"Conversation saved to ${ManualTDDInputEnvVar}%s", subdir_to_print)

    def load_conversation(self) -> Tuple[list[dict[str, str]], str] | None:
        if not self.enabled():
            return None

        dir = self._get_conversation_dir()
        if not os.path.exists(dir):
            return None
        
        conversation_file_path = os.path.join(dir, "conversation.json")
        if not os.path.exists(conversation_file_path):
            return None
        
        with open(conversation_file_path, "r") as f:
            conversation = json_deserialize_str(f.read())

        patch_file_path = os.path.join(dir, "patch.diff")

        # a missing patch isn't an error (will happen with the first tdd_repro call)
        if os.path.exists(patch_file_path):
            with open(patch_file_path, "r") as f:
                patch = f.read()
        else:
            patch = None

        dir_to_print = dir[len(self.base_dir):]
        logger.info("Conversation loaded from ${ManualTDDInputEnvVar}%s", dir_to_print)

        return conversation, patch