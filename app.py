import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO
from roboflow import Roboflow

# ... (Önceki kütüphane ve stil tanımları aynı) ...

if dxf_file:
    # Plan analiz simülasyonu
    img_buf = BytesIO()
    # (Burada planı görselleştirip img_buf'a yazan kısım yer almalı)
    
    preds = run_roboflow_ai(img_buf)
    results = process_hybrid_metraj(preds, unit_scale)
    
    # DataFrame oluşturma
    df = pd.DataFrame(results)

    col1, col2 = st.columns([2, 1])

    with col2:
        st.subheader("📋 Metraj Listesi")
        # HATAYI ENGELLEYEN KONTROL: Eğer liste boş değilse göster
        if not df.empty:
            # Seçim mekanizması
            selected_index = st.radio("Vurgulanacak Duvarı Seçin:", df.index)
            st.dataframe(df[["Uzunluk", "Tip"]], use_container_width=True)
        else:
            st.warning("⚠️ Seçilen katmanda veya görselde duvar bulunamadı.")
            selected_index = None

    with col1:
        st.subheader("🖼️ İnteraktif Plan")
        fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0e1117')
        
        if not df.empty:
            for i, row in df.iterrows():
                # Seçili satırı fosforlu yeşil yap
                is_selected = (i == selected_index)
                color = "#32CD32" if is_selected else "#00d2ff"
                width = 5 if is_selected else 1.5
                
                ax.plot([row['p1'][0], row['p2'][0]], [row['p1'][1], row['p2'][1]], 
                        color=color, lw=width, solid_capstyle='round')
                
                if is_selected:
                    ax.text(row['p1'][0], row['p1'][1], f"  {row['Uzunluk']} m", 
                            color="white", fontsize=12, fontweight='bold')
        
        ax.set_aspect("equal")
        ax.axis("off")
        st.pyplot(fig)

    if not df.empty:
        st.success(f"✅ Toplam {len(df)} adet duvar segmenti başarıyla doğrulandı.")
