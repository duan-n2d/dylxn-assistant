from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AssistantMode(str, Enum):
    ASK = "ask"
    LEARN = "learn"
    COMPARE = "compare"
    DESIGN = "design"
    INTERVIEW = "interview"


@dataclass
class AssistantTurn:
    role: str
    message: str


class AssistantService:
    def __init__(
        self,
        history: list[AssistantTurn] | None = None,
    ) -> None:
        self.history = list(history) if history else []

    def add_turn(
        self,
        role: str,
        message: str,
    ) -> AssistantTurn:
        turn = AssistantTurn(role=role, message=message)
        self.history.append(turn)
        return turn

    def build_prompt(
        self,
        question: str,
        context: str,
        mode: AssistantMode = AssistantMode.ASK,
    ) -> str:
        return (
            f"You are operating in {mode.value.lower()} mode.\n"
            "Use the provided context as the source of truth.\n\n"
            f"Context:\n{context or 'No context provided.'}\n\n"
            f"Question:\n{question}\n\n"
            "Answer clearly and cite the relevant source sections."
        )

    def summarize_history(self) -> str:
        if not self.history:
            return "No conversation history yet."

        return "\n".join(
            f"{turn.role}: {turn.message}" for turn in self.history
        )


def build_citation_text(
    text: str,
    sources: list[str],
    source_number: int,
) -> str:
    source_ref = sources[0] if sources else "unknown source"
    return f"[Source {source_number}] {text}\nSource: {source_ref}"
