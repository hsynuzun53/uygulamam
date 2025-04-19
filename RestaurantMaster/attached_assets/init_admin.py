from database import add_user, init_db
from auth import hash_password

def create_admin():
    init_db()  # Veritabanını başlat
    password = "1234"
    hashed_password = hash_password(password)
    success = add_user("admin", hashed_password, is_admin=1)
    if success:
        print("Admin kullanıcısı başarıyla oluşturuldu!")
    else:
        print("Admin kullanıcısı zaten mevcut veya bir hata oluştu!")

if __name__ == "__main__":
    create_admin()
