import streamlit as st
import google.generativeai as genai
import pdfplumber
import re
import time
import io

# ─────────────────────────────────────────────

# Page config  (MUST be the very first Streamlit call)

# ─────────────────────────────────────────────

st.set_page_config(
page_title="🎓 AI Quiz Generator",
page_icon=“🧠”,
layout=“wide”,
initial_sidebar_state=“expanded”,
)

# ─────────────────────────────────────────────

# Global CSS – Dark Mode + Polish

# ─────────────────────────────────────────────

st.markdown(”””

<style>
/* ── Base ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0f1117 !important;
    color: #e0e0e0 !important;
    font-family: 'Segoe UI', sans-serif;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1d2e 0%, #12141f 100%) !important;
    border-right: 1px solid #2e3250;
}
[data-testid="stSidebar"] * { color: #c9d1ff !important; }
[data-testid="stSidebar"] .stTextInput input {
    background: #1e2235 !important;
    border: 1px solid #3d4270 !important;
    color: #fff !important;
    border-radius: 8px;
}

/* ── Main area cards ── */
.quiz-card {
    background: #1a1d2e;
    border: 1px solid #2e3250;
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 18px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}
.quiz-card:hover { border-color: #5b63b7; transition: border-color .3s; }

/* ── Section headings inside quiz ── */
.section-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #7c85f5;
    border-bottom: 2px solid #2e3250;
    padding-bottom: 6px;
    margin-bottom: 14px;
}

/* ── Buttons ── */
div.stButton > button {
    background: linear-gradient(135deg, #5b63b7 0%, #7c85f5 100%);
    color: #fff !important;
    border: none;
    border-radius: 10px;
    padding: 0.55rem 1.6rem;
    font-weight: 600;
    font-size: 1rem;
    cursor: pointer;
    transition: opacity .2s;
    width: 100%;
}
div.stButton > button:hover { opacity: 0.88; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #1a1d2e !important;
    border: 2px dashed #3d4270 !important;
    border-radius: 12px !important;
}

/* ── Expander (answer reveal) ── */
details { background: #1e2235; border-radius: 10px; padding: 10px 16px; border: 1px solid #2e3250; }
summary { color: #7c85f5; font-weight: 600; cursor: pointer; }

/* ── Progress bar ── */
div[data-testid="stProgress"] > div { background: #5b63b7 !important; border-radius: 6px; }

/* ── Alerts ── */
.stAlert { border-radius: 10px; }

/* ── Selectbox / radio ── */
[data-testid="stSelectbox"], [data-testid="stRadio"] { color: #c9d1ff; }
</style>

“””, unsafe_allow_html=True)

# ─────────────────────────────────────────────

# Helper – extract & clean text

# ─────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
text_parts = []
with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
for page in pdf.pages:
t = page.extract_text()
if t:
text_parts.append(t)
return “\n”.join(text_parts)

def clean_text(raw: str) -> str:
raw = re.sub(r’\s+’, ’ ‘, raw)          # collapse whitespace
raw = re.sub(r’[^\w\s.,!?:;-()[]"'؀-ۿ]’, ‘’, raw)  # keep arabic too
return raw.strip()

# ─────────────────────────────────────────────

# Helper – call Gemini

# ─────────────────────────────────────────────

PROMPT_TEMPLATE = “””
أنت أستاذ خبير في إعداد الاختبارات الأكاديمية. بناءً على النص التالي، قم بإنشاء اختبار شامل ومتنوع باللغة العربية يحتوي على:

**القسم الأول: أسئلة الاختيار من متعدد (5 أسئلة)**
لكل سؤال: اكتب السؤال، ثم 4 خيارات (أ، ب، ج، د)، ثم الإجابة الصحيحة.

**القسم الثاني: أسئلة صح وخطأ (5 أسئلة)**
لكل سؤال: اكتب الجملة، ثم الإجابة (صح / خطأ).

**القسم الثالث: أسئلة مقالية قصيرة (3 أسئلة)**
لكل سؤال: اكتب السؤال، ثم نموذج الإجابة في 3-4 جمل.

استخدم هذا الفاصل بالضبط بين كل قسم:
—SECTION_BREAK—

النص:
{text}
“””

def generate_quiz(api_key: str, text: str) -> str:
genai.configure(api_key=api_key)
model = genai.GenerativeModel(“gemini-1.5-flash”)
prompt = PROMPT_TEMPLATE.format(text=text[:12000])  # safe token limit
response = model.generate_content(prompt)
return response.text

# ─────────────────────────────────────────────

# Helper – render quiz

# ─────────────────────────────────────────────

def render_quiz_section(title: str, content: str, icon: str):
st.markdown(f”””
<div class="quiz-card">
<div class="section-title">{icon} {title}</div>
{content}
</div>
“””, unsafe_allow_html=True)

def parse_and_display_quiz(raw_quiz: str):
sections = raw_quiz.split(”—SECTION_BREAK—”)

```
section_configs = [
    ("أسئلة الاختيار من متعدد", "🔵"),
    ("أسئلة صح وخطأ", "🟢"),
    ("الأسئلة المقالية القصيرة", "📝"),
]

for i, section_text in enumerate(sections):
    section_text = section_text.strip()
    if not section_text:
        continue

    title, icon = section_configs[i] if i < len(section_configs) else (f"القسم {i+1}", "📌")

    # Split questions from answers for the expander trick
    # Strategy: show questions, hide answers in expander
    lines = section_text.split("\n")
    question_lines = []
    answer_lines = []

    for line in lines:
        low = line.lower()
        if any(k in line for k in ["الإجابة الصحيحة", "الإجابة:", "الجواب:", "صح", "خطأ", "نموذج الإجابة"]):
            answer_lines.append(line)
        else:
            question_lines.append(line)

    questions_md = "\n".join(question_lines)
    answers_md = "\n".join(answer_lines) if answer_lines else "الإجابات مضمنة في النص أعلاه."

    with st.container():
        st.markdown(f"""
        <div class="quiz-card">
            <div class="section-title">{icon} {title}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(questions_md)

        with st.expander("🔓 اظهار الإجابات النموذجية (بعد الحل فقط!)"):
            st.markdown(f"**الإجابات:**\n\n{answers_md}")

        st.divider()
```

# ─────────────────────────────────────────────

# Sidebar

# ─────────────────────────────────────────────

with st.sidebar:
st.markdown(”## 🧠 AI Quiz Generator”)
st.markdown(”—”)

```
st.markdown("### 🔑 إعدادات Gemini API")
api_key = st.text_input(
    "أدخل مفتاح Gemini API",
    type="password",
    placeholder="AIza...",
    help="مفتاحك آمن ولا يُحفظ",
)
with st.expander("كيف أحصل على مفتاح API؟"):
    st.markdown("""
```

1. اذهب إلى [Google AI Studio](https://aistudio.google.com/)
1. سجّل الدخول بحساب Google
1. اضغط **“Get API Key”**
1. انسخ المفتاح والصقه هنا
   “””)
   
   st.markdown(”—”)
   st.markdown(”### 📂 رفع الملف”)
   uploaded_file = st.file_uploader(
   “اختر ملف PDF أو TXT”,
   type=[“pdf”, “txt”],
   help=“الحد الأقصى: 10 ميجابايت”,
   )
   
   st.markdown(”—”)
   quiz_lang = st.selectbox(“🌐 لغة الاختبار”, [“العربية”, “English”, “Bilingual”])
   num_mcq = st.slider(“عدد أسئلة الاختيار من متعدد”, 3, 10, 5)
   generate_btn = st.button(“✨ إنشاء الاختبار”)
   
   st.markdown(”—”)
   st.markdown(”<small style='color:#555'>Powered by Gemini 1.5 Flash</small>”, unsafe_allow_html=True)

# ─────────────────────────────────────────────

# Main Area

# ─────────────────────────────────────────────

st.markdown(”””

<h1 style='text-align:center; color:#7c85f5; margin-bottom:4px;'>
    🎓 مولّد الاختبارات بالذكاء الاصطناعي
</h1>
<p style='text-align:center; color:#888; font-size:1.05rem;'>
    ارفع ملفك الدراسي واحصل على اختبار احترافي في ثوانٍ
</p>
<hr style='border-color:#2e3250; margin: 14px 0 28px 0;'>
""", unsafe_allow_html=True)

# ── Welcome cards ──

if not uploaded_file:
c1, c2, c3 = st.columns(3)
for col, icon, title, desc in [
(c1, “📄”, “ارفع ملفك”, “PDF أو TXT حتى 10 ميجابايت”),
(c2, “⚡”, “معالجة فورية”, “استخراج وتنظيف النص تلقائياً”),
(c3, “🎯”, “اختبار متكامل”, “MCQ + صح/خطأ + مقالي”),
]:
with col:
st.markdown(f”””
<div class="quiz-card" style="text-align:center;">
<div style="font-size:2.2rem;">{icon}</div>
<div style="font-weight:700; color:#7c85f5; margin:8px 0 4px;">{title}</div>
<div style="color:#888; font-size:.9rem;">{desc}</div>
</div>
“””, unsafe_allow_html=True)
st.info(“👈 ابدأ برفع ملفك من الشريط الجانبي وأدخل مفتاح Gemini API”)
st.stop()

# ── File uploaded ──

file_bytes = uploaded_file.read()
file_name = uploaded_file.name

st.markdown(f”**📎 الملف المرفوع:** `{file_name}` ({len(file_bytes)/1024:.1f} KB)”)

if generate_btn:
if not api_key:
st.error(“⛔ يرجى إدخال مفتاح Gemini API أولاً من الشريط الجانبي.”)
st.stop()

```
# ── Step 1: Extract text ──
progress = st.progress(0, text="⏳ جارٍ استخراج النص من الملف...")
time.sleep(0.3)

try:
    if file_name.endswith(".pdf"):
        raw_text = extract_text_from_pdf(file_bytes)
    else:
        raw_text = file_bytes.decode("utf-8", errors="ignore")

    if not raw_text.strip():
        st.error("❌ لم يتم استخراج أي نص من الملف. تأكد أن الملف يحتوي على نصوص قابلة للقراءة.")
        st.stop()

    progress.progress(30, text="🧹 جارٍ تنظيف النص...")
    time.sleep(0.3)
    clean = clean_text(raw_text)

except Exception as e:
    st.error(f"❌ خطأ في قراءة الملف: {e}")
    st.stop()

# ── Step 2: Call Gemini ──
progress.progress(55, text="🤖 Gemini يولّد الاختبار...")

try:
    quiz_text = generate_quiz(api_key, clean)
except Exception as e:
    err = str(e)
    if "API_KEY" in err.upper() or "invalid" in err.lower():
        st.error("🔑 مفتاح API غير صالح. تحقق من المفتاح وحاول مجدداً.")
    elif "quota" in err.lower():
        st.error("⚠️ تجاوزت حصة الاستخدام. انتظر قليلاً أو استخدم مفتاحاً آخر.")
    else:
        st.error(f"❌ خطأ من Gemini: {err}")
    st.stop()

progress.progress(90, text="🎨 جارٍ تنسيق الاختبار...")
time.sleep(0.4)
progress.progress(100, text="✅ اكتمل!")
time.sleep(0.5)
progress.empty()

st.success(f"✅ تم إنشاء الاختبار بنجاح من **{len(clean.split())} كلمة** مستخرجة!")

st.markdown("---")
st.markdown("""
<h2 style='color:#7c85f5; text-align:center;'>📋 الاختبار</h2>
""", unsafe_allow_html=True)

# Display parsed quiz
parse_and_display_quiz(quiz_text)

# Raw download
with st.expander("📥 تحميل الاختبار كنص خام"):
    st.text_area("نص الاختبار", quiz_text, height=300)
    st.download_button(
        label="⬇️ تحميل كملف TXT",
        data=quiz_text.encode("utf-8"),
        file_name="quiz_output.txt",
        mime="text/plain",
    )
```

else:
st.markdown(f”””
<div class="quiz-card" style="text-align:center; padding: 32px;">
<div style="font-size:3rem;">📄</div>
<div style="color:#7c85f5; font-weight:700; font-size:1.1rem; margin-top:10px;">
الملف جاهز: <code>{file_name}</code>
</div>
<div style="color:#888; margin-top:8px;">
اضغط <b>“✨ إنشاء الاختبار”</b> من الشريط الجانبي للبدء
</div>
</div>
“””, unsafe_allow_html=True)
