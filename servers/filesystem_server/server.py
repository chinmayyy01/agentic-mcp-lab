from mcp.server.fastmcp import FastMCP

mcp = FastMCP("filesystem-server")

@mcp.tool()
def say_hello(name: str) -> str:
    """Greets a person by name. Use it when the user wants a greeting."""
    return f"Hello, {name}!"

@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Adds two integers together and returns the sum."""
    return a + b

if __name__ == "__main__":
    mcp.run(transport="stdio")