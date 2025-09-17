import streamlit as st

st.title("はじめてのStreamlitアプリ")
st.write("こんにちは！PythonとStreamlitでWebアプリを作りました。")

if st.button("押してみる"):
    st.success("ボタンが押されました！ 🎉")
