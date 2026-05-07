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
        page_title=config.get("app_name", "Northbrook Archives"),
        page_icon=".streamlit/static/favicon.png",
        layout="wide",
    )

    st.logo(".streamlit/static/logo.png")

    st.markdown(
        """
        <style>
        /* Sidebar: dark text on cream background (overrides global cream textColor) */
        [data-testid="stSidebar"], [data-testid="stSidebar"] * {
            color: #3A1F12 !important;
        }
        /* Widget labels (text_input, etc.) and subheaders use BaseWeb attributes
           that escape the wildcard above — force them dark explicitly. */
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] *,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] label *,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #3A1F12 !important;
            opacity: 1 !important;
        }
        [data-testid="stSidebar"] h1 {
            font-family: serif;
            border-bottom: 3px solid #D49729;
            padding-bottom: 0.3rem;
        }

        /* Logo: enlarge and center in the sidebar header */
        [data-testid="stSidebarHeader"], [data-testid="stLogoSpacer"] {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            padding: 1rem 0 !important;
            height: auto !important;
        }
        [data-testid="stLogo"], [data-testid="stSidebarHeader"] img {
            height: 140px !important;
            width: auto !important;
            max-width: 90% !important;
            margin: 0 auto !important;
            display: block !important;
        }

        /* Sidebar buttons: JP red with amber border */
        [data-testid="stSidebar"] button {
            background-color: #B8252A !important;
            color: #F2E2BD !important;
            border: 1px solid #D49729 !important;
            border-radius: 6px;
        }
        [data-testid="stSidebar"] button:hover {
            background-color: #D49729 !important;
            color: #1A0F0A !important;
        }
        [data-testid="stSidebar"] button * {
            color: inherit !important;
        }

        /* Chat bubbles: dark amber-bordered cards */
        [data-testid="stChatMessage"] {
            background-color: #2A1810;
            border: 1px solid #D49729;
            border-radius: 8px;
            padding: 0.75rem 1rem;
        }

        /* Headings: serif feel reinforced */
        h1, h2, h3 { font-family: serif; }

        /* Dividers: JP gold */
        hr { border-color: #D49729 !important; }

        /* Chat input bar: dark text on cream input so the user can see what they type */
        [data-testid="stChatInput"] textarea,
        [data-testid="stChatInput"] input,
        [data-testid="stChatInputTextArea"] textarea {
            color: #3A1F12 !important;
            caret-color: #B8252A !important;
        }
        [data-testid="stChatInput"] textarea::placeholder {
            color: #8A6A4A !important;
        }

        /* Assistant avatar: replace default robot with a dinosaur */
        [data-testid="stChatMessageAvatarAssistant"] > * {
            display: none !important;
        }
        [data-testid="stChatMessageAvatarAssistant"] {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 1.4rem;
            line-height: 1;
        }
        [data-testid="stChatMessageAvatarAssistant"]::before {
            content: "🦖";
        }
        </style>
        """,
        unsafe_allow_html=True,
    )