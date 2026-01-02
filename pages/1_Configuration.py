import streamlit as st

st.set_page_config(page_title="Configuration", layout="wide")
st.header("1) Configuration")

model = st.selectbox("Model do generowania treści", ["OpenAI", "Gemini", "Qwen"], index=0)
st.session_state.provider = model.lower()

st.caption("Wytyczne, outline i frazy ustawiasz w kolejnych zakładkach.")
