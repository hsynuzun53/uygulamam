import streamlit as st
import hashlib
from database import get_db

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_user(username, password):
    conn = get_db()
    c = conn.cursor()
    hashed_pw = hash_password(password)
    c.execute("SELECT id, is_admin FROM users WHERE username = ? AND password = ?",
             (username, hashed_pw))
    result = c.fetchone()
    conn.close()
    return result

def init_session_state():
    if 'remember_me' not in st.session_state:
        st.session_state.remember_me = False
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    
    if st.session_state.remember_me and not st.session_state.logged_in:
        st.session_state.logged_in = True

def check_auth():
    return st.session_state.logged_in

def login_page():
    st.title("KALE SOSYAL TESİSİ STOK TAKİP SİSTEMİ")

    with st.form("login_form"):
        username = st.text_input("Kullanıcı Adı")
        password = st.text_input("Şifre", type="password")
        remember_me = st.checkbox("Oturumu Açık Tut")
        submitted = st.form_submit_button("Giriş Yap")

        if submitted:
            result = login_user(username, password)
            if result:
                user_id, is_admin = result
                st.session_state.logged_in = True
                st.session_state.user_id = user_id
                st.session_state.is_admin = bool(is_admin)
                st.session_state.username = username
                st.session_state.remember_me = remember_me
                st.success("Giriş başarılı!")
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")

def logout():
    if not st.session_state.remember_me:
        for key in ['logged_in', 'user_id', 'is_admin', 'remember_me', 'username']:
            if key in st.session_state:
                del st.session_state[key]
    else:
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.is_admin = False
        st.session_state.username = None
    st.rerun()
