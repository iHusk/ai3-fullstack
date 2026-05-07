"""
Northbrook Q&A -- Streamlit Chat Application

Session 2.1: Build a stateful chat application with RAG integration.

This is your starter template. The structure is complete. Your job:
  1. Initialize session state for messages, conversations, and current chat (Step 1)
  2. Implement the chat input handler (Step 5)

Steps 2 (sidebar), 3 (display), and 4 (source display) are provided.
The RAG pipeline is handled by app/rag.py (instructor-managed).

Run with: streamlit run app/main.py
"""

import sys
from pathlib import Path

# Streamlit adds the script's directory (app/) to sys.path, not the project
# root. This fix ensures package imports like `from app.branding` resolve
# correctly regardless of where `streamlit run` is invoked from.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# pysqlite3 shim — required for ChromaDB on Streamlit Community Cloud.
# Community Cloud's system sqlite3 is older than ChromaDB requires.
# pysqlite3-binary ships a newer sqlite3; we swap it in before chromadb imports.
# Local Mac dev skips this gracefully (pysqlite3 not installed).
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import os
import uuid

import streamlit as st
import yaml
from dotenv import load_dotenv

from app.branding import apply_branding
from app.feedback import get_feedback_summary, submit_feedback
from app.rag import get_response

load_dotenv(_PROJECT_ROOT / ".env")

# ============================================================
# LOAD CONFIG & APPLY BRANDING
# st.set_page_config() is inside apply_branding() and MUST be
# the first st.* call — keep this block above everything else.
# ============================================================
with open(_PROJECT_ROOT / "student_config.yaml") as f:
    config = yaml.safe_load(f)

apply_branding(config)

# Keys loaded from .env at top of file via load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY") or not os.getenv("VOYAGE_API_KEY"):
    st.error("ANTHROPIC_API_KEY and VOYAGE_API_KEY must be set in your .env file.")
    st.stop()

# Initialize Phoenix tracing ONCE per session
if "phoenix_initialized" not in st.session_state:
    try:
        from phoenix.otel import register
        register(
            project_name=os.getenv("PHOENIX_PROJECT_NAME", "ai3"),
            auto_instrument=True,
        )
    except Exception:
        pass
    st.session_state.phoenix_initialized = True

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# ============================================================
# STEP 1: Initialize Session State
# ============================================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversations" not in st.session_state:
    st.session_state.conversations = {}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = None

if st.session_state.current_chat is None:
    chat_id = "chat_0"
    st.session_state.current_chat = chat_id
    st.session_state.conversations[chat_id] = []
# ============================================================


# ============================================================
# STEP 2: Sidebar — Chat History (PROVIDED — do not modify)
# ============================================================
# Safety net: ensure session state keys exist even if Step 1 is not yet
# implemented. Once you complete Step 1, these lines are redundant.
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversations" not in st.session_state:
    st.session_state.conversations = {}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "chat_0"
    st.session_state.conversations["chat_0"] = []

with st.sidebar:
    st.title(config.get("app_name", "Northbrook Q&A"))
    st.caption(config.get("tagline", "Ask questions about Northbrook Partners"))

    if st.button("+ New Chat", use_container_width=True):
        chat_id = f"chat_{len(st.session_state.conversations)}"
        st.session_state.current_chat = chat_id
        st.session_state.messages = []
        st.session_state.conversations[chat_id] = []
        st.rerun()

    st.divider()

    for chat_id, msgs in st.session_state.conversations.items():
        if msgs:
            label = next(
                (m["content"][:30] + "..." for m in msgs if m["role"] == "user"),
                "New Chat",
            )
        else:
            label = "Empty Chat"

        if st.button(label, key=chat_id, use_container_width=True):
            # Save current conversation before switching
            if st.session_state.current_chat:
                st.session_state.conversations[st.session_state.current_chat] = (
                    st.session_state.messages.copy()
                )
            st.session_state.current_chat = chat_id
            st.session_state.messages = msgs.copy()
            st.rerun()

    st.divider()
    msg_count = len(st.session_state.get("messages", []))
    st.write(f"Messages: {msg_count}")

    summary = get_feedback_summary()
    if summary["total"] > 0:
        st.write(
            f"Feedback: {summary['positive']} :thumbsup: / "
            f"{summary['negative']} :thumbsdown:"
        )

    if st.button("Clear Chat"):
        st.session_state.messages = []
        if st.session_state.current_chat:
            st.session_state.conversations[st.session_state.current_chat] = []
        st.rerun()


# ============================================================
# STEP 3: Display Chat History (PROVIDED — do not modify)
# ============================================================
# Show welcome message if no messages yet
if not st.session_state.get("messages"):
    welcome = config.get(
        "welcome_message",
        "Hello! Ask me anything about Northbrook Partners.",
    )
    with st.chat_message("assistant"):
        st.markdown(welcome)

