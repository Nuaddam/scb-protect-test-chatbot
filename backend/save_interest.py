from fastmcp import Client
from langchain_core.messages import HumanMessage, AIMessage
from pydantic_models import ProductInterest

MCP_URL = "http://localhost:8080/mcp"

REQUIRED_FIELDS = ["name", "age", "occupation", "income", "product_name", "memo"]

async def save_interest_node(state):
    messages = state["messages"]
    user_data = state.get("user_data", {})
    latest_message = messages[-1].content if messages else ""

    # Fill next missing field with user input
    for field in REQUIRED_FIELDS:
        if field not in user_data:
            user_data[field] = latest_message.strip()
            break

    # Check for missing fields
    missing = [f for f in REQUIRED_FIELDS if f not in user_data]

    if missing:
        next_field = missing[0]
        questions = {
            "name": "What is your name?",
            "age": "How old are you?",
            "occupation": "What is your occupation?",
            "income": "What is your monthly income?",
            "product_name": "Which product are you interested in?",
            "memo": "Any notes or preferences?",
        }

        ai_msg = AIMessage(content=questions[next_field])
        state["messages"].append(ai_msg)
        state["user_data"] = user_data
        state["route"] = "save_interest"
        return state

    # ✅ All fields collected → create structured output
    interest = ProductInterest(**user_data)

    # 🧾 Build structured preview message
    preview = (
        f"Here’s what I’ve collected:\n\n"
        f"**Name:** {interest.name}\n"
        f"**Age:** {interest.age}\n"
        f"**Occupation:** {interest.occupation}\n"
        f"**Income:** {interest.income}\n"
        f"**Product:** {interest.product_name}\n"
        f"**Memo:** {interest.memo}\n\n"
        f"Is this information correct? (yes/no)"
    )

    # If user just confirmed “yes” or “no”
    if latest_message.lower() in ["yes", "y"]:
        client = Client(MCP_URL)
        async with client:
            result = await client.call_tool("log_product_interest", interest.dict())

        confirm = AIMessage(content=result["message"])
        state["messages"].append(confirm)
        state["route"] = "answer"
        state["user_data"] = {}
        return state

    elif latest_message.lower() in ["no", "n"]:
        state["messages"].append(AIMessage(content="Okay, let’s start over. What is your name?"))
        state["user_data"] = {}
        state["route"] = "save_interest"
        return state

    # Otherwise show preview for confirmation
    state["messages"].append(AIMessage(content=preview))
    state["route"] = "save_interest"
    state["user_data"] = user_data
    return state
