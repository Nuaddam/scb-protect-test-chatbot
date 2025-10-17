import streamlit as st
import requests
import uuid
import os

# CONFIG
API_BASE = "http://127.0.0.1:8000"
UPLOAD_ENDPOINT = f"{API_BASE}/upload-doc"
CHAT_ENDPOINT = f"{API_BASE}/chat"
SESSIONS_ENDPOINT = f"{API_BASE}/sessions"
HISTORY_ENDPOINT = f"{API_BASE}/history"

st.set_page_config(page_title="RAG Chatbot", page_icon="💬")
#  Ensure persistence across reruns
st.session_state.setdefault("awaiting_reply", False)
st.session_state.setdefault("session_id", str(uuid.uuid4()))
st.session_state.setdefault("chat_history", [])

# --- SESSION HANDLING ---
st.sidebar.header("💬 Chat Session")


# Try to load available sessions
try:
    response = requests.get(SESSIONS_ENDPOINT)
    existing_sessions = response.json().get("sessions", [])
except Exception as e:
    existing_sessions = []
    st.sidebar.error(f"Failed to fetch sessions: {e}")

# Let user pick
selected_session = st.sidebar.selectbox(
    "Select previous session", ["New session"] + existing_sessions
)

#  Ensure session_id always exists
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())

#  New session only if NOT in middle of interview
if selected_session == "New session":
    # Only start a new session if we're not in the middle of an interview
    if not st.session_state.get("awaiting_reply", False):
        if "session_id" not in st.session_state or not st.session_state["chat_history"]:
            st.session_state["session_id"] = str(uuid.uuid4())
            st.session_state["chat_history"] = []
    else:
        st.sidebar.info("🕐 Continuing existing session — interview in progress.")
else:
    #  Use selected session_id (only real IDs)
    st.session_state["session_id"] = selected_session
    # Load history
    try:
        r = requests.get(f"{HISTORY_ENDPOINT}/{selected_session}")
        if r.status_code == 200:
            data = r.json()
            st.session_state["chat_history"] = []
            for h in data.get("history", []):
                st.session_state["chat_history"].append({"role": "user", "content": h["user"]})
                st.session_state["chat_history"].append({"role": "assistant", "content": h["assistant"]})
        else:
            st.sidebar.warning("Could not load chat history.")
    except Exception as e:
        st.sidebar.error(f"Error loading history: {e}")

#  Debug info in sidebar
st.sidebar.info(f"📎 Current session ID: {st.session_state['session_id']}")
st.caption(f"💬 Current session: `{st.session_state['session_id']}`")

# FILE UPLOAD
st.sidebar.subheader("Upload Documents")
uploaded_file = st.sidebar.file_uploader("Upload a document", type=["pdf", "txt", "docx"])

if uploaded_file:
    with st.spinner("Uploading file..."):
        files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
        try:
            r = requests.post(UPLOAD_ENDPOINT, files=files)
            if r.status_code == 200:
                st.sidebar.success(" File uploaded successfully!")
            else:
                st.sidebar.error(f"Upload failed: {r.text}")
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

# CHAT INTERFACE
st.title("SCB Protect RAG Chatbot")

# Display chat history
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

for msg in st.session_state["chat_history"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
prompt = st.chat_input("Ask me anything...")

if prompt:
    # Show user message immediately
    st.chat_message("user").markdown(prompt)
    st.session_state["chat_history"].append({"role": "user", "content": prompt})

    # Prepare payload
    payload = {
        "question": prompt,
        "session_id": st.session_state["session_id"],
        "model": "gpt-4.1-mini",
    }

    # Send to backend
    with st.spinner("Thinking..."):
        try:
            response = requests.post(CHAT_ENDPOINT, json=payload)
            # if response.status_code == 200:
            #     answer = response.json().get("answer", "No answer.")
            # else:
            #     answer = f"Error: {response.text}"
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "No answer.")

                # 🧩 If backend paused for human input
                if data.get("status") == "interrupted" or data.get("status") == "__interrupted__":
                    answer = f"🤖 {answer}"  # show the question
                    st.session_state["awaiting_reply"] = True
                else:
                    st.session_state["awaiting_reply"] = False
                if " Logged interest" in answer:
                    st.session_state["awaiting_reply"] = False
            else:
                answer = f"Error: {response.text}"
                st.session_state["awaiting_reply"] = False
        except Exception as e:
            answer = f"Exception: {e}"

    # Display assistant response
    with st.chat_message("assistant"):
        st.markdown(answer)

    # Save to local session chat history
    st.session_state["chat_history"].append({"role": "assistant", "content": answer})
