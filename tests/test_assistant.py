from de_assistant.assistant import (
    AssistantMode,
    AssistantService,
    build_citation_text,
)
from de_assistant.knowledge_graph import KnowledgeGraph


def test_assistant_tracks_history() -> None:
    service = AssistantService()

    service.add_turn("user", "What is OLTP?")
    service.add_turn("assistant", "OLTP handles transactions.")
    service.add_turn("user", "And OLAP?")

    assert len(service.history) == 3
    assert service.history[-1].message == "And OLAP?"


def test_assistant_mode_prompt_includes_mode() -> None:
    service = AssistantService()

    prompt = service.build_prompt(
        "Explain similarly",
        "Context text",
        AssistantMode.LEARN,
    )

    assert "learn" in prompt.lower()
    assert "Context text" in prompt


def test_citation_formatter_adds_source_markers() -> None:
    text = build_citation_text(
        "OLAP is analytical.",
        ["knowledge/test.md"],
        1,
    )

    assert "[Source 1]" in text
    assert "knowledge/test.md" in text


def test_knowledge_graph_tracks_relationships() -> None:
    graph = KnowledgeGraph()
    graph.add_entity("OLTP", "technology")
    graph.add_entity("OLAP", "technology")
    graph.add_relation("OLTP", "compared_with", "OLAP")

    assert graph.has_relation("OLTP", "compared_with", "OLAP")
    assert "OLAP" in graph.related_nodes("OLTP")
