from fastmcp import FastMCP
import csv
import os
from pydantic import BaseModel

# Create MCP server
mcp = FastMCP("ProductInterestMCP")

# Define tool via decorator
@mcp.tool()
def log_product_interest(
    name: str,
    age: int,
    occupation: str,
    income: int,
    product_name: str,
    memo: str = ""
) -> dict:
    """
    Log a user’s interest in a product by writing to CSV.
    Returns a dict with status message.
    """
    DATA_PATH = "data/interested_users.csv"
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    file_exists = os.path.exists(DATA_PATH)

    with open(DATA_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["name", "age", "occupation", "income", "product_name", "memo"])
        writer.writerow([name, age, occupation, income, product_name, memo])

    return {"message": f"✅ Logged interest: {name} wants {product_name}"}


if __name__ == "__main__":
    # Run MCP server (default transport is stdio; for HTTP use transport="streamable-http", etc.)
    mcp.run(transport="streamable-http", port=8081)
    