# Feedback callbacks
def _save_feedback(index):
    feedback_value = st.session_state[f"fb_{index}"]
    st.session_state.messages[index]["feedback"] = feedback_value
    span_id = st.session_state.messages[index].get("span_id", "")
    if span_id:
        submit_feedback(span_id, feedback_value)
    st.session_state.conversations[st.session_state.current_chat] = (
        st.session_state.messages.copy()
    )
    st.toast("Thanks for the positive feedback!" if feedback_value == 1
             else "Thanks — you can add details below.")


def _save_feedback_note(index):
    note = st.session_state.get(f"note_{index}", "")
    if not note:
        return
    span_id = st.session_state.messages[index].get("span_id", "")
    if span_id:
        submit_feedback(span_id, 0, note=note)
    st.session_state.messages[index]["feedback_note"] = note
    st.session_state.conversations[st.session_state.current_chat] = (
        st.session_state.messages.copy()
    )
    st.toast("Detailed feedback submitted!")


def render_feedback(index):
    message     = st.session_state.messages[index]
    existing_fb = message.get("feedback", None)
    st.session_state[f"fb_{index}"] = existing_fb
    st.feedback(
        "thumbs",
        key=f"fb_{index}",
        disabled=existing_fb is not None,
        on_change=_save_feedback,
        args=[index],
    )
    if existing_fb == 0 and not message.get("feedback_note"):
        st.text_input(
            "What went wrong?",
            key=f"note_{index}",
            placeholder="Help us improve (press Enter to submit)",
            on_change=_save_feedback_note,
            args=[index],
        )
    elif message.get("feedback_note"):
        st.caption(f"Your note: _{message['feedback_note']}_")


# Display all previous messages
for i, message in enumerate(st.session_state.get("messages", [])):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_feedback(i)


# ============================================================
# STEP 4: Source Display Helper
# ============================================================
def display_sources(sources: list[dict], original_query: str = "", rewritten_query: str = ""):
    """Show pipeline details and retrieved sources in collapsible expanders."""
    from app.rag import STRATEGY_NAME

    _STRATEGY_LABELS = {
        "naive": "Naive semantic search",
        "rrf":   "Reciprocal Rank Fusion (naive + enriched)",
        "hyde":  "HyDE (Hypothetical Document Embeddings)",
    }
    strategy_label = _STRATEGY_LABELS.get(STRATEGY_NAME, STRATEGY_NAME)
    query_was_rewritten = bool(rewritten_query and rewritten_query != original_query)

    with st.expander("Pipeline Details", expanded=False):
        st.markdown("**Input**")
        if query_was_rewritten:
            st.markdown(f"- Query rewrite (contextualize): **on**")
            st.caption(f"Original: _{original_query}_")
            st.caption(f"Rewritten: _{rewritten_query}_")
        else:
            st.markdown(f"- Query rewrite (contextualize): off — query used as-is")
        st.markdown(f"- Retrieval strategy: **{strategy_label}** · {len(sources)} chunks retrieved")

        st.markdown("**Output**")
        st.markdown("- Context assembly: **on** — chunks grouped by source, sorted by chunk index")
        st.markdown("- Input safety validation: **on** — override / roleplay / extraction patterns checked")
        st.markdown("- Output safety validation: **on** — prompt leakage and credential patterns checked")

    if sources:
        # Group chunks by source document for a cleaner display
        grouped: dict[str, list[dict]] = {}
        for src in sources:
            doc = src["metadata"].get("source", "Unknown")
            grouped.setdefault(doc, []).append(src)

        with st.expander(f"Sources — {len(grouped)} document(s), {len(sources)} chunk(s)", expanded=False):
            for doc_name, chunks in grouped.items():
                st.markdown(f"**{doc_name}**")
                for chunk in chunks:
                    score = chunk.get("score", 0.0)
                    chunk_idx = chunk["metadata"].get("chunk_index", "?")
                    rrf_src = chunk.get("rrf_sources", "")
                    meta_parts = [f"chunk {chunk_idx}", f"relevance {score:.3f}"]
                    if rrf_src and rrf_src != "naive":
                        meta_parts.append(f"fused via {rrf_src}")
                    st.caption(" · ".join(meta_parts))
                    snippet = chunk["text"][:350]
                    if len(chunk["text"]) > 350:
                        snippet += "…"
                    st.markdown(f"> {snippet}")
                st.divider()
    else:
        st.caption("No sources retrieved — answer drawn from model knowledge only.")


# ============================================================
# STEP 5: Chat Input Handler
# ============================================================
if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        from openinference.instrumentation import using_attributes
        with using_attributes(
            session_id=st.session_state.session_id,
            user_id="student",
            tags=["streamlit"],
        ):
            response = get_response(prompt, st.session_state.messages)
    except ImportError:
        response = get_response(prompt, st.session_state.messages)

    st.session_state.messages.append({
        "role":    "assistant",
        "content": response.answer,
        "span_id": response.span_id,
    })
    st.session_state.conversations[st.session_state.current_chat] = (
        st.session_state.messages.copy()
    )

    with st.chat_message("assistant"):
        st.markdown(response.answer)
        display_sources(response.sources, original_query=prompt, rewritten_query=response.rewritten_query)
        render_feedback(len(st.session_state.messages) - 1)
# ============================================================
