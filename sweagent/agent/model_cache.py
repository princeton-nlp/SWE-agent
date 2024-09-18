from __future__ import annotations
import json
import hashlib
import os
import copy
from typing import Any

from anthropic.types import ContentBlock, TextBlock, ToolUseBlock, ToolResultBlockParam

from sweagent.utils.log import get_logger
from sweagent.agent.model_result import AnthropicModelResult, ModelQueryResult

ModelCacheEnvVar = "MODEL_CACHE_DIRECTORY"

logger = get_logger("model_cache")


class CacheEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, AnthropicModelResult):
            return {
                "type": "anthropic_model_result",
                "blocks": [encode_anthropic_types(block) for block in o.blocks],
            }

        encoded = encode_anthropic_types(o)
        if encoded is not None:
            return encoded

        return super().default(o)


def encode_anthropic_types(obj) -> dict[str, Any] | None:
    # it should be possible to use the Anthropic library to encode these (using BaseModel#to_dict),
    # but there doesn't seem to be a way to reconstruct instances from those dicts directly.  Given
    # that it seems I have to write the latter, I'd like to keep code for both close to the other to
    # make it easier to keep them in sync.
    if isinstance(obj, TextBlock):
        return {
            "type": "text",
            "text": obj.text,
        }

    if isinstance(obj, ToolUseBlock):
        return {
            "type": "tool_use",
            "id": obj.id,
            "name": obj.name,
            "input": obj.input,
        }

    if isinstance(obj, dict) and "type" in obj and obj["type"] == "tool_result":
        return {
            "type": "tool_result",
            "tool_use_id": obj["id"],
            "is_error": obj["is_error"],
            "content": [encode_anthropic_types(c) for c in obj["content"]],
        }

    return None


def cache_decoder(dct: dict[str, Any]):
    if "type" not in dct:
        return dct

    if dct["type"] == "anthropic_model_result":
        return AnthropicModelResult(blocks=dct["blocks"])

    if dct["type"] == "text":
        return TextBlock(type="text", text=dct["text"])

    if dct["type"] == "tool_use":
        return ToolUseBlock(
            type="tool_use",
            id=dct["id"],
            name=dct["name"],
            input=dct["input"],
        )

    if dct["type"] == "tool_result":
        return ToolResultBlockParam(
            type="tool_result",
            tool_use_id=dct["tool_use_id"],
            is_error=dct["is_error"],
            content=dct["content"],
        )


def normalize_tool_use_ids(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # grovel around in the history and find all tool_result blocks.  for all those tool_use_ids
    # generate a dictionary from id -> int (starting at 1).  then go through the history and
    # replace all tool_use_id's/id's with the corresponding integer if the id is a key in the dict.

    mapping = {}
    for entry in history:
        if not isinstance(entry["content"], list):
            continue
        for c in entry["content"]:
            if not isinstance(c, dict) or "tool_use_id" not in c:
                continue
            id = c["tool_use_id"]
            mapping[id] = len(mapping) + 1

    if len(mapping) == 0:
        return history

    normalized = copy.deepcopy(history)

    logger.warn("Normalizing tool use ids")
    for entry in normalized:
        if not isinstance(entry["content"], list):
            continue
        for c in entry["content"]:
            if isinstance(c, ToolUseBlock):
                if c.id in mapping:
                    mapped = mapping[c.id]
                    c.id = f"toolu_normalized_{mapped}"
                continue

            if "tool_use_id" in c:
                id = c["tool_use_id"]
                if id in mapping:
                    mapped = mapping[id]
                    c["tool_use_id"] = f"toolu_normalized_{mapped}"
                continue

    return normalized


class ModelCache:
    def __init__(self):
        self.directory = None
        if ModelCacheEnvVar in os.environ:
            logger.warning("⚠ ModelCache is enabled")
            self.directory = os.environ[ModelCacheEnvVar]

    def _get_file(self, history: list[dict[str, str]]) -> str:
        hash_input = json.dumps(history, cls=CacheEncoder)
        logger.warn(f"HASH_INPUT\n{hash_input}\nEND_OF_HASH_INPUT")
        hash_object = hashlib.sha256(hash_input.encode("utf-8"))
        return f"{self.directory}/model-query-{hash_object.hexdigest()}.json"

    def query(self, history: list[dict[str, str]]) -> tuple[ModelQueryResult, list[dict[str, str]]] | None:
        if self.directory is None:
            return None
        file = self._get_file(history)
        if not os.path.exists(file):
            logger.info(f"ModelCacheMiss file={file}")
            return None
        logger.info(f"ModelCacheHit file={file}")
        file_handle = open(file, "r")
        [_, model_result, stats_calls] = json.load(file_handle, object_hook=cache_decoder)
        return model_result, stats_calls

    def insert(
        self,
        history: list[dict[str, str]],
        model_result: ModelQueryResult,
        stats_calls: list[dict[str, str]],
    ):
        if self.directory is None:
            return

        normalized_history = normalize_tool_use_ids(history)

        file = self._get_file(normalized_history)
        logger.info(f"ModelCacheInsert file={file}")

        file_handle = open(file, "w")
        json.dump([history, model_result, stats_calls], file_handle, cls=CacheEncoder)
