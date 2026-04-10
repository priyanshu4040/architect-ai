"""
======================================================================
 Autonomous Software Architecture Planning System
 Multi-Agent System using LangGraph + Ollama (llama3)
======================================================================
"""

import os
from langgraph.graph import StateGraph

# Import extracted components
from agents.state import AgentState
from agents.greenfield import architecture_agent
from agents.brownfield import code_agent
from agents.router import router
from agents.utils import read_codebase
from agents.ast_parser import generate_ast_summary
from agents.memory import train_memory, retrieve_memory, forget_memory
from agents.graph_builder import generate_d3_from_ast_summary, generate_d3_graph_from_plan

# ─────────────────────────────────────────────
# Build and Compile LangGraph
# ─────────────────────────────────────────────
builder = StateGraph(AgentState)

# Register agent nodes
builder.add_node("architecture", architecture_agent)
builder.add_node("code", code_agent)

# Set router as the conditional entry point
builder.set_conditional_entry_point(router)

# Brownfield flows into Greenfield for architecture refactoring
builder.add_edge("code", "architecture")

# Only Architecture Agent is the terminal node now
builder.set_finish_point("architecture")

# Compile the graph
graph = builder.compile()

# ─────────────────────────────────────────────
# Main — Interactive CLI Loop
# ─────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  🚀 Autonomous Software Architecture Planning System")
    print("       Powered by LangGraph + Ollama (llama3) + ChromaDB")
    print("=" * 60)
    print("\n📌 Modes:")
    print("   🟢 greenfield → Design a NEW system from requirements")
    print("   🔵 brownfield → Analyze EXISTING code for issues")
    print("   🧠 train      → Teach the agents from past code/architecture")
    print("   🗑️  forget     → Remove specific files (or all) from training memory")
    print("\nType 'exit' to quit.\n")

    while True:
        # ── Get mode ──
        mode = input("Mode (greenfield / brownfield / train / forget): ").strip().lower()

        if mode in ("exit", "quit", "q"):
            print("\n👋 Goodbye!")
            break

        if mode not in ("greenfield", "brownfield", "train", "forget"):
            print("⚠️  Please enter a valid mode.\n")
            continue

        ast_summary_text = ""
        readme_text = ""

        # ── Get input ──
        if mode == "forget":
            print("\n[Forget Mode]")
            path = input("Enter the EXACT file path to remove (or type 'all' to wipe database): ").strip()
            forget_memory(path)
            continue
        elif mode == "train":
            print("\n[Train Mode]")
            path = input("Enter the project folder or file path to train on: ").strip()
            train_memory(path)
            continue
        elif mode == "greenfield":
            user_input = input("Enter your requirements: ").strip()
        else:
            print("\n[Brownfield Mode]")
            print("You can paste code, describe the system, OR provide a file/folder path.")
            user_input = input("Enter code or path: ").strip()

            # Check if the input is actually a valid file or directory path
            if os.path.exists(user_input):
                readme_path = os.path.join(user_input, "README.md")
                if os.path.exists(readme_path):
                    with open(readme_path, "r", encoding="utf-8") as rf:
                        readme_text = rf.read()
                        print("📖 Found README.md. Extracting Project Topic/Idea...")

                print(f"📁 Detected path. Extracting AST Structural Graph from: {user_input} ...")
                ast_summary_text = generate_ast_summary(user_input)

                # Build ACCURATE D3 graph from real AST (not LLM hallucination)
                generate_d3_from_ast_summary(ast_summary_text, output_file="dependency_graph.html")

                print(f"📁 Reading full codebase content...")
                code_content = read_codebase(user_input)
                if code_content.strip():
                    user_input = code_content
                    print(f"✅ AST Parse complete. Loaded {len(code_content)} characters of code.")
                else:
                    print("⚠️  No readable code found in path.")
                    continue

        if not user_input:
            print("⚠️  Input cannot be empty.\n")
            continue

        print("\n⏳ Searching for past architectural memories (RAG)...")
        # Prevent context length errors: don't embed the entire codebase in Brownfield mode
        if mode == "brownfield":
            search_query = ast_summary_text[:4000] if ast_summary_text else "Software architecture refactoring"
        else:
            search_query = user_input

        past_memory = retrieve_memory(search_query)
        
        print("⏳ Processing Graph Pipeline...\n")

        # ── Run the graph ──
        result = graph.invoke({
            "input": user_input,
            "mode": mode,
            "readme_content": readme_text,
            "past_memory": past_memory,
            "ast_summary": ast_summary_text,
            "analysis_report": "",
            "architecture_plan": ""
        })

        # ── Display result ──
        arch_plan = result.get("architecture_plan", "")
        if mode == "brownfield":
            print("\n" + "=" * 60)
            print("📋 [CODE ANALYSIS REPORT]")
            print("=" * 60)
            print(result.get("analysis_report", "No report generated."))

            print("\n" + "=" * 60)
            print("🏗️ [REFACTORED ARCHITECTURE PLAN]")
            print("=" * 60)
            print(arch_plan)
            print("=" * 60 + "\n")
        else:
            # Greenfield — render the proposed architecture as D3 graph
            print("\n" + "=" * 60)
            print("🏗️ [ARCHITECTURE PLAN]")
            print("=" * 60)
            print(arch_plan)
            print("=" * 60 + "\n")
            if arch_plan:
                generate_d3_graph_from_plan(arch_plan, output_file="dependency_graph.html")

if __name__ == "__main__":
    main()
