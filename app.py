import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
import json
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

# -----------------
# Load Backend Config
# -----------------
load_dotenv()
BACKEND_API_KEY = os.getenv("GEMINI_API_KEY")

# -----------------
# App Configuration
# -----------------
st.set_page_config(page_title="AI Smart Study Buddy", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

# -----------------
# Database Logic (Persistence)
# -----------------
DB_FILE = "users_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

GROUPS_DB_FILE = "groups_db.json"
UPLOADS_DIR = "uploads"

if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

def load_groups():
    if os.path.exists(GROUPS_DB_FILE):
        with open(GROUPS_DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_groups(data):
    with open(GROUPS_DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

GLOBAL_NOTES_DB = "global_notes_db.json"

def load_global_notes():
    if os.path.exists(GLOBAL_NOTES_DB):
        with open(GLOBAL_NOTES_DB, "r") as f:
            return json.load(f)
    return []

def save_global_notes(data):
    with open(GLOBAL_NOTES_DB, "w") as f:
        json.dump(data, f, indent=4)

# -----------------
# Knowledge Cache (Bypass API Limits)
# -----------------
CACHE_FILE = "knowledge_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_to_cache(prompt, response):
    cache = load_cache()
    # Normalize prompt for better matching
    key = prompt.strip().lower()
    cache[key] = response
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=4)

def get_from_cache(prompt):
    cache = load_cache()
    return cache.get(prompt.strip().lower())

def login_user(email):
    db = load_db()
    if email not in db:
        return None
    
    user = db[email]
    if "username" not in user:
        user["username"] = email.split('@')[0]
    if "password" not in user:
        user["password"] = ""
    if "dob" not in user:
        user["dob"] = "2000-01-01"
        
    today_str = datetime.now().strftime("%Y-%m-%d")
    last_login_date = datetime.strptime(user["last_login"], "%Y-%m-%d")
    today_date = datetime.now()
    delta = (today_date.date() - last_login_date.date()).days
    
    # Streak logic
    if delta == 1:
        user["streak"] += 1
    elif delta > 1:
        user["streak"] = 1 # Reset if they missed a day
        
    user["last_login"] = today_str
    
    if "chat_history" not in user:
        user["chat_history"] = []
        
    save_db(db)
    return user

def register_user(email, username, password, dob):
    db = load_db()
    if email in db:
        return False
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    db[email] = {
        "username": username,
        "password": password,
        "dob": dob,
        "streak": 1, 
        "last_login": today_str, 
        "xp": 0, 
        "level": 1,
        "api_key": "",
        "chat_history": []
    }
    save_db(db)
    return db[email]

def update_chat_history(email, messages):
    db = load_db()
    if email in db:
        db[email]["chat_history"] = messages
        save_db(db)
        st.session_state.user_data = db[email]

def award_xp(email, amount=20):
    """Gives the user XP for studying. Levels up if XP hits 100"""
    db = load_db()
    if email in db:
        db[email]["xp"] += amount
        if db[email]["xp"] >= 100:
            db[email]["level"] += 1
            db[email]["xp"] -= 100
        save_db(db)
        # Immediately reflect in current session state
        st.session_state.user_data = db[email]

# -----------------
# Session State Init
# -----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "user_data" not in st.session_state:
    st.session_state.user_data = {}
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_group_id" not in st.session_state:
    st.session_state.current_group_id = None
if "theme" not in st.session_state:
    st.session_state.theme = "Dark"
if "api_key" not in st.session_state:
    st.session_state.api_key = "" # Fallback for legacy sessions

# -----------------
# Aggressive HTML/CSS Styling
# -----------------
# Stripped any hardcoded black/white font colors to guarantee full browser Dark/Light mode support.
dark_mode_css = """
    .stApp { background-color: #0b0f19; }
    section[data-testid="stSidebar"] { background-color: #111827 !important; border-right: 1px solid #1f2937 !important; }
    .gradient-text { background: linear-gradient(135deg, #60a5fa, #a78bfa, #38bdf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .glass-header { background: #1f2937; border-color: #374151; }
    .glass-header h2 { color: #f8fafc !important; }
    .glass-header p { color: #94a3b8 !important; }
    div[data-testid="stMetricValue"] { color: #60a5fa !important; }
    div[data-testid="stChatMessage"] { background-color: #1f2937; border-color: #374151; color: white !important;}
    .stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox select { background-color: #111827 !important; border-color: #374151 !important; color: white !important;}
    .highlight-name { color: #60a5fa; }
    p, li, span, label, .stMarkdown { color: #e2e8f0; }
    h1, h2, h3, h4, h5, h6 { color: #f8fafc !important; }
    div[data-testid="stMetricLabel"] { color: #94a3b8 !important; }
"""

light_mode_css = """
    .stApp { background-color: #f8fafc !important; }
    section[data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0 !important; }
    .gradient-text { background: linear-gradient(135deg, #1e3a8a, #3b82f6, #0ea5e9); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .glass-header { background: #ffffff !important; border-color: #e2e8f0 !important; }
    .glass-header h2 { color: #0f172a !important; }
    .glass-header p { color: #475569 !important; }
    div[data-testid="stMetricValue"] { color: #2563eb !important; }
    div[data-testid="stChatMessage"] { background-color: #ffffff !important; border-color: #e2e8f0 !important; color: #1e293b !important; }
    .stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox select { background-color: #ffffff !important; border-color: #cbd5e1 !important; color: #1e293b !important; }
    .highlight-name { color: #2563eb; }
    p, li, span, label, .stMarkdown { color: #1e293b !important; }
    h1, h2, h3, h4, h5, h6 { color: #0f172a !important; }
    div[data-testid="stMetricLabel"] { color: #475569 !important; }
"""

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Extreme Streamlit Hiding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {
        background-color: #f8fafc;
    }
    
    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 3rem !important;
        max-width: 1200px !important;
    }

    /* Refined Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0 !important;
        box-shadow: 2px 0 10px rgba(0,0,0,0.02);
    }
    
    /* Metrics */
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #1e40af !important;
        letter-spacing: -0.5px;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 1rem !important;
        font-weight: 600 !important;
        color: #64748b !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Headers & Typography */
    .gradient-text {
        background: linear-gradient(135deg, #0f172a, #1e3a8a, #3b82f6);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3.5rem !important;
        letter-spacing: -0.03em;
        margin-bottom: 0px;
    }

    /* Cards */
    .glass-header {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 24px 32px;
        border-left: 6px solid #3b82f6;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        margin-bottom: 28px;
    }
    
    .glass-header h2 {
        color: #0f172a !important;
        font-weight: 700 !important;
        margin-bottom: 8px !important;
        font-size: 1.8rem !important;
    }
    
    .glass-header p {
        color: #64748b !important;
        font-size: 1.1rem !important;
    }

    /* Professional Buttons */
    div.stButton > button {
        background-color: #2563eb !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        letter-spacing: 0.2px;
        padding: 0.6em 1.8em !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.2) !important;
    }
    
    div.stButton > button:hover {
        background-color: #1d4ed8 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 8px -1px rgba(59, 130, 246, 0.3) !important;
    }
    
    /* Clean Inputs */
    .stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox select {
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: #ffffff !important;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03) !important;
        transition: all 0.2s ease !important;
        font-size: 14.5px !important;
        padding: 0.5rem 0.75rem !important;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus, .stSelectbox select:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
    }

    /* Subdued text highlight */
    .highlight-name {
        color: #1d4ed8;
        font-weight: 700;
    }
    
    /* Chat bubbles styling */
    div[data-testid="stChatMessage"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    
</style>
""", unsafe_allow_html=True)

if st.session_state.theme == "Dark":
    st.markdown(f"<style>{dark_mode_css}</style>", unsafe_allow_html=True)
else:
    st.markdown(f"<style>{light_mode_css}</style>", unsafe_allow_html=True)

# -----------------
# Main Header
# -----------------
col1, col2 = st.columns([1, 11])
with col1:
    st.markdown("<h1 style='text-align: center; font-size: 3.5rem; margin-top: -10px;'>🎓</h1>", unsafe_allow_html=True)
with col2:
    st.markdown("<h1 class='gradient-text'>Smart Study Buddy</h1>", unsafe_allow_html=True)
    if st.session_state.logged_in:
        st.markdown(f"<p style='font-size:1.1rem; color: #64748b; font-weight: 500; margin-top: -5px;'>Welcome back, <span class='highlight-name'>{st.session_state.user_email.split('@')[0].capitalize()}</span></p>", unsafe_allow_html=True)
    else:
        st.markdown("<p style='font-size:1.1rem; color: #64748b; font-weight: 500; margin-top: -5px;'>Your elite AI tutoring dashboard.</p>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------
# Auth Wall
# -----------------
if not st.session_state.logged_in:
    with st.sidebar:
        st.markdown("<h2 style='text-align: center; margin-top: 10px;'>🔒 Access Portal</h2>", unsafe_allow_html=True)
        
        tab_login, tab_signup, tab_forgot = st.tabs(["Log In", "Sign Up", "Forgot Password"])
        
        with tab_login:
            login_email = st.text_input("✉️ Email Address", key="login_email").strip().lower()
            login_pass = st.text_input("🔑 Password", type="password", key="login_pass")
            if st.button("Secure Login", type="primary", use_container_width=True):
                if login_email and login_pass:
                    user_data = login_user(login_email)
                    if user_data:
                        if user_data.get("password") == login_pass or user_data.get("password") == "":
                            st.session_state.logged_in = True
                            st.session_state.user_email = login_email
                            st.session_state.user_data = user_data
                            st.session_state.messages = user_data.get("chat_history", [])
                            st.rerun()
                        else:
                            st.error("Incorrect password.")
                    else:
                        st.error("Email not found. Please Sign Up.")
                else:
                    st.warning("Please provide email and password.")

        with tab_signup:
            signup_username = st.text_input("👤 Username", key="signup_user")
            signup_email = st.text_input("✉️ Email Address", key="signup_email").strip().lower()
            signup_pass = st.text_input("🔑 Password", type="password", key="signup_pass")
            signup_dob = st.date_input("🎂 Date of Birth", min_value=datetime(1900, 1, 1), max_value=datetime.now())
            if st.button("Create Account", type="primary", use_container_width=True):
                if signup_username and signup_email and signup_pass:
                    dob_str = signup_dob.strftime("%Y-%m-%d")
                    new_user = register_user(signup_email, signup_username, signup_pass, dob_str)
                    if new_user:
                        st.success("Account created! Please log in.")
                    else:
                        st.error("Email is already registered.")
                else:
                    st.warning("Please fill out all fields.")

        with tab_forgot:
            st.markdown("### Reset Password")
            forgot_email = st.text_input("✉️ Email Address", key="forgot_email").strip().lower()
            forgot_dob = st.date_input("🎂 Date of Birth (Verification)", min_value=datetime(1900, 1, 1), max_value=datetime.now(), key="forgot_dob")
            new_forgot_pass = st.text_input("🔑 New Password", type="password", key="new_forgot_pass")
            
            if st.button("Reset Password", type="primary", use_container_width=True, key="btn_forgot"):
                if forgot_email and new_forgot_pass:
                    db = load_db()
                    if forgot_email in db:
                        stored_dob = db[forgot_email].get("dob", "2000-01-01")
                        input_dob_str = forgot_dob.strftime("%Y-%m-%d")
                        if stored_dob == input_dob_str:
                            db[forgot_email]["password"] = new_forgot_pass
                            save_db(db)
                            st.success("✅ Password reset! You can now Log In.")
                        else:
                            st.error("Date of Birth does not match.")
                    else:
                        st.error("Email not found.")
                else:
                    st.warning("Please provide Email and New Password.")
                
        st.divider()
        st.info("ℹ️ Login is required to securely access your personal Study Buddy features.")
        
    with st.container(border=True):
        st.markdown("## 🔒 Authentication Required")
        st.markdown("Please use the sidebar to securely Log In or Sign Up to access the dashboard.")
    st.stop()

# -----------------
# Sidebar UI (Authenticated)
# -----------------
with st.sidebar:
    seed = st.session_state.user_email
    avatar_url = f"https://api.dicebear.com/9.x/avataaars/svg?seed={seed}&backgroundColor=transparent"
    display_name = st.session_state.user_email.split("@")[0].replace(".", " ").title()

    st.markdown(f"""
    <div style='text-align: center; margin-bottom: 24px; margin-top: -10px;'>
        <img src='{avatar_url}' width='100' height='100' style='background: #f1f5f9; border-radius: 50%; object-fit: cover; border: 2px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);'>
        <h3 style='margin-top: 12px; margin-bottom: 2px; font-weight: 600;'>{display_name}</h3>
        <p style='color: #64748b; font-size: 12px; font-weight: 500; letter-spacing: 0.5px;'>VERIFIED SCHOLAR</p>
    </div>
    """, unsafe_allow_html=True)
    
    streak = st.session_state.user_data["streak"]
    level = st.session_state.user_data["level"]
    xp = st.session_state.user_data["xp"]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📈 Streak", f"{streak} Days")
    with col2:
        st.metric("🏅 Rank", f"Lvl {level}", f"XP: {xp}/100")

    if st.button("🔓 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.session_state.user_data = {}
        st.session_state.messages = []
        st.rerun()

    # 🔐 API Key Management
    user_data = st.session_state.user_data
    
    # Priority: Backend (.env) > User Profile > Session State
    current_api_key = BACKEND_API_KEY or user_data.get("api_key") or st.session_state.api_key
    
    if not BACKEND_API_KEY:
        st.markdown("### 🔐 AI Engine Key")
        new_key = st.text_input("Gemini API Key", value=current_api_key, type="password", help="Get your key from https://aistudio.google.com/app/apikey")
        
        if new_key != current_api_key:
            db = load_db()
            db[st.session_state.user_email]["api_key"] = new_key
            save_db(db)
            st.session_state.user_data = db[st.session_state.user_email]
            st.session_state.api_key = new_key
            st.success("✅ Key Saved!")
            st.rerun()

        if st.button("🔌 Test Connection", use_container_width=True):
            if not new_key:
                st.error("Please enter an API Key first.")
            else:
                with st.spinner("Testing connection..."):
                    try:
                        genai.configure(api_key=new_key)
                        genai.list_models()
                        st.success("✅ Connection Successful!")
                    except Exception as e:
                        st.error(f"❌ Connection Failed: {e}")
        st.divider()
    else:
        # Key is in backend, just store it in session for consistency
        st.session_state.api_key = BACKEND_API_KEY
        st.sidebar.success("📡 AI Engine: Backend Connected")
        st.divider()
    
    st.markdown("### ⚙️ Configuration")
    
    theme_choice = st.radio("Interface Theme", ["Dark", "Light"], index=0 if st.session_state.theme == "Dark" else 1, horizontal=True)
    if theme_choice != st.session_state.theme:
        st.session_state.theme = theme_choice
        st.rerun()
        
    subject = st.selectbox(
        "Choose Your Universe", 
        ["Computer Science", "DBMS", "Operating Systems", "Java", "Data Structures", "Python", "Mathematics", "Physics"]
    )
    
    tutor_persona = st.selectbox(
        "🧠 AI Brain Persona",
        [
            "Strict Academic Professor", 
            "Friendly & Supportive Mentor", 
            "Socratic (Asks guiding questions)", 
            "Explain it like I am 5 years old"
        ]
    )
    
    st.markdown("### 📋 Operations")
    feature = st.radio(
        "Launch Protocol", 
        [
            "💬 Concept Chat", 
            "📝 AI Quiz Generator", 
            "📅 Smart Study Planner", 
            "🎓 Exam Accelerator",
            "🗄️ Chat Archives",
            "👥 Study Groups",
            "📚 Global Shared Notes",
            "⚙️ Profile Settings"
        ],
        key="feature_selector",
        label_visibility="collapsed"
    )

# -----------------
# Main Logic (Authenticated)
# -----------------
SYSTEM_PROMPT = f"You are a helpful AI study assistant specializing in {subject}. Explain concepts simply with examples and help students learn effectively."

@st.cache_resource
def get_best_available_model(api_key):
    try:
        genai.configure(api_key=api_key)
        # Fetch all available models that support content generation
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        # Updated Priority List for 2026 Models
        for preferred in ['models/gemini-flash-latest', 'models/gemini-2.5-flash-lite', 'models/gemini-1.5-flash', 'models/gemini-pro-latest', 'models/gemini-pro']:
            if preferred in available_models:
                return preferred
        
        # Fallback to the first available if none of our preferred ones match
        if available_models:
            return available_models[0]
            
        return "models/gemini-pro"
    except Exception as e:
        # Final fallback string
        return "models/gemini-pro"

import time

def get_ai_response(prompt_text, include_history=False):
    # 1. CHECK CACHE FIRST (Bypass limits)
    cached_res = get_from_cache(prompt_text)
    if cached_res:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧠 Knowledge Cache Hit! Bypassing API.")
        return cached_res

    # Priority: Backend > user_data > session_state
    key = BACKEND_API_KEY or st.session_state.user_data.get("api_key") or st.session_state.api_key
    if not key:
        st.error("🔑 **Authentication Required**: Please enter your Gemini API key in the Sidebar.")
        st.stop()
    
    genai.configure(api_key=key)
    generation_config = {"temperature": 0.5, "top_p": 0.9}
    
    max_retries = 3
    retry_delay = 2 # Initial delay in seconds
    
    for attempt in range(max_retries):
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] API Call Attempt {attempt + 1}...")
            best_model = get_best_available_model(key)
            
            model = genai.GenerativeModel(
                model_name=best_model,
                generation_config=generation_config,
                system_instruction=SYSTEM_PROMPT
            )
            
            if include_history and len(st.session_state.messages) > 0:
                gemini_history = []
                # OPTIMIZATION: Limit context to last 10 messages to stay within Token Limits
                history_subset = st.session_state.messages[-10:]
                for msg in history_subset:
                    role = "model" if msg["role"] == "assistant" else "user"
                    gemini_history.append({"role": role, "parts": [msg["content"]]})
                    
                chat = model.start_chat(history=gemini_history)
                response = chat.send_message(prompt_text)
                award_xp(st.session_state.user_email, 20) 
                
                # Save to cache for future use
                save_to_cache(prompt_text, response.text)
                return response.text
            else:
                response = model.generate_content(prompt_text)
                award_xp(st.session_state.user_email, 20) 
                
                # Save to cache
                save_to_cache(prompt_text, response.text)
                return response.text
                
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "resource_exhausted" in error_msg or "quota" in error_msg:
                if attempt < max_retries - 1:
                    st.warning(f"⚠️ **Rate Limit Hit**: Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2 
                else:
                    st.error("⚠️ **API Quota Reached**: Your current API key has hit its limit. Please update your `.env` file with a new key and restart the app.")
                    # Still provide a fallback so the UI doesn't look empty
                    return "I've hit my temporary knowledge limit for this key. Please wait a moment or update my configuration!"
            else:
                st.error(f"⚠️ **Technical Glitch**: {e}")
                return None

# -----------------
# Feature Handlers
# -----------------

if feature == "💬 Concept Chat":
    st.markdown("<div class='glass-header'><h2>💬 Interactive Concept Deep-Dive</h2><p style='margin:0;'>Chat live with the smartest logical AI tutor available.</p></div>", unsafe_allow_html=True)
    
    chat_container = st.container(height=400, border=False)
    
    with chat_container:
        if len(st.session_state.messages) == 0:
            st.markdown(f"<br><p style='text-align:center;'>No messages yet. Ask a question below to start chatting with the <b>{tutor_persona}</b>!</p>", unsafe_allow_html=True)
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input(f"Ask your doubt about {subject}..."):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.session_state.messages.append({"role": "user", "content": prompt, "timestamp": timestamp})
        update_chat_history(st.session_state.user_email, st.session_state.messages)
        
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing parameters..."):
                    answer = get_ai_response(prompt, include_history=True)
                    if answer:
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer, "timestamp": timestamp})
                        update_chat_history(st.session_state.user_email, st.session_state.messages)
                        
    col1, col2, col3 = st.columns([1,1,1])
    with col3:
        if st.button("🔄 Wipe Memory Engine"):
            st.session_state.messages = []
            update_chat_history(st.session_state.user_email, [])
            st.rerun()

elif feature == "📝 AI Quiz Generator":
    st.markdown("<div class='glass-header'><h2>🎯 Advanced AI Quiz Generator</h2><p style='margin:0;'>Generate impossible (or easy) quizzes using AI to test your boundaries.</p></div>", unsafe_allow_html=True)
    
    with st.form("quiz_form", border=False):
        topic = st.text_input("📍 Target Topic:", placeholder="E.g., B-Trees, Quantum Mechanics, Machine Learning")
        col1, col2 = st.columns(2)
        with col1:
            difficulty = st.selectbox("📊 Difficulty Level", ["Easy", "Medium", "Hard", "Nightmare"])
        with col2:
            question_count = st.slider("🔢 Question Count", min_value=3, max_value=15, value=5)
            
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("▶️ Initialize Quiz Generation", type="primary", use_container_width=True)
        
    if submitted:
        if topic:
            query = f"Generate a highly professional {difficulty} level quiz with {question_count} conceptual questions on the topic: '{topic}' in {subject}. Break it into a visually pleasing format. Provide the absolute correct answers hidden at the very bottom with solid reasoning."
            with st.spinner("Compiling neural pathways..."):
                quiz_content = get_ai_response(query)
                if quiz_content:
                    st.success("✅ Assessment compiled successfully. (+20 XP)")
                    with st.container(border=True):
                        st.markdown(quiz_content)
        else:
            st.warning("A Target Topic is required.")

elif feature == "📅 Smart Study Planner":
    st.markdown("<div class='glass-header'><h2>📅 AI Study Workflow Architect</h2><p style='margin:0;'>Calculate an optimized, day-by-day roadmap tailored exactly to your timeline.</p></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        duration = st.number_input("⏳ Days Remaining", min_value=1, max_value=60, value=14)
    with col2:
        time_per_day = st.number_input("⏰ Hours Per Day Available", min_value=1, max_value=16, value=4)
        
    focus_areas = st.text_area("🎯 High-Priority Concepts (Optional):", placeholder="E.g., Focus mainly on Matrix Multiplication and Vectors...")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⚙️ Synthesize Roadmap", type="primary", use_container_width=True):
        query = f"Act as an elite productivity architect. Create a highly structured {duration}-day study plan for {subject}, assuming {time_per_day} hours of study per day."
        if focus_areas:
            query += f" Ensure heavy emphasis on these specific areas: {focus_areas}."
        query += " Break down the tasks day-by-day, include specific subtopics, allocate time for practice and revision, and format it using beautiful markdown tables and emojis."
        
        with st.spinner("Processing timeframe..."):
            plan_content = get_ai_response(query)
            if plan_content:
                st.balloons()
                st.success("✅ Custom Roadmap Deployed. (+20 XP)")
                with st.container(border=True):
                    st.markdown(plan_content)

elif feature == "🎓 Exam Accelerator":
    st.markdown("<div class='glass-header'><h2>📈 High-Yield Exam Accelerator</h2><p style='margin:0;'>Extract maximum value. Paste your syllabus and get instant core notes and predicted questions.</p></div>", unsafe_allow_html=True)
    
    exam_topic = st.text_area("📝 Paste syllabus snippet here:", placeholder="Unit 1, Unit 2...", height=150)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔍 Extract Knowledge", type="primary", use_container_width=True):
        if exam_topic:
            query = f"Act as a strict exam grader. Provide highly concise, bulleted revision notes and a list of 5 deeply conceptual/important exam questions that are highly likely to appear for the following syllabus/topics in {subject}: {exam_topic}"
            with st.spinner("Extracting critical vectors..."):
                material_content = get_ai_response(query)
                if material_content:
                    st.success("✅ Extraction Complete. (+20 XP)")
                    with st.container(border=True):
                        st.markdown(material_content)
        else:
            st.warning("Syllabus required for extraction.")

elif feature == "🗄️ Chat Archives":
    st.markdown("<div class='glass-header'><h2>🗄️ Master Chat Archives</h2><p style='margin:0;'>Review all your past conversations, notes, and interactions across all sessions.</p></div>", unsafe_allow_html=True)
    
    if len(st.session_state.messages) == 0:
        st.info("No chat history found. Start talking in the Concept Chat!")
    else:
        for i, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                if "timestamp" in msg:
                    st.markdown(f"<small style='color:#64748b; font-weight: 600;'>{msg['timestamp']}</small>", unsafe_allow_html=True)
                st.markdown(msg["content"])

elif feature == "👥 Study Groups":
    groups_db = load_groups()
    user_email = st.session_state.user_email
    
    if st.session_state.current_group_id is None:
        st.markdown("<div class='glass-header'><h2>👥 Study Groups Dashboard</h2><p style='margin:0;'>Join, create, and manage study groups.</p></div>", unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["📚 My Groups", "🌐 Public Groups", "➕ Create Group"])
        
        with tab1:
            my_groups = {g_id: g for g_id, g in groups_db.items() if user_email in g["members"]}
            if not my_groups:
                st.info("You haven't joined any groups yet. Go to 'Public Groups' to join one or 'Create Group' to make your own!")
            for g_id, g in my_groups.items():
                with st.container(border=True):
                    cols = st.columns([4, 1])
                    with cols[0]:
                        st.markdown(f"<h3 style='color: #60a5fa; margin-bottom: 0px;'>{g['name']}</h3>", unsafe_allow_html=True)
                        st.markdown(f"<p style='color: #94a3b8; font-weight: 500; margin-bottom: 5px;'>📚 Subject: {g['subject']}</p>", unsafe_allow_html=True)
                        privacy = "🌐 Public" if g['is_public'] else "🔒 Private"
                        st.markdown(f"<span style='background:#1e293b; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; color: #e2e8f0;'>👥 {len(g['members'])} Members &nbsp;|&nbsp; {privacy}</span>", unsafe_allow_html=True)
                    with cols[1]:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Enter Group ➔", key=f"enter_{g_id}", type="primary", use_container_width=True):
                            st.session_state.current_group_id = g_id
                            st.rerun()
                            
        with tab2:
            public_groups = {g_id: g for g_id, g in groups_db.items() if g["is_public"] and user_email not in g["members"]}
            if not public_groups:
                st.info("No public groups available to join right now.")
            for g_id, g in public_groups.items():
                with st.container(border=True):
                    cols = st.columns([4, 1])
                    with cols[0]:
                        st.markdown(f"<h3 style='color: #a78bfa; margin-bottom: 0px;'>{g['name']}</h3>", unsafe_allow_html=True)
                        st.markdown(f"<p style='color: #94a3b8; font-weight: 500; margin-bottom: 5px;'>📚 Subject: {g['subject']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<span style='background:#1e293b; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; color: #e2e8f0;'>👥 {len(g['members'])} Members &nbsp;|&nbsp; 👤 Creator: {g['creator'].split('@')[0]}</span>", unsafe_allow_html=True)
                    with cols[1]:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Join Group ➕", key=f"join_{g_id}", type="primary", use_container_width=True):
                            groups_db[g_id]["members"].append(user_email)
                            save_groups(groups_db)
                            st.session_state.current_group_id = g_id
                            st.rerun()
                            
        with tab3:
            with st.form("create_group_form"):
                new_group_name = st.text_input("Group Name", placeholder="e.g. CS 101 Study Squad")
                new_group_subject = st.text_input("Subject", placeholder="e.g. Data Structures")
                is_public = st.checkbox("Public Group (Anyone can join)", value=True)
                
                if st.form_submit_button("Create Group"):
                    if new_group_name and new_group_subject:
                        new_g_id = "group_" + datetime.now().strftime("%Y%m%d%H%M%S")
                        groups_db[new_g_id] = {
                            "name": new_group_name,
                            "subject": new_group_subject,
                            "creator": user_email,
                            "is_public": is_public,
                            "members": [user_email],
                            "messages": [],
                            "notes": []
                        }
                        save_groups(groups_db)
                        st.success(f"Group '{new_group_name}' created!")
                        st.session_state.current_group_id = new_g_id
                        st.rerun()
                    else:
                        st.error("Please fill out both Name and Subject.")
                        
    else:
        g_id = st.session_state.current_group_id
        if g_id not in groups_db or user_email not in groups_db[g_id]["members"]:
            st.session_state.current_group_id = None
            st.rerun()
            
        group = groups_db[g_id]
        
        if st.button("⬅️ Back to Dashboard"):
            st.session_state.current_group_id = None
            st.rerun()
            
        st.markdown(f"<div class='glass-header'><h2>{group['name']}</h2><p style='margin:0;'>{group['subject']} | {'Public' if group['is_public'] else 'Private'} | {len(group['members'])} Members</p></div>", unsafe_allow_html=True)
        
        g_tabs = st.tabs(["💬 Chat", "📚 Notes", "⚙️ Manage"])
        
        with g_tabs[0]:
            chat_container = st.container(height=400, border=False)
            with chat_container:
                if len(group["messages"]) == 0:
                    st.info("No messages yet. Say hello!")
                for msg in group["messages"]:
                    sender = msg.get("sender", "Unknown")
                    role = "user" if sender == user_email else "assistant"
                    with st.chat_message(role):
                        st.markdown(f"**{sender.split('@')[0]}** <span style='font-size:0.8em;color:gray;'>{msg.get('timestamp', '')}</span>", unsafe_allow_html=True)
                        st.markdown(msg["content"])

            if prompt := st.chat_input("Say something to the group..."):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                new_msg = {
                    "sender": user_email,
                    "content": prompt,
                    "timestamp": timestamp
                }
                groups_db[g_id]["messages"].append(new_msg)
                save_groups(groups_db)
                st.rerun()
                
            if st.button("🔄 Refresh Chat", use_container_width=True):
                st.rerun()
                
        with g_tabs[1]:
            st.markdown("<div style='background: linear-gradient(90deg, #1e3a8a, #3b82f6); padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center;'><h3 style='color: white; margin: 0;'>📚 Shared Notes Vault</h3><p style='color: #e0f2fe; margin: 0; font-size: 14px;'>Upload documents here. Anyone in the group can read and download them.</p></div>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader("Drop a new file here to share with the group:", type=["pdf", "txt", "md", "png", "jpg"])
            if uploaded_file is not None:
                if st.button("Save Note to Group"):
                    group_dir = os.path.join(UPLOADS_DIR, g_id)
                    if not os.path.exists(group_dir):
                        os.makedirs(group_dir)
                    
                    file_path = os.path.join(group_dir, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    note_meta = {
                        "filename": uploaded_file.name,
                        "path": file_path,
                        "uploaded_by": user_email,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    groups_db[g_id]["notes"].append(note_meta)
                    save_groups(groups_db)
                    st.success("File uploaded successfully!")
                    st.rerun()
                    
            st.divider()
            if len(group["notes"]) == 0:
                st.info("No notes uploaded yet.")
            else:
                for note in reversed(group["notes"]):
                    with st.container(border=True):
                        cols = st.columns([4, 1])
                        with cols[0]:
                            st.markdown(f"<h4 style='color: #38bdf8; margin-bottom: 2px;'>📄 {note['filename']}</h4>", unsafe_allow_html=True)
                            st.markdown(f"<p style='color: #94a3b8; font-size: 13px; margin: 0;'>Shared by <b>{note['uploaded_by'].split('@')[0]}</b> &bull; {note['timestamp']}</p>", unsafe_allow_html=True)
                        with cols[1]:
                            st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
                            if os.path.exists(note["path"]):
                                with open(note["path"], "rb") as f:
                                    st.download_button(
                                        label="⬇️ Download",
                                        data=f,
                                        file_name=note["filename"],
                                        key=f"dl_{note['timestamp']}_{note['filename']}",
                                        use_container_width=True
                                    )
                            else:
                                st.error("File missing")

        with g_tabs[2]:
            st.markdown("### Group Settings")
            st.write(f"**Creator:** {group['creator']}")
            st.write(f"**Status:** {'Public' if group['is_public'] else 'Private'}")
            
            st.markdown("**Current Members:**")
            for m in group['members']:
                st.markdown(f"- {m}")
                
            if user_email == group["creator"]:
                st.divider()
                st.markdown("**Add Member (Email)**")
                with st.form("add_member_form"):
                    new_member_email = st.text_input("Enter Email Address").strip().lower()
                    if st.form_submit_button("Add Member"):
                        if new_member_email and "@" in new_member_email:
                            if new_member_email not in group["members"]:
                                groups_db[g_id]["members"].append(new_member_email)
                                save_groups(groups_db)
                                st.success(f"Added {new_member_email}!")
                                st.rerun()
                            else:
                                st.warning("User is already a member.")
                        else:
                            st.error("Please enter a valid email.")

elif feature == "📚 Global Shared Notes":
    st.markdown("<div class='glass-header'><h2>📚 Global Shared Notes</h2><p style='margin:0;'>A public repository to upload and download study materials for everyone.</p></div>", unsafe_allow_html=True)
    
    global_notes = load_global_notes()
    user_email = st.session_state.user_email
    
    st.markdown("<div style='background: linear-gradient(90deg, #10b981, #059669); padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center;'><h3 style='color: white; margin: 0;'>☁️ Public Upload Zone</h3><p style='color: #d1fae5; margin: 0; font-size: 14px;'>Drop a file here to share it globally with all students across all subjects.</p></div>", unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Upload a public document", type=["pdf", "txt", "md", "png", "jpg"], key="global_uploader")
    if uploaded_file is not None:
        if st.button("Share Globally", type="primary"):
            global_dir = os.path.join(UPLOADS_DIR, "global")
            if not os.path.exists(global_dir):
                os.makedirs(global_dir)
            
            file_path = os.path.join(global_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            note_meta = {
                "filename": uploaded_file.name,
                "path": file_path,
                "uploaded_by": user_email,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            global_notes.append(note_meta)
            save_global_notes(global_notes)
            st.success("File shared globally!")
            st.rerun()
            
    st.divider()
    if len(global_notes) == 0:
        st.info("No global notes have been shared yet. Be the first!")
    else:
        for note in reversed(global_notes):
            with st.container(border=True):
                cols = st.columns([4, 1])
                with cols[0]:
                    st.markdown(f"<h4 style='color: #10b981; margin-bottom: 2px;'>📄 {note['filename']}</h4>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color: #94a3b8; font-size: 13px; margin: 0;'>Shared by <b>{note['uploaded_by'].split('@')[0]}</b> &bull; {note['timestamp']}</p>", unsafe_allow_html=True)
                with cols[1]:
                    st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
                    if os.path.exists(note["path"]):
                        with open(note["path"], "rb") as f:
                            st.download_button(
                                label="⬇️ Download",
                                data=f,
                                file_name=note["filename"],
                                key=f"global_dl_{note['timestamp']}_{note['filename']}",
                                use_container_width=True
                            )
                    else:
                        st.error("File missing")

elif feature == "⚙️ Profile Settings":
    st.markdown("<div class='glass-header'><h2>⚙️ Profile Settings</h2><p style='margin:0;'>Manage your account details and authentication credentials.</p></div>", unsafe_allow_html=True)
    
    user_email = st.session_state.user_email
    user_data = st.session_state.user_data
    
    # API Key is now handled exclusively via the backend (.env file) as per requirements.

    with st.container(border=True):
        st.markdown("### 👤 Update Profile")
        with st.form("profile_settings_form"):
            new_username = st.text_input("Username", value=user_data.get("username", user_email.split("@")[0]))
            new_email = st.text_input("Email Address", value=user_email).strip().lower()
            new_password = st.text_input("New Password (leave blank to keep current)", type="password")
            
            # Parse existing DOB or default
            dob_str = user_data.get("dob", "2000-01-01")
            try:
                current_dob = datetime.strptime(dob_str, "%Y-%m-%d")
            except:
                current_dob = datetime(2000, 1, 1)
                
            new_dob = st.date_input("Date of Birth", value=current_dob, min_value=datetime(1900, 1, 1), max_value=datetime.now())
            
            if st.form_submit_button("💾 Save Changes", type="primary"):
                db = load_db()
                
                # Check if email is being changed
                if new_email != user_email:
                    if new_email in db:
                        st.error("This email address is already taken by another account.")
                        st.stop()
                    else:
                        # Email Migration Logic
                        # 1. Move user data to new email key
                        db[new_email] = db.pop(user_email)
                        
                        # 2. Update Groups DB
                        groups = load_groups()
                        for g_id, g in groups.items():
                            if g["creator"] == user_email:
                                g["creator"] = new_email
                            if user_email in g["members"]:
                                g["members"] = [new_email if m == user_email else m for m in g["members"]]
                            for msg in g["messages"]:
                                if msg.get("sender") == user_email:
                                    msg["sender"] = new_email
                            for note in g["notes"]:
                                if note.get("uploaded_by") == user_email:
                                    note["uploaded_by"] = new_email
                        save_groups(groups)
                        
                        # 3. Update Global Notes DB
                        global_notes = load_global_notes()
                        for note in global_notes:
                            if note.get("uploaded_by") == user_email:
                                note["uploaded_by"] = new_email
                        save_global_notes(global_notes)
                        
                        # Update current tracking variables
                        user_email = new_email
                        st.session_state.user_email = new_email
                
                # Update other fields
                db[user_email]["username"] = new_username
                if new_password:
                    db[user_email]["password"] = new_password
                st.success("✅ Profile updated successfully!")
                st.rerun()
