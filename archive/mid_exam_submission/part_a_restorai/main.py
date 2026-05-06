"""
RestorAI - Lab 3: Main Execution Script
Multi-Agent Furniture Restoration System

This script runs the complete RestorAI workflow:
1. User provides furniture image
2. Agent system analyzes, researches, and generates restoration plan
3. Output includes shopping list and step-by-step instructions

Author: Abdullah Noor - 2022029
"""

import os
import sys
from pathlib import Path

# Add parent directory to import Lab 2 modules
sys.path.append(str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage
from graph import create_simple_restorai_graph, run_restorai_agent


def check_environment():
    """
    Check that all required environment variables and dependencies are set.
    """
    print("\n" + "="*70)
    print("RestorAI Environment Check")
    print("="*70)
    
    issues = []
    
    # Using Hardcoded API keys for Exam
    print("[OK] Using hardcoded API keys for Mid Exam")
    
    # Check ChromaDB exists
    os.environ["CHROMA_TELEMETRY_IMPL"] = "None"
    chroma_path = Path(__file__).parent / "chroma_db"
    if not chroma_path.is_dir():
        issues.append("Cannot find knowledge base directory 'chroma_db'. Run ingest_data.py first.")
    else:
        print("[OK] ChromaDB knowledge base directory found.")
    
    if issues:
        print("\n" + "="*70)
        print("[!] SETUP ISSUES FOUND:")
        print("="*70)
        for issue in issues:
            print(f"  {issue}")
        print("\nPlease fix these issues before running the agent.")
        print("See SETUP_GUIDE.txt for instructions.")
        print("="*70)
        return False
    
    print("\n[OK] All checks passed! Ready to run RestorAI.")
    print("="*70)
    return True


def interactive_mode():
    """
    Interactive mode for testing RestorAI with sample images.
    """
    print("\n" + "="*70)
    print("RestorAI Interactive Mode")
    print("="*70)
    
    print("\nWelcome to RestorAI - The Furniture Flip Planner!")
    print("\nThis AI system will:")
    print("  1. Analyze your furniture image")
    print("  2. Research restoration techniques")
    print("  3. Create a comprehensive restoration plan")
    print("  4. Generate a shopping list with product recommendations")
    
    # Get image path
    print("\n" + "-"*70)
    image_path = input("\n[?] Enter path to furniture image (or 'demo' for test): ").strip()
    
    if image_path.lower() == 'demo':
        # Use demo mode with mock data
        print("\n[DEMO] Using simulated furniture scenario")
        user_query = """I have a vintage wooden table with water ring damage. 
The wood appears to be dark (possibly walnut or mahogany), and there are 
white cloudy marks on the surface from where someone placed a wet glass.
The finish seems old but intact otherwise.

Please help me create a restoration plan."""
        
        # Run in demo mode (won't call vision API)
        run_demo_workflow(user_query)
    else:
        # Check if file exists
        if not os.path.exists(image_path):
            print(f"\n[X] Error: Image file not found: {image_path}")
            return
        
        user_query = input("\n[?] Any additional details? (or press Enter): ").strip()
        if not user_query:
            user_query = f"Please analyze this furniture and create a restoration plan."
        
        # Run real workflow
        try:
            final_state = run_restorai_agent(
                image_path=image_path,
                user_query=f"{user_query}\n\nImage path: {image_path}",
                use_simple=True
            )
            
            # Display final result
            print("\n" + "="*70)
            print("📋 FINAL RESTORATION PLAN")
            print("="*70)
            
            if final_state and "messages" in final_state:
                last_message = final_state["messages"][-1]
                if hasattr(last_message, "content"):
                    print(last_message.content)
            
        except Exception as e:
            print(f"\n❌ Error during execution: {e}")
            import traceback
            traceback.print_exc()


def run_demo_workflow(user_query: str):
    """
    Run a demo workflow without requiring an actual image.
    Shows the agent reasoning process with knowledge base queries.
    """
    print("\n" + "="*70)
    print("RestorAI Demo Workflow")
    print("="*70)
    
    # Create simple graph
    app = create_simple_restorai_graph()
    
    # Initial message
    initial_message = HumanMessage(content=user_query)
    initial_state = {"messages": [initial_message]}
    
    config = {"configurable": {"thread_id": "demo_session"}}
    
    print("\n🤖 Agent is thinking and using tools...\n")
    
    # Execute with streaming
    step = 0
    try:
        # First run, may hit the breakpoint
        for event in app.stream(initial_state, config, stream_mode="values"):
            step += 1
            messages = event.get("messages", [])
            
            if messages:
                last_message = messages[-1]
                
                if isinstance(last_message, HumanMessage):
                    print(f"\n👤 User Input:")
                    print(f"   {last_message.content[:150]}...")
                
                elif hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    print(f"\n🔧 Step {step}: Agent calling tools")
                    for tool_call in last_message.tool_calls:
                        print(f"   • {tool_call['name']}")
                        args_str = str(tool_call['args'])[:80]
                        print(f"     Args: {args_str}...")
                
                elif hasattr(last_message, "content") and last_message.content:
                    # Check if it's a tool response or final answer
                    if hasattr(last_message, "name"):  # ToolMessage
                        print(f"   ✓ Tool result: {len(last_message.content)} chars")
                    else:  # AI reasoning/final answer
                        content_preview = last_message.content[:300]
                        if len(last_message.content) > 300:
                            content_preview += "..."
                        print(f"\n💭 Step {step}: Agent reasoning")
                        print(f"   {content_preview}")
                        
        # Check if we hit a breakpoint (Lab 5 HITL)
        state_snapshot = app.get_state(config)
        
        if state_snapshot.next:
            print("\n" + "!"*70)
            print("🛑 HIGH-RISK ACTION INTERRUPTED: Approval Required")
            print("!"*70)
            
            last_message = state_snapshot.values["messages"][-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                tool_call = last_message.tool_calls[0]
                if tool_call['name'] == "approve_and_purchase_materials":
                    print(f"\nManager has finalized the plan and wants to purchase materials:")
                    print(f"Items: {tool_call['args'].get('items_to_purchase')}")
                    print(f"Cost: {tool_call['args'].get('estimated_cost')}")
                    
                    user_approval = input("\n[?] Approve this purchase? (y/n): ")
                    
                    if user_approval.lower() == 'y':
                        print("\n✅ Purchase approved. Resuming workflow...")
                        # Resume execution
                        for event in app.stream(None, config, stream_mode="values"):
                            messages = event.get("messages", [])
                            if messages:
                                last_message = messages[-1]
                                if hasattr(last_message, "content") and last_message.content and not hasattr(last_message, "name"):
                                    print(f"\n💭 Final Step: Agent formatting output")
                    else:
                        print("\n❌ Purchase rejected. Ending workflow.")
                        return

    except Exception as e:
        print(f"Error during execution: {e}")
    
    print("\n" + "="*70)
    print("✅ Demo Complete")
    print("="*70)
    
    # Show final output
    if messages:
        final_message = messages[-1]
        if hasattr(final_message, "content"):
            print("\n📋 FINAL OUTPUT:")
            print("-" * 70)
            print(final_message.content)
            print("-" * 70)


def batch_test():
    """
    Run automated tests on the agent system.
    """
    print("\n" + "="*70)
    print("RestorAI Automated Testing")
    print("="*70)
    
    test_scenarios = [
        {
            "name": "Water Ring Damage",
            "query": "I have water ring damage on oak furniture. What should I do?",
            "expected_tools": ["search_restoration_knowledge"]
        },
        {
            "name": "Material Identification",
            "query": "How can I tell if my furniture is solid wood or veneer?",
            "expected_tools": ["search_restoration_knowledge"]
        },
        {
            "name": "Safety Check",
            "query": "What safety precautions should I take when using chemical strippers?",
            "expected_tools": ["search_restoration_knowledge"]
        }
    ]
    
    app = create_simple_restorai_graph()
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*70}")
        print(f"Test {i}: {scenario['name']}")
        print('='*70)
        
        initial_message = HumanMessage(content=scenario["query"])
        initial_state = {"messages": [initial_message]}
        config = {"configurable": {"thread_id": f"test_{i}"}}
        
        try:
            # Run graph
            tool_calls_made = []
            for event in app.stream(initial_state, config, stream_mode="values"):
                messages = event.get("messages", [])
                if messages:
                    last_message = messages[-1]
                    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                        for tc in last_message.tool_calls:
                            tool_calls_made.append(tc['name'])
            
            print(f"✓ Test passed")
            print(f"  Tools used: {list(set(tool_calls_made))}")
            print(f"  Expected: {scenario['expected_tools']}")
        
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    print("\n" + "="*70)
    print("✅ Automated testing complete")
    print("="*70)


def main():
    """
    Main entry point for RestorAI Lab 3.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="RestorAI - Furniture Restoration AI Agent")
    parser.add_argument("--mode", choices=["interactive", "demo", "test", "check"], 
                        default="demo", help="Execution mode")
    parser.add_argument("--image", type=str, help="Path to furniture image")
    parser.add_argument("--query", type=str, help="User query/instructions")
    
    args = parser.parse_args()
    
    if args.mode != "check" and args.mode != "test":
        env_ok = check_environment()
        if not env_ok:
            print("\n[!] Please fix environment issues before running in interactive/demo mode.")
            sys.exit(1)
    
    # Execute based on mode
    if args.mode == "check":
        check_environment()
    
    elif args.mode == "interactive":
        interactive_mode()
    
    elif args.mode == "demo":
        # Run demo with sample query
        demo_query = """I have a vintage wooden table with water ring damage. 
The wood appears to be dark (possibly walnut or mahogany), and there are 
white cloudy marks on the surface from where someone placed a wet glass.
The finish seems old but intact otherwise.

Please help me create a restoration plan with:
1. Material identification
2. Damage assessment  
3. Repair techniques
4. Safety precautions
5. Shopping list
6. Step-by-step instructions"""
        
        run_demo_workflow(demo_query)
    
    elif args.mode == "test":
        batch_test()


if __name__ == "__main__":
    main()
