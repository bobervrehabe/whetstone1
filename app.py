from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import sqlite3
import hashlib
import re
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'whetstone_secret_key_2024_secure'
CORS(app)

# ==================== БАЗА ДАННЫХ ====================

def init_db():
    """Инициализация базы данных SQLite"""
    conn = sqlite3.connect('whetstone.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            role TEXT DEFAULT 'user'
        )
    ''')
    
    # Таблица товаров
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            brand TEXT,
            price REAL NOT NULL,
            original_price REAL,
            description TEXT,
            category TEXT,
            images TEXT,
            discount INTEGER DEFAULT 0,
            installment INTEGER,
            badge TEXT,
            stock INTEGER DEFAULT 10,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица корзины
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # Таблица заказов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount REAL,
            status TEXT DEFAULT 'pending',
            pickup_point TEXT,
            items TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Таблица пунктов выдачи
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pickup_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            work_time TEXT,
            city TEXT DEFAULT 'Москва'
        )
    ''')
    
    # Таблица отзывов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            rating INTEGER,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # Добавляем тестовые данные
    add_test_data(cursor)
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def add_test_data(cursor):
    """Добавление тестовых данных в БД"""
    
    # Проверяем, есть ли уже пункты выдачи
    cursor.execute('SELECT COUNT(*) FROM pickup_points')
    if cursor.fetchone()[0] == 0:
        pickup_data = [
            ('ТЦ "Европолис", м. Багратионовская', 'Москва, ул. Киевская, д. 2', '10:00 - 22:00', 'Москва'),
            ('ТЦ "Авиапарк", м. ЦСКА', 'Москва, Ходынский б-р, д. 4', '10:00 - 23:00', 'Москва'),
            ('ТЦ "Метрополис", м. Войковская', 'Москва, Ленинградское ш., д. 16А', '10:00 - 22:00', 'Москва'),
            ('ТЦ "Океания", м. Славянский бульвар', 'Москва, ул. Большая Дорогомиловская, д. 14', '10:00 - 21:00', 'Москва'),
            ('ТЦ "Ривьера", м. Автозаводская', 'Москва, ул. Автозаводская, д. 18', '10:00 - 22:00', 'Москва')
        ]
        cursor.executemany('INSERT INTO pickup_points (name, address, work_time, city) VALUES (?, ?, ?, ?)', pickup_data)
        print("✅ Добавлены пункты выдачи")
    
    # Проверяем, есть ли уже товары
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        products_data = [
            ('Balenciaga 3XL Extreme Lace', 'Balenciaga', 99900, 149900, 
             'Массивные кроссовки с эффектом старения, кружевные вставки. Лимитированная коллекция.', 
             'Обувь', 
             'https://st-cdn.tsum.com/sig/d053e3b8d393e5cfb5b7e8edfe974dcc/width/400/i/90/28/87/b1/82a2b512-effb-49a7-987a-f9152dd12dc6.jpg|https://st-cdn.tsum.com/sig/6ed982b8e1745ada9ced6bcbecd020a9/width/400/i/90/28/87/b1/91553352-cf68-11f0-b80d-b4969139ea48.jpg|https://st-cdn.tsum.com/sig/a2662d2b5ef60b6be706dd9e38153071/width/400/i/90/28/87/b1/916dd69c-cf68-11f0-b80d-b4969139ea48.jpg',
             33, 8325, 'ХИТ', 10),
            ('Vetements Oversized Hoodie', 'Vetements', 45000, 65000,
             'Худи оверсайз с фирменной графикой, мягкий футер, принт на спине. Идеально для стритвира.',
             'Худи',
             'https://st-cdn.tsum.com/sig/c0f503c5df4835f46ec5d7a802c070cb/width/400/i/34/9d/5a/3d/2e7b7c61-f365-42b8-bcfc-b1f9ec405106.jpg|https://st-cdn.tsum.com/sig/cc9c5ba01aa84cf9fb1fefed30a5aa07/width/400/i/34/9d/5a/3d/9ce1d164-81d2-47e0-8862-f8180dfb6480.jpg|https://st-cdn.tsum.com/sig/cbfdab53ae41bd492d57d880be05ad6c/width/400/i/34/9d/5a/3d/fb01b148-4c36-41bc-abf6-33d62ac96395.jpg',
             31, 3750, 'НОВИНКА', 15),
            ('Rick Owens Cargo Pants', 'Rick Owens', 82000, 115000,
             'Карго-штаны из плотного хлопка, многослойный крой, люверсы и ремни. Авангардный стиль.',
             'Штаны',
             'https://st-cdn.tsum.com/sig/294c739a80f32170548a2cb5200be7c5/width/400/i/5e/a2/7a/c2/f86c452c-9d30-4c97-842b-275fb23ddc0e.jpg|https://st-cdn.tsum.com/sig/f93ccac684d4f1428270ea73004ef831/width/400/i/5e/a2/7a/c2/f67b9952-fb88-11f0-b80d-b4969139ea48.jpg|https://st-cdn.tsum.com/sig/2aa6bffeca9dbc3ebf1640f3b16f2079/width/400/i/5e/a2/7a/c2/f685e5df-fb88-11f0-b80d-b4969139ea48.jpg',
             29, 6834, None, 8),
            ('Maison Margiela Tabi Boots', 'Maison Margiela', 129000, 189000,
             'Культовые ботинки с раздвоенным мысом, кожаная отделка, устойчивая подошва.',
             'Обувь',
             'https://st-cdn.tsum.com/sig/7b611eb3d957ad5f3a2ac4cb1a631b7b/width/400/i/86/08/13/71/275c2372-bf8b-4f1b-81b1-619d57a39598.jpg|https://st-cdn.tsum.com/sig/cb9f2053784e27c3a47c994688b84a33/width/400/i/86/08/13/71/ee886ff6-6446-495c-a84d-4a93eb10ba1f.jpg|https://st-cdn.tsum.com/sig/88dc0c921c6356c611ff585601328af8/width/400/i/86/08/13/71/6ef902d6-8c37-4db7-a898-292bd0e28ca3.jpg',
             32, 10750, 'ПРЕМИУМ', 5),
            ('Acne Studios Denim Jacket', 'Acne Studios', 52000, 75000,
             'Классическая джинсовка с потертостями, металлические пуговицы, прямой крой.',
             'Куртки',
             'https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=500&h=500&fit=crop|https://images.unsplash.com/photo-1582418702059-97ebafb35d09?w=500&h=500&fit=crop|https://images.unsplash.com/photo-1608062592965-585d0cfedfce?w=500&h=500&fit=crop',
             31, 4334, None, 12),
            ('Raf Simons Knit Sweater', 'Raf Simons', 68000, 99000,
             'Тонкий свитер из мериносовой шерсти с контрастными панелями и нашивками.',
             'Свитеры',
             'https://images.unsplash.com/photo-1620799139837-8da2ab3dffd0?w=500&h=500&fit=crop|https://images.unsplash.com/photo-1618354691373-d851c5c3a990?w=500&h=500&fit=crop|https://images.unsplash.com/photo-1535666669445-e8c15cd2e7d9?w=500&h=500&fit=crop',
             31, 5667, 'ХИТ', 7),
            ('Off-White Diagonal Tee', 'Off-White', 31000, 45000,
             'Фирменная футболка с диагональными полосами, стрелки, бирка. Хлопок премиум.',
             'Футболки',
             'https://images.unsplash.com/photo-1581655353564-df123a1eb100?w=500&h=500&fit=crop|https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=500&h=500&fit=crop|https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=500&h=500&fit=crop',
             31, 2584, 'НОВИНКА', 20),
            ('Stone Island Compass Vest', 'Stone Island', 78000, 112000,
             'Жилет с нашивкой compass, ветрозащитная ткань, множество карманов.',
             'Жилеты',
             'https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=500&h=500&fit=crop|https://images.unsplash.com/photo-1591369822096-ffd140ec948f?w=500&h=500&fit=crop|https://images.unsplash.com/photo-1605100804763-247f67b3557e?w=500&h=500&fit=crop',
             30, 6500, None, 6)
        ]
        cursor.executemany('''
            INSERT INTO products (name, brand, price, original_price, description, category, images, discount, installment, badge, stock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', products_data)
        print("✅ Добавлены товары")

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def hash_password(password):
    """Хеширование пароля с использованием SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def is_valid_email(email):
    """Проверка корректности email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_phone(phone):
    """Проверка корректности номера телефона"""
    pattern = r'^\+?[0-9]{10,15}$'
    return re.match(pattern, phone) is not None

def get_db():
    """Получение соединения с базой данных"""
    return sqlite3.connect('whetstone.db')

# ==================== API ЭНДПОИНТЫ ====================

# ---------- АВТОРИЗАЦИЯ ----------

@app.route('/api/register', methods=['POST'])
def register():
    """Регистрация нового пользователя"""
    data = request.json
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    phone = data.get('phone', '').strip()
    
    # Валидация
    if not username or not email or not password:
        return jsonify({'error': 'Все поля обязательны для заполнения'}), 400
    
    if len(username) < 3:
        return jsonify({'error': 'Имя пользователя должно содержать минимум 3 символа'}), 400
    
    if not is_valid_email(email):
        return jsonify({'error': 'Некорректный email'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Пароль должен содержать минимум 6 символов'}), 400
    
    if phone and not is_valid_phone(phone):
        return jsonify({'error': 'Некорректный номер телефона'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        hashed = hash_password(password)
        cursor.execute('''
            INSERT INTO users (username, email, password, full_name, phone)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email, hashed, full_name, phone))
        conn.commit()
        user_id = cursor.lastrowid
        
        return jsonify({
            'success': True,
            'message': 'Регистрация успешна',
            'user_id': user_id,
            'username': username
        }), 201
        
    except sqlite3.IntegrityError as e:
        if 'username' in str(e):
            return jsonify({'error': 'Пользователь с таким именем уже существует'}), 400
        elif 'email' in str(e):
            return jsonify({'error': 'Пользователь с таким email уже существует'}), 400
        return jsonify({'error': 'Ошибка при регистрации'}), 400
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    """Авторизация пользователя"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Введите имя пользователя и пароль'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, username, email, full_name, phone, role 
        FROM users 
        WHERE username = ? AND password = ?
    ''', (username, hash_password(password)))
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['role'] = user[5]
        
        # Обновляем время последнего входа
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user[0],))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Вход выполнен успешно',
            'user': {
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'full_name': user[3],
                'phone': user[4],
                'role': user[5]
            }
        }), 200
    
    return jsonify({'error': 'Неверное имя пользователя или пароль'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    """Выход из системы"""
    session.clear()
    return jsonify({'success': True, 'message': 'Выход выполнен'}), 200

@app.route('/api/profile', methods=['GET'])
def get_profile():
    """Получение информации о пользователе"""
    if 'user_id' not in session:
        return jsonify({'error': 'Необходима авторизация'}), 401
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username, email, full_name, phone, created_at, last_login, role
        FROM users WHERE id = ?
    ''', (session['user_id'],))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'full_name': user[3],
            'phone': user[4],
            'created_at': user[5],
            'last_login': user[6],
            'role': user[7]
        }), 200
    
    return jsonify({'error': 'Пользователь не найден'}), 404

# ---------- ТОВАРЫ ----------

@app.route('/api/products', methods=['GET'])
def get_products():
    """Получение списка всех товаров"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, brand, price, original_price, description, 
               category, images, discount, installment, badge, stock
        FROM products
        WHERE stock > 0
        ORDER BY id
    ''')
    products = cursor.fetchall()
    conn.close()
    
    result = []
    for p in products:
        result.append({
            'id': p[0],
            'name': p[1],
            'brand': p[2],
            'price': p[3],
            'originalPrice': p[4],
            'description': p[5],
            'category': p[6],
            'images': p[7].split('|') if p[7] else [],
            'discount': p[8],
            'installment': p[9],
            'badge': p[10],
            'stock': p[11]
        })
    
    return jsonify(result), 200

@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Получение информации о конкретном товаре"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, brand, price, original_price, description, 
               category, images, discount, installment, badge, stock
        FROM products WHERE id = ?
    ''', (product_id,))
    p = cursor.fetchone()
    conn.close()
    
    if not p:
        return jsonify({'error': 'Товар не найден'}), 404
    
    return jsonify({
        'id': p[0],
        'name': p[1],
        'brand': p[2],
        'price': p[3],
        'originalPrice': p[4],
        'description': p[5],
        'category': p[6],
        'images': p[7].split('|') if p[7] else [],
        'discount': p[8],
        'installment': p[9],
        'badge': p[10],
        'stock': p[11]
    }), 200

