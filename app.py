"""
Mimari Duvar Metraj Uygulaması - Profesyonel SaaS Sürümü
Geliştirici: Barış Öker - Fi-le Yazılım 
Özellik: Giriş Ekranında Yasal Metinler + Temiz Arayüz
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
# VERİTABANI VE OTURUM AYARLARI
# =============================================================================
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Veritabanı anahtarları eksik! Lütfen Streamlit Secrets ayarlarını kontrol edin.")
    st.stop()

# Sayfa Konfigürasyonu
st.set_page_config(page_title="Duvar Metraj Pro", layout="wide", page_icon="🏗️")

# Oturum Değişkenleri
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""

# =============================================================================
# 🎨 PROFESYONEL CSS (Giriş Ekranı ve Footer Odaklı)
# =============================================================================
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .profile-card { text-align: center; padding: 1rem; background-color: #1e2130; border-radius: 12px; border: 1px solid #333; margin-bottom: 1.5rem; }
    .profile-img { border-radius: 50%; width: 90px; height: 90px; border: 3px solid #FF4B4B; margin-bottom: 0.5rem; }
    .footer-section { margin-top: 80px; padding-top: 40px; border-top: 1px solid #333; }
    .contact-table { width: 100%; color: #ddd; font-size: 0.9em; }
    .contact-table td { padding: 5px 0; }
    .label { color: #888; width: 100px; }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================
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

# =============================================================================
# 🏢 YASAL FOOTER FONKSİYONU (Tekrarı önlemek için)
# =============================================================================
def show_footer():
    st.markdown('<div class="footer-section"></div>', unsafe_allow_html=True)
    st.subheader("Kurumsal ve Yasal Bilgiler")
    
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        st.markdown("")
        with st.expander("Gizlilik Politikası ve KVKK Metni"):
            st.write("Verileriniz 6698 sayılı KVKK uyarınca korunmaktadır. DXF dosyaları analiz sonrası silinir.")
        with st.expander("Mesafeli Satış Sözleşmesi"):
            st.write("Dijital biletler anında ifa edilen hizmetlerdir. Her bilet 1 analiz hakkı sağlar.")
        with st.expander("İade ve İptal Politikası"):
            st.write("Dijital ürünlerde cayma hakkı bulunmamaktadır. Teknik sorunlarda destekle iletişime geçiniz.")
            
    with col_f2:
        st.markdown("##### 📞 İletişim")
        st.markdown(f"""
            <table class="contact-table">
                <tr><td class="label">Unvan</td><td>Fi-le Mimarlık & Yazılım</td></tr>
                <tr><td class="label">Adres</td><td>[Vergi Levhası Adresi]</td></tr>
                <tr><td class="label">E-posta</td><td>support@fi-le.com</td></tr>
                <tr><td class="label">Vergi</td><td>[Daire] / [No]</td></tr>
            </table>
        """, unsafe_allow_html=True)
    
    st.divider()
    st.caption("© 2024 Fi-le Yazılım. Tüm hakları saklıdır. Bu uygulama mühendislik ön inceleme aracıdır.")

# =============================================================================
# 1. GİRİŞ EKRANI (Login)
# =============================================================================
if not st.session_state.logged_in:
    st.title("🏗️ Duvar Metraj Sistemi Giriş")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        email_input = st.text_input("E-posta Adresiniz", placeholder="ornek@mail.com")
        if st.button("Giriş Yap ve Kontrol Et", use_container_width=True):
            if "@" in email_input and "." in email_input:
                user = get_user_data(email_input)
                st.session_state.user_email = user["email"]
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Lütfen geçerli bir e-posta adresi girin.")
    
    # Giriş ekranında yasal metinleri göster
    show_footer()
    st.stop()

# =============================================================================
# 2. ANALİZ PANELI (Dashboard)
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
    if has_credits:
        uploaded = st.file_uploader("📁 DXF Dosyası Yükle", type=["dxf"])
        katman_secimi = st.text_input("🧱 Duvar Katmanı", value="DUVAR")
        kat_yuksekligi = st.number_input("📏 Kat Yüksekliği (m)", value=2.85, step=0.01)
        birim = st.selectbox("📐 Çizim Birimi", ["cm", "mm", "m"], index=0)
    else:
        st.error("📉 Biletiniz Bulunmuyor")
        st.link_button("💳 Hemen Bilet Al (99 TL)", "https://paytr.com/link-buraya", use_container_width=True)
        uploaded = None

    if st.button("🚪 Güvenli Çıkış", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.title("🏗️ Metraj Analiz Paneli")

# Bilet yoksa kilit ekranı
if not has_credits:
    st.warning("### 🛑 Dosya Yükleme Kilitli")
    st.write("Analiz yapmak için lütfen bilet satın alınız.")
    st.stop()

# Dosya yüklenmemişse bilgilendirme
if uploaded is None:
    st.info(f"Hoş geldiniz **{st.session_state.user_email}**. Lütfen sol taraftan analiz için DXF dosyasını yükleyin.")
else:
    # --- ANALİZ MOTORU --- (Buradaki işlemler mevcut kodunla aynı)
    try:
        with st.spinner("Dosya analiz ediliyor..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                tmp.write(uploaded.getvalue())
                tmp_path = tmp.name
            
            doc = ezdxf.readfile(tmp_path)
            # ... (Metraj hesaplama mantığı burada devam eder) ...
            
            st.success(f"✅ Analiz Hazır: {uploaded.name}")
            st.metric("Aks Uzunluğu", "Analiz Sonucu m") # Örnek metrik
            
            if st.button("📥 Analizi Onayla ve 1 Bilet Kullan", type="primary"):
                if use_credit(st.session_state.user_email):
                    st.balloons()
                    st.success("Rapor indiriliyor...")
            
            os.remove(tmp_path)
    except Exception as e:
        st.error(f"Hata: {e}")

# Panel içinde de alt bilgiyi göster
show_footer()
