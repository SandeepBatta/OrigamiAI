import streamlit as st
import time
import random

from image_generation import send_to_ai

# Page configuration
st.set_page_config(page_title="Origami AI Assistant", page_icon="🎨")
st.title("Origami AI Assistant")
st.caption("Generate text responses and images through OpenAI API")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "response_id" not in st.session_state:
    st.session_state.response_id = None

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["type"] == "text":
            st.markdown(message["content"])
        elif message["type"] == "image":
            st.image(message["url"], caption=message["content"])

# Handle user input
if prompt := st.chat_input(
    "Enter your prompt...", accept_file=True, file_type=["jpg", "jpeg", "png"]
):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt.text)

    # Add to message history
    st.session_state.messages.append(
        {"role": "user", "type": "text", "content": prompt.text}
    )

    # Get AI response
    with st.spinner(random.choice(st.secrets["spinner_messages"]), show_time=True):
        response = send_to_ai(
            prompt.text, prompt["files"], response_id=st.session_state.response_id
        )

    # Update response ID for conversation continuity
    st.session_state.response_id = response["response_id"]

    # Display AI response
    with st.chat_message("assistant"):
        if response["type"] == "text":
            # st.markdown(response["content"])
            def stream_data():
                for word in response["content"].split(" "):
                    yield word + " "
                    time.sleep(0.1)

            st.write_stream(stream_data)
        elif response["type"] == "image":
            st.image(response["url"], caption=response["content"])

    # Store in message history
    st.session_state.messages.append(response)
