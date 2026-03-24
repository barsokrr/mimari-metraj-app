import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os

# --- 1. OTURUM VE SAYFA AYARI ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

st.set_page_config(page_title="SaaS Metraj Pro v2", layout="wide")

# --- 2. GELİŞMİŞ ANALİZ FONKSİYONU ---
def calculate_metrics(msp, wall_l, floor_l, door_l, win_l, h, unit_divider):
    results = {"w_area": 0, "f_area": 0, "d_count": 0, "w_count": 0}
    
    # 1. DUVAR: Çizgisel toplam
    for e in msp.query(f'*[layer=="{wall_l}"]'):
        if e.dxftype() == "LINE":
            results["w_area"] += math.dist(e.dxf.start, e.dxf.end)
        elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
            pts = list(e.get_points())
            results["w_area"] += sum(math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1))
    results["w_area"] = ((results["w_area"] / 2) / unit_divider) * h

    # 2. ZEMİN: Alan hesabı
    for e in msp.query(f'LWPOLYLINE[layer=="{floor_l}"]'):
        pts = [(p[0], p[1]) for p in e.get_points()]
        if len(pts) > 2:
            a = 0.5 * abs(sum(pts[i][0]*pts[i+1][1] - pts[i+1][0]*pts[i][1] for i in range(len(pts)-1)) + (pts[-1][0]*pts[0][1] - pts[0][0]*pts[-1][1]))
            results["f_area"] += a / (unit_divider**2)

    # 3. KAPI & PENCERE: Hatalı sayımı önlemek için BLOK odaklı sayım
    # Önce INSERT (Blok) olanları sayıyoruz, çünkü mimari projelerde kapı/pencere bloktur.
    results["d_count"] = len(msp.query(f'INSERT[layer=="{door_l}"]'))
    results["w_count"] = len(msp.query(f'INSERT[layer=="{win_l}"]'))

    # Eğer blok olarak çizilmemişse (ham çizgiyse), çizgileri gruplayarak say:
    if results["w_count"] == 0:
        raw_elements = len(msp.query(f'*[layer=="{win_l}"]'))
        # Ham çizgileri yaklaşık 10'a bölerek (bir pencere ortalama 10 çizgidir) normalize et
        results["w_count"] = math.ceil(raw_elements / 10) if raw_elements > 0 else 0
        
    if results["d_count"] == 0:
        raw_elements = len(msp.query(f'*[layer=="{door_l}"]'))
        results["d_count"] = math.ceil(raw_elements / 8) if raw_elements > 0 else 0

    return results

# --- 3. GİRİŞ EKRANI ---
if not st.session_state.logged_in:
    st.title("🏗️ SaaS Metraj Pro Giriş")
    with st.form("login"):
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş"):
            if u == "admin" and p == "1234":
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("Hatalı!")

# --- 4. ANA PROGRAM ---
else:
    with st.sidebar:
        st.markdown(f'<div style="text-align:center"><img src="https://www.w3schools.com/howto/img_avatar.png" width="80" style="border-radius:50%"><br><b>Barış Öker</b><br><small>Fi-le Yazılım A.Ş.</small></div>', unsafe_allow_html=True)
        st.write("---")
        uploaded = st.file_uploader("DXF Yükle", type=["dxf"])
        
        with st.expander("📂 Katman ve Birim Ayarları", expanded=True):
            if uploaded:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                    tmp.write(uploaded.getbuffer())
                    doc = ezdxf.readfile(tmp.name)
                    msp = doc.modelspace()
                    all_layers = [layer.dxf.name for layer in doc.layers]
                
                sel_wall = st.selectbox("Duvar Katmanı", all_layers, index=all_layers.index("DUVAR") if "DUVAR" in all_layers else 0)
                sel_floor = st.selectbox("Zemin Katmanı", all_layers, index=all_layers.index("ZEMIN") if "ZEMIN" in all_layers else 0)
                sel_door = st.selectbox("Kapı Katmanı", all_layers, index=all_layers.index("KAPI") if "KAPI" in all_layers else 0)
                sel_win = st.selectbox("Pencere Katmanı", all_layers, index=all_layers.index("PENCERE") if "PENCERE" in all_layers else 0)
            else:
                st.warning("Dosya bekliyor...")
            
            h = st.number_input("Kat Yüksekliği (m)", 2.85)
            u_div = {"cm": 100, "mm": 1000, "m": 1}[st.selectbox("Çizim Birimi", ["cm", "mm", "m"])]

        if st.button("Çıkış Yap"):
            st.session_state.logged_in = False
            st.rerun()

    st.title("📊 Metraj Analiz Sonuçları")

    if uploaded and 'msp' in locals():
        res = calculate_metrics(msp, sel_wall, sel_floor, sel_door, sel_win, h, u_div)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Toplam Duvar (m²)", f"{res['w_area']:.2f}")
        c2.metric("Toplam Zemin (m²)", f"{res['f_area']:.2f}")
        c3.metric("Kapı Adedi", res['d_count'])
        c4.metric("Pencere Adedi", res['w_count'])

        # Plan Çizimi
        fig, ax = plt.subplots(figsize=(10, 5), facecolor='#0e1117')
        for e in msp.query('LINE LWPOLYLINE'):
            pts = [e.dxf.start, e.dxf.end] if e.dxftype() == "LINE" else list(e.get_points())
            xs, ys = zip(*[(p[0], p[1]) for p in pts])
            ax.plot(xs, ys, color="gray", lw=0.4, alpha=0.3)
        ax.set_aspect("equal"); ax.axis("off")
        st.pyplot(fig)
        os.remove(tmp.name)
