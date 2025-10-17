# nodes.py
from fastmcp import Client
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic_models import ProductInterest
import logging
import os

# ---- Config ----
MCP_URL = "http://localhost:8081/mcp"
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.5,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
)

# ---- Interview Node ----
# async def interview_node(state):
#     """
#     Conversational interview node using OpenAI and MCP.
#     """
#     logging.info("➡️ Entered interview_node")

#     messages = state.get("messages", [])
#     customer_data = dict(state.get("customer_data", {}) or {})
#     fields = ["name", "age", "occupation", "income", "product_name", "memo"]

#     # detect missing field
#     missing_field = next((f for f in fields if not customer_data.get(f)), None)
    
#     # ask next question
#     if missing_field:
#         system_prompt = (
#             "You are a polite bilingual insurance assistant (Thai/English).\n"
#             "Ask only one clear question at a time to collect required information.\n"
#             "Required fields: name, age, occupation, income, product_name, memo.\n"
#             "Use the same language as the customer."
#         )

#         convo = [SystemMessage(content=system_prompt)] + messages
#         llm_reply = llm.invoke(convo)
#         question = llm_reply.content.strip()

#         state["messages"].append(AIMessage(content=question))
#         state["awaiting_field"] = missing_field
#         return state

#     # all fields collected → log via MCP
#     try:
#         interest = ProductInterest(**customer_data)
#     except Exception as e:
#         logging.error(f"Validation error: {e}")
#         state["messages"].append(AIMessage(content=f"❌ Invalid data: {e}"))
#         return state

#     client = Client(MCP_URL)
#     async with client:
#         result = await client.call_tool("log_product_interest", interest.dict())
#         logging.info(f"🧾 MCP result: {result}")

#     message = (
#         result.data.get("message")
#         or result.structured_content.get("message")
#         or result.content[0].text
#     )

#     confirmation_prompt = (
#         f"The user's info has been saved: {interest.dict()}.\n"
#         "Reply politely confirming that their information was recorded successfully."
#     )
#     confirmation = llm.invoke([SystemMessage(content=confirmation_prompt)])
#     reply = f"{message}\n\n{confirmation.content}"

#     state["messages"].append(AIMessage(content=reply))
#     state["done"] = True
#     return state

async def log_to_mcp(state, customer_data):
    """
    Log collected data to MCP server and confirm with user.
    """
    try:
        interest = ProductInterest(**customer_data)
    except Exception as e:
        logging.error(f"Validation error: {e}")
        state["messages"].append(AIMessage(content=f"❌ Invalid data: {e}"))
        return state

    # 🔗 Call MCP tool
    client = Client(MCP_URL)
    async with client:
        result = await client.call_tool("log_product_interest", interest.dict())
        logging.info(f"🧾 MCP result: {result}")

    message = (
        result.data.get("message")
        or result.structured_content.get("message")
        or result.content[0].text
    )

    # 💬 Generate polite confirmation message
    confirm_prompt = (
        f"The user's info has been saved: {interest.dict()}.\n"
        "Reply politely (in the user's language) confirming that their information was recorded successfully."
    )
    confirm_reply = llm.invoke([SystemMessage(content=confirm_prompt)])

    final_message = f"{message}\n\n{confirm_reply.content}"

    state["messages"].append(AIMessage(content=final_message))
    state["done"] = True
    state["awaiting_confirmation"] = False
    return state

# Interview Node
async def interview_node(state):
    """
    Conversationally collect user info, confirm, and send to MCP.
    """
    logging.info("➡️ Entered interview_node")

    messages = state.get("messages", [])
    customer_data = dict(state.get("customer_data", {}) or {})

    # If user is confirming
    if state.get("awaiting_confirmation"):
        user_last = messages[-1].content.lower()
        if any(word in user_last for word in ["ถูกต้อง", "ยืนยัน", "yes", "correct", "ok"]):
            logging.info("✅ User confirmed information — sending to MCP")

            # ---- Send to MCP ----
            result = await log_to_mcp(state, customer_data)

            # Extract response text from MCP result
            mcp_message = (
                result.get("message")
                if isinstance(result, dict)
                else str(result)
            )

            # ---- Use LLM to summarize confirmation ----
            confirm_prompt = (
                f"The customer has completed the insurance interview. "
                f"The recorded information is:\n\n{customer_data}\n\n"
                "Write a short, polite closing message in the same language as the user. "
                "Thank them for their time and confirm that their data was recorded successfully."
            )

            llm_reply = llm.invoke([SystemMessage(content=confirm_prompt)])
            summary_text = llm_reply.content.strip()

            # ---- Send the final summary to the user ----
            full_response = f"{mcp_message}\n\n{summary_text}"
            state["messages"].append(AIMessage(content=full_response))
            state["done"] = True  # mark conversation complete
            return state

        else:
            # User rejected confirmation → ask for correction
            state["messages"].append(
                AIMessage(content="ข้อมูลใดที่ต้องการแก้ไขบ้างครับ/ค่ะ?")
            )
            state["awaiting_field"] = None
            return state

    # Ask next question if still collecting info
    fields = ["name", "age", "occupation", "income", "product_name", "memo"]
    missing_field = next((f for f in fields if not customer_data.get(f)), None)

    if missing_field:
        system_prompt = (
            "You are a polite bilingual (Thai/English) insurance assistant.\n"
            "Ask only one clear question at a time to collect the customer's information.\n"
            "Required fields: name, age, occupation, income, product_name, memo.\n"
            "When all fields are complete, summarize them for confirmation.\n"
            "Use the same language as the customer."
        )
        convo = [SystemMessage(content=system_prompt)] + messages
        llm_reply = llm.invoke(convo)
        question = llm_reply.content.strip()

        state["messages"].append(AIMessage(content=question))
        state["awaiting_field"] = missing_field
        return state

    # All fields filled → ask for confirmation
    summary = (
        "ขอสรุปข้อมูลที่ได้ดังนี้นะครับ/ค่ะ:\n"
        f"- ชื่อ: {customer_data.get('name')}\n"
        f"- อายุ: {customer_data.get('age')} ปี\n"
        f"- อาชีพ: {customer_data.get('occupation')}\n"
        f"- รายได้: {customer_data.get('income')} บาท\n"
        f"- สินค้าที่สนใจ: {customer_data.get('product_name')}\n"
        f"- หมายเหตุ: {customer_data.get('memo') or 'ไม่มี'}\n\n"
        "หากข้อมูลถูกต้อง พิมพ์ 'ถูกต้อง' เพื่อยืนยันครับ/ค่ะ."
    )

    state["messages"].append(AIMessage(content=summary))
    state["awaiting_confirmation"] = True
    return state
