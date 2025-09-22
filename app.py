import io
import requests
import streamlit as st
from PIL import Image

# --- 設定 ---
OCRSPACE_ENDPOINT = "https://api.ocr.space/parse/image"
OCR_LANG = "eng"  # まず英語

def ocr_with_ocrspace(image_bytes: bytes) -> str:
    api_key = st.secrets.get("OCR_API_KEY", "helloworld")  # 学習用デフォルトキー
    files = {"filename": ("upload.png", image_bytes)}
    data = {
        "apikey": api_key,
        "language": OCR_LANG,
        "OCREngine": 2,  # 高精度側
        "scale": True,
        "isTable": False,
    }
    r = requests.post(OCRSPACE_ENDPOINT, files=files, data=data, timeout=60)
    r.raise_for_status()
    js = r.json()
    if not js.get("ParsedResults"):
        raise RuntimeError(js.get("ErrorMessage") or "OCR API failed")
    return js["ParsedResults"][0]["ParsedText"]

def ocr_with_tesseract(image: Image.Image) -> str:
    try:
        import pytesseract
        return pytesseract.image_to_string(image, lang=OCR_LANG)
    except Exception as e:
        # Tesseract が無い/動かない場合はこちらへ
        raise RuntimeError(f"Tesseract not available: {e}")

st.title("📷 OCR Demo (Cloud-friendly)")
st.write("画像からテキストを抽出します。クラウドでは自動的にOCR APIに切り替えます。")

uploaded = st.file_uploader("画像をアップロード (PNG/JPG/WebP)", type=["png","jpg","jpeg","webp"])
if uploaded:
    image = Image.open(uploaded).convert("RGB")
    st.image(image, caption="アップロードした画像", use_column_width=True)

    if st.button("文字を抽出する"):
        with st.spinner("OCR中..."):
            try:
                # まずローカル（Tesseract）を試す
                text = ocr_with_tesseract(image)
            except Exception:
                # 失敗したらAPIへ（Streamlit Cloudはこちら）
                text = ocr_with_ocrspace(uploaded.getvalue())

        st.subheader("📄 抽出結果")
        st.text_area("Text", text, height=240)
        st.download_button("結果をダウンロード (.txt)", data=text, file_name="ocr_result.txt")
