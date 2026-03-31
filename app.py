"""
Mimari Duvar Metraj Uygulaması - Profesyonel SaaS Sürümü
Geliştirici: Barış Öker - Fi-le Yazılım 
Özellik: Önce Bilet Kontrolü + Profesyonel SaaS Footer & Yasal Mevzuat
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
# 🎨 PROFESYONEL SaaS CSS TASARIMI
# =============================================================================
st.markdown("""
    <style>
    /* Global Ayarlar */
    .stApp { background-color: #0e1117; }
    
    /* Profil Kartı */
    .profile-card { text-align: center; padding: 1rem; background-color: #1e2130; border-radius: 12px; border: 1px solid #333; margin-bottom: 1.5rem; }
    .profile-img { border-radius: 50%; width: 90px; height: 90px; border: 3px solid #FF4B4B; margin-bottom: 0.5rem; }
    .profile-card h4 { color: white; margin: 0; font-size: 1.2em; font-weight: 600; }
    .profile-card p { color: #FF4B4B; margin: 0; font-weight: bold; font-size: 1.3em; }

    /* Butonlar */
    .stButton>button { border-radius: 8px; font-weight: bold; transition: all 0.3s ease; }
    .stButton>button:hover { transform: translateY(-1px); box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .stDownloadButton>button { border-radius: 8px; font-weight: bold; width: 100%; }

    /* Metrik Kartları */
    div[data-testid="stMetricValue"] { color: #FF4B4B; }
    div[data-testid="stMetricLabel"] { color: #888; }

    /* --- PROFESYONEL SaaS FOOTER TASARIMI --- */
    .saas-footer { margin-top: 60px; padding: 40px 0; border-top: 1px solid #262730; background-color: #0c0f14; }
    .footer-heading { color: white !important; font-weight: 600; font-size: 1.6em; margin-bottom: 30px; }
    
    /* Expanderları Minimal Hale Getirme */
    .st-emotion-cache-1vt4y43 { border: none !important; background-color: #1e2130 !important; border-radius: 10px !important; margin-bottom: 10px !important; }
    .st-emotion-cache-1vt4y43 .st-emotion-cache-0 { color: #ddd !important; font-weight: 500 !important; } /* Başlık */
    
    /* İletişim Bilgileri Düzeni */
    .contact-info-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .contact-info-table td { padding: 8px 10px; vertical-align: top; }
    .contact-info-label { color: #888; width: 140px; font-size: 0.9em; text-align: right; }
    .contact-info-value { color: white; font-size: 1em; font-weight: 500; }
    
    /* Telif ve Caption */
    .copyright-text { text-align: center; color: #666; font-size: 12px; margin-top: 30px; }
    .disclaimer-text { text-align: center; color: #444; font-size: 11px; margin-top: 10px; }
    
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
# 1. GİRİŞ EKRANI (Aynı Kalıyor)
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
    st.stop()

# =============================================================================
# 2. SIDEBAR VE KONTROL MERKEZİ (Aynı Kalıyor)
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
        st.success("✅ Erişim İzni Verildi")
        uploaded = st.file_uploader("📁 DXF Dosyası Yükle", type=["dxf"])
        katman_secimi = st.text_input("🧱 Duvar Katmanı", value="DUVAR")
        kat_yuksekligi = st.number_input("📏 Kat Yüksekliği (m)", value=2.85, step=0.01)
        birim = st.selectbox("📐 Çizim Birimi", ["cm", "mm", "m"], index=0)
    else:
        st.error("📉 Biletiniz Bulunmuyor")
        st.info("Analiz yapmak için bilet satın almalısınız.")
        st.link_button("💳 Hemen Bilet Al (99 TL)", "https://paytr.com/link-buraya", use_container_width=True)
        uploaded = None

    st.divider()
    if st.button("🚪 Güvenli Çıkış", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()

# =============================================================================
# 3. ANA ANALİZ PANELI (Aynı Kalıyor)
# =============================================================================
st.title("🏗️ Metraj Analiz Paneli")

if not has_credits:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.warning("### 🛑 Dosya Yükleme Kilitli")
        st.write("""
        Sistemi kullanabilmek için aktif biletiniz olmalıdır. 
        Satın aldığınız biletler ile hızlıca duvar metrajı çıkarabilir, 
        alan hesabı yapabilir ve raporlarınızı indirebilirsiniz.
        """)
        st.info("💡 Satın alınan biletler anında hesabınıza tanımlanır.")
    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/261/261168.png", width=150)
else:
    if uploaded is None:
        st.info(f"Hoş geldiniz **{st.session_state.user_email}**. Biletiniz tanımlı. Lütfen sol taraftan bir DXF dosyası yükleyin.")
    else:
        try:
            # (Analiz motoru kodu buraya)
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

            # SONUÇLAR
            st.success(f"✅ Analiz Başarılı: {uploaded.name}")
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Obje Sayısı", f"{entity_count} ad")
            with c2: st.metric("Aks Uzunluğu", f"{aks_uzunluk:.2f} m")
            with c3: st.metric("Toplam Alan", f"{toplam_alan:.2f} m²")

            # Grafik
            fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0e1117')
            ax.set_facecolor('#0e1117')
            # Grafik çizim kodu (Kısaltıldı)
            ax.set_aspect('equal'); ax.axis('off')
            st.pyplot(fig)

            st.divider()
            if st.button("📥 Analizi Onayla ve Rapor İndir (1 Bilet)", use_container_width=True, type="primary"):
                if use_credit(st.session_state.user_email):
                    st.balloons()
                    csv = f"Parametre,Deger\nDosya,{uploaded.name}\nKatman,{katman_secimi}\nAks Uzunlugu,{aks_uzunluk:.2f} m\nToplam Alan,{toplam_alan:.2f} m2"
                    st.download_button("📥 Raporu Kaydet (CSV)", csv, f"rapor_{uploaded.name}.csv", use_container_width=True)
                else:
                    st.error("Hata: Biletiniz bitti!")
            os.remove(tmp_path)
        except Exception as e:
            st.error(f"❌ Hata: {str(e)}")

# =============================================================================
# 🎨 4. PROFESYONEL SaaS FOOTER (GÜNCELLENDİ)
# =============================================================================
# Ana ekrandan ayırmak için boşluk ve çizgi
st.markdown("<br><br>", unsafe_allow_html=True)

# Footer Başlığı
st.markdown('<h2 class="footer-heading">📄 Kurumsal ve Yasal Bilgiler</h2>', unsafe_allow_html=True)

col_f1, col_f2 = st.columns([2, 1]) # Yasal metinlere daha çok alan, iletişime daha az alan

with col_f1:
    st.markdown("### ⚖️ Yasal Mevzuat ve Politikalar")
    
    with st.expander("🔐 Gizlilik Politikası ve KVKK Metni", expanded=False):
        st.write("""
            **Veri Sorumlusu:** Fi-le Mimarlık & Yazılım - Barış Öker  
            Bu uygulama, hizmet sunumu ve bilet takibi amacıyla sadece kullanıcıların e-posta adreslerini saklar. 
            Verileriniz, 6698 sayılı KVKK uyarınca korunmaktadır. 
            Yüklediğiniz DXF dosyaları analiz tamamlandıktan sonra sunucudan kalıcı olarak silinir, 
            hiçbir şekilde depolanmaz veya 3. şahıslarla paylaşılmaz.
        """)
    
    with st.expander("📜 Mesafeli Satış Sözleşmesi", expanded=False):
        st.write("""
            Bu sözleşme, alıcının dijital bilet (kullanım hakkı) satın alımına ilişkindir. 
            Her bilet, sistemdeki duvar metrajı hesaplama araçlarını 1 (bir) kez kullanma hakkı verir. 
            Bilet hesabınıza tanımlandığı an, hizmet elektronik ortamda anında ifa edilmiş sayılır.
        """)
        
    with st.expander("🔄 İptal, İade ve Değişim Politikası", expanded=False):
        st.write("""
            6502 sayılı Tüketicinin Korunması Hakkında Kanun uyarınca, 'Elektronik ortamda anında ifa edilen hizmetler' 
            kapsamında olan dijital ürünlerde cayma hakkı bulunmamaktadır. 
            Bilet kullanıldıktan sonra iade veya değişim yapılamaz. 
            Sistemsel hatalardan kaynaklı bilet düşümlerinde destek ekibiyle iletişime geçiniz.
        """)

with col_f2:
    st.markdown("### 📞 İletişim ve Destek")
    
    st.markdown(f"""
        <table class="contact-info-table">
            <tr>
                <td class="contact-info-label">Unvan</td>
                <td class="contact-info-value">Fi-le Mimarlık & Yazılım<br>Barış Öker</td>
            </tr>
            <tr>
                <td class="contact-info-label">Adres</td>
                <td class="contact-info-value">[Vergi Levhasındaki Adresiniz]</td>
            </tr>
            <tr>
                <td class="contact-info-label">E-posta</td>
                <td class="contact-info-value">support@fi-le.com</td>
            </tr>
            <tr>
                <td class="contact-info-label">Vergi Bilgisi</td>
                <td class="contact-info-value">[Vergi Dairesi] / [Vergi No]</td>
            </tr>
        </table>
    """, unsafe_allow_html=True)
    st.caption("Fatura talepleri için destek ekibimize e-posta atabilirsiniz.")

# Telif ve Caption
st.divider()
st.markdown('<p class="copyright-text">© 2024 Fi-le Yazılım. Tüm hakları saklıdır. Bu uygulama bir mühendislik ön inceleme aracıdır.</p>', unsafe_allow_html=True)
st.markdown('<p class="disclaimer-text">Bu araçla elde edilen sonuçlar kesin metrajlar değildir, nihai uygulama öncesi mühendislik kontrolleri yapılmalıdır.</p>', unsafe_allow_html=True)
