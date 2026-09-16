from de_assistant.llm.ollama import OllamaLLM


def main() -> None:
    llm = OllamaLLM()

    answer = llm.generate(
        prompt="Explain OLTP vs OLAP in 3 sentences."
    )

    print("=" * 80)
    print("OLLAMA TEST")
    print("=" * 80)
    print(answer)


if __name__ == "__main__":
    main()