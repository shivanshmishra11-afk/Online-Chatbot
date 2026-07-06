import os
import streamlit as st
from google import genai

st.set_page_config(page_title="My AI Document Assistant", layout="centered")
st.title("📄 Multimodal Document Assistant")

# Step 1: Secure API Key Input
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    # Fallback to sidebar input if the environment variable isn't set
    api_key = st.sidebar.text_input("Enter Google API Key", type="password")

if not api_key:
    st.info("Please enter your Google API key to get started.")
    st.stop()

# Initialize the Google GenAI Client
client = genai.Client(api_key=api_key)

# Initialize persistent session states for Chat History and Cloud Files
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_file_id" not in st.session_state:
    st.session_state.uploaded_file_id = None
if "uploaded_file_obj" not in st.session_state:
    st.session_state.uploaded_file_obj = None

# Step 2: Drag & Drop File Uploader
uploaded_file = st.file_uploader("Upload a PDF document (contains text & images)", type=["pdf"])

if uploaded_file:
    # If a brand-new file is uploaded, process it
    if st.session_state.uploaded_file_id != uploaded_file.name:
        
        # Cleanup: Delete the old file from Google's server if it exists
        if st.session_state.uploaded_file_obj:
            try:
                client.files.delete(name=st.session_state.uploaded_file_obj.name)
            except Exception:
                pass
        
        # Save uploaded file temporarily to disk so the GenAI SDK can upload it
        temp_path = os.path.join("/tmp" if os.name != 'nt' else "C:/temp", uploaded_file.name)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        with st.spinner("Processing and visually analyzing document..."):
            google_file = client.files.upload(file=temp_path)
            st.session_state.uploaded_file_id = uploaded_file.name
            st.session_state.uploaded_file_obj = google_file
            st.session_state.messages = [] # Reset chat history for the new file
            
        st.success(f"Document '{uploaded_file.name}' loaded successfully! Ask anything.")

# Step 3: Render Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Step 4: Handle User Queries
if user_query := st.chat_input("Ask a question about the document..."):
    if not st.session_state.uploaded_file_obj:
        st.warning("Please upload a PDF document first.")
        st.stop()

    # Append user question to Chat History
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.write(user_query)

    # Query Gemini Multimodal directly (supports text + visual elements)
    with st.chat_message("assistant"):
        with st.spinner("Gemini is reading..."):
            try:
                # Retries automatically to handle brief 503 server overloads
                response = None
                for attempt in range(3):
                    try:
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=[st.session_state.uploaded_file_obj, user_query]
                        )
                        break
                    except Exception as e:
                        if "503" in str(e) and attempt < 2:
                            import time
                            time.sleep(4)
                        else:
                            raise e

                if response:
                    st.write(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"An error occurred: {e}")
