from __future__ import annotations
import json
import hashlib
import os
import copy
from typing import Any

from anthropic.types import TextBlock, ToolUseBlock, ToolResultBlockParam

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
        result = {
            "type": "tool_result",
            "tool_use_id": obj["id"],
        }
        if "is_error" in obj:
            result["is_error"] = obj["is_error"]
        if "content" in obj:
            result["content"] = [encode_anthropic_types(c) for c in obj["content"]]
        return result
    
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
        return dct

    raise ValueError(f"Unknown type {dct['type']} in cache_decoder")

def normalize_tool_use_ids(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mapping = {}
    for entry in history:
        if not isinstance(entry["content"], list):
            continue
        for c in entry["content"]:
            if not isinstance(c, ToolUseBlock):
                continue
            mapping[c.id] = len(mapping) + 1

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

def hash_string(s: str) -> str:
    hash_object = hashlib.sha256(s.encode("utf-8"))
    return hash_object.hexdigest()

def json_serialize_str(obj: Any, **kwargs) -> str:
    return json.dumps(obj, **kwargs, cls=CacheEncoder)

def json_serialize_file(obj: Any, fp: Any, **kwargs): # SupportsWrite[str] on fp here
    json.dump(obj, fp, **kwargs, cls=CacheEncoder)

def json_deserialize_str(s: str, **kwargs) -> Any:
    return json.loads(s, **kwargs, object_hook=cache_decoder)

def json_deserialize_file(fp: Any, **kwargs) -> Any: # SupportsRead[str] on fp here
    return json.load(fp, **kwargs, object_hook=cache_decoder)

class ModelCache:
    def __init__(self):
        self.directory = None
        if ModelCacheEnvVar in os.environ:
            logger.warning("⚠ ModelCache is enabled")
            self.directory = os.environ[ModelCacheEnvVar]

    def _get_file(self, history: list[dict[str, str]]) -> str:
        hash_input = json_serialize_str(history)
        # print(f"HASH_INPUT\n{hash_input}\nEND_OF_HASH_INPUT")
        hash = hash_string(hash_input)
        return f"{self.directory}/model-query-{hash}.json"

    def query(self, history: list[dict[str, str]]) -> tuple[ModelQueryResult, list[dict[str, str]]] | None:
        if self.directory is None:
            return None
        normalized_history = normalize_tool_use_ids(history)
        file = self._get_file(normalized_history)
        if not os.path.exists(file):
            logger.info(f"ModelCacheMiss file={file}")
            return None
        logger.info(f"ModelCacheHit file={file}")
        file_handle = open(file, "r")
        [_, model_result, stats_calls] = json_deserialize_file(file_handle)
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
        json_serialize_file([history, model_result, stats_calls], file_handle)
