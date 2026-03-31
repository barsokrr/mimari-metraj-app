"""
Mimari Duvar Metraj Uygulaması - Profesyonel SaaS Sürümü
Geliştirici: Barış Öker - Fi-le Mimarlık & Yazılım
Özellik: Zorlanmış Yukarı Hizalama (Z-Index ve Margin-Top)
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
# 🎨 ÖZEL CSS (FORMU YUKARI ÇEKME)
# =============================================================================
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    
    .centered-title {
        text-align: center;
        margin-top: 5vh !important; /* Başlığı daha yukarı aldım */
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
        font-weight: 700;
    }
    
    /* FORMU YUKARI ZORLAYAN KUTU */
    .pushed-up-form {
        max-width: 400px;
        margin: -40px auto 0 auto !important; /* Negatif margin ile yukarı çektim */
        padding: 0px !important;
    }

    .st-emotion-cache-p5mtransition {
        font-size: 13px !important;
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
        margin-top: 10px;
    }

    .profile-card { text-align: center; padding: 1rem; background-color: #1e2130; border-radius: 12px; border: 1px solid #333; }
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
    
    st.markdown(f"""
        <div class="copyright-text">
            © 2026 Fi-le Mimarlık & Yazılım. Tüm hakları saklıdır. <br>
            Destek: barsokrr@gmail.com | Bu uygulama mühendislik ön inceleme aracıdır.
        </div>
        </div>
    """, unsafe_allow_html=True)

# =============================================================================
# 1. GİRİŞ EKRANI
# =============================================================================
if not st.session_state.logged_in:
    # Başlık
    st.markdown('<h1 class="centered-title">🏗️ İnşaat Metraj Sistemi Giriş</h1>', unsafe_allow_html=True)
    
    # Formu yukarı çeken özel div sarmalayıcı
    st.markdown('<div class="pushed-up-form">', unsafe_allow_html=True)
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
# 2. ANALİZ PANELI (Dashboard)
# =============================================================================
# Giriş sonrası içerik buraya gelecek
st.title("🏗️ Metraj Analiz Paneli")
st.info(f"Hoş geldiniz {st.session_state.user_email}")

if st.sidebar.button("🚪 Çıkış"):
    st.session_state.logged_in = False
    st.rerun()

show_footer()
