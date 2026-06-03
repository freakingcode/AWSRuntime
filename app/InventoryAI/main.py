from typing import Any

from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client

# from tools.inventory_tools import (
#     get_product_stock,
#     update_stock,
#     record_sale,
#     list_products
# )

app = BedrockAgentCoreApp()
log = app.logger

# Define a Streamable HTTP MCP Client
mcp_clients = [get_streamable_http_mcp_client()]

DEFAULT_SYSTEM_PROMPT = """
You are an Inventory AI Agent.

Available tools:

1. get_product_stock(product_name)
   - Get stock information

2. record_sale(product_id, quantity)
   - Record product sale

3. list_products()
   - List all products

Rules:
- Return ONLY valid JSON
- No explanation
- Use exact tool names

Call the appropriate tool based on the user query. Always return the response from the tool as the final answer. Do not attempt to answer the user's query directly.

User Query:
{query}
"""


# Define a collection of tools used by the model
tools = []

# ------------------------------
# List Products
# ------------------------------
import sqlite3
from pathlib import Path

# Database path
BASE_DIR = Path(__file__).resolve().parent / "database"
DB_PATH = BASE_DIR / "inventory.db"
# print(f"Using database at: {DB_PATH}")
def get_connection():
    return sqlite3.connect(DB_PATH)


# -----------------------------
# Get Product Stock
# -----------------------------
@tool
def get_product_stock(product_name: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, stock, price
        FROM products
        WHERE LOWER(name) = LOWER(?)
    """, (product_name,))

    product = cursor.fetchone()

    conn.close()

    if product:
        return {
            "id": product[0],
            "name": product[1],
            "stock": product[2],
            "price": product[3]
        }

    return {"error": "Product not found"}


# -----------------------------
# Update Stock
# -----------------------------
@tool
def update_stock(product_id: int, quantity: int):
    conn = get_connection()
    cursor = conn.cursor()

    # Check current stock
    cursor.execute("""
        SELECT stock
        FROM products
        WHERE id = ?
    """, (product_id,))

    result = cursor.fetchone()

    if not result:
        conn.close()
        return {"error": "Product not found"}

    current_stock = result[0]
    new_stock = current_stock + quantity

    if new_stock < 0:
        conn.close()
        return {"error": "Insufficient stock"}

    # Update stock
    cursor.execute("""
        UPDATE products
        SET stock = ?
        WHERE id = ?
    """, (new_stock, product_id))

    conn.commit()
    conn.close()

    return {
        "message": "Stock updated successfully",
        "new_stock": new_stock
    }


# -----------------------------
# Record Sale
# -----------------------------
@tool
def record_sale(product_id: int, quantity: int):
    conn = get_connection()
    cursor = conn.cursor()

    # Fetch product details
    cursor.execute("""
        SELECT stock, price
        FROM products
        WHERE id = ?
    """, (product_id,))

    result = cursor.fetchone()

    if not result:
        conn.close()
        return {"error": "Product not found"}

    current_stock, price = result

    if current_stock < quantity:
        conn.close()
        return {"error": "Not enough stock available"}

    # Reduce stock
    new_stock = current_stock - quantity

    cursor.execute("""
        UPDATE products
        SET stock = ?
        WHERE id = ?
    """, (new_stock, product_id))

    # Insert sale record
    total_price = quantity * price

    cursor.execute("""
        INSERT INTO sales (product_id, quantity, total_price)
        VALUES (?, ?, ?)
    """, (product_id, quantity, total_price))

    conn.commit()
    conn.close()

    return {
        "message": "Sale recorded successfully",
        "remaining_stock": new_stock,
        "total_amount_of_sale": total_price
    }


# -----------------------------
# List Products
# -----------------------------
@tool
def list_products():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, category, stock, price
        FROM products
    """)

    products = cursor.fetchall()

    conn.close()

    return [
        {
            "id": p[0],
            "name": p[1],
            "category": p[2],
            "stock": p[3],
            "price": p[4]
        }
        for p in products
    ]

# -----------------------------
tools.append(get_product_stock)
tools.append(update_stock)
tools.append(record_sale)
tools.append(list_products)

# Add MCP client to tools if available
for mcp_client in mcp_clients:
    if mcp_client:
        tools.append(mcp_client)


_agent = None

def get_or_create_agent():
    global _agent
    if _agent is None:
        _agent = Agent(
            model=load_model(),
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            tools=tools
        )
    return _agent


@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")

    agent = get_or_create_agent()

    # Execute and format response
    stream = agent.stream_async(payload.get("prompt"))

    async for event in stream:
        # Handle Text parts of the response
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]


if __name__ == "__main__":
    app.run()
