import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import ToolMessage
import json, os

load_dotenv()

github_token  = os.getenv("GITHUB_TOKEN")
expense_token = os.getenv("EXPENSE_TOKEN")

SERVERS = { 
    "math_server": {
        "transport": "stdio",
        "command": "uv",
        "args": [
            "run",
            "fastmcp",
            "run",
            r"C:\Users\bonami\Desktop\Ajay\mcp_servers\build_mcp_clients\main.py",
       ]
    },
    "expense-tracker": {
        "transport": "streamable_http",  # if this fails, try "sse"
        "url": "https://expense-trackk.fastmcp.app/mcp",
        "headers": {
        "Authorization": f"Bearer {expense_token}"
    }
    },
    "github": {
            "transport": "streamable_http",
            "url": "https://api.githubcopilot.com/mcp/",
            "headers": {
                "Authorization": f"Bearer {github_token}"
            }
        },
}

async def main():

    client = MultiServerMCPClient(SERVERS)
    tools = await client.get_tools()

    # print(tools)

    named_tools = {}
    for tool in tools:
        print(tool.name)
        named_tools[tool.name] = tool

    
    # print("Available tools: ", named_tools)
    # print(named_tools["add_expense"].args_schema)
    print(named_tools["pull_request_read"].args_schema)

    llm = ChatGroq(model="llama-3.3-70b-versatile")
    llm_with_tools = llm.bind_tools(tools)

    # prompt = "what is the product of 14 and 20 using math tool?"
    # prompt = "What is Python?"
    # prompt = "what is the remainder of 23434 divided by 9?"
    # prompt = "Use the expense tracker tool: Add an expense: 800 to my expenses for new tshirt purchased on 13th april"
    # prompt = """
    #     Call add_expense.

    #     date: 2024-04-13
    #     amount: 800
    #     category: Clothing
    #     note: new tshirt purchased

    #     IMPORTANT:
    #     amount must be numeric not string.
    #     """
    prompt = """
    You have access to GitHub tools.

    Call pull_request_read.

    Use exactly these arguments:

    method: get
    owner: openai
    repo: openai-python
    pullNumber: 1
    """

    response = await llm_with_tools.ainvoke(prompt)

    # print("response: ", response)

    if not getattr(response, "tool_calls", None):
        print("\nLLM Reply:", response.content)
        return
    
    tool_messages = []
    for tc in response.tool_calls:
        selected_tool = tc["name"]
        selected_tool_args = tc.get("args") or {}
        selected_tool_id = tc["id"]

        print(f"\n -> Executing remote tool: {selected_tool}")
        print(" with args: ", selected_tool_args)
        

        result = await named_tools[selected_tool].ainvoke(selected_tool_args)
        tool_messages.append(ToolMessage(tool_call_id=selected_tool_id, content=json.dumps(result)))

        print("\nTool Result:", result)


    final_response = await llm_with_tools.ainvoke(
        [
            ToolMessage(
                tool_call_id=selected_tool_id,
                content=json.dumps(result)
            )
        ]
    )

    print("\nFinal Response:")
    print(final_response.content)

    # selected_tool = response.tool_calls[0]["name"]
    # selected_tool_args = response.tool_calls[0]["args"]
    # selected_tool_id = response.tool_calls[0]["id"]

    # print(f"selected_tool:  {selected_tool}")
    # print(f"selected tool args:  {selected_tool_args}")

    # tool_result = await named_tools[selected_tool].ainvoke(selected_tool_args)
    # # print(f"Tool result: {tool_result}")

    # tool_message = ToolMessage(content=tool_result, tool_call_id=selected_tool_id)
    # final_response = await llm_with_tools.ainvoke([prompt, response, tool_message])

    # print(f"Final response: {final_response.content}")

if __name__ == '__main__':
    asyncio.run(main())