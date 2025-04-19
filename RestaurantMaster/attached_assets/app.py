import streamlit as st
from datetime import datetime, timedelta
from auth import init_session_state, check_auth, login_page, logout, hash_password
from database import (init_db, add_product, get_products, delete_product,
                     add_inventory_movement, get_inventory_report, get_latest_inventory_movements, delete_inventory_movement, get_detailed_movements_report, get_summary_report, add_user, update_user, get_users, check_user_permission)
from utils import export_to_excel, format_date

# Initialize database and session state
init_db()
init_session_state()

# Sayfa konfigürasyonu
st.set_page_config(
    page_title="Restoran Stok Takip",
    page_icon="🏪",
    layout="wide"
)

# Ana sayfa düzeni
if not check_auth():
    login_page()
else:
    st.sidebar.title(f"Hoş Geldiniz!")

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
        st.session_state.current_page = "Stok Ekle/Düzenle"

    page = st.sidebar.radio("Sayfalar", pages, index=pages.index(st.session_state.current_page) if pages and st.session_state.current_page in pages else 0)
    st.session_state.current_page = page

    if st.sidebar.button("Çıkış Yap"):
        logout()

    if page == "Ürün Tanımlama" and (st.session_state.is_admin or check_user_permission(st.session_state.user_id, "can_add_product")):
        st.title("Ürün Tanımlama")

        with st.form("add_product_form"):
            product_name = st.text_input("Ürün Adı")

            if st.form_submit_button("Ürün Ekle"):
                if product_name:
                    success, message = add_product(product_name)
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
            with st.container():
                st.markdown("""
                    <style>
                        .products-container {
                            max-height: 300px;
                            overflow-y: auto;
                            padding: 1rem;
                            border: 1px solid #ddd;
                            border-radius: 4px;
                        }
                    </style>
                """, unsafe_allow_html=True)

                st.markdown('<div class="products-container">', unsafe_allow_html=True)
                for _, row in products_df.iterrows():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(row['name'])
                    with col2:
                        if st.button("Sil", key=f"delete_{row['id']}"):
                            success, message = delete_product(row['id'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                    st.divider()
                st.markdown('</div>', unsafe_allow_html=True)
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

                if st.form_submit_button("Güncelle"):
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
                    datetime.now().date()
                )
                filter_start_time = st.time_input(
                    "Başlangıç Saati",
                    datetime.strptime("00:00", "%H:%M").time()
                )
            with col2:
                filter_end_date = st.date_input(
                    "Bitiş Tarihi",
                    (datetime.now() + timedelta(days=7)).date()
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
                                cols = st.columns([2, 2, 2, 2, 1])
                                with cols[0]:
                                    st.write(f"**{movement['product_name']}**")
                                    st.write(f"Tarih: {movement_date.strftime('%d.%m.%Y %H:%M')}")
                                with cols[1]:
                                    st.write(f"{movement['quantity']} {movement['unit']}")
                                with cols[2]:
                                    st.write(f"Toplam: {movement['total_price']:.2f} TL")
                                with cols[3]:
                                    if st.button("Sil", key=f"delete_movement_{movement['movement_id']}"):
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
                datetime.now().date()
            )
            start_time = st.time_input(
                "Başlangıç Saati",
                datetime.strptime("00:00", "%H:%M").time()
            )
        with col2:
            end_date = st.date_input(
                "Bitiş Tarihi",
                (datetime.now() + timedelta(days=7)).date()
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
                    st.dataframe(detailed_df)
                    excel_data = export_to_excel(
                        detailed_df,
                        start_date=start_datetime.strftime('%d.%m.%Y %H:%M'),
                        end_date=end_datetime.strftime('%d.%m.%Y %H:%M')
                    )
                    st.download_button(
                        label="Detaylı Raporu Excel'e Aktar",
                        data=excel_data,
                        file_name=f"detayli_stok_raporu_{start_datetime.strftime('%Y-%m-%d_%H-%M')}_to_{end_datetime.strftime('%Y-%m-%d_%H-%M')}.xlsx",
                        mime="application/vnd.ms-excel"
                    )
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

                    st.dataframe(summary_df)
                    excel_data = export_to_excel(
                        summary_df,
                        start_date=start_datetime.strftime('%d.%m.%Y %H:%M'),
                        end_date=end_datetime.strftime('%d.%m.%Y %H:%M')
                    )
                    st.download_button(
                        label="Özet Raporu Excel'e Aktar",
                        data=excel_data,
                        file_name=f"ozet_stok_raporu_{start_datetime.strftime('%Y-%m-%d_%H-%M')}_to_{end_datetime.strftime('%Y-%m-%d_%H-%M')}.xlsx",
                        mime="application/vnd.ms-excel"
                    )
                else:
                    st.info("Seçilen tarih aralığında veri bulunmamaktadır.")

    elif page == "Kullanıcı Yönetimi" and st.session_state.is_admin:
        st.title("Kullanıcı Yönetimi")

        # Yeni kullanıcı ekleme formu
        with st.form("add_user_form"):
            st.subheader("Yeni Kullanıcı Ekle")
            new_username = st.text_input("Kullanıcı Adı")
            new_password = st.text_input("Şifre", type="password")

            col1, col2 = st.columns(2)
            with col1:
                is_admin = st.checkbox("Admin Yetkisi")
                can_add_product = st.checkbox("Ürün Tanımlama Yetkisi")
            with col2:
                can_view_reports = st.checkbox("Rapor Görüntüleme Yetkisi")
                can_manage_inventory = st.checkbox("Stok Yönetimi Yetkisi")

            if st.form_submit_button("Kullanıcı Ekle"):
                if new_username and new_password:
                    hashed_pw = hash_password(new_password)
                    success, message = add_user(
                        new_username, hashed_pw,
                        is_admin=is_admin,
                        can_add_product=can_add_product,
                        can_view_reports=can_view_reports,
                        can_manage_inventory=can_manage_inventory
                    )
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Kullanıcı adı ve şifre gereklidir")

        # Mevcut kullanıcıları listele
        st.subheader("Mevcut Kullanıcılar")
        users_df = get_users()

        if not users_df.empty:
            with st.container():
                st.markdown("""
                    <style>
                        .users-container {
                            max-height: 300px;
                            overflow-y: auto;
                            padding: 1rem;
                            border: 1px solid #ddd;
                            border-radius: 4px;
                        }
                    </style>
                """, unsafe_allow_html=True)

                st.markdown('<div class="users-container">', unsafe_allow_html=True)
                for _, user in users_df.iterrows():
                    with st.expander(f"👤 {user['username']}"):
                        with st.form(f"update_user_{user['id']}"):
                            new_pw = st.text_input("Yeni Şifre (boş bırakılabilir)", type="password", key=f"pw_{user['id']}")

                            col1, col2 = st.columns(2)
                            with col1:
                                admin = st.checkbox("Admin Yetkisi", user['is_admin'], key=f"admin_{user['id']}")
                                add_product = st.checkbox("Ürün Tanımlama", user['can_add_product'], key=f"prod_{user['id']}")
                            with col2:
                                view_reports = st.checkbox("Rapor Görüntüleme", user['can_view_reports'], key=f"report_{user['id']}")
                                manage_inv = st.checkbox("Stok Yönetimi", user['can_manage_inventory'], key=f"inv_{user['id']}")

                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("Güncelle"):
                                    updates = {
                                        'is_admin': admin,
                                        'can_add_product': add_product,
                                        'can_view_reports': view_reports,
                                        'can_manage_inventory': manage_inv
                                    }
                                    if new_pw:
                                        updates['password'] = hash_password(new_pw)

                                    success, message = update_user(user['id'], **updates)
                                    if success:
                                        st.success(message)
                                        st.rerun()
                                    else:
                                        st.error(message)
                            
                            with col2:
                                if st.form_submit_button("Kullanıcıyı Sil", type="secondary"):
                                    success, message = delete_user(user['id'])
                                    if success:
                                        st.success(message)
                                        st.rerun()
                                    else:
                                        st.error(message)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Henüz kullanıcı bulunmamaktadır.")