"""
Mimari Duvar Metraj Uygulaması - SaaS Sürümü
Geliştirici: Barış Öker - Fi-le Yazılım 
Sürüm: 4.0 - Supabase & Jeton Sistemi Entegre
"""
import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os
from supabase import create_client

# =============================================================================
# VERİTABANI BAĞLANTISI (SUPABASE)
# =============================================================================
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Veritabanı bağlantı anahtarları eksik! Lütfen secrets.toml dosyasını kontrol edin.")
    st.stop()

# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================
def get_user_data(email):
    """Kullanıcıyı sorgular, yoksa oluşturur."""
    email = email.lower().strip()
    response = supabase.table("users").select("*").eq("email", email).execute()
    
    if len(response.data) == 0:
        # Yeni kullanıcı kaydı (0 jetonla başlar)
        new_user = {"email": email, "credits": 0}
        supabase.table("users").insert(new_user).execute()
        return new_user
    return response.data[0]

def use_credit(email):
    """Kullanıcının 1 jetonunu düşer."""
    current_credits = get_user_data(email)["credits"]
    if current_credits > 0:
        new_credits = current_credits - 1
        supabase.table("users").update({"credits": new_credits}).eq("email", email).execute()
        return True
    return False

# =============================================================================
# SAYFA KONFİGÜRASYONU
# =============================================================================
st.set_page_config(page_title="Duvar Metraj Pro", layout="wide")

