import streamlit as st
from datetime import datetime, timedelta
from auth import init_session_state, check_auth, login_page, logout, hash_password
from database import (init_db, add_product, get_products, delete_product,
                     add_inventory_movement, get_inventory_report, get_latest_inventory_movements, 
                     delete_inventory_movement, get_detailed_movements_report, get_summary_report, 
                     add_user, update_user, get_users, delete_user, check_user_permission)
from utils import export_to_excel, format_date

# Initialize database and session state
init_db()
init_session_state()

# Page configuration
st.set_page_config(
    page_title="Restoran Stok Takip",
    page_icon="🏪",
    layout="wide"
)

# Main page layout
if not check_auth():
    login_page()
else:
    st.sidebar.title(f"Hoş Geldiniz, {st.session_state.username}!")

    # Admin için ekstra sayfa seçeneği
    if st.session_state.is_admin:
        pages = ["Stok Ekle/Düzenle", "Ürün Tanımlama", "Raporlama", "Kullanıcı Yönetimi"]
    else:
        pages = []
        if check_user_permission(st.session_state.user_id, "can_manage_inventory"):
            pages.append("Stok Ekle/Düzenle")
        if check_user_permission(st.session_state.user_id, "can_add_product"):
            pages.append("Ürün Tanımlama")
        if check_user_permission(st.session_state.user_id, "can_view_reports"):
            pages.append("Raporlama")

    # Varsayılan sayfa "Stok Ekle/Düzenle" olarak ayarla
    if 'current_page' not in st.session_state:
        st.session_state.current_page = pages[0] if pages else None

    # Üst kısımda ana navigasyon menüsü ve performans optimizasyonu
    st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f0f0;
        border-radius: 4px;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: #186f65;
        color: white;
    }

    /* Buton tıklama sorununu gidermek için ekstra CSS */
    button {
        transition: background-color 0.2s;
    }
    button:active {
        background-color: #186f65 !important;
        color: white !important;
    }
    .stButton button {
        cursor: pointer !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Streamlit'in önbelleğini temizleyen bir fonksiyon
    if 'button_clicked' not in st.session_state:
        st.session_state.button_clicked = False

    if pages:
        # Navigasyon için sidebar kullan
        if not st.session_state.current_page in pages and pages:
            st.session_state.current_page = pages[0]  # Varsayılan sayfayı ayarla
            
        page = st.sidebar.radio("Sayfalar", pages, index=pages.index(st.session_state.current_page), key='page_selection')
        if page != st.session_state.current_page:
            st.session_state.current_page = page
            st.rerun()

        # Sidebar'da çıkış butonu
        if st.sidebar.button("Çıkış Yap"):
            logout()

        if page == "Ürün Tanımlama" and (st.session_state.is_admin or check_user_permission(st.session_state.user_id, "can_add_product")):
            st.title("Ürün Tanımlama")

            with st.form("add_product_form"):
                product_name = st.text_input("Ürün Adı")
                product_category = st.selectbox(
                    "Ürün Bölümü",
                    ["TEMİZLİK", "BAR", "MUTFAK", "İÇECEK", "PASTA", "DONDURMA", "GENEL"]
                )

                if st.form_submit_button("Ürün Ekle"):
                    if product_name:
                        success, message = add_product(product_name, product_category)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Lütfen ürün adını giriniz")

            # Mevcut ürünleri göster
            st.subheader("Tanımlı Ürünler")
            products_df = get_products()

            if not products_df.empty:
                # Kategori bazında grupla
                categories = sorted(products_df['category'].unique())

                for category in categories:
                    st.markdown(f"**{category}**")
                    category_products = products_df[products_df['category'] == category]

                    for _, row in category_products.iterrows():
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.write(row['name'])
                        with col2:
                            st.write(f"Bölüm: {row['category']}")
                        with col3:
                            if st.button("Sil", key=f"delete_{row['id']}"):
                                success, message = delete_product(row['id'])
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
                        st.divider()
            else:
                st.info("Henüz ürün tanımlanmamış.")

        elif page == "Stok Ekle/Düzenle" and (st.session_state.is_admin or check_user_permission(st.session_state.user_id, "can_manage_inventory")):
            st.title("Stok Güncelleme")

            products_df = get_products()
            if not products_df.empty:
                with st.form("update_stock_form"):
                    product_id = st.selectbox(
                        "Ürün",
                        options=products_df['id'].tolist(),
                        format_func=lambda x: products_df[
                            products_df['id']==x
                        ]['name'].iloc[0]
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        quantity = st.number_input(
                            "Miktar",
                            min_value=0.0,
                            step=0.1
                        )
                        unit = st.selectbox(
                            "Birim", 
                            ["kg", "litre", "adet", "gram", "paket", "kova", "ml"]
                        )
                    with col2:
                        total_price = st.number_input(
                            "Toplam Fiyat (TL)",
                            min_value=0.0,
                            step=0.1
                        )

                    button_style = """
                        <style>
                        div[data-testid="stButton"] button {
                            background-color: #186f65;
                            color: white;
                            font-weight: bold;
                            border-radius: 4px;
                            padding: 0.5rem 1rem;
                            border: none;
                        }
                        </style>
                    """
                    st.markdown(button_style, unsafe_allow_html=True)

                    if st.form_submit_button("ÜRÜN GİR"):
                        if quantity > 0 and total_price > 0:
                            success, message = add_inventory_movement(
                                product_id, quantity, unit, total_price,
                                st.session_state.user_id
                            )
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                        else:
                            st.error("Miktar ve fiyat 0'dan büyük olmalıdır")

                # Son eklenen ürünleri göster
                st.subheader("Son Eklenen Ürünler")

                # Tarih filtresi
                col1, col2 = st.columns(2)
                with col1:
                    filter_start_date = st.date_input(
                        "Başlangıç Tarihi",
                        datetime.now().date() - timedelta(days=7)
                    )
                    filter_start_time = st.time_input(
                        "Başlangıç Saati",
                        datetime.strptime("00:00", "%H:%M").time()
                    )
                with col2:
                    filter_end_date = st.date_input(
                        "Bitiş Tarihi",
                        datetime.now().date()
                    )
                    filter_end_time = st.time_input(
                        "Bitiş Saati",
                        datetime.strptime("23:59", "%H:%M").time()
                    )

                filter_start = datetime.combine(filter_start_date, filter_start_time)
                filter_end = datetime.combine(filter_end_date, filter_end_time)

                # Son hareketleri göster
                with st.container():
                    max_height = 300  # piksel cinsinden maksimum yükseklik
                    st.markdown(f"""
                        <style>
                            .movement-container {{
                                max-height: {max_height}px;
                                overflow-y: auto;
                                padding: 1rem;
                                border: 1px solid #ddd;
                                border-radius: 4px;
                            }}
                        </style>
                    """, unsafe_allow_html=True)

                    latest_movements = get_latest_inventory_movements(100)  # Daha fazla hareket göster
                    if latest_movements:
                        with st.container():
                            st.markdown('<div class="movement-container">', unsafe_allow_html=True)
                            for movement in latest_movements:
                                movement_date = datetime.strptime(movement['local_date'], '%Y-%m-%d %H:%M:%S')
                                if filter_start <= movement_date <= filter_end:
                                    # Standart görünüm
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.write(f"**{movement['product_name']}**")
                                        st.write(f"Bölüm: {movement['product_category']}")
                                    with col2:
                                        st.write(f"Tarih: {movement_date.strftime('%d.%m.%Y %H:%M')}")
                                        st.write(f"Miktar: {movement['quantity']} {movement['unit']}")
                                        st.write(f"Toplam: {movement['total_price']:.2f} TL")

                                    # Hareket silme butonunu da iyileştir
                                    button_key = f"delete_movement_{movement['movement_id']}"
                                    if st.button("Hareketi Sil", key=button_key):
                                        with st.spinner("Hareket siliniyor..."):
                                            success, message = delete_inventory_movement(movement['movement_id'])
                                            if success:
                                                st.success(message)
                                                st.rerun()
                                            else:
                                                st.error(message)
                                    st.divider()
                            st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.info("Henüz stok hareketi bulunmamaktadır.")

            else:
                st.warning("Henüz ürün tanımlanmamış. Lütfen önce ürün tanımlayınız.")

        elif page == "Raporlama" and (st.session_state.is_admin or check_user_permission(st.session_state.user_id, "can_view_reports")):
            st.title("Stok ve Değer Raporu")

            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Başlangıç Tarihi",
                    datetime.now().date() - timedelta(days=30)
                )
                start_time = st.time_input(
                    "Başlangıç Saati",
                    datetime.strptime("00:00", "%H:%M").time()
                )
            with col2:
                end_date = st.date_input(
                    "Bitiş Tarihi",
                    datetime.now().date()
                )
                end_time = st.time_input(
                    "Bitiş Saati",
                    datetime.strptime("23:59", "%H:%M").time()
                )

            if st.button("Rapor Oluştur"):
                # Tarih ve saatleri birleştir
                start_datetime = datetime.combine(start_date, start_time)
                end_datetime = datetime.combine(end_date, end_time)

                # Sekmeleri oluştur
                tab1, tab2 = st.tabs(["Detaylı Hareket Raporu", "Özet Rapor"])

                with tab1:
                    st.subheader("Detaylı Hareket Raporu")
                    detailed_df = get_detailed_movements_report(
                        start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                        end_datetime.strftime('%Y-%m-%d %H:%M:%S')
                    )

                    if not detailed_df.empty:
                        # Excel aktarma butonunu üste yerleştir
                        excel_data = export_to_excel(
                            detailed_df,
                            start_date=start_datetime.strftime('%d.%m.%Y %H:%M'),
                            end_date=end_datetime.strftime('%d.%m.%Y %H:%M')
                        )
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.download_button(
                                label="Detaylı Raporu Excel'e Aktar",
                                data=excel_data,
                                file_name=f"detayli_stok_raporu_{start_datetime.strftime('%Y-%m-%d_%H-%M')}_to_{end_datetime.strftime('%Y-%m-%d_%H-%M')}.xlsx",
                                mime="application/vnd.ms-excel"
                            )

                        # Veriyi göster
                        st.dataframe(detailed_df)
                    else:
                        st.info("Seçilen tarih aralığında hareket bulunmamaktadır.")

                with tab2:
                    st.subheader("Özet Rapor")
                    summary_df = get_summary_report(
                        start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                        end_datetime.strftime('%Y-%m-%d %H:%M:%S')
                    )

                    if not summary_df.empty:
                        # Toplam değeri göster
                        total_value = summary_df['TOPLAM FİYAT'].sum()
                        st.metric("Toplam Stok Değeri", f"{total_value:.2f} TL")

                        # Excel aktarma butonunu üste yerleştir
                        excel_data = export_to_excel(
                            summary_df,
                            start_date=start_datetime.strftime('%d.%m.%Y %H:%M'),
                            end_date=end_datetime.strftime('%d.%m.%Y %H:%M')
                        )
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.download_button(
                                label="Özet Raporu Excel'e Aktar",
                                data=excel_data,
                                file_name=f"ozet_stok_raporu_{start_datetime.strftime('%Y-%m-%d_%H-%M')}_to_{end_datetime.strftime('%Y-%m-%d_%H-%M')}.xlsx",
                                mime="application/vnd.ms-excel"
                            )

                        # Veriyi göster
                        st.dataframe(summary_df)
                    else:
                        st.info("Seçilen tarih aralığında hareket bulunmamaktadır.")

        elif page == "Kullanıcı Yönetimi" and st.session_state.is_admin:
            st.title("Kullanıcı Yönetimi")

            # Kullanıcı ekleme formu
            with st.form("add_user_form"):
                st.subheader("Yeni Kullanıcı Ekle")
                new_username = st.text_input("Kullanıcı Adı")
                new_password = st.text_input("Şifre", type="password")
                confirm_password = st.text_input("Şifre (Tekrar)", type="password")

                col1, col2 = st.columns(2)
                with col1:
                    is_admin = st.checkbox("Admin")
                with col2:
                    can_add_product = st.checkbox("Ürün Ekleyebilir")

                col3, col4 = st.columns(2)
                with col3:
                    can_view_reports = st.checkbox("Raporları Görebilir")
                with col4:
                    can_manage_inventory = st.checkbox("Stok Yönetebilir")

                if st.form_submit_button("Kullanıcı Ekle"):
                    if not new_username or not new_password:
                        st.error("Kullanıcı adı ve şifre alanları boş olamaz!")
                    elif new_password != confirm_password:
                        st.error("Şifreler eşleşmiyor!")
                    else:
                        hashed_password = hash_password(new_password)
                        success, message = add_user(
                            new_username, 
                            hashed_password, 
                            is_admin=1 if is_admin else 0,
                            can_add_product=1 if can_add_product else 0,
                            can_view_reports=1 if can_view_reports else 0,
                            can_manage_inventory=1 if can_manage_inventory else 0
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

            # Kullanıcı listesi
            st.subheader("Kullanıcı Listesi")
            users_df = get_users()

            if not users_df.empty:
                for _, user in users_df.iterrows():
                    with st.expander(f"Kullanıcı: {user['username']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"ID: {user['id']}")
                            st.write(f"Admin: {'Evet' if user['is_admin'] else 'Hayır'}")
                        with col2:
                            st.write(f"Ürün Ekleyebilir: {'Evet' if user['can_add_product'] else 'Hayır'}")
                            st.write(f"Raporları Görebilir: {'Evet' if user['can_view_reports'] else 'Hayır'}")
                            st.write(f"Stok Yönetebilir: {'Evet' if user['can_manage_inventory'] else 'Hayır'}")

                        edit_col1, edit_col2, edit_col3 = st.columns(3)
                        with edit_col1:
                            new_password = st.text_input(f"Yeni Şifre", key=f"new_pass_{user['id']}", type="password")
                        with edit_col2:
                            if st.button("Şifre Güncelle", key=f"update_pass_{user['id']}"):
                                if new_password:
                                    hashed_password = hash_password(new_password)
                                    success, message = update_user(user['id'], password=hashed_password)
                                    if success:
                                        st.success(message)
                                        st.rerun()
                                    else:
                                        st.error(message)
                                else:
                                    st.error("Şifre boş olamaz!")
                        with edit_col3:
                            if user['id'] != st.session_state.user_id:  # Kendini silememeli
                                if st.button("Kullanıcıyı Sil", key=f"delete_user_{user['id']}"):
                                    success, message = delete_user(user['id'])
                                    if success:
                                        st.success(message)
                                        st.rerun()
                                    else:
                                        st.error(message)

                        # Yetki güncelleme
                        permission_col1, permission_col2 = st.columns(2)
                        with permission_col1:
                            user_is_admin = st.checkbox("Admin", key=f"admin_{user['id']}", value=bool(user['is_admin']))
                            user_can_add_product = st.checkbox("Ürün Ekleyebilir", key=f"product_{user['id']}", value=bool(user['can_add_product']))
                        with permission_col2:
                            user_can_view_reports = st.checkbox("Raporları Görebilir", key=f"reports_{user['id']}", value=bool(user['can_view_reports']))
                            user_can_manage_inventory = st.checkbox("Stok Yönetebilir", key=f"inventory_{user['id']}", value=bool(user['can_manage_inventory']))

                        if st.button("Yetkileri Güncelle", key=f"update_perm_{user['id']}"):
                            success, message = update_user(
                                user['id'],
                                is_admin=1 if user_is_admin else 0,
                                can_add_product=1 if user_can_add_product else 0,
                                can_view_reports=1 if user_can_view_reports else 0,
                                can_manage_inventory=1 if user_can_manage_inventory else 0
                            )
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
            else:
                st.info("Henüz kullanıcı bulunmamaktadır.")
    else:
        st.warning("Herhangi bir sayfaya erişim izniniz bulunmamaktadır. Lütfen yönetici ile iletişime geçiniz.")