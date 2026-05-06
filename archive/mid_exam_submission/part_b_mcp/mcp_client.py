import asyncio
import json
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_mcp_client():
    """
    Connects to the MCP server, discovers tools, and executes them.
    Demonstrates LangChain/LangGraph independence using raw MCP.
    """
    # Define parameters to start the MCP server process
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"]
    )
    
    print("\n" + "="*70)
    print("Initializing MCP Client Connection")
    print("="*70)
    
    # Connect using stdio transport
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize connection
                await session.initialize()
                print("[OK] Connected to RestorationMetricsServer")
                
                # 1. Discover available tools
                print("\n" + "-"*70)
                print("1. Discovering Tools via MCP Protocol")
                print("-"*70)
                
                tools_response = await session.list_tools()
                
                available_tools = []
                for tool in tools_response.tools:
                    available_tools.append(tool.name)
                    print(f"  • {tool.name}: {tool.description}")
                print(f"\n[OK] Found {len(available_tools)} exposed tools.")
                
                # 2. Execute First Tool: get_system_metric
                print("\n" + "-"*70)
                print("2. Executing Tool: get_system_metric")
                print("-"*70)
                
                try:
                    metric_result = await session.call_tool(
                        name="get_system_metric",
                        arguments={"query": {"metric_name": "inventory_status"}}
                    )
                    
                    if not metric_result.isError:
                        print("✓ Execution Successful. Content:")
                        for content in metric_result.content:
                            # Formatting the raw response JSON for display
                            if content.type == 'text':
                                parsed_content = json.loads(content.text)
                                print(json.dumps(parsed_content, indent=2))
                    else:
                        print(f"❌ Execution failed: {metric_result}")
                        
                except Exception as e:
                     print(f"❌ Tool call error: {e}")

                # 3. Execute Second Tool: read_report_summary
                print("\n" + "-"*70)
                print("3. Executing Tool: read_report_summary")
                print("-"*70)
                
                try:
                    file_result = await session.call_tool(
                        name="read_report_summary",
                        arguments={"query": {"filename": "weekly_summary.txt"}}
                    )
                    
                    if not file_result.isError:
                        print("✓ Execution Successful. Content:")
                        for content in file_result.content:
                            if content.type == 'text':
                                print(f"  > {content.text}")
                    else:
                        print(f"❌ Execution failed: {file_result}")
                        
                except Exception as e:
                     print(f"❌ Tool call error: {e}")
                
                print("\n" + "="*70)
                print("MCP Session Completed.")
                print("="*70)

    except Exception as e:
        print(f"\n❌ Failed to connect to or interact with MCP Server: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check if running on Windows and handle the event loop policy if needed
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    asyncio.run(run_mcp_client())