# ---------- ПУНКТЫ ВЫДАЧИ ----------

@app.route('/api/pickup-points', methods=['GET'])
def get_pickup_points():
    """Получение списка пунктов выдачи"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, address, work_time, city FROM pickup_points')
    points = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        'id': p[0],
        'name': p[1],
        'address': p[2],
        'workTime': p[3],
        'city': p[4]
    } for p in points]), 200

# ---------- КОРЗИНА ----------

@app.route('/api/cart', methods=['GET'])
def get_cart():
    """Получение корзины пользователя"""
    if 'user_id' not in session:
        return jsonify({'error': 'Необходима авторизация'}), 401
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, c.product_id, c.quantity, p.name, p.price, p.images, p.brand
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', (session['user_id'],))
    cart = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        'id': item[0],
        'productId': item[1],
        'quantity': item[2],
        'name': item[3],
        'price': item[4],
        'image': item[5].split('|')[0] if item[5] else '',
        'brand': item[6]
    } for item in cart]), 200

@app.route('/api/cart', methods=['POST'])
def add_to_cart():
    """Добавление товара в корзину"""
    if 'user_id' not in session:
        return jsonify({'error': 'Необходима авторизация'}), 401
    
    data = request.json
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    if not product_id:
        return jsonify({'error': 'ID товара обязателен'}), 400
    
    if quantity < 1:
        return jsonify({'error': 'Количество должно быть больше 0'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Проверяем наличие товара в корзине
    cursor.execute('SELECT id, quantity FROM cart WHERE user_id = ? AND product_id = ?',
                  (session['user_id'], product_id))
    existing = cursor.fetchone()
    
    try:
        if existing:
            cursor.execute('UPDATE cart SET quantity = quantity + ? WHERE id = ?',
                          (quantity, existing[0]))
        else:
            cursor.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)',
                          (session['user_id'], product_id, quantity))
        conn.commit()
        return jsonify({'success': True, 'message': 'Товар добавлен в корзину'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/cart/<int:product_id>', methods=['DELETE'])
def remove_from_cart(product_id):
    """Удаление товара из корзины"""
    if 'user_id' not in session:
        return jsonify({'error': 'Необходима авторизация'}), 401
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cart WHERE user_id = ? AND product_id = ?',
                  (session['user_id'], product_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Товар удален из корзины'}), 200

@app.route('/api/cart/<int:product_id>', methods=['PUT'])
def update_cart_quantity(product_id):
    """Обновление количества товара в корзине"""
    if 'user_id' not in session:
        return jsonify({'error': 'Необходима авторизация'}), 401
    
    data = request.json
    quantity = data.get('quantity', 1)
    
    if quantity < 1:
        return jsonify({'error': 'Количество должно быть больше 0'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE cart SET quantity = ? WHERE user_id = ? AND product_id = ?',
                  (quantity, session['user_id'], product_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Количество обновлено'}), 200

@app.route('/api/cart/clear', methods=['DELETE'])
def clear_cart():
    """Очистка корзины пользователя"""
    if 'user_id' not in session:
        return jsonify({'error': 'Необходима авторизация'}), 401
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cart WHERE user_id = ?', (session['user_id'],))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Корзина очищена'}), 200

# ---------- ЗАКАЗЫ ----------

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Создание нового заказа"""
    if 'user_id' not in session:
        return jsonify({'error': 'Необходима авторизация'}), 401
    
    data = request.json
    pickup_point_id = data.get('pickup_point_id')
    
    if not pickup_point_id:
        return jsonify({'error': 'Выберите пункт выдачи'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Получаем корзину пользователя
    cursor.execute('''
        SELECT c.product_id, c.quantity, p.name, p.price
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?
    ''', (session['user_id'],))
    cart_items = cursor.fetchall()
    
    if not cart_items:
        conn.close()
        return jsonify({'error': 'Корзина пуста'}), 400
    
    # Получаем пункт выдачи
    cursor.execute('SELECT name FROM pickup_points WHERE id = ?', (pickup_point_id,))
    pickup = cursor.fetchone()
    
    if not pickup:
        conn.close()
        return jsonify({'error': 'Пункт выдачи не найден'}), 404
    
    # Вычисляем общую сумму
    total = sum(item[2] * item[3] for item in cart_items)
    
    # Формируем строку с товарами
    items_str = '|'.join([f"{item[0]}:{item[1]}" for item in cart_items])
    
    try:
        # Создаём заказ
        cursor.execute('''
            INSERT INTO orders (user_id, total_amount, pickup_point, items, status)
            VALUES (?, ?, ?, ?, 'pending')
        ''', (session['user_id'], total, pickup[0], items_str))
        order_id = cursor.lastrowid
        
        # Очищаем корзину
        cursor.execute('DELETE FROM cart WHERE user_id = ?', (session['user_id'],))
        
        # Уменьшаем количество товаров на складе
        for item in cart_items:
            cursor.execute('UPDATE products SET stock = stock - ? WHERE id = ?',
                          (item[1], item[0]))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Заказ оформлен успешно',
            'order_id': order_id,
            'total': total
        }), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Получение заказов пользователя"""
    if 'user_id' not in session:
        return jsonify({'error': 'Необходима авторизация'}), 401
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, order_date, total_amount, status, pickup_point, items
        FROM orders
        WHERE user_id = ?
        ORDER BY order_date DESC
    ''', (session['user_id'],))
    orders = cursor.fetchall()
    conn.close()
    
    result = []
    for order in orders:
        # Парсим товары
        items = []
        if order[5]:
            for item_str in order[5].split('|'):
                parts = item_str.split(':')
                if len(parts) == 2:
                    # Получаем название товара
                    conn2 = get_db()
                    cursor2 = conn2.cursor()
                    cursor2.execute('SELECT name, price FROM products WHERE id = ?', (int(parts[0]),))
                    product = cursor2.fetchone()
                    conn2.close()
                    if product:
                        items.append({
                            'name': product[0],
                            'quantity': int(parts[1]),
                            'price': product[1]
                        })
        
        result.append({
            'id': order[0],
            'date': order[1],
            'total': order[2],
            'status': order[3],
            'pickup': order[4],
            'items': items
        })
    
    return jsonify(result), 200

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    """Получение информации о конкретном заказе"""
    if 'user_id' not in session:
        return jsonify({'error': 'Необходима авторизация'}), 401
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, order_date, total_amount, status, pickup_point, items
        FROM orders
        WHERE id = ? AND user_id = ?
    ''', (order_id, session['user_id']))
    order = cursor.fetchone()
    conn.close()
    
    if not order:
        return jsonify({'error': 'Заказ не найден'}), 404
    
    return jsonify({
        'id': order[0],
        'date': order[1],
        'total': order[2],
        'status': order[3],
        'pickup': order[4],
        'items': order[5]
    }), 200

# ==================== ГЛАВНАЯ СТРАНИЦА ====================

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

# ==================== ЗАПУСК ====================

if __name__ == '__main__':
    # Создаём папку для шаблонов, если её нет
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Инициализируем базу данных
    init_db()
    
    # Запускаем сервер
    app.run(debug=True, host='0.0.0.0', port=5000)