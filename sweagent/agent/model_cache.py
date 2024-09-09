
import json
import hashlib
import os

from sweagent.utils.log import get_logger

ModelCacheEnvVar = "MODEL_CACHE_DIRECTORY"

logger = get_logger("model_cache")

class ModelCache:
    def __init__(self):
        self.directory = None
        if ModelCacheEnvVar in os.environ:
            self.directory = os.environ[ModelCacheEnvVar]

    def _get_file(self, history: list[dict[str, str]]) -> str:
      hash_input = str(history)
      hash_object = hashlib.sha256(hash_input.encode('utf-8'))
      return f"{self.directory}/model-query-{hash_object.hexdigest()}.json"

    def query(self, history: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]] | None:
        if self.directory is None:
            return None
        file = self._get_file(history)
        if not os.path.exists(file):
            logger.info(f"ModelCacheMiss file={file}")
            return None
        logger.info(f"ModelCacheHit file={file}")
        file_handle = open(file, 'r')
        entries = json.load(file_handle)
        return entries[1], entries[2]

    def insert(self, history: list[dict[str, str]], result_string: str, stats_calls: list[dict[str,str]]):
        if self.directory is None:
            return
        file = self._get_file(history)
        logger.info(f"ModelCacheInsert file={file}")
        file_handle = open(file, 'w')
        json.dump([history, result_string, stats_calls], file_handle)
