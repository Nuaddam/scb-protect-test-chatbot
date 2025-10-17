import os
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic_models import QueryInput, QueryResponse, DocumentInfo, DeleteFileRequest
from db_utils import insert_chat_history, get_chat_history, get_all_documents, insert_document_record, delete_document_record
from documents_loaders import index_document_to_chroma, delete_doc_from_chroma
from agent import agent
from langchain_core.messages import HumanMessage, AIMessage
import logging
import shutil
from utils import get_or_create_session_id, history_to_lc_messages, append_message
from langchain_utils import contextualise_chain
from fastapi import UploadFile, File, HTTPException
import sqlite3


logging.basicConfig(filename='app.log', level=logging.INFO)
app = FastAPI()
load_dotenv(override=True)
DB_PATH = "rag_app.db"
SESSION_STORE: dict[str, dict] = {}

# @app.post("/chat", response_model=QueryResponse)
# async def chat(query_input: QueryInput):
#     """Endpoint to handle chat queries."""
#     session_id = get_or_create_session_id(query_input.session_id)
#     logging.info(f"Session ID: {session_id}, User Query: {query_input.question}, Model: {query_input.model.value}")

#     try:
#         # Convert chat history to LangChain messages
#         chat_history = get_chat_history(session_id)
#         messages = history_to_lc_messages(chat_history)


#         # Generate a stand-alone question
#         standalone_q = contextualise_chain.invoke({
#             "chat_history": messages,
#             "input": query_input.question,
#         })

#         messages = append_message(messages, HumanMessage(content=standalone_q))
#         result = await agent.ainvoke(
#             {"messages": messages}
#         )

#         # Get the last AI message
#         last_message = next((m for m in reversed(result["messages"])
#                            if isinstance(m, AIMessage)), None)

#         if last_message:
#             answer = last_message.content
#         else:
#             answer = "I apologize, but I couldn't generate a response at this time."

#         # Store the conversation
#         insert_chat_history(session_id, query_input.question, answer, query_input.model.value)
#         logging.info(f"Session ID: {session_id}, AI Response: {answer}")

#         return QueryResponse(answer=answer, session_id=session_id, model=query_input.model)

#     except Exception as e:
#         logging.error(f"Error in chat: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

SESSION_STORE: dict[str, dict] = {}

def get_state(session_id):
    return SESSION_STORE.setdefault(session_id, {"messages": []})

def save_state(session_id, state):
    SESSION_STORE[session_id] = state

@app.post("/chat", response_model=QueryResponse)
async def chat(query_input: QueryInput):
    session_id = get_or_create_session_id(query_input.session_id)
    state = get_state(session_id)

    user_input = query_input.question
    state["messages"].append(HumanMessage(content=user_input))

    # ✅ If we were waiting for confirmation
    if state.get("awaiting_confirmation"):
        logging.info("🧠 Continuing interview confirmation flow")
        result = await agent.ainvoke(state, start_at="interview")
    else:
        result = await agent.ainvoke(state)

    save_state(session_id, result)
    try:
        # Load state for this session
        state = get_state(session_id)
        user_input = query_input.question

        # 🧠 Handle ongoing interview
        if state.get("awaiting_field"):
            field = state["awaiting_field"]
            state.setdefault("customer_data", {})[field] = user_input
            state["awaiting_field"] = None
            state["messages"].append(HumanMessage(content=user_input))
            result = await agent.ainvoke(state, start_at="interview")
        else:
            # Normal flow
            chat_history = get_chat_history(session_id)
            messages = history_to_lc_messages(chat_history)
            messages = append_message(messages, HumanMessage(content=user_input))
            result = await agent.ainvoke({"messages": messages})
        
        

        # Extract last AI message
        last_msg = next((m for m in reversed(result["messages"]) if isinstance(m, AIMessage)), None)
        answer = last_msg.content if last_msg else "I couldn't respond."

        save_state(session_id, result)
        insert_chat_history(session_id, user_input, answer, query_input.model.value)
        logging.info(f"Session ID: {session_id}, AI Response: {answer}")

        return QueryResponse(answer=answer, session_id=session_id, model=query_input.model)

    except Exception as e:
        logging.exception("Error in chat")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")



@app.get("/sessions")
def get_sessions():
    """Return all distinct session_ids from chat_history"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT session_id FROM chat_history ORDER BY id DESC;")
    sessions = [row[0] for row in cursor.fetchall()]
    conn.close()
    return {"sessions": sessions}

@app.post("/upload-doc")
def upload_and_index_document(file: UploadFile = File(...)):
    allowed_extensions = ['.pdf', '.docx', '.html']
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed types are: {', '.join(allowed_extensions)}")
    
    temp_file_path = f"temp_{file.filename}"
    
    try:
        # Save the uploaded file to a temporary file
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_id = insert_document_record(file.filename)
        success = index_document_to_chroma(temp_file_path, file_id)
        
        if success:
            return {"message": f"File {file.filename} has been successfully uploaded and indexed.", "file_id": file_id}
        else:
            delete_document_record(file_id)
            raise HTTPException(status_code=500, detail=f"Failed to index {file.filename}.")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.get("/list-docs", response_model=list[DocumentInfo])
def list_documents():
    return get_all_documents()

@app.post("/delete-doc")
def delete_document(request: DeleteFileRequest):
    # Delete from Chroma
    chroma_delete_success = delete_doc_from_chroma(request.file_id)

    if chroma_delete_success:
        # Then delete from the database
        db_delete_success = delete_document_record(request.file_id)
        if db_delete_success:
            return {"message": f"Successfully deleted document with file_id {request.file_id} from the system."}
        else:
            return {"error": f"Deleted from Chroma but failed to delete document with file_id {request.file_id} from the database."}
    else:
        return {"error": f"Failed to delete document with file_id {request.file_id} from Chroma."}