import streamlit as st
from db import new_session, load_messages, save_message, get_session_summaries
from image_generation import send_to_ai
import random
import time


def show_app():
    st.set_page_config(page_title="Origami AI", page_icon="static/origami_icon.png")
    st.title("Origami AI Studio")
    st.caption("Unfold your creativity with the power of AI")

    user = st.experimental_user
    user_id = user["email"]

    if "response_id" not in st.session_state:
        st.session_state.response_id = None

    # ─── Sidebar: list & create sessions ────────────────────────────────────────
    with st.sidebar:
        st.logo(image="static/origami_icon.png", size="large")
        st.subheader(f"Logged in as {user_id}")
        if st.button("Logout", icon=":material/logout:", use_container_width=True):
            st.logout()

        st.divider()

        # New chat button creates and prepends a fresh session
        if st.button(
            "New Chat",
            use_container_width=True,
            icon=":material/add_box:",
            type="primary",
        ):
            new_sid = new_session(user_id)
            # prepend so it appears first
            st.session_state.session_summaries.insert(0, (new_sid, "New chat"))
            st.session_state.session_id = new_sid
            st.session_state.response_id = None
            st.rerun()

        st.divider()

        st.title("Chat History :material/history:")

        # Initialize session summaries in state once
        if "session_summaries" not in st.session_state:
            st.session_state.session_summaries = get_session_summaries(user_id)

        # Ensure there's at least one session
        if not st.session_state.session_summaries:
            sid = new_session(user_id)
            st.session_state.session_summaries = [(sid, "New chat")]

        # Default current session
        session_ids = [sid for sid, _ in st.session_state.session_summaries]
        if (
            "session_id" not in st.session_state
            or st.session_state.session_id not in session_ids
        ):
            st.session_state.session_id = session_ids[0]

        # Render a button per session (newest first)
        for sid, title in st.session_state.session_summaries:
            disabled = sid == st.session_state.session_id
            if st.button(
                title,
                key=sid,
                disabled=disabled,
                use_container_width=True,
                icon=":material/chat:",
            ):
                st.session_state.session_id = sid
                st.session_state.response_id = None
                st.rerun()

    # ─── Main: display chat history for the chosen session ───────────────────────
    current_sid = st.session_state.session_id
    messages = load_messages(user_id, current_sid)
    for msg in messages:
        with st.chat_message(msg["role"]):
            if msg["type"] == "text":
                st.markdown(msg["content"])
            else:
                st.image(msg["url"], caption=msg["content"])

    # ─── Handle user input ───────────────────────────────────────────────────────
    if prompt := st.chat_input(
        "Enter your prompt...", accept_file=True, file_type=["jpg", "jpeg", "png"]
    ):
        # Save & display user message
        user_msg = {"role": "user", "type": "text", "content": prompt.text}
        save_message(user_id, st.session_state.session_id, user_msg)
        with st.chat_message("user"):
            st.markdown(prompt.text)

        # Call AI and stream response
        with st.spinner(random.choice(st.secrets["spinner_messages"]), show_time=True):
            resp = send_to_ai(
                prompt.text,
                user_id,
                prompt["files"],
                previous_response_id=st.session_state.response_id,
            )

        # Save & display AI response
        save_message(user_id, st.session_state.session_id, resp)
        with st.chat_message("assistant"):
            if resp["type"] == "text":

                def stream_data():
                    for word in resp["content"].split(" "):
                        yield word + " "
                        time.sleep(0.1)

                st.write_stream(stream_data)
            else:
                st.image(resp["url"], caption=resp["content"])

        st.session_state.response_id = resp["response_id"]
