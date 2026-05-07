"""
branding.py -- Student-owned customization file.

Customize your app's appearance here. The instructor will NEVER modify this file.
Your changes survive all future git pulls.
"""
import streamlit as st


def apply_branding(config: dict) -> None:
    """Apply branding to the Streamlit app.

    Customize this function to personalize your app's appearance.

    Args:
        config: Dict from student_config.yaml with app_name, tagline, etc.
    """
    # IMPORTANT: st.set_page_config() MUST be the first st.* call in the app.
    # Do not add any st.write(), st.markdown(), etc. above this line.
    st.set_page_config(
        page_title=config.get("app_name", "Falcon Logistics"),
        page_icon="🦅",
        layout="wide",
    )

    st.sidebar.image(".streamlit/static/logo.png", use_container_width=True)

    st.markdown("""
    <style>
    [data-testid="stSidebar"] * {
        color: #E0E0E0 !important;
    }
    [data-testid="stSidebar"] img {
        border-radius: 10px;
        margin-bottom: 0.5rem;
    }
    [data-testid="stSidebar"] .stButton > button {
        color: #E0E0E0 !important;
        border-color: #555 !important;
    }
    [data-testid="stSidebar"] input {
        color: #1a1a1a !important;
        caret-color: #1a1a1a !important;
    }
    [data-testid="stSidebar"] [data-testid="tooltipIcon"] svg {
        fill: #E0E0E0 !important;
        color: #E0E0E0 !important;
    }
    [data-testid="stSidebar"] [data-testid="stPasswordInput"] button svg {
        fill: #E0E0E0 !important;
        color: #E0E0E0 !important;
    }
    [data-testid="stChatInput"] textarea {
        color: #F2F2F2 !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: #AAAAAA !important;
        opacity: 1;
    }
    </style>
    """, unsafe_allow_html=True)
