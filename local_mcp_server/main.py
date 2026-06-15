import random
from fastmcp import FastMCP
import os
import sqlite3

def main():
    print("Hello from local-mcp-server!")

#create FastMCP server instance
mcp = FastMCP("Demo Server")

@mcp.tool
def roll_dice(n_dice: int=1) -> list[int]:
    """Roll n_dice 6-sided dice and return the results"""
    
    return [random.randint(1,6) for _ in range(n_dice)]

@mcp.tool
def add_numbers(a: float, b: float) -> float:
    """add two numbers together."""
    return a+b


if __name__ == "__main__":
    mcp.run()