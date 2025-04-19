from database import init_db, add_product, add_inventory_movement, add_user
from auth import hash_password
import time

def create_demo_data():
    # Veritabanını başlat
    init_db()
    
    print("Demo veriler oluşturuluyor...")
    
    # Departmanlar için örnek ürünler oluştur
    departments = ["TEMİZLİK", "BAR", "MUTFAK", "İÇECEK", "PASTA", "DONDURMA"]
    
    # Her departman için örnek ürünler
    products = {
        "TEMİZLİK": ["Sıvı Deterjan", "Çamaşır Suyu", "Yüzey Temizleyici", "Yer Temizleme Maddesi", "Cam Temizleyici"],
        "BAR": ["Viski", "Votka", "Cin", "Rom", "Likör", "Tekila"],
        "MUTFAK": ["Domates", "Patates", "Soğan", "Salatalık", "Biber", "Havuç", "Pirinç", "Makarna"],
        "İÇECEK": ["Kola", "Fanta", "Meyve Suyu", "Gazoz", "Ayran", "Su", "Soda"],
        "PASTA": ["Un", "Şeker", "Yumurta", "Kabartma Tozu", "Süt", "Krema", "Çikolata"],
        "DONDURMA": ["Vanilya", "Çikolata", "Çilek", "Limon", "Fıstık", "Karamel"]
    }
    
    # Her departman için ürünleri ekle
    product_ids = {}
    
    for department, prod_list in products.items():
        for product_name in prod_list:
            success, message = add_product(product_name, department)
            if success:
                # Ürün ID'sini almak için mesajı parse et (örn: "Ürün başarıyla eklendi. ID: 5")
                product_id = int(message.split("ID:")[-1].strip())
                product_ids[product_name] = product_id
                print(f"Eklendi: {product_name} - {department}")
            else:
                print(f"Eklenemedi: {product_name} - Hata: {message}")
            time.sleep(0.1)  # Kısa bir gecikme
    
    # Demo kullanıcılar oluştur
    users = [
        {"username": "satın_alma", "password": "1234", "is_admin": 0, "can_add_product": 1, "can_view_reports": 1, "can_manage_inventory": 1},
        {"username": "şef", "password": "1234", "is_admin": 0, "can_add_product": 1, "can_view_reports": 1, "can_manage_inventory": 0},
        {"username": "barmen", "password": "1234", "is_admin": 0, "can_add_product": 0, "can_view_reports": 0, "can_manage_inventory": 1}
    ]
    
    for user in users:
        hashed_password = hash_password(user["password"])
        success, message = add_user(
            user["username"], 
            hashed_password, 
            is_admin=user["is_admin"],
            can_add_product=user["can_add_product"],
            can_view_reports=user["can_view_reports"],
            can_manage_inventory=user["can_manage_inventory"]
        )
        if success:
            print(f"Kullanıcı eklendi: {user['username']}")
        else:
            print(f"Kullanıcı eklenemedi: {user['username']} - Hata: {message}")
    
    # Örnek stok hareketleri oluştur
    # Admin kullanıcısının ID'si genellikle 1'dir
    admin_id = 1
    
    # Birkaç örnek stok hareketi ekle
    sample_inventory = [
        {"product_name": "Sıvı Deterjan", "quantity": 5, "unit": "litre", "price": 150},
        {"product_name": "Çamaşır Suyu", "quantity": 10, "unit": "litre", "price": 120},
        {"product_name": "Viski", "quantity": 3, "unit": "litre", "price": 800},
        {"product_name": "Votka", "quantity": 4, "unit": "litre", "price": 600},
        {"product_name": "Domates", "quantity": 10, "unit": "kg", "price": 150},
        {"product_name": "Patates", "quantity": 20, "unit": "kg", "price": 200},
        {"product_name": "Kola", "quantity": 30, "unit": "litre", "price": 300},
        {"product_name": "Su", "quantity": 50, "unit": "litre", "price": 100},
        {"product_name": "Un", "quantity": 25, "unit": "kg", "price": 250},
        {"product_name": "Şeker", "quantity": 15, "unit": "kg", "price": 180},
        {"product_name": "Vanilya", "quantity": 5, "unit": "kg", "price": 500},
        {"product_name": "Çikolata", "quantity": 8, "unit": "kg", "price": 800}
    ]
    
    for item in sample_inventory:
        if item["product_name"] in product_ids:
            product_id = product_ids[item["product_name"]]
            success, message = add_inventory_movement(
                product_id,
                item["quantity"],
                item["unit"],
                item["price"],
                admin_id
            )
            if success:
                print(f"Stok hareketi eklendi: {item['product_name']} - {item['quantity']} {item['unit']}")
            else:
                print(f"Stok hareketi eklenemedi: {item['product_name']} - Hata: {message}")
            time.sleep(0.1)  # Kısa bir gecikme
    
    print("Demo veriler başarıyla oluşturuldu!")

if __name__ == "__main__":
    create_demo_data()