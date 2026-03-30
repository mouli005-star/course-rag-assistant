import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import streamlit as st

from app import Advisor
from config import get_openai_api_key


BASE_DIR = Path(__file__).resolve().parent
CHAT_STORE_PATH = BASE_DIR / "data" / "chat_sessions.json"


st.set_page_config(
    page_title="Cisco College Advisor",
    page_icon="C",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def utc_now():
    return datetime.utcnow().isoformat(timespec="seconds")


def load_chat_store():
    if not CHAT_STORE_PATH.exists():
        return []
    try:
        return json.loads(CHAT_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_chat_store(chat_sessions):
    CHAT_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHAT_STORE_PATH.write_text(json.dumps(chat_sessions, indent=2), encoding="utf-8")


def create_chat_session():
    return {
        "id": str(uuid4()),
        "title": "New chat",
        "history": [],
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }


def shorten_title(text):
    words = " ".join(str(text or "").split()).split()
    if not words:
        return "New chat"
    return " ".join(words[:6])[:50]


def bootstrap_state():
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = load_chat_store()

    if not st.session_state.chat_sessions:
        session = create_chat_session()
        st.session_state.chat_sessions = [session]
        save_chat_store(st.session_state.chat_sessions)

    if "active_chat_id" not in st.session_state:
        st.session_state.active_chat_id = st.session_state.chat_sessions[0]["id"]


def get_active_session():
    for session in st.session_state.chat_sessions:
        if session["id"] == st.session_state.active_chat_id:
            return session

    session = st.session_state.chat_sessions[0]
    st.session_state.active_chat_id = session["id"]
    return session


def create_new_chat():
    session = create_chat_session()
    st.session_state.chat_sessions.insert(0, session)
    st.session_state.active_chat_id = session["id"]
    save_chat_store(st.session_state.chat_sessions)


def build_advisor():
    return Advisor()


def has_openai_key_configured():
    return bool(get_openai_api_key(required=False))


def submit_question(question):
    session = get_active_session()
    advisor = build_advisor()
    response = advisor.handle(question)
    session["history"].append({"user": question, "assistant": response})
    if session["title"] == "New chat":
        session["title"] = shorten_title(question)
    session["updated_at"] = utc_now()
    save_chat_store(st.session_state.chat_sessions)
    return response


SECTION_HEADERS = [
    "Answer / Plan:",
    "Why (requirements/prereqs satisfied):",
    "Citations:",
    "Clarifying questions (if needed):",
    "Assumptions / Not in catalog:",
]


def parse_response_sections(text):
    sections = {}
    current_header = None
    buffer = []

    for line in str(text or "").splitlines():
        stripped = line.strip()
        if stripped in SECTION_HEADERS:
            if current_header is not None:
                sections[current_header] = "\n".join(buffer).strip()
            current_header = stripped
            buffer = []
            continue
        buffer.append(line)

    if current_header is not None:
        sections[current_header] = "\n".join(buffer).strip()

    return sections


def has_meaningful_section(value):
    cleaned = " ".join(str(value or "").replace("-", " ").split()).strip().lower()
    return bool(cleaned and cleaned not in {"none", "none."})


def render_assistant_response(text):
    sections = parse_response_sections(text)
    answer = sections.get("Answer / Plan:", text).strip()
    why = sections.get("Why (requirements/prereqs satisfied):", "").strip()
    citations = sections.get("Citations:", "").strip()
    clarifying = sections.get("Clarifying questions (if needed):", "").strip()
    assumptions = sections.get("Assumptions / Not in catalog:", "").strip()

    st.markdown(f"<div class='assistant-copy'>{answer.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

    if why:
        with st.expander("Why this answer", expanded=False):
            st.markdown(why.replace("\n", "  \n"))

    if citations:
        st.markdown("<div class='section-label'>Citations</div>", unsafe_allow_html=True)
        st.markdown(citations.replace("\n", "  \n"))

    if has_meaningful_section(clarifying):
        with st.expander("Clarifying questions", expanded=False):
            st.markdown(clarifying.replace("\n", "  \n"))

    if has_meaningful_section(assumptions):
        with st.expander("Assumptions / Not in catalog", expanded=False):
            st.markdown(assumptions.replace("\n", "  \n"))


def inject_styles():
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            display: none;
        }
        [data-testid="collapsedControl"] {
            display: none;
        }
        .stApp {
            background:
                radial-gradient(circle at top, rgba(60, 68, 90, 0.18), transparent 24%),
                linear-gradient(180deg, #1a1b1f 0%, #17181c 100%);
            color: #f3f4f6;
        }
        .block-container {
            max-width: 1120px;
            padding-top: 1.4rem;
            padding-bottom: 8rem;
        }
        .app-shell {
            min-height: calc(100vh - 10rem);
            display: flex;
            flex-direction: column;
        }
        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        .brand {
            font-size: 1.1rem;
            font-weight: 700;
            letter-spacing: 0.01em;
        }
        .brand-subtitle {
            color: #a4a9b3;
            font-size: 0.96rem;
            margin-top: 0.25rem;
        }
        .welcome-shell {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 4rem 1rem 6rem 1rem;
        }
        .welcome-shell h1 {
            font-size: 2.6rem;
            font-weight: 600;
            margin-bottom: 0.7rem;
        }
        .welcome-shell p {
            max-width: 720px;
            color: #9ea4ae;
            font-size: 1.06rem;
            line-height: 1.7;
            margin: 0 auto;
        }
        .chat-thread {
            padding-bottom: 2rem;
        }
        div[data-testid="stChatMessage"] {
            background: transparent;
            margin-bottom: 0.6rem;
        }
        div[data-testid="stChatMessageContent"] {
            max-width: 860px;
        }
        div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] {
            margin-left: auto;
        }
        div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stMarkdownContainer"] {
            background: linear-gradient(180deg, #343841 0%, #2c3038 100%);
            border: 1px solid #454b56;
            border-radius: 24px 24px 10px 24px;
            padding: 0.95rem 1.05rem;
            box-shadow: 0 14px 28px rgba(0, 0, 0, 0.14);
        }
        div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] {
            background: linear-gradient(180deg, #1f2229 0%, #1a1d23 100%);
            border: 1px solid #2f333b;
            border-radius: 24px 24px 24px 10px;
            padding: 1rem 1.1rem;
            box-shadow: 0 18px 34px rgba(0, 0, 0, 0.2);
        }
        div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
        div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
            font-size: 1.03rem;
            line-height: 1.72;
        }
        .assistant-copy {
            font-size: 1.03rem;
            line-height: 1.76;
        }
        .section-label {
            color: #cfd4dd;
            font-size: 0.95rem;
            font-weight: 700;
            margin-top: 1rem;
            margin-bottom: 0.35rem;
        }
        [data-testid="stExpander"] {
            border: 1px solid #2f343d;
            border-radius: 16px;
            background: rgba(20, 22, 27, 0.82);
            margin-top: 0.85rem;
        }
        [data-testid="stExpander"] details summary p {
            font-size: 0.95rem;
            font-weight: 600;
        }
        [data-testid="stChatInput"] {
            position: fixed;
            left: 50%;
            bottom: 1.2rem;
            transform: translateX(-50%);
            width: min(780px, calc(100vw - 6rem));
            background: transparent;
            padding-top: 0;
            border-top: none;
            z-index: 10;
        }
        [data-testid="stChatInput"] > div {
            background: transparent;
            border: none;
            box-shadow: none;
        }
        [data-testid="stChatInput"] textarea {
            background: rgba(36, 38, 44, 0.98);
            border: 1px solid #424854;
            border-radius: 28px;
            padding-top: 0.7rem;
            padding-bottom: 0.7rem;
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.2);
        }
        [data-testid="stChatInput"] button {
            border-radius: 999px;
        }
        .new-chat-row {
            display: flex;
            justify-content: flex-end;
        }
        .stButton button {
            border-radius: 999px;
            border: 1px solid #3b414d;
            background: rgba(31, 34, 40, 0.9);
            color: #f3f4f6;
        }
        .thinking {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            color: #bcc2cb;
            font-size: 0.96rem;
        }
        .thinking span {
            width: 0.45rem;
            height: 0.45rem;
            border-radius: 50%;
            background: #cfd4dd;
            display: inline-block;
            animation: pulse 1.2s infinite ease-in-out;
        }
        .thinking span:nth-child(2) {
            animation-delay: 0.2s;
        }
        .thinking span:nth-child(3) {
            animation-delay: 0.4s;
        }
        @keyframes pulse {
            0%, 80%, 100% { opacity: 0.25; transform: scale(0.9); }
            40% { opacity: 1; transform: scale(1.05); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


bootstrap_state()
active_session = get_active_session()
inject_styles()
has_openai_key = has_openai_key_configured()

st.markdown("<div class='app-shell'>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="topbar">
        <div>
            <div class="brand">Cisco College Catalog Advisor</div>
            <div class="brand-subtitle">Catalog-grounded answers with citations from the uploaded PDF.</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

top_controls = st.columns([1, 0.16])
with top_controls[1]:
    if st.button("New chat", use_container_width=True):
        create_new_chat()
        st.rerun()

if not has_openai_key:
    st.warning(
        "OpenAI API key is missing. Add your key before starting chat."
    )
    st.markdown(
        "Add this to the project root .env file and restart Streamlit:"
    )
    st.code("OPENAI_API_KEY=your_key_here", language="bash")
    st.caption("File location: .env (project root)")

history = active_session.get("history", [])
if not history:
    st.markdown(
        """
        <div class="welcome-shell">
            <div>
                <h1>Ready when you are.</h1>
                <p>Ask about course descriptions, prerequisites, transfer credit, policies, or next-term planning. Responses are grounded in the Cisco catalog and cite the PDF page numbers used.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown("<div class='chat-thread'>", unsafe_allow_html=True)
    for chat in history:
        with st.chat_message("user"):
            st.markdown(chat["user"])
        with st.chat_message("assistant"):
            render_assistant_response(chat["assistant"])
    st.markdown("</div>", unsafe_allow_html=True)

question = st.chat_input(
    "Ask about the Cisco catalog" if has_openai_key else "Add OPENAI_API_KEY in .env to begin",
    disabled=not has_openai_key,
)
if question:
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        thinking_placeholder = st.empty()
        thinking_placeholder.markdown(
            "<div class='thinking'><span></span><span></span><span></span>Searching the catalog</div>",
            unsafe_allow_html=True,
        )
        response = submit_question(question)
        thinking_placeholder.empty()
        render_assistant_response(response)

st.markdown("</div>", unsafe_allow_html=True)
