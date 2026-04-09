import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000/chat"


st.set_page_config(page_title="Hotel Concierge Chat", page_icon="🛎️", layout="centered")

st.title("Hotel Concierge")
st.write("Chat with the hotel concierge assistant. This is a prototype UI.")


if "messages" not in st.session_state:
    st.session_state.messages = []


with st.container(border=True):
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        else:
            with st.chat_message("assistant"):
                st.markdown(content)


user_input = st.chat_input("Ask the concierge anything about your stay...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                resp = requests.post(API_URL, json={"message": user_input}, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                answer = data.get("response", "Sorry, I could not understand the response from the server.")
            except Exception as e:
                answer = f"Error talking to backend: {e}"

            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

