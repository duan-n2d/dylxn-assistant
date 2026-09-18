from __future__ import annotations


def main() -> None:
    try:
        import streamlit as st
    except ImportError as exc:  # pragma: no cover - optional UI dependency
        raise RuntimeError(
            "Streamlit is not installed. Install the UI dependency to use the assistant dashboard."
        ) from exc

    st.title("Dylxn Assistant")
    st.write("Local-first Data Engineering assistant")

    question = st.text_input("Ask a question")
    if question:
        st.info("This UI is a starter shell for the assistant workflow.")
        st.write(f"Question: {question}")
