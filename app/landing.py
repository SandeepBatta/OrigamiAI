import streamlit as st


def show_landing():
    st.set_page_config(
        page_title="Origami AI Studio", page_icon="static/origami_icon.png"
    )
    st.title("Origami AI Studio", anchor=False)
    st.write("Please sign up or log in to continue.")

    # Privacy notice
    st.info(
        "📋 **Privacy Notice**: By using Origami AI Studio, you agree that your chat conversations and interactions may be used for research and improvement purposes. We are committed to protecting your privacy while enhancing our AI capabilities."
    )

    if st.button(
        "Sign up / Log in",
        key="login-button",
        use_container_width=True,
        icon=":material/login:",
    ):
        st.login("auth0")
    st.stop()
