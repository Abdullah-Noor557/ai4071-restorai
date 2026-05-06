# -*- coding: utf-8 -*-
"""
RestorAI Lab 3 - Simple Demo Runner
Runs the agent system without Unicode display issues
"""

import os
import sys
from pathlib import Path

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage
from graph import create_simple_restorai_graph


def run_simple_demo():
    """Run a simple demo of the RestorAI agent system."""
    
    print("\n" + "="*70)
    print("RestorAI Lab 3 - Demo Workflow")
    print("="*70)
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n[ERROR] OPENAI_API_KEY not set!")
        print("Set it with: $env:OPENAI_API_KEY='your_key_here'")
        return
    
    print("\n[OK] OpenAI API key found")
    
    # Create graph
    try:
        app = create_simple_restorai_graph()
        print("[OK] LangGraph compiled successfully")
    except Exception as e:
        print(f"[ERROR] Failed to create graph: {e}")
        return
    
    # Demo query - more directive
    demo_query = """I have a vintage wooden table with water ring damage. 
The wood appears to be dark (possibly walnut or mahogany), and there are 
white cloudy marks on the surface from where someone placed a wet glass.
The finish seems old but intact otherwise.

Use your search_restoration_knowledge tool to research:
1. How to remove water rings from dark wood (walnut/mahogany)
2. Safety precautions for water ring removal
3. Product recommendations

Then use search_web_for_products to find where to buy needed items.

Finally, create a complete restoration plan with shopping list and step-by-step instructions."""
    
    print("\n[USER QUERY]")
    print(demo_query[:150] + "...")
    
    # Run agent
    print("\n" + "-"*70)
    print("[AGENT] Starting execution...\n")
    
    initial_message = HumanMessage(content=demo_query)
    initial_state = {"messages": [initial_message]}
    config = {"configurable": {"thread_id": "demo_session"}}
    
    try:
        step = 0
        for event in app.stream(initial_state, config, stream_mode="values"):
            step += 1
            messages = event.get("messages", [])
            
            if messages:
                last_message = messages[-1]
                
                # Show tool calls
                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    print(f"\n[STEP {step}] Agent calling tools:")
                    for tool_call in last_message.tool_calls:
                        print(f"  - {tool_call['name']}")
                        args_preview = str(tool_call['args'])[:60]
                        print(f"    Args: {args_preview}...")
                
                # Show tool results
                elif hasattr(last_message, "name") and last_message.name:
                    print(f"  [OK] {last_message.name} completed")
                
                # Show final answer
                elif hasattr(last_message, "content") and last_message.content and len(last_message.content) > 100:
                    if "RESTORATION PLAN" in last_message.content or "Shopping" in last_message.content:
                        print(f"\n[STEP {step}] Agent generated final plan")
        
        print("\n" + "-"*70)
        print("[SUCCESS] Agent execution complete!")
        print("="*70)
        
        # Display final output
        if messages:
            final_message = messages[-1]
            if hasattr(final_message, "content"):
                print("\n[FINAL OUTPUT]")
                print("-" * 70)
                print(final_message.content)
                print("-" * 70)
    
    except Exception as e:
        print(f"\n[ERROR] Execution failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_simple_demo()
