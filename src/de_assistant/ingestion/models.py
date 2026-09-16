from dataclasses import dataclass, field


@dataclass
class Document:
    source: str
    title: str
    heading: str | None
    content: str
    metadata: dict[str, object] = field(default_factory=dict)