import json
import hashlib
import os

from anthropic.types import ContentBlock, TextBlock, ToolUseBlock

from sweagent.utils.log import get_logger
from sweagent.agent.model_result import AnthropicModelResult, ModelQueryResult

ModelCacheEnvVar = "MODEL_CACHE_DIRECTORY"

logger = get_logger("model_cache")


class CacheEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, AnthropicModelResult):
            return {
                "type": "anthropic_model_result",
                "blocks": [
                    encode_anthropic_content_block(block) for block in obj.blocks
                ],
            }

        if isinstance(obj, TextBlock) or isinstance(obj, ToolUseBlock):
            return encode_anthropic_content_block(obj)

        return super().default(obj)


def encode_anthropic_content_block(block: ContentBlock) -> dict[str, str]:
    # it should be possible to use the Anthropic library to encode these (using BaseModel#to_dict),
    # but there doesn't seem to be a way to reconstruct instances from those dicts directly.  Given
    # that it seems I have to write the latter, I'd like to keep code for both close to the other to
    # make it easier to keep them in sync.
    if isinstance(block, TextBlock):
        return {
            "type": "text",
            "text": block.text,
        }
    if isinstance(block, ToolUseBlock):
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
        }


def cache_decoder(dct: dict[str, str]):
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


class ModelCache:
    def __init__(self):
        self.directory = None
        if ModelCacheEnvVar in os.environ:
            logger.warning("⚠ ModelCache is enabled")
            self.directory = os.environ[ModelCacheEnvVar]

    def _get_file(self, history: list[dict[str, str]]) -> str:
        hash_input = str(history)
        hash_object = hashlib.sha256(hash_input.encode("utf-8"))
        return f"{self.directory}/model-query-{hash_object.hexdigest()}.json"

    def query(
        self, history: list[dict[str, str]]
    ) -> tuple[ModelQueryResult, list[dict[str, str]]] | None:
        if self.directory is None:
            return None
        file = self._get_file(history)
        if not os.path.exists(file):
            logger.info(f"ModelCacheMiss file={file}")
            return None
        logger.info(f"ModelCacheHit file={file}")
        file_handle = open(file, "r")
        [_, model_result, stats_calls] = json.load(
            file_handle, object_hook=cache_decoder
        )
        return model_result, stats_calls

    def insert(
        self,
        history: list[dict[str, str]],
        model_result: ModelQueryResult,
        stats_calls: list[dict[str, str]],
    ):
        if self.directory is None:
            return
        file = self._get_file(history)
        logger.info(f"ModelCacheInsert file={file}")

        file_handle = open(file, "w")
        json.dump([history, model_result, stats_calls], file_handle, cls=CacheEncoder)
