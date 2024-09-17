from dataclasses import dataclass

from anthropic.types import ContentBlock

@dataclass
class AnthropicModelResult:
    blocks: list[ContentBlock]

    def get_tool_uses(self):
        return [block for block in self.blocks if block.type == "tool_use"]

    def get_last_tool_use(self):
        return next(reversed(self.get_tool_uses()), None)

    def __init__(self, blocks):
        self.blocks = blocks

    def __repr__(self) -> str:
        return f"AnthropicModelResult(blocks={repr(self.blocks)})"

ModelQueryResult = str | AnthropicModelResult
