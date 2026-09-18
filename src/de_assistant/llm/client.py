from collections.abc import Iterator
from typing import Protocol


class LLMClient(Protocol):
    def generate(
        self,
        prompt: str,
        system: str | None = None,
    ) -> str:
        ...

    def stream_generate(
        self,
        prompt: str,
        system: str | None = None,
    ) -> Iterator[str]:
        ...