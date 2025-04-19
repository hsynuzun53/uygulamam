from database import add_user, init_db
from auth import hash_password

def create_admin():
    init_db()  # Veritabanını başlat
    
    password = "1234"
    hashed_password = hash_password(password)
    
    success, message = add_user(
        "admin", 
        hashed_password, 
        is_admin=1,
        can_add_product=1,
        can_view_reports=1,
        can_manage_inventory=1
    )
    
    if success:
        print("Admin kullanıcısı başarıyla oluşturuldu!")
    else:
        print(f"Admin kullanıcısı oluşturulurken bir hata oluştu: {message}")

if __name__ == "__main__":
    create_admin()
