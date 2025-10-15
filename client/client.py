import streamlit as st
import requests
import uuid

# CONFIG
API_BASE = "http://127.0.0.1:8000"  # 👈 change to your backend URL
UPLOAD_ENDPOINT = f"{API_BASE}/upload-doc"
CHAT_ENDPOINT = f"{API_BASE}/chat"
SESSIONS_ENDPOINT = f"{API_BASE}/sessions"

st.set_page_config(page_title="RAG Chatbot", page_icon="💬")

# SESSION HANDLING

st.sidebar.header("💬 Chat Session")

# Fetch existing sessions from backend
try:
    response = requests.get(SESSIONS_ENDPOINT)
    existing_sessions = response.json().get("sessions", [])
except Exception as e:
    existing_sessions = []
    st.sidebar.error(f"⚠️ Failed to fetch sessions: {e}")

# Select or create a new session
selected_session = st.sidebar.selectbox(
    "Select previous session", ["🆕 New session"] + existing_sessions
)

if selected_session == "🆕 New session":
    st.session_state["session_id"] = str(uuid.uuid4())
else:
    st.session_state["session_id"] = selected_session

# SIDEBAR: File Upload
st.sidebar.subheader("📄 Upload Documents")
uploaded_file = st.sidebar.file_uploader("Upload a document", type=["pdf", "txt", "docx"])

if uploaded_file:
    with st.spinner("Uploading file..."):
        files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
        try:
            r = requests.post(UPLOAD_ENDPOINT, files=files)
            if r.status_code == 200:
                st.sidebar.success("✅ File uploaded successfully!")
            else:
                st.sidebar.error(f"❌ Upload failed: {r.text}")
        except Exception as e:
            st.sidebar.error(f"⚠️ Error: {e}")

# MAIN CHAT
st.title("RAG Chatbot 🧠")

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

for msg in st.session_state["chat_history"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Ask me anything...")

if prompt:
    st.chat_message("user").markdown(prompt)
    st.session_state["chat_history"].append({"role": "user", "content": prompt})

    payload = {
        "question": prompt,
        "session_id": st.session_state["session_id"],
        "model": "gpt-4.1-mini"
    }

    try:
        response = requests.post(CHAT_ENDPOINT, json=payload)
        if response.status_code == 200:
            answer = response.json().get("answer", "No answer.")
        else:
            answer = f"⚠️ Error: {response.text}"
    except Exception as e:
        answer = f"⚠️ Exception: {e}"

    with st.chat_message("assistant"):
        st.markdown(answer)

    st.session_state["chat_history"].append({"role": "assistant", "content": answer})
