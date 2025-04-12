import os
import json
import streamlit as st
from prescription_processing import extract_prescription, translate_to_hindi, text_to_speech
from rag_search import setup_rag_pipeline, answer_question
from web_search import fetch_web_info

# Define the path to the credentials file
credentials_path = os.path.expanduser("~/Desktop/credentials/PP/credentials.json")
# Load credentials
with open(credentials_path, "r") as f:
    credentials = json.load(f)

SARVAM_API_KEY = credentials["sarvam_api_key"]
OPENAI_API_KEY = credentials["openai_api_key"]
SEARCH_ENGINE_ID = credentials.get("search_engine_id")  # Optional, use .get() to avoid KeyError if absent

# Streamlit app setup
st.title("Prescription Chatbot")
st.subheader("Upload a prescription image and ask questions about your medicines")

# File uploader for prescription image
uploaded_file = st.file_uploader("Upload Prescription Image (PNG)", type="png")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "prescription_text" not in st.session_state:
    st.session_state.prescription_text = ""
if "qa_chain" not in st.session_state:
    st.session_state.qa_chain = None
if "hindi_text" not in st.session_state:
    st.session_state.hindi_text = ""
if "last_answer_sufficient" not in st.session_state:
    st.session_state.last_answer_sufficient = True
if "last_question" not in st.session_state:
    st.session_state.last_question = ""
print(f"Start of script - last_question: '{st.session_state.last_question}' (length: {len(st.session_state.last_question)})")  # Debug

# Process the uploaded image and extract prescription details once
if uploaded_file and not st.session_state.prescription_text:
    st.session_state.prescription_text = extract_prescription(uploaded_file, OPENAI_API_KEY)
    with open("extracted_truncated_prescription.txt", "w", encoding="utf-8") as file:
        file.write(st.session_state.prescription_text)

    st.session_state.hindi_text = translate_to_hindi(st.session_state.prescription_text, SARVAM_API_KEY)
    with open("translated_prescription_hindi.txt", "w", encoding="utf-8") as file:
        file.write(st.session_state.hindi_text)

    success, message = text_to_speech(st.session_state.hindi_text, SARVAM_API_KEY, output_file="output.wav")
    if not success:
        st.error(message)

    st.session_state.qa_chain = setup_rag_pipeline(st.session_state.prescription_text, st.session_state.hindi_text, OPENAI_API_KEY)

# Display prescriptions persistently at the top using an expander
if st.session_state.prescription_text:
    with st.expander("View Prescription Summaries", expanded=True):  # Expanded by default
        st.write("### Truncated Prescription Summary in English")
        st.write(st.session_state.prescription_text)
        st.write("### Prescription Summary in Hindi")
        st.write(st.session_state.hindi_text)
        if "output.wav" in [f.name for f in st.session_state.get('generated_files', [])] or st.session_state.get('audio_generated', False):
            st.write("### Listen to the Prescription Summary (Hindi)")
            st.audio("output.wav")
        else:
            success, message = text_to_speech(st.session_state.hindi_text, SARVAM_API_KEY, output_file="output.wav")
            if success:
                st.write("### Listen to the Prescription Summary (Hindi)")
                st.audio("output.wav")
                st.session_state['audio_generated'] = True
            else:
                st.error(message)

# Display conversation history below the prescriptions
st.write("### Conversation")
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

print(f"Messages: {st.session_state.messages}")

if st.session_state.messages:
    for message in reversed(st.session_state.messages):
        print(f"Checking message: {message}")  # Debug
        if message["role"] == "user" and message["content"].strip().lower() != "i need more information.":
            st.session_state.last_question = message["content"]
            print(f"Set last_question from messages: '{st.session_state.last_question}'")  # Debug
            break

print(f"Before button logic - last_question: '{st.session_state.last_question}' (length: {len(st.session_state.last_question)})")  # Debug

