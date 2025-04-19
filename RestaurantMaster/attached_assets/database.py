import sqlite3
import pandas as pd
from datetime import datetime

def init_db():
    conn = sqlite3.connect('restaurant.db')
    c = conn.cursor()

    # Kullanıcılar tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  is_admin INTEGER DEFAULT 0,
                  can_add_product INTEGER DEFAULT 0,
                  can_view_reports INTEGER DEFAULT 0,
                  can_manage_inventory INTEGER DEFAULT 0)''')

    # Ürünler tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY,
                  name TEXT UNIQUE NOT NULL)''')

    # Stok tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS inventory
                 (id INTEGER PRIMARY KEY,
                  product_id INTEGER NOT NULL,
                  quantity REAL NOT NULL,
                  unit TEXT NOT NULL,
                  total_price REAL NOT NULL,
                  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_by INTEGER,
                  FOREIGN KEY (product_id) REFERENCES products (id),
                  FOREIGN KEY (updated_by) REFERENCES users (id))''')

    # Stok hareket tablosu
    c.execute('''CREATE TABLE IF NOT EXISTS inventory_movements
                 (id INTEGER PRIMARY KEY,
                  product_id INTEGER NOT NULL,
                  quantity_change REAL NOT NULL,
                  unit TEXT NOT NULL,
                  total_price REAL NOT NULL,
                  movement_type TEXT NOT NULL,
                  movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  user_id INTEGER,
                  FOREIGN KEY (product_id) REFERENCES products (id),
                  FOREIGN KEY (user_id) REFERENCES users (id))''')

    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect('restaurant.db')
    conn.row_factory = sqlite3.Row
    return conn

def add_user(username, password, is_admin=0, can_add_product=0, can_view_reports=0, can_manage_inventory=0):
    if not username or not password:
        return False, "Kullanıcı adı ve şifre boş olamaz"

    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("""INSERT INTO users 
                    (username, password, is_admin, can_add_product, can_view_reports, can_manage_inventory) 
                    VALUES (?, ?, ?, ?, ?, ?)""",
                 (username, password, is_admin, can_add_product, can_view_reports, can_manage_inventory))
        conn.commit()
        return True, "Kullanıcı başarıyla eklendi"
    except sqlite3.IntegrityError:
        return False, "Bu kullanıcı adı zaten kullanılıyor"
    except Exception as e:
        return False, f"Beklenmeyen bir hata oluştu: {str(e)}"
    finally:
        conn.close()

def update_user(user_id, password=None, is_admin=None, can_add_product=None, can_view_reports=None, can_manage_inventory=None):
    conn = get_db()
    c = conn.cursor()
    try:
        updates = []
        params = []
        if password is not None:
            updates.append("password = ?")
            params.append(password)
        if is_admin is not None:
            updates.append("is_admin = ?")
            params.append(is_admin)
        if can_add_product is not None:
            updates.append("can_add_product = ?")
            params.append(can_add_product)
        if can_view_reports is not None:
            updates.append("can_view_reports = ?")
            params.append(can_view_reports)
        if can_manage_inventory is not None:
            updates.append("can_manage_inventory = ?")
            params.append(can_manage_inventory)

        if not updates:
            return False, "Güncellenecek alan belirtilmedi"

        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        params.append(user_id)

        c.execute(query, params)
        conn.commit()
        return True, "Kullanıcı başarıyla güncellendi"
    except Exception as e:
        return False, f"Güncelleme sırasında hata oluştu: {str(e)}"
    finally:
        conn.close()

def get_users():
    conn = get_db()
    df = pd.read_sql_query("""
        SELECT id, username, is_admin, can_add_product, can_view_reports, can_manage_inventory 
        FROM users
        ORDER BY username
    """, conn)
    conn.close()
    return df

def delete_user(user_id):
    if not user_id:
        return False, "Geçersiz kullanıcı ID'si"
    
    conn = get_db()
    c = conn.cursor()
    try:
        # Admin kontrolü
        c.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        admin_count = c.fetchone()[0]
        
        c.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        
        if user and user[0] and admin_count <= 1:
            return False, "Son admin kullanıcısı silinemez"
            
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        if c.rowcount == 0:
            return False, "Kullanıcı bulunamadı"
            
        conn.commit()
        return True, "Kullanıcı başarıyla silindi"
    except Exception as e:
        return False, f"Kullanıcı silinirken hata oluştu: {str(e)}"
    finally:
        conn.close()

def check_user_permission(user_id, permission):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(f"SELECT {permission} FROM users WHERE id = ?", (user_id,))
        result = c.fetchone()
        return bool(result[0]) if result else False
    finally:
        conn.close()

def add_product(name):
    if not name:
        return False, "Ürün adı boş olamaz"

    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO products (name) VALUES (?)", (name,))
        conn.commit()
        return True, "Ürün başarıyla eklendi"
    except sqlite3.IntegrityError:
        return False, "Bu ürün zaten tanımlı"
    except Exception as e:
        return False, f"Beklenmeyen bir hata oluştu: {str(e)}"
    finally:
        conn.close()

def get_products():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM products ORDER BY name", conn)
    conn.close()
    return df

def add_inventory_movement(product_id, quantity, unit, total_price, user_id):
    if not product_id or not unit or total_price < 0:
        return False, "Lütfen tüm alanları doğru şekilde doldurun"

    conn = get_db()
    c = conn.cursor()
    try:
        # Önce stok kaydını kontrol et/güncelle
        c.execute("SELECT id FROM inventory WHERE product_id = ?", (product_id,))
        inv_record = c.fetchone()

        if inv_record:
            c.execute("""UPDATE inventory 
                        SET quantity = quantity + ?,
                            unit = ?,
                            total_price = total_price + ?,
                            last_updated = CURRENT_TIMESTAMP,
                            updated_by = ?
                        WHERE product_id = ?""",
                     (quantity, unit, total_price, user_id, product_id))
        else:
            c.execute("""INSERT INTO inventory 
                        (product_id, quantity, unit, total_price, updated_by)
                        VALUES (?, ?, ?, ?, ?)""",
                     (product_id, quantity, unit, total_price, user_id))

        # Hareket kaydı ekle
        c.execute("""INSERT INTO inventory_movements 
                    (product_id, quantity_change, unit, total_price, movement_type, user_id)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                 (product_id, quantity, unit, total_price, 'update', user_id))

        conn.commit()
        return True, "Stok başarıyla güncellendi"
    except sqlite3.IntegrityError:
        return False, "Ürün veya kullanıcı bulunamadı"
    except Exception as e:
        return False, f"Beklenmeyen bir hata oluştu: {str(e)}"
    finally:
        conn.close()

def get_inventory_report(start_date, end_date):
    conn = get_db()
    query = """
    SELECT 
        p.name as product_name,
        i.unit,
        i.total_price,
        i.quantity as current_quantity,
        SUM(im.quantity_change) as total_movement,
        COUNT(im.id) as movement_count,
        i.total_price as total_value
    FROM products p
    LEFT JOIN inventory i ON p.id = i.product_id
    LEFT JOIN inventory_movements im ON p.id = im.product_id
    AND im.movement_date BETWEEN ? AND ?
    GROUP BY p.id
    ORDER BY p.name
    """
    df = pd.read_sql_query(query, conn, params=[start_date, end_date])
    conn.close()
    return df

def get_inventory():
    conn = get_db()
    df = pd.read_sql_query("""
        SELECT p.name as product_name, i.* 
        FROM inventory i 
        JOIN products p ON i.product_id = p.id
    """, conn)
    conn.close()
    return df

def get_latest_inventory_movements(limit=5):
    conn = get_db()
    query = """
    SELECT 
        p.name as product_name,
        im.id as movement_id,
        im.quantity_change as quantity,
        im.unit,
        im.total_price,
        im.movement_date,
        datetime(im.movement_date, 'localtime') as local_date
    FROM inventory_movements im
    JOIN products p ON im.product_id = p.id
    ORDER BY im.movement_date DESC
    LIMIT ?
    """
    try:
        df = pd.read_sql_query(query, conn, params=[limit])
        return df.to_dict('records') if not df.empty else None
    except Exception as e:
        print(f"Hata: {str(e)}")
        return None
    finally:
        conn.close()

def delete_inventory_movement(movement_id):
    if not movement_id:
        return False, "Geçersiz hareket ID'si"

    conn = get_db()
    c = conn.cursor()
    try:
        # Önce hareketin detaylarını al
        c.execute("""
            SELECT product_id, quantity_change, unit
            FROM inventory_movements
            WHERE id = ?
        """, (movement_id,))
        movement = c.fetchone()

        if not movement:
            return False, "Hareket bulunamadı"

        product_id, quantity, unit = movement

        # Stok miktarını güncelle
        c.execute("""
            UPDATE inventory 
            SET quantity = quantity - ?
            WHERE product_id = ? AND unit = ?
        """, (quantity, product_id, unit))

        # Hareketi sil
        c.execute("DELETE FROM inventory_movements WHERE id = ?", (movement_id,))

        conn.commit()
        return True, "Stok hareketi başarıyla silindi"
    except Exception as e:
        return False, f"Stok hareketi silinirken hata oluştu: {str(e)}"
    finally:
        conn.close()

def delete_product(product_id):
    if not product_id:
        return False, "Geçersiz ürün ID'si"

    conn = get_db()
    c = conn.cursor()
    try:
        # İlk olarak bu ürünün stok hareketleri ve stok kaydı var mı kontrol et
        c.execute("SELECT COUNT(*) FROM inventory_movements WHERE product_id = ?", (product_id,))
        movement_count = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM inventory WHERE product_id = ?", (product_id,))
        inventory_count = c.fetchone()[0]

        if movement_count > 0 or inventory_count > 0:
            return False, "Bu ürüne ait stok hareketleri bulunmaktadır. Önce stok kayıtlarını temizleyiniz."

        # Ürünü sil
        c.execute("DELETE FROM products WHERE id = ?", (product_id,))
        if c.rowcount == 0:
            return False, "Ürün bulunamadı"

        conn.commit()
        return True, "Ürün başarıyla silindi"
    except Exception as e:
        return False, f"Ürün silinirken hata oluştu: {str(e)}"
    finally:
        conn.close()

def get_detailed_movements_report(start_date, end_date):
    conn = get_db()
    query = """
    SELECT 
        datetime(im.movement_date, 'localtime') as "TARİH",
        p.name as "ÜRÜN ADI",
        im.quantity_change as "MİKTAR",
        im.unit as "BİRİM",
        ROUND(CAST(im.total_price as FLOAT) / CAST(im.quantity_change as FLOAT), 2) as "BİRİM FİYAT",
        im.total_price as "TOPLAM FİYAT"
    FROM inventory_movements im
    JOIN products p ON im.product_id = p.id
    WHERE im.movement_date BETWEEN ? AND ?
    ORDER BY im.movement_date DESC
    """
    df = pd.read_sql_query(query, conn, params=[start_date, end_date])
    conn.close()
    return df

def get_summary_report(start_date, end_date):
    conn = get_db()
    query = """
    SELECT 
        p.name as "ÜRÜN ADI",
        SUM(im.quantity_change) as "TOPLAM MİKTAR",
        im.unit as "BİRİM",
        SUM(im.total_price) as "TOPLAM FİYAT"
    FROM products p
    LEFT JOIN inventory_movements im ON p.id = im.product_id
    WHERE im.movement_date BETWEEN ? AND ?
    GROUP BY p.id, p.name, im.unit
    ORDER BY p.name
    """
    df = pd.read_sql_query(query, conn, params=[start_date, end_date])
    conn.close()
    return df