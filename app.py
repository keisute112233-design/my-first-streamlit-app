import io
import json
import requests
import streamlit as st
from PIL import Image

# ====== 設定 ======
OCRSPACE_ENDPOINT = "https://api.ocr.space/parse/image"
OCR_LANG = "eng"  # まずは英語
OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"  # 低コスト＆高速

# ====== OCR: OCR.Space（クラウド用 / ローカルのフォールバック先） ======
def ocr_with_ocrspace(image_bytes: bytes) -> str:
    api_key = st.secrets.get("OCR_API_KEY", "helloworld")  # 自分のAPIキー推奨
    files = {"filename": ("upload.png", image_bytes)}
    data = {
        "apikey": api_key,
        "language": OCR_LANG,
        "OCREngine": 2,   # 高精度側
        "scale": True,
        "isTable": False,
    }
    r = requests.post(OCRSPACE_ENDPOINT, files=files, data=data, timeout=60)
    r.raise_for_status()
    js = r.json()
    if not js.get("ParsedResults"):
        raise RuntimeError(js.get("ErrorMessage") or "OCR API failed")
    return js["ParsedResults"][0]["ParsedText"]

# ====== OCR: Tesseract（ローカル向け。クラウドでは失敗→APIに切替） ======
def ocr_with_tesseract(image: Image.Image) -> str:
    try:
        import pytesseract
        return pytesseract.image_to_string(image, lang=OCR_LANG)
    except Exception as e:
        raise RuntimeError(f"Tesseract not available: {e}")

# ====== スペルチェック（OpenAI Chat Completions API を直接叩く） ======
def spellcheck_with_gpt(text: str) -> dict:
    """
    戻り値:
    {
      "corrected": "修正後テキスト",
      "issues": [
        {"original":"teh","suggestion":"the","explanation":"typo","start":10,"end":13},
        ...
      ]
    }
    """
    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が Secrets に設定されていません。")

    system = (
        "You are a professional copy editor. "
        "Fix English spelling, obvious typos, and light grammar/punctuation only. "
        "Keep meaning and tone. Return strict JSON with keys: "
        "`corrected` (string) and `issues` (array of objects with `original`, `suggestion`, "
        "`explanation`, `start`, `end`). No extra text."
    )
    user = f"Text to check:\n{text}\n\nReturn JSON only."

    payload = {
        "model": OPENAI_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    r = requests.post(OPENAI_ENDPOINT, headers=headers, json=payload, timeout=90)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]

    # JSONとしてパース（コードブロックで返る可能性にも対応）
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # ```json ... ``` をはがす
        if "```" in content:
            content = content.split("```", 2)[-1]
            content = content.replace("json", "").strip()
        return json.loads(content)

# ====== UI ======
st.title("📷 OCR + Spell Check (Cloud-friendly)")
st.caption("OCR: Tesseract(ローカル) / OCR.Space(クラウド). その後、ChatGPT APIでスペルチェック。")

uploaded = st.file_uploader("画像をアップロード (PNG/JPG/JPEG/WebP)", type=["png", "jpg", "jpeg", "webp"])
text_state = st.session_state.setdefault("ocr_text", "")

if uploaded:
    image = Image.open(uploaded).convert("RGB")
    st.image(image, caption="アップロードした画像", use_column_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("文字を抽出する"):
            with st.spinner("OCR中..."):
                # まずローカルTesseractを試し、失敗したらAPIへ
                try:
                    text_state = ocr_with_tesseract(image)
                except Exception:
                    text_state = ocr_with_ocrspace(uploaded.getvalue())
                st.session_state.ocr_text = text_state

    with col2:
        if st.button("スペルチェック（GPT）"):
            if not st.session_state.ocr_text.strip():
                st.warning("先に OCR でテキストを抽出してください。")
            else:
                with st.spinner("ChatGPTでチェック中..."):
                    result = spellcheck_with_gpt(st.session_state.ocr_text)
                st.session_state["spellcheck"] = result

# ==== 出力表示 ====
if st.session_state.get("ocr_text"):
    st.subheader("📄 抽出結果（OCR）")
    st.text_area("Text", st.session_state.ocr_text, height=220)
    st.download_button("結果をダウンロード (.txt)", data=st.session_state.ocr_text, file_name="ocr_result.txt")

if st.session_state.get("spellcheck"):
    st.subheader("✅ スペルチェック結果（GPT）")
    corrected = st.session_state["spellcheck"].get("corrected", "")
    issues = st.session_state["spellcheck"].get("issues", [])
    st.markdown("**修正後テキスト**")
    st.text_area("Corrected", corrected, height=220)
    st.download_button("修正後テキストをダウンロード (.txt)", data=corrected, file_name="corrected.txt")

    if issues:
        st.markdown("**指摘一覧**")
        # 表形式で見やすく
        try:
            import pandas as pd
            st.dataframe(pd.DataFrame(issues))
        except Exception:
            # pandasがなければテキストで
            for i, it in enumerate(issues, 1):
                st.write(f"{i}. {it}")
    else:
        st.info("特に問題は見つかりませんでした。")