st.markdown("""
    <style>
    .profile-card { text-align: center; padding: 1rem; background-color: #262730; border-radius: 10px; margin-bottom: 1rem; }
    .profile-img { border-radius: 50%; width: 80px; height: 80px; border: 3px solid #FF4B4B; margin-bottom: 0.5rem; }
    .stButton>button { border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# GİRİŞ VE JETON KONTROL EKRANI
# =============================================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""

if not st.session_state.logged_in:
    st.title("🏗️ Duvar Metraj Sistemi")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.info("Sisteme erişmek için e-posta adresinizi girin.")
        email_input = st.text_input("E-posta Adresiniz", placeholder="ornek@mail.com")
        
        if st.button("Giriş Yap ve Kontrol Et", use_container_width=True):
            if "@" in email_input and "." in email_input:
                user = get_user_data(email_input)
                st.session_state.user_email = user["email"]
                
                if user["credits"] > 0:
                    st.success(f"Giriş Başarılı! Mevcut biletiniz: {user['credits']} adet.")
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.warning("Kullanım hakkınız (biletiniz) bulunmuyor. Lütfen devam etmek için 1 adet kullanım hakkı alın.")
                    # BURAYA PAYTR ÖDEME LİNKİ GELECEK
                    st.link_button("💳 1 Kullanım Hakkı Al (99 TL)", "https://paytr.com/odeme-linki-ornegi", use_container_width=True)
            else:
                st.error("Lütfen geçerli bir e-posta adresi girin.")
    st.stop()

# =============================================================================
# SIDEBAR
# =============================================================================
user_info = get_user_data(st.session_state.user_email)

with st.sidebar:
    st.markdown(f"""
        <div class="profile-card">
            <img src="https://api.dicebear.com/7.x/bottts/svg?seed={st.session_state.user_email}" class="profile-img">
            <h4 style="color: white; margin: 0;">{st.session_state.user_email.split('@')[0]}</h4>
            <p style="color: #FF4B4B; margin: 0; font-weight: bold;">Bilet Sayısı: {user_info['credits']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    uploaded = st.file_uploader("📁 DXF Dosyası Yükle", type=["dxf"])
    katman_secimi = st.text_input("🧱 Duvar Katmanı", value="DUVAR")
    kat_yuksekligi = st.number_input("📏 Kat Yüksekliği (m)", value=2.85, step=0.01)
    birim = st.selectbox("📐 Çizim Birimi", ["cm", "mm", "m"], index=0)
    
    st.divider()
    if st.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()

# =============================================================================
# ANA UYGULAMA
# =============================================================================
st.title("🏗️ Duvar Metraj Analizi")

if uploaded is None:
    st.info(f"Hoş geldiniz **{st.session_state.user_email}**. Başlamak için sol menüden DXF dosyanızı yükleyin. İşlemi tamamladığınızda 1 biletiniz düşülecektir.")
    st.stop()

# DXF İŞLEME VE ANALİZ (Senin Mevcut Kodun)
try:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = tmp.name
    
    doc = ezdxf.readfile(tmp_path)
    birim_carpani = {"mm": 1000.0, "cm": 100.0, "m": 1.0}.get(birim, 100.0)
    hedef_katman = katman_secimi.strip().upper()
    
    total_length = 0.0
    entity_count = 0
    
    for entity in doc.modelspace():
        try:
            layer = getattr(entity.dxf, 'layer', '').upper()
            if hedef_katman not in layer: continue
            dtype = entity.dxftype()
            if dtype == "LINE":
                s, e = entity.dxf.start, entity.dxf.end
                total_length += math.sqrt((e[0]-s[0])**2 + (e[1]-s[1])**2)
                entity_count += 1
            elif dtype == "LWPOLYLINE":
                pts = list(entity.get_points('xy'))
                for i in range(len(pts)-1):
                    total_length += math.sqrt((pts[i+1][0]-pts[i][0])**2 + (pts[i+1][1]-pts[i][1])**2)
                entity_count += 1
        except: continue

    aks_uzunluk = (total_length / 2.0) / birim_carpani 
    toplam_alan = aks_uzunluk * kat_yuksekligi
    
    # SONUÇ GÖSTERİMİ
    st.subheader("📊 Analiz Önizleme")
    c1, c2, c3 = st.columns(3)
    c1.metric("Objeler", f"{entity_count} adet")
    c2.metric("Aks Uzunluğu", f"{aks_uzunluk:.2f} m")
    c3.metric("Toplam Alan", f"{toplam_alan:.2f} m²")

    # ÇİZİM GÖRSELLEŞTİRME
    fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0e1117')
    ax.set_facecolor('#0e1117')
    for entity in doc.modelspace():
        try:
            color = "#333333"; lw = 0.5
            if hedef_katman in getattr(entity.dxf, 'layer', '').upper():
                color = "#FF4B4B"; lw = 2.0
            if entity.dxftype() == "LINE":
                s, e = entity.dxf.start, entity.dxf.end
                ax.plot([s[0], e[0]], [s[1], e[1]], color=color, lw=lw)
            elif entity.dxftype() == "LWPOLYLINE":
                pts = list(entity.get_points('xy'))
                xs, ys = zip(*pts)
                ax.plot(xs, ys, color=color, lw=lw)
        except: continue
    ax.set_aspect('equal'); ax.axis('off')
    st.pyplot(fig)

    # JETON HARCAMA VE İNDİRME
    st.divider()
    st.warning("⚠️ Raporu indirmek biletinizden 1 kullanım hakkı düşecektir.")
    
    if st.button("✅ Analizi Onayla ve Raporu Al", use_container_width=True):
        if use_credit(st.session_state.user_email):
            st.balloons()
            csv = f"Katman,Aks_Uzunluk_m,Kat_Yuksekligi_m,Toplam_Alan_m2\n{katman_secimi},{aks_uzunluk:.2f},{kat_yuksekligi},{toplam_alan:.2f}"
            st.download_button("📥 Raporu (CSV) İndir", csv, f"rapor_{uploaded.name}.csv", use_container_width=True)
            st.success("İşlem başarılı! 1 bilet kullanıldı. Yeni analiz için sayfayı yenileyebilirsiniz.")
        else:
            st.error("Yetersiz bilet! Lütfen yeni bilet alın.")

    os.remove(tmp_path)

except Exception as e:
    st.error(f"❌ Hata: {str(e)}")
