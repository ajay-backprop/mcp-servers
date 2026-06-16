import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

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
    }
}

async def main():

    client = MultiServerMCPClient(SERVERS)
    tools = await client.get_tools()

    # print(tools)

    named_tools = {}
    for tool in tools:
        named_tools[tool.name] = tool
    
    print(named_tools)

if __name__ == '__main__':
    asyncio.run(main())