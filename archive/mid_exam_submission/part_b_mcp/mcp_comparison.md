# RestorAI: Tool Execution Comparison

This document technically compares three distinct paradigms of tool execution explored during the AI407L Mid-Exam project.

## 1. Direct Tool Invocation (Lab 2)
**Description:**
In this approach, tools are essentially predefined Python functions. The agent (or LLM) predicts the function to call and the exact arguments. The execution script (the developer's code) manually intercepts this prediction, runs the local function with the arguments, and appends the result to the prompt context.

**Pros:**
- Simple to implement logically and requires minimal overhead.
- Excellent for small, monolithic applications.
- Easy to debug because execution runs in the same environment block.

**Cons:**
- Tightly coupled. The LLM must be implemented in the exact same programming language and runtime as the tools.
- Scaling requires modifying the core reasoning loop to accommodate new tools.
- Poor security isolation; the LLM runs in the exact environment where the system tools exist.

## 2. LangGraph-Based Execution (Lab 4)
**Description:**
LangGraph provides a state-machine framework wrapping LangChain's existing tool abstractions. Tools are bound to specific `Agent` nodes and a distinct logic flow (edges) routes the system from a `Reasoning` state to a `Tool Execution` node.

**Pros:**
- Supports Multi-Agent structures seamlessly (e.g., separating the Diagnostician's tools from the Project Manager's tools).
- Excellent built-in features like `interrupt_before` for Human-in-the-Loop configurations without breaking scope.
- State persistence automatically tracks tool history.

**Cons:**
- Still fundamentally bound to the Python process and LangChain ecosystems.
- High complexity overhead for small tasks.
- Tools cannot easily be shared with external applications written in other languages.

## 3. Model Context Protocol (MCP) Exposure (Lab 6 / Mid-Exam Part B)
**Description:**
MCP formalizes tool execution via a standard client-server architecture (e.g., over `stdio` or HTTP/SSE). The "Server" hosts the tools and capabilities, exposing them through standard JSON-RPC endpoints. The "Client" (an LLM or Agent system) connects, discovers available tools automatically, and requests execution.

**Pros:**
- **Universal Decoupling:** The agent and the tools can exist on entirely different servers, written in entirely different languages.
- **Security & Sandboxing:** The MCP Server explicitly restricts what the client can do. The LLM cannot accidentally execute arbitrary local code; it can only invoke what is exposed.
- **Dynamic Discovery:** LLMs can connect to an MCP server and immediately index what it can do without the developer manually updating prompts.

**Cons:**
- Heavier infrastructure setup (requires managing server lifecycles, transports, and client synchronization).
- Latency increases due to network or IPC boundaries.

### Summary
For RestorAI, **LangGraph** provided the best balance of orchestration and Human-in-the-Loop review for the multi-agent planning stage. However, as the system grows to interact with real-world databases (like purchasing APIs or inventory management), abstracting those actions behind an **MCP Server** ensures the AI core remains secure, modular, and universally scalable.
