import streamlit as st


def show_landing():
    st.title("🔒 Welcome to Origami AI Assistant")
    st.write("Please sign up or log in to continue.")
    if st.button(
        "Sign up / Log in",
        key="login-button",
        use_container_width=True,
        icon=":material/login:",
    ):
        st.login("auth0")
    st.stop()
