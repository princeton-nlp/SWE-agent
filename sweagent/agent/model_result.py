from dataclasses import dataclass

from anthropic.types import ContentBlock

@dataclass
class AnthropicModelResult:
    blocks: list[ContentBlock]

    def get_tool_use_blocks(self):
        return [block for block in self.blocks if block.type == "tool_use"]

    def get_last_tool_use(self):
        return next(reversed(self.get_tool_use_blocks()), None)

    def get_text_blocks(self):
        return [block for block in self.blocks if block.type == "text"]

    def get_non_content_blocks(self):
        return [block for block in self.blocks if block.type not in ["tool_use", "text"]]

    def __init__(self, blocks):
        self.blocks = blocks

    def __repr__(self) -> str:
        return f"AnthropicModelResult(blocks={repr(self.blocks)})"

ModelQueryResult = str | AnthropicModelResult
