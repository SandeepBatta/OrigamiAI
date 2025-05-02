import streamlit as st


def show_landing():
    st.set_page_config(
        page_title="Origami AI Studio", page_icon="static/origami_icon.png"
    )
    st.title("Origami AI Studio", anchor=False)
    st.write("Please sign up or log in to continue.")
    if st.button(
        "Sign up / Log in",
        key="login-button",
        use_container_width=True,
        icon=":material/login:",
    ):
        st.login("auth0")
    st.stop()
