import streamlit as st
from db import new_session, load_messages, save_message, get_session_summaries
from image_generation import send_to_ai
import random
import time
from datetime import datetime, timedelta
import pytz


def show_app():
    st.set_page_config(
        page_title="Origami AI Studio",
        page_icon="static/origami_icon.png",
        layout="wide",
    )
    st.title("Origami AI Studio", anchor=False)
    st.caption(
        "Unfold your creativity through AI's generative images and how-to instructions"
    )

    user = st.experimental_user
    user_id = user["email"]

    if "response_id" not in st.session_state:
        st.session_state.response_id = None

    # Timezone selector in sidebar
    timezones = pytz.all_timezones
    default_tz = "US/Eastern"
    if "user_timezone" not in st.session_state:
        st.session_state["user_timezone"] = default_tz

    # ─── Sidebar: list & create sessions ────────────────────────────────────────
    with st.sidebar:
        st.logo(image="static/origami_icon.png", size="large")
        st.subheader("Logged in as:")
        st.text(user_id)

        if st.button("Logout", icon=":material/logout:", use_container_width=True):
            st.logout()

        st.divider()

        user_tz = st.sidebar.selectbox(
            "Select your timezone",
            timezones,
            index=timezones.index(st.session_state["user_timezone"]),
            key="tz_selectbox",
        )
        st.session_state["user_timezone"] = user_tz

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

        st.title("Chat History :material/history:")

        # Initialize session summaries in state once
        if "session_summaries" not in st.session_state:
            st.session_state.session_summaries = get_session_summaries(user_id)

        if not st.session_state.session_summaries:
            new_sid = new_session(user_id)
            # prepend so it appears first
            st.session_state.session_summaries.insert(0, (new_sid, "New chat"))
            st.session_state.session_id = new_sid
            st.session_state.response_id = None
            st.rerun()

        # Only show sessions that have at least one message and correct tuple length
        session_summaries = [
            s for s in st.session_state.session_summaries if len(s) == 3
        ]

        # Ensure session_id is initialized to the first available session
        if session_summaries and "session_id" not in st.session_state:
            st.session_state.session_id = session_summaries[0][0]

        # Group sessions
        grouped = {"Today": [], "Last Week": [], "Previous Chats": []}
        user_tz_obj = pytz.timezone(st.session_state["user_timezone"])
        now_local = datetime.now(pytz.utc).astimezone(user_tz_obj).date()
        week_ago_local = now_local - timedelta(days=7)
        for sid, snippet, ts in session_summaries:
            # Convert UTC timestamp to user's timezone
            utc_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            utc_dt = pytz.utc.localize(utc_dt)
            local_dt = utc_dt.astimezone(user_tz_obj)
            session_date = local_dt.date()
            date_str = local_dt.strftime("%m/%d/%Y")
            if session_date == now_local:
                grouped["Today"].append((sid, snippet, date_str))
            elif session_date > week_ago_local:
                grouped["Last Week"].append((sid, snippet, date_str))
            else:
                grouped["Previous Chats"].append((sid, snippet, date_str))

        def render_history_group(label, items):
            if not items:
                return
            st.markdown(f"**{label}**")
            for sid, snippet, date_str in items:
                is_selected = sid == st.session_state.session_id
                btn_label = f"{date_str}  {snippet}"
                btn_kwargs = {"key": f"hist_{sid}", "use_container_width": True}
                if is_selected:
                    btn_kwargs["disabled"] = True
                if st.button(btn_label, **btn_kwargs):
                    st.session_state.session_id = sid
                    st.session_state.response_id = None
                    st.rerun()

        render_history_group("Today", grouped["Today"])
        render_history_group("Last Week", grouped["Last Week"])
        render_history_group("Previous Chats", grouped["Previous Chats"])

    # ─── Main: display chat history for the chosen session ───────────────────────
    current_sid = st.session_state.session_id
    messages = load_messages(user_id, current_sid)
    for msg in messages:
        avatar_map = {
            "user": "static/you_icon.png",
            "assistant": "static/ai_icon.png",
        }
        with st.chat_message(msg["role"], avatar=avatar_map[msg["role"]]):
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
        # Refresh session summaries after saving a message
        st.session_state.session_summaries = get_session_summaries(user_id)
        with st.chat_message("user", avatar="static/you_icon.png"):
            st.markdown(prompt.text)
            # Show image preview if user uploaded an image
            if prompt.files:
                for file in prompt.files:
                    st.image(file, caption="Uploaded image")

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
        # Refresh session summaries after saving a message
        st.session_state.session_summaries = get_session_summaries(user_id)
        with st.chat_message("assistant", avatar="static/ai_icon.png"):
            if resp["type"] == "text":

                def stream_data():
                    for word in resp["content"].split(" "):
                        yield word + " "
                        time.sleep(0.1)

                st.write_stream(stream_data)
            else:
                st.image(resp["url"], caption=resp["content"])

        st.session_state.response_id = resp["response_id"]
