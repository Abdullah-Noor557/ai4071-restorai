import json
import asyncio
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# Initialize FastMCP Server
mcp = FastMCP("RestorationMetricsServer")

class MetricQuery(BaseModel):
    metric_name: str = Field(description="The name of the metric to fetch (e.g., 'active_projects', 'completion_rate', 'inventory_status')")

@mcp.tool()
def get_system_metric(query: MetricQuery) -> str:
    """
    Fetches system-level metrics for the restoration workshop.
    Demonstrates a read-only tool exposed via MCP.
    """
    mock_db = {
        "active_projects": {"count": 12, "critical": 3},
        "completion_rate": {"weekly": "85%", "monthly": "92%"},
        "inventory_status": {"wood_conditioner": "low", "varnish": "in_stock", "sandpaper": "out_of_stock"}
    }
    
    result = mock_db.get(query.metric_name.lower(), {"error": f"Metric '{query.metric_name}' not found."})
    return json.dumps(result, indent=2)

class FileOpQuery(BaseModel):
    filename: str = Field(description="The name of the report file to read.")

@mcp.tool()
def read_report_summary(query: FileOpQuery) -> str:
    """
    Simulates reading a summary report securely via the MCP boundary.
    """
    if query.filename == "weekly_summary.txt":
        return "Weekly Summary: Outstanding tasks: 5. Completed repairs: 15. Pending invoices: 2."
    return f"File {query.filename} could not be read or does not exist."

if __name__ == "__main__":
    print("Starting MCP Server (RestorationMetricsServer) on stdio...")
    mcp.run(transport='stdio')
