from app.graph.workflow_v1 import compile_workflow_v1


def main() -> None:
    """Compiles workflow_v1 and prints its architectural visualization."""
    print("==================================================")
    print("      LangGraph Workflow V1 Architecture")
    print("==================================================")

    # Compile the V1 workflow
    app_v1 = compile_workflow_v1()

    # Print ASCII representation
    print("\n--- ASCII Graph Representation ---")
    try:
        app_v1.get_graph().print_ascii()
    except Exception as e:
        print(f"Could not print ASCII graph: {e}")

    # Print Mermaid diagram markup
    print("\n--- Mermaid Graph Diagram ---")
    try:
        mermaid_code = app_v1.get_graph().draw_mermaid()
        print(mermaid_code)
    except Exception as e:
        print(f"Could not generate Mermaid representation: {e}")

    print("\n==================================================")


if __name__ == "__main__":
    main()
