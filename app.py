"""
Mimari Metraj Uygulaması - v2.0
Özellikler: DXF Analiz, Görsel Plan Çizimi, Blok Sayımı ve Biletleme
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
    st.error("Veritabanı anahtarları eksik!")
    st.stop()

st.set_page_config(page_title="Duvar Metraj Pro", layout="wide", page_icon="🏗️")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""

# --- CSS VE TASARIM ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .centered-title { text-align: center; margin-top: 5vh !important; font-weight: 700; }
    .pushed-up-form { max-width: 400px; margin: -20px auto 0 auto !important; }
    .footer-fixed-section { position: fixed; left: 0; bottom: 0; width: 100%; background-color: #0e1117; padding: 20px 5% 15px 5%; border-top: 1px solid #333; z-index: 999; }
    .copyright-text { text-align: center; color: #666; font-size: 11px; margin-top: 10px; }
    .profile-card { text-align: center; padding: 1rem; background-color: #1e2130; border-radius: 12px; border: 1px solid #333; }
    .profile-img { border-radius: 50%; width: 80px; height: 80px; border: 2px solid #FF4B4B; margin-bottom: 0.5rem; }
    </style>
""", unsafe_allow_html=True)

# --- ANALİZ FONKSİYONLARI ---
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

def process_dxf(file_path, mode, layer_name="DUVAR", height=2.85):
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()
    fig, ax = plt.subplots(figsize=(10, 10))
    fig.patch.set_facecolor('#0e1117')
    ax.set_facecolor('#0e1117')
    
    # Tüm çizgileri görselleştirme için çiz
    for e in msp.query('LINE LWPOLYLINE'):
        color = 'white'
        if e.dxf.layer == layer_name: color = '#FF4B4B'
        
        if e.dxftype() == 'LINE':
            ax.plot([e.dxf.start.x, e.dxf.end.x], [e.dxf.start.y, e.dxf.end.y], color=color, linewidth=0.5)
        elif e.dxftype() == 'LWPOLYLINE':
            pts = e.get_points()
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, linewidth=0.5)

    ax.axis('off')
    
    # Metraj Hesaplama
    if mode == "🧱 Duvar Metrajı":
        entities = msp.query(f'*[layer=="{layer_name}"]')
        total_len = 0
        for e in entities:
            if e.dxftype() == 'LINE':
                total_len += math.sqrt((e.dxf.start.x - e.dxf.end.x)**2 + (e.dxf.start.y - e.dxf.end.y)**2)
            elif e.dxftype() == 'LWPOLYLINE':
                pts = e.get_points()
                for i in range(len(pts)-1):
                    total_len += math.sqrt((pts[i][0]-pts[i+1][0])**2 + (pts[i][1]-pts[i+1][1])**2)
        
        res = pd.DataFrame({"Analiz": ["Toplam Uzunluk", "Alan"], "Sonuç": [round(total_len, 2), round(total_len*height, 2)], "Birim": ["m", "m2"]})
    else:
        blocks = msp.query('INSERT')
        counts = {}
        for b in blocks: counts[b.dxf.name] = counts.get(b.dxf.name, 0) + 1
        res = pd.DataFrame(list(counts.items()), columns=["Blok Adı", "Adet"]).sort_values("Adet", ascending=False)
        
    return fig, res

# --- GİRİŞ EKRANI ---
if not st.session_state.logged_in:
    st.markdown('<h1 class="centered-title">🏗️ Duvar Metraj Sistemi Giriş</h1>', unsafe_allow_html=True)
    st.markdown('<div class="pushed-up-form">', unsafe_allow_html=True)
    email_input = st.text_input("E-posta Adresiniz", placeholder="ornek@mail.com")
    if st.button("Giriş Yap", use_container_width=True):
        if "@" in email_input:
            user = get_user_data(email_input)
            st.session_state.user_email = user["email"]; st.session_state.logged_in = True; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    # Footer Expanders...
    st.stop()

# --- ANALİZ PANELİ ---
user_info = get_user_data(st.session_state.user_email)
with st.sidebar:
    st.markdown(f'<div class="profile-card"><h4>{st.session_state.user_email}</h4><p>🎫 {user_info["credits"]} Bilet</p></div>', unsafe_allow_html=True)
    st.divider()
    if user_info['credits'] > 0:
        uploaded = st.file_uploader("📁 DXF Yükle", type=["dxf"])
        mode = st.selectbox("🎯 Analiz Tipi", ["🧱 Duvar Metrajı", "🚪 Kapı/Pencere Sayımı"])
        l_name = st.text_input("🧱 Katman", value="DUVAR") if mode == "🧱 Duvar Metrajı" else "DUVAR"
        h = st.number_input("📏 Yükseklik", value=2.85)
    else:
        st.link_button("💳 Bilet Al (200 TL)", "https://paytr.com/link-buraya")
        uploaded = None
    if st.button("🚪 Çıkış"): st.session_state.logged_in = False; st.rerun()

st.title("🏗️ Metraj Analiz Paneli")
if uploaded:
    if st.button("📥 Analizi Başlat (1 Bilet)", type="primary"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            tmp.write(uploaded.getvalue()); tmp_path = tmp.name
        
        if use_credit(st.session_state.user_email):
            fig, results = process_dxf(tmp_path, mode, l_name, h)
            st.balloons()
            col1, col2 = st.columns([2, 1])
            with col1: st.pyplot(fig) # PLAN GÖRSELİ BURADA GELİYOR
            with col2: st.subheader("📊 Sonuçlar"); st.table(results)
            os.remove(tmp_path)
