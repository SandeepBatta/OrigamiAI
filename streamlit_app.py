import streamlit as st
from app.landing import show_landing
from app.app import show_app

# 1) If not logged in, show landing (calls st.login("auth0") and stops)
if not st.experimental_user.is_logged_in:
    show_landing()

# 2) Require email verification
if not st.experimental_user.get("email_verified", False):
    st.warning("✅ Check your inbox, click the verification link.")
    if st.button("🔄 Login"):
        st.logout()
        st.rerun()
    st.stop()

show_app()
