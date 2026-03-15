import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os

# --- 1. GÜVENLİK VE YAPILANDIRMA ---
st.set_page_config(page_title="SaaS Metraj Pro | Kusursuz Sürüm", layout="wide", page_icon="🏗️")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🛡️ Kurumsal Metraj Giriş")
    with st.form("login_form"):
        user = st.text_input("Kullanıcı Adı")
        pw = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            try:
                # Streamlit Secrets veya manuel yedek şifre
                admin_pass = st.secrets["credentials"]["usernames"]["admin"]["password"] if "credentials" in st.secrets else "123"
                if user == "admin" and pw == admin_pass:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Hatalı Giriş Bilgileri!")
            except:
                st.error("Sistem Hatası: Lütfen Secrets ayarlarını kontrol edin.")
    st.stop()

# --- 2. HATASIZ GEOMETRİ ANALİZ MOTORU ---
def get_dxf_data(file_path, filter_layers):
    try:
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        geoms = []
        
        # Katman isimlerini temizle (Boşlukları al ve büyüt)
        target_layers = [t.upper().strip() for t in filter_layers.split(",") if t.strip()]
        
        # DÜZELTME 1: Blokları (INSERT) da sorguya dahil et
        entities = msp.query('LINE LWPOLYLINE POLYLINE INSERT')
        
        for e in entities:
            # DÜZELTME 2: AutoCAD katmanındaki görünmez boşlukları temizle
            layer_name = e.dxf.layer.upper().strip()
            
            # DÜZELTME 3: Birebir eşleşme değil, "İçeriyor mu?" (Substring) kontrolü yap
            if target_layers and not any(t in layer_name for t in target_layers):
                continue
            
            pts_list = []
            
            # Eğer obje bir Blok/Grup (INSERT) ise, bloğun içindeki çizgileri patlatarak al
            if e.dxftype() == "INSERT":
                for sub_e in e.virtual_entities():
                    if sub_e.dxftype() == "LINE":
                        pts_list.append([(sub_e.dxf.start.x, sub_e.dxf.start.y), (sub_e.dxf.end.x, sub_e.dxf.end.y)])
                    elif sub_e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                        pts_list.append([(p[0], p[1]) for p in sub_e.get_points()])
            else:
                # Normal çizgiler
                if e.dxftype() == "LINE":
                    pts_list.append([(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)])
                elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                    pts_list.append([(p[0], p[1]) for p in e.get_points()])
            
            # Elde edilen tüm koordinatları ana listeye ekle
            for pts in pts_list:
                if len(pts) > 1:
                    geoms.append(pts)
                    
        return geoms
    except Exception as e:
        st.error(f"DXF Okuma Hatası: {e}")
        return []

# --- 3. ANA PANEL ---
st.sidebar.success("Oturum Aktif: BARIŞ")
st.title("🏗️ Profesyonel Metraj ve Analiz Platformu")

with st.sidebar:
    st.header("⚙️ Veri Girişi")
    uploaded_file = st.file_uploader("AutoCAD DXF Dosyası", type=["dxf"])
    kat_yuk = st.number_input("Duvar Yüksekliği (m)", value=2.85, format="%.2f")
    birim_tipi = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    layer_name = st.text_input("Layer (Katman) İsmi", "DUVAR")
    
    st.divider()
    st.header("📐 Hesaplama Ayarı")
    cizim_modu = st.radio("Metot", ["Tek Çizgi (Aks Ölçümü)", "Çift Çizgi (Mimari Duvar)"], index=1)

if uploaded_file:
    # GEÇİCİ DOSYA OLUŞTURMA
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded_file.getbuffer())
        temp_path = tmp.name

    # Veri Analizi
    wall_data = get_dxf_data(temp_path, layer_name)

    if wall_data:
        total_unit_length = 0
        for poly in wall_data:
            for i in range(len(poly) - 1):
                # Hassas 2D Öklid Mesafesi
                d = math.sqrt((poly[i+1][0] - poly[i][0])**2 + (poly[i+1][1] - poly[i][1])**2)
                total_unit_length += d

        # Ölçekleme (Unit -> Metre)
        scale = 100 if birim_tipi == "cm" else (1000 if birim_tipi == "mm" else 1)
        raw_meters = total_unit_length / scale
        
        # Çizim moduna göre final uzunluk
        final_l = raw_meters / 2 if cizim_modu == "Çift Çizgi (Mimari Duvar)" else raw_meters
        final_area = final_l * kat_yuk

        # SONUÇ EKRANI
        st.success(f"Analiz Başarılı! {len(wall_data)} adet duvar segmenti tespit edildi.")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("📏 Net Uzunluk", f"{round(final_l, 2)} m")
        m2.metric("🧱 Toplam Alan", f"{round(final_area, 2)} m²")
        m3.metric("🔍 Ham Veri", f"{round(total_unit_length, 1)} unit")

        # Raporlama
        df_final = pd.DataFrame({
            "İmalat": ["Duvar Kaplama/İmalat"],
            "Birim": [birim_tipi],
            "Net Metraj (m)": [round(final_l, 3)],
            "Yükseklik (m)": [kat_yuk],
            "Toplam Alan (m2)": [round(final_area, 3)]
        })
        st.dataframe(df_final, use_container_width=True)

        # Görselleştirme
        fig, ax = plt.subplots(figsize=(10, 4))
        for line in wall_data:
            x_coords, y_coords = zip(*line)
            ax.plot(x_coords, y_coords, color="#e67e22", lw=2)
        ax.set_aspect("equal")
        ax.axis("off")
        st.pyplot(fig)
        
    else:
        st.error(f"❌ '{layer_name}' katmanında veya blokların içinde uygun çizgi bulunamadı. Lütfen layer ismini kontrol edin.")

    # Temizlik: Geçici dosyayı sil
    if os.path.exists(temp_path):
        os.remove(temp_path)
else:
    st.info("💡 Başlamak için lütfen sol taraftan bir DXF dosyası yükleyin.")
