from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Сначала создаем приложение
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///music_store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализируем db
from extensions import db
db.init_app(app)

# Импортируем модели ПОСЛЕ инициализации db
from models import User, Product, Order, OrderItem

# Создаем таблицы
with app.app_context():
    db.create_all()
    print("Таблицы базы данных созданы!")

print("Скрипт начал работу!")  

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Это имя пользователя уже занято', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Этот email уже используется', 'error')
            return redirect(url_for('register'))
        
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash('Неверное имя пользователя или пароль', 'error')
            return redirect(url_for('login'))
        
        session['user_id'] = user.id
        session['username'] = user.username
        session['is_admin'] = user.is_admin
        
        flash('Вы успешно вошли в систему!', 'success')
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

@app.route('/products')
def products():
    all_products = Product.query.all()
    return render_template('products.html', products=all_products)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash('Для добавления товаров в корзину необходимо войти в систему', 'error')
        return redirect(url_for('login'))
    
    if 'cart' not in session:
        session['cart'] = {}
    
    cart = session['cart']
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session['cart'] = cart
    
    flash('Товар добавлен в корзину', 'success')
    return redirect(url_for('products'))

@app.route('/checkout')
def checkout():
    if 'user_id' not in session or 'cart' not in session or not session['cart']:
        flash('Ваша корзина пуста или вы не вошли в систему', 'error')
        return redirect(url_for('products'))
    
    user = User.query.get(session['user_id'])
    cart = session['cart']
    
    total_amount = 0
    order_items = []
    
    for product_id, quantity in cart.items():
        product = Product.query.get(product_id)
        if product and product.stock >= quantity:
            total_amount += product.price * quantity
            order_items.append({
                'product': product,
                'quantity': quantity,
                'price': product.price
            })
    
    if not order_items:
        flash('Нет доступных товаров для заказа', 'error')
        return redirect(url_for('products'))
    
    # Создание заказа
    new_order = Order(user_id=user.id, total_amount=total_amount)
    db.session.add(new_order)
    db.session.commit()
    
    # Добавление товаров в заказ
    for item in order_items:
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item['product'].id,
            quantity=item['quantity'],
            price=item['price']
        )
        db.session.add(order_item)
        # Уменьшение количества на складе
        item['product'].stock -= item['quantity']
    
    db.session.commit()
    session.pop('cart', None)
    
    flash('Заказ успешно оформлен!', 'success')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)