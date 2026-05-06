import os
import sys
from graph import create_restorai_graph
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

def run_custom():
    image_path = r"d:\AI Lab Final\mid_exam_submission\pic.png"
    query = f"Please analyze this furniture and create a restoration plan.\n\nImage path: {image_path}"
    
    print("\n" + "="*70)
    print("Running RestorAI Agent with pic.png")
    print("="*70)
    
    os.environ["CHROMA_TELEMETRY_IMPL"] = "None"
    os.environ["OPENAI_API_KEY"] = "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"
    os.environ["GOOGLE_API_KEY"] = "AIzaSyAddHUKxHIt-Xv8c_vLaaGwn6Pf4wFIrQs"

    app = create_restorai_graph()
    
    initial_message = HumanMessage(content=query)
    initial_state = {
        "messages": [initial_message],
        "current_agent": "start",
        "vision_analysis": "",
        "restoration_plan": "",
        "final_output": "",
        "image_path": image_path
    }
    
    config = {"configurable": {"thread_id": "test_pic_run_3"}}
    
    final_messages = []
    
    print("Starting agent stream...")
    # Loop to automatically resume from breakpoints
    is_first_run = True
    while True:
        try:
            input_val = initial_state if is_first_run else None
            is_first_run = False
            
            for event in app.stream(input_val, config, stream_mode="values"):
                messages = event.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    final_messages = messages
                    if isinstance(last_msg, AIMessage) and last_msg.content:
                        print(f"Agent: {last_msg.content[:200]}")
                    elif isinstance(last_msg, ToolMessage):
                        print(f"Tool returned: {len(last_msg.content)} chars")
            
            # Check breakpoint state
            state_snapshot = app.get_state(config)
            if not state_snapshot.next:
                break # Graph is completed
                
            # We hit a breakpoint (tool execution)
            print("--- Graph suspended at tools --- Resuming automatically...")
        except Exception as e:
            print(f"Error in stream: {e}")
            break
            
    print("\n" + "="*70)
    print("📋 FINAL OUTPUT MESSAGES")
    print("="*70)
    
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage) and msg.content and "RESTORATION" in msg.content:
             with open("final_plan.txt", "w", encoding="utf-8") as f:
                 f.write(msg.content)
             print("\nFINAL PLAN written to final_plan.txt")
             break

if __name__ == "__main__":
    run_custom()
