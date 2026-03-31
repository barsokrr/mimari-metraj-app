"""
Mimari Duvar Metraj Uygulaması - Profesyonel SaaS Sürümü
Geliştirici: Barış Öker - Fi-le Mimarlık & Yazılım
Özellik: Optimize Edilmiş Giriş Formu Yerleşimi
"""
import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os
from supabase import create_client

# --- VERİTABANI VE OTURUM AYARLARI ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Veritabanı anahtarları eksik! Lütfen Streamlit Secrets ayarlarını kontrol edin.")
    st.stop()

st.set_page_config(page_title="Duvar Metraj Pro", layout="wide", page_icon="🏗️")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""

# =============================================================================
# 🎨 PROFESYONEL CSS
# =============================================================================
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    
    .centered-title {
        text-align: center;
        margin-top: 10vh; /* Başlığı biraz aşağı indir */
        margin-bottom: 1rem;
        font-weight: 700;
    }
    
    /* Form Alanı Konteynırı */
    .login-form-container {
        max-width: 450px;
        margin: 0 auto;
        padding-top: 10px;
    }

    .st-emotion-cache-p5mtransition {
        font-size: 13px !important;
        font-weight: 500 !important;
    }
    
    .footer-fixed-section {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #0e1117;
        padding: 20px 5% 15px 5%;
        border-top: 1px solid #333;
        z-index: 999;
    }
    
    .copyright-text {
        text-align: center;
        color: #666;
        font-size: 11px;
        margin-top: 15px;
        line-height: 1.6;
    }
    
    .profile-card { text-align: center; padding: 1rem; background-color: #1e2130; border-radius: 12px; border: 1px solid #333; margin-bottom: 1.5rem; }
    .profile-img { border-radius: 50%; width: 90px; height: 90px; border: 3px solid #FF4B4B; margin-bottom: 0.5rem; }
    </style>
""", unsafe_allow_html=True)

# --- YARDIMCI FONKSİYONLAR ---
def get_user_data(email):
    email = email.lower().strip()
    response = supabase.table("users").select("*").eq("email", email).execute()
    if len(response.data) == 0:
        new_user = {"email": email, "credits": 0}
        supabase.table("users").insert(new_user).execute()
        return new_user
    return response.data[0]

def use_credit(email):
    user = get_user_data(email)
    if user["credits"] > 0:
        new_credits = user["credits"] - 1
        supabase.table("users").update({"credits": new_credits}).eq("email", email).execute()
        return True
    return False

# --- FOOTER ---
def show_footer():
    st.markdown('<div class="footer-fixed-section">', unsafe_allow_html=True)
    col_leg1, col_leg2, col_leg3 = st.columns(3)
    with col_leg1:
        with st.expander("🔐 Gizlilik ve KVKK"):
            st.write("Verileriniz 6698 sayılı KVKK uyarınca korunmaktadır.")
    with col_leg2:
        with st.expander("📜 Satış Sözleşmesi"):
            st.write("Dijital biletler anında ifa edilen hizmetlerdir.")
    with col_leg3:
        with st.expander("🔄 İade Politikası"):
            st.write("Dijital ürünlerde cayma hakkı bulunmamaktadır.")
    
    st.markdown("""
        <div class="copyright-text">
            © 2026 Fi-le Mimarlık & Yazılım. Tüm hakları saklıdır. <br>
            Destek: barsokrr@gmail.com | Bu uygulama mühendislik ön inceleme aracıdır.
        </div>
        </div>
    """, unsafe_allow_html=True)

# =============================================================================
# 1. GİRİŞ EKRANI (Yeni Yerleşim)
# =============================================================================
if not st.session_state.logged_in:
    st.markdown('<h1 class="centered-title">🏗️ İnşaat Metraj Sistemi Giriş</h1>', unsafe_allow_html=True)
    
    # Formu tam ortalamak için kolon yapısı
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="login-form-container">', unsafe_allow_html=True)
        email_input = st.text_input("E-posta Adresiniz", placeholder="ornek@mail.com")
        if st.button("Giriş Yap", use_container_width=True):
            if "@" in email_input and "." in email_input:
                user = get_user_data(email_input)
                st.session_state.user_email = user["email"]
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Lütfen geçerli bir e-posta adresi girin.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    show_footer()
    st.stop()

# =============================================================================
# 2. ANALİZ PANELI
# =============================================================================
user_info = get_user_data(st.session_state.user_email)
bilet_sayisi = user_info['credits']
has_credits = bilet_sayisi > 0

with st.sidebar:
    st.markdown(f"""
        <div class="profile-card">
            <img src="https://api.dicebear.com/7.x/bottts/svg?seed={st.session_state.user_email}" class="profile-img">
            <h4>{st.session_state.user_email.split('@')[0]}</h4>
            <p>🎫 {bilet_sayisi} Bilet</p>
        </div>
    """, unsafe_allow_html=True)
    st.divider()
    # Sidebar içerikleri...
    if st.button("🚪 Güvenli Çıkış", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.title("🏗️ Metraj Analiz Paneli")
# ... Analiz Motoru Kodları ...

show_footer()
