from fastmcp import FastMCP
import os
import random, json

mcp = FastMCP("Simple Calculator Server")

@mcp.tool
def add_numbers(a: float, b: float) -> float:
    """add two numbers together."""
    return a+b

@mcp.tool()
def generate_random_number(min_value: float, max_value: float) -> float:
    """
    Generate a random integer within the given range.
    """
    if min_value > max_value:
        raise ValueError("min_value must be less than or equal to max_value")

    return random.uniform(min_value, max_value)

@mcp.resource("info://server")
def server_info()-> str:
    """get information about this Server"""
    info = {
        "name" : "Simple Calculator Server",
        "version" : "1.0.0",
        "description" : "A Basic MCP Server with Math tools",
        "tools" : ["add_numbers", "generate_random_number"],
        "author" : "Ajay Kumar"
    }

    return json.dumps(info, indent=2)

if __name__ == "__main__":
    map.run(transport = "http", host="0.0.0.0", port=8000)