# Chat input for follow-up questions
if prompt := st.chat_input("Ask a question about your prescription (e.g., 'What are the side effects of Paracetamol?')"):
    print("Chat input block executed")  # Debug
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.last_question = prompt
    print(f"Set last_question to: {st.session_state.last_question}")  # Debug

    if st.session_state.qa_chain:
        conversation_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages[:-1]])
        
        answer, source_documents = answer_question(
            st.session_state.qa_chain,
            prompt,
            conversation_history,
            prescription_text=st.session_state.prescription_text,
            web_info=None
        )

        insufficient_answer = "I don't have enough information" in answer.lower() or len(answer) < 50 or "not mentioned" in answer.lower()
        user_not_satisfied = any("more information" in msg["content"].lower() or "not clear" in msg["content"].lower() for msg in st.session_state.messages[-2:])

        if insufficient_answer or user_not_satisfied or not st.session_state.last_answer_sufficient:
            st.write("Let me search the web for more information...")
            web_info = fetch_web_info(prompt)
            answer, source_documents = answer_question(
                st.session_state.qa_chain,
                prompt,
                conversation_history,
                prescription_text=st.session_state.prescription_text,
                web_info=web_info
            )
            st.session_state.last_answer_sufficient = True
        else:
            st.session_state.last_answer_sufficient = True

        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)

        st.write("### Sources Used")
        for doc in source_documents:
            source = doc.metadata.get("source", "Unknown Source")
            st.write(f"- {doc.page_content[:200]}... (Source: {source})")

        hindi_answer = translate_to_hindi(answer, SARVAM_API_KEY)
        success, message = text_to_speech(hindi_answer, SARVAM_API_KEY, output_file="answer_audio.wav")
        if success:
            st.write("### Listen to the Answer (Hindi)")
            st.audio("answer_audio.wav")
        else:
            st.error(message)

# "I need more information" button
if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
    if st.button("I need more information"):
        st.session_state.last_answer_sufficient = False
        st.session_state.messages.append({"role": "user", "content": "I need more information."})
        with st.chat_message("user"):
            st.markdown("I need more information.")

        print(f"last_question: '{st.session_state.last_question}' (length: {len(st.session_state.last_question)})")  # Debug
        print(f"qa_chain: {st.session_state.qa_chain}")
        
        if st.session_state.last_question and st.session_state.last_question.strip():
            prompt = st.session_state.last_question
            conversation_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages[:-1]])
            st.write("Let me search the web for more information...")
            print(f"Calling fetch_web_info with prompt: {prompt}")  # Debug
            web_info = fetch_web_info(prompt)

            if st.session_state.qa_chain:
                answer, source_documents = answer_question(
                    st.session_state.qa_chain,
                    prompt,
                    conversation_history,
                    prescription_text=st.session_state.prescription_text,
                    web_info=web_info
                )
            else:
                answer = f"Additional information from the web: {' '.join([item['text'] for item in web_info])}\n\nIf you need more details, please consult a healthcare professional."
                source_documents = [Document(page_content=item["text"], metadata={"source": item["url"]}) for item in web_info]

            st.session_state.last_answer_sufficient = True
            st.session_state.messages.append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.markdown(answer)

            if source_documents:
                st.write("### Sources Used")
                for doc in source_documents:
                    source = doc.metadata.get("source", "Unknown Source")
                    st.write(f"- {doc.page_content[:200]}... (Source: {source})")

            hindi_answer = translate_to_hindi(answer, SARVAM_API_KEY)
            print (len(hindi_answer))
            if len(hindi_answer) > 500:
                hindi_answer = hindi_answer[:500]
            
            print(f"Truncated hindi_answer length: {len(hindi_answer)}, content: {hindi_answer}")  # Debug
            success, message = text_to_speech(hindi_answer, SARVAM_API_KEY, output_file="answer_audio.wav")
            if success:
                st.write("### Listen to the Answer (Hindi)")
                st.audio("answer_audio.wav")
            else:
                st.error(message)
        else:
            st.session_state.messages.append({"role": "assistant", "content": "Please ask a question first before requesting more information."})
            with st.chat_message("assistant"):
                st.markdown("Please ask a question first before requesting more information.")