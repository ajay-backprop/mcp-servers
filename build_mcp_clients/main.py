from fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("Math Server")

@mcp.tool()
def add(a: float, b: float) -> float:
    """Adds two numbers together (a + b)."""
    return a + b

@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtracts the second number from the first (a - b)."""
    return a - b

@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiplies two numbers together (a * b)."""
    return a * b

@mcp.tool()
def divide(a: float, b: float) -> str:
    """Divides the first number by the second (a / b)."""
    if b == 0:
        return "Error: Division by zero is not allowed."
    return str(a / b)

@mcp.tool()
def power(base: float, exponent: float) -> float:
    """Raises the base to the exponent power (base^exponent)."""
    return base ** exponent

@mcp.tool()
def modulus(a: float, b: float) -> str:
    """Returns the remainder of dividing a by b (a % b)."""
    if b == 0:
        return "Error: Modulus by zero is not allowed."
    return str(a % b)

if __name__ == "__main__":
    mcp.run()
