import streamlit as st
from PIL import Image
import pytesseract

st.title("📷 OCR Demo App")
st.write("画像をアップロードして、文字を抽出します。")

# ファイルアップロード
uploaded_file = st.file_uploader("画像ファイルをアップロードしてください (PNG/JPG)", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # アップロードした画像を表示
    image = Image.open(uploaded_file)
    st.image(image, caption="アップロードした画像", use_column_width=True)

    # OCR処理ボタン
    if st.button("文字を抽出する"):
        with st.spinner("OCR処理中..."):
            text = pytesseract.image_to_string(image, lang="eng")  # 英語のみ
        st.subheader("📄 抽出結果")
        st.text_area("テキスト", text, height=200)
