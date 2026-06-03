from typing import Any

from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client

app = BedrockAgentCoreApp()
log = app.logger

# Define a Streamable HTTP MCP Client
mcp_clients = [get_streamable_http_mcp_client()]

DEFAULT_SYSTEM_PROMPT = """
You are an Procurement AI Agent.

Available tools:

1. get_top_selling_products()
   - Get top selling products

2. get_low_stock_products()
   - Get low stock products

3. get_dead_stock_products()
   - Get dead stock products

4. generate_restock_recommendations()
   - Generate restock recommendations based on current stock and sales data

Rules:
- Return ONLY valid JSON
- No explanation
- Use exact tool names

Call the appropriate tool based on the user query and return the results in JSON format.

User Query:
{query}
"""


# Define a collection of tools used by the model
tools = []

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent / "database"
DB_PATH = BASE_DIR / "inventory.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


# -----------------------------------
# Top Selling Products
# -----------------------------------
@tool
def get_top_selling_products(limit=5):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.name,
            SUM(s.quantity) as total_sold
        FROM sales s
        JOIN products p
        ON p.id = s.product_id
        GROUP BY p.name
        ORDER BY total_sold DESC
        LIMIT ?
    """, (limit,))

    results = cursor.fetchall()

    conn.close()

    return [
        {
            "product": row[0],
            "total_sold": row[1]
        }
        for row in results
    ]


# -----------------------------------
# Low Stock Products
# -----------------------------------
@tool
def get_low_stock_products():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            name,
            stock,
            reorder_level
        FROM products
        WHERE stock < reorder_level
    """)

    results = cursor.fetchall()

    conn.close()

    return [
        {
            "product": row[0],
            "stock": row[1],
            "reorder_level": row[2]
        }
        for row in results
    ]


# -----------------------------------
# Dead Stock Products
# -----------------------------------
@tool
def get_dead_stock_products():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.name,
            p.stock
        FROM products p
        LEFT JOIN sales s
        ON p.id = s.product_id
        GROUP BY p.id
        HAVING COALESCE(SUM(s.quantity), 0) = 0
    """)

    results = cursor.fetchall()

    conn.close()

    return [
        {
            "product": row[0],
            "stock_remaining": row[1]
        }
        for row in results
    ]


# -----------------------------------
# Restock Recommendations
# -----------------------------------
@tool
def generate_restock_recommendations():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.name,
            p.stock,
            p.reorder_level,
            COALESCE(SUM(s.quantity), 0) as total_sales
        FROM products p
        LEFT JOIN sales s
        ON p.id = s.product_id
        GROUP BY p.id
    """)

    rows = cursor.fetchall()

    conn.close()

    recommendations = []

    for row in rows:

        name = row[0]
        stock = row[1]
        reorder_level = row[2]
        total_sales = row[3]

        if stock < reorder_level and total_sales > 5:
            recommendations.append({
                "product": name,
                "recommendation": "Restock immediately"
            })

        elif stock > 50 and total_sales == 0:
            recommendations.append({
                "product": name,
                "recommendation": "Potential dead stock"
            })

    return recommendations

#-----------------------------------
tools.append(tool(get_top_selling_products))
tools.append(tool(get_low_stock_products))
tools.append(tool(get_dead_stock_products))
tools.append(tool(generate_restock_recommendations))


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
