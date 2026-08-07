from app.graph.graph import get_graph


def main() -> None:
    """Compiles the complete workflow graph and prints its Mermaid visualization."""
    print("==================================================")
    print("      Complete Self-Correcting RAG LangGraph")
    print("==================================================")

    # Compile the graph
    app = get_graph().compile()

    # Print Mermaid diagram markup
    print("\n--- Mermaid Graph Diagram ---")
    try:
        mermaid_code = app.get_graph().draw_mermaid()
        print(mermaid_code)
    except Exception as e:
        print(f"Could not generate Mermaid representation: {e}")

    print("\n==================================================")


if __name__ == "__main__":
    main()
