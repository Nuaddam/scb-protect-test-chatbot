from fastmcp import Client
from langchain_core.messages import AIMessage
from interest_structure import ProductInterest
import logging

MCP_URL = "http://localhost:8081/mcp"

async def interview_node(state):
    logging.info("➡️ Entered interview_node")

    customer_data = dict(state.get("customer_data", {}) or {})

    fields = ["name", "age", "occupation", "income", "product_name", "memo"]
    questions = {
        "name": "What is your name?",
        "age": "How old are you?",
        "occupation": "What do you do for a living?",
        "income": "What is your monthly income?",
        "product_name": "Which product are you interested in?",
        "memo": "Any other notes or requirements?"
    }

    for field in fields:
        if field not in customer_data or customer_data[field] in [None, ""]:
            state["messages"].append(AIMessage(content=questions[field]))
            state["awaiting_field"] = field
            return state

    # ✅ All info collected → send to MCP
    interest = ProductInterest(**customer_data)
    client = Client(MCP_URL)
    async with client:
        result = await client.call_tool("log_product_interest", interest.dict())

    # ✅ Extract message safely
    message = (
        result.data.get("message")
        or result.structured_content.get("message")
        or result.content[0].text
    )

    state["messages"].append(AIMessage(content=message))
    state["done"] = True
    state["route"] = "answer"  # so graph knows what to do next
    return state