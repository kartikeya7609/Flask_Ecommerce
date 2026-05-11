import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_wtf.file import FileField, FileAllowed
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect

from flask_wtf.csrf import CSRFProtect
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///market.db'
app.config['SECRET_KEY'] = 'ec9439cfc6c796ae2029594d'
app.config["JWT_SECRET_KEY"] = "ec9439cfc6c796ae2029594d_jwt"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
app.config['WTF_CSRF_TIME_LIMIT'] = 86400  # 24 hours

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login_page"
login_manager.login_message_category = "info"

# Security Configurations
csrf = CSRFProtect(app)

@app.errorhandler(400)
def handle_csrf_error(e):
    if "CSRF token" in str(e):
        flash("Your session expired. Please try again.", category='info')
        return redirect(request.url)
    return "Bad Request", 400
jwt = JWTManager(app)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "200 per hour"],
    storage_uri="memory://",
)

csp = {
    'default-src': [
        '\'self\'',
        'https://cdn.tailwindcss.com',
        'https://cdn.jsdelivr.net',
        'https://code.jquery.com',
        'https://images.unsplash.com'
    ],
    'img-src': ['\'self\'', '*', 'data:', 'blob:'],
    'script-src': [
        '\'self\'',
        '\'unsafe-inline\'',
        'https://cdn.tailwindcss.com',
        'https://cdn.jsdelivr.net',
        'https://code.jquery.com'
    ],
    'style-src': [
        '\'self\'',
        '\'unsafe-inline\'',
        'https://cdn.tailwindcss.com',
        'https://fonts.googleapis.com'
    ],
    'font-src': ['\'self\'', 'https://fonts.gstatic.com', 'data:']
}
talisman = Talisman(app, content_security_policy=csp, force_https=False)

from forms import RegisterForm, LoginForm

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(length=30), nullable=False, unique=True)
    email_address = db.Column(db.String(length=50), nullable=False, unique=True)
    password_hash = db.Column(db.String(length=60), nullable=False)
    budget = db.Column(db.Float(), nullable=False, default=10000.0)
    role = db.Column(db.String(length=20), nullable=False, default='consumer')
    
    # New Personal & Shipping Info
    full_name = db.Column(db.String(length=50), nullable=True)
    phone_number = db.Column(db.String(length=15), nullable=True)
    address = db.Column(db.String(length=100), nullable=True)
    city = db.Column(db.String(length=50), nullable=True)
    state = db.Column(db.String(length=50), nullable=True)
    zip_code = db.Column(db.String(length=10), nullable=True)

    cart_items = db.relationship('CartItem', backref='user', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)
    wishlist = db.relationship('Wishlist', backref='user', uselist=False, lazy=True)
    addresses = db.relationship('Address', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)

    def __init__(self, username, email_address, password, role='consumer', **kwargs):
        self.username = username
        self.email_address = email_address
        self.password = password
        self.role = role
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def prettier_budget(self):
        if len(str(int(self.budget))) >= 4:
            return f'₹{str(int(self.budget))[:-3]},{str(int(self.budget))[-3:]}'
        else:
            return f"₹{int(self.budget)}"

    @property
    def password(self):
        return self.password

    @password.setter
    def password(self, plain_text_password):
        self.password_hash = bcrypt.generate_password_hash(plain_text_password).decode('utf-8')

    def check_password_correction(self, attempted_password):
        return bcrypt.check_password_hash(self.password_hash, attempted_password)

    def can_purchase(self, total_price):
        return self.budget >= total_price

class CartItem(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer(), db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer(), nullable=False, default=1)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    
    item = db.relationship('Item')

    def __init__(self, user_id, item_id, quantity=1):
        self.user_id = user_id
        self.item_id = item_id
        self.quantity = quantity

class Order(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
    total_price = db.Column(db.Float(), nullable=False)
    status = db.Column(db.String(length=30), nullable=False, default='Ordered')
    date_ordered = db.Column(db.DateTime, default=datetime.utcnow)
    address_id = db.Column(db.Integer(), db.ForeignKey('address.id'), nullable=True)
    items = db.relationship('OrderItem', backref='order', lazy=True)
    address = db.relationship('Address')

    def __init__(self, user_id, total_price, status='Ordered'):
        self.user_id = user_id
        self.total_price = total_price
        self.status = status

class OrderItem(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    order_id = db.Column(db.Integer(), db.ForeignKey('order.id'), nullable=False)
    item_id = db.Column(db.Integer(), db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer(), nullable=False)
    price = db.Column(db.Float(), nullable=False)
    
    item = db.relationship('Item')

    def __init__(self, order_id, item_id, quantity, price):
        self.order_id = order_id
        self.item_id = item_id
        self.quantity = quantity
        self.price = price

class Wishlist(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
    is_public = db.Column(db.Boolean(), default=False)
    items = db.relationship('WishlistItem', backref='wishlist', lazy=True)

    def __init__(self, user_id, is_public=False):
        self.user_id = user_id
        self.is_public = is_public

class WishlistItem(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    wishlist_id = db.Column(db.Integer(), db.ForeignKey('wishlist.id'), nullable=False)
    item_id = db.Column(db.Integer(), db.ForeignKey('item.id'), nullable=False)
    
    item = db.relationship('Item')

    def __init__(self, wishlist_id, item_id):
        self.wishlist_id = wishlist_id
        self.item_id = item_id

class Address(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(length=50), nullable=False)
    phone_number = db.Column(db.String(length=15), nullable=False)
    address_line = db.Column(db.String(length=100), nullable=False)
    city = db.Column(db.String(length=50), nullable=False)
    state = db.Column(db.String(length=50), nullable=False)
    zip_code = db.Column(db.String(length=10), nullable=False)
    is_default = db.Column(db.Boolean(), default=False)

    def __init__(self, user_id, full_name, phone_number, address_line, city, state, zip_code, is_default=False):
        self.user_id = user_id
        self.full_name = full_name
        self.phone_number = phone_number
        self.address_line = address_line
        self.city = city
        self.state = state
        self.zip_code = zip_code
        self.is_default = is_default

class Coupon(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    code = db.Column(db.String(length=20), nullable=False, unique=True)
    discount_percent = db.Column(db.Integer(), nullable=False)
    is_active = db.Column(db.Boolean(), default=True)

    def __init__(self, code, discount_percent, is_active=True):
        self.code = code
        self.discount_percent = discount_percent
        self.is_active = is_active

class Notification(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(length=255), nullable=False)
    is_read = db.Column(db.Boolean(), default=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, message):
        self.user_id = user_id
        self.message = message

def send_notification(user_id, message):
    notif = Notification(user_id=user_id, message=message)
    db.session.add(notif)
    # We don't commit here to allow it to be part of the caller's transaction

class Review(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer(), db.ForeignKey('item.id'), nullable=False)
    rating = db.Column(db.Integer(), nullable=False)
    comment = db.Column(db.String(length=1024), nullable=False)
    image_file = db.Column(db.String(length=40), nullable=True)
    seller_reply = db.Column(db.String(length=1024), nullable=True)
    is_verified = db.Column(db.Boolean(), default=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User')

    def __init__(self, user_id, item_id, rating, comment, image_file=None, seller_reply=None, is_verified=False):
        self.user_id = user_id
        self.item_id = item_id
        self.rating = rating
        self.comment = comment
        self.image_file = image_file
        self.seller_reply = seller_reply
        self.is_verified = is_verified

class Item(db.Model):
    # CHANGE 1: Added the primary key 'id' column. This is required by all database tables.
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(length=30), nullable=False, unique=True)
    price = db.Column(db.Float(), nullable=False)
    barcode = db.Column(db.String(length=12), nullable=False, unique=True)
    description = db.Column(db.String(length=1024), nullable=False)
    user_file = db.Column(db.String(length=40), nullable=False, default='default.jpg')
    seller_id = db.Column(db.Integer(), db.ForeignKey('user.id'))
    seller = db.relationship('User', backref='items_sold', foreign_keys=[seller_id])
    stock = db.Column(db.Integer(), nullable=False, default=1)
    category = db.Column(db.String(length=30), nullable=False, default='General')
    reviews = db.relationship('Review', backref='item', lazy=True)

    @property
    def average_rating(self):
        if not self.reviews:
            return 0
        return sum([r.rating for r in self.reviews]) / len(self.reviews)

    def __init__(self, name, price, barcode, description, user_file='default.jpg', seller_id=None, stock=1, category='General', **kwargs):
        self.name = name
        self.price = price
        self.barcode = barcode
        self.description = description
        self.user_file = user_file
        self.seller_id = seller_id
        self.stock = stock
        self.category = category
        for key, value in kwargs.items():
            setattr(self, key, value)
            
    def __repr__(self):
        return f'Item {self.name}'

@app.route('/')
@app.route('/home')
def home_page():
    return redirect(url_for('market_page'))

@app.route('/market', methods=['GET', 'POST'])
@login_required
def market_page():
    if request.method == "POST":
        # Add to Cart Logic
        added_item = request.form.get('added_item')
        item_obj = Item.query.filter_by(name=added_item).first()
        if item_obj and item_obj.stock > 0:
            existing_cart_item = CartItem.query.filter_by(user_id=current_user.id, item_id=item_obj.id).first()
            if existing_cart_item:
                if existing_cart_item.quantity < item_obj.stock:
                    existing_cart_item.quantity += 1
                    flash(f"Increased {item_obj.name} quantity in your cart!", category='success')
                else:
                    flash(f"Cannot add more of {item_obj.name}. Not enough stock!", category='danger')
            else:
                new_cart_item = CartItem(user_id=current_user.id, item_id=item_obj.id, quantity=1)
                db.session.add(new_cart_item)
                flash(f"Successfully added {item_obj.name} to your cart!", category='success')
            db.session.commit()
        return redirect(url_for('market_page'))

    q = request.args.get('q')
    category_filter = request.args.get('category')
    sort = request.args.get('sort', 'random')
    page = request.args.get('page', 1, type=int)
    
    query = Item.query.filter(Item.stock > 0)
    
    if q:
        query = query.filter(Item.name.contains(q) | Item.description.contains(q) | Item.category.contains(q))
    if category_filter and category_filter != 'All':
        query = query.filter_by(category=category_filter)
    
    if sort == 'price_low':
        query = query.order_by(Item.price.asc())
    elif sort == 'price_high':
        query = query.order_by(Item.price.desc())
    elif sort == 'name':
        query = query.order_by(Item.name.asc())
    elif sort == 'category':
        query = query.order_by(Item.category.asc(), Item.name.asc())
    else:
        query = query.order_by(func.random())
        
    pagination = query.paginate(page=page, per_page=12, error_out=False)
    items = pagination.items
        
    all_categories = [c[0] for c in db.session.query(Item.category).distinct().all()]
    
    return render_template('market.html', items=items, q=q, sort=sort, 
                           categories=all_categories, active_category=category_filter,
                           pagination=pagination)

@app.route('/my_listings')
@login_required
def my_listings_page():
    if current_user.role != 'seller':
        flash("Unauthorized access.", category='danger')
        return redirect(url_for('market_page'))
    
    page = request.args.get('page', 1, type=int)
    
    pagination = Item.query.filter_by(seller_id=current_user.id).paginate(page=page, per_page=12, error_out=False)
    listed_items = pagination.items
    
    # Get all item IDs by this seller for order tracking
    all_seller_items = Item.query.filter_by(seller_id=current_user.id).all()
    item_ids = [i.id for i in all_seller_items]
    order_items = OrderItem.query.filter(OrderItem.item_id.in_(item_ids)).all()
    
    return render_template('my_listings.html', items=listed_items, order_items=order_items, pagination=pagination)

@app.route('/cart', methods=['GET'])
@login_required
def cart_page():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    # Auto-revalidation & Expiration
    revalidated = False
    expired = False
    now = datetime.utcnow()
    
    for c in cart_items:
        # 1. Expiration check (30 minutes)
        if now - c.date_added > timedelta(minutes=30):
            db.session.delete(c)
            expired = True
            continue

        # 2. Stock revalidation
        if c.item.stock < c.quantity:
            if c.item.stock <= 0:
                db.session.delete(c)
                flash(f"Oops! {c.item.name} just sold out and was removed from your cart.", category='warning')
            else:
                c.quantity = c.item.stock
                flash(f"Stock for {c.item.name} changed. Adjusted your cart to {c.item.stock} units.", category='warning')
            revalidated = True
    
    if revalidated or expired:
        db.session.commit()
        if expired:
            flash("Some items in your cart expired and were removed.", category='info')
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    subtotal = sum([c.item.price * c.quantity for c in cart_items])
    
    # Coupon logic
    discount = 0
    coupon_id = session.get('coupon_id')
    coupon_code = None
    if coupon_id:
        coupon = Coupon.query.get(coupon_id)
        if coupon and coupon.is_active:
            discount = (subtotal * coupon.discount_percent) / 100
            coupon_code = coupon.code
        else:
            session.pop('coupon_id', None)
            
    total = subtotal - discount
    
    # Estimated delivery (4 days from now)
    est_delivery = (datetime.now() + timedelta(days=4)).strftime('%A, %b %d')
    
    return render_template('cart.html', cart_items=cart_items, total=total, subtotal=subtotal, discount=discount, est_delivery=est_delivery, coupon_code=coupon_code)

@app.route('/cart/apply_coupon', methods=['POST'])
@login_required
def apply_coupon():
    code = request.form.get('coupon_code').strip().upper()
    coupon = Coupon.query.filter_by(code=code, is_active=True).first()
    if coupon:
        session['coupon_id'] = coupon.id
        flash(f"Coupon '{code}' applied! {coupon.discount_percent}% discount added.", category='success')
    else:
        flash("Invalid or expired coupon code.", category='danger')
    return redirect(url_for('cart_page'))

@app.route('/cart/save_for_later/<int:cart_item_id>', methods=['GET', 'POST'])
@login_required
def save_for_later(cart_item_id):
    cart_item = CartItem.query.get_or_404(cart_item_id)
    if cart_item.user_id != current_user.id:
        flash("Unauthorized action.", category='danger')
        return redirect(url_for('cart_page'))
    
    item = cart_item.item
    wishlist = Wishlist.query.filter_by(user_id=current_user.id).first()
    if not wishlist:
        wishlist = Wishlist(user_id=current_user.id)
        db.session.add(wishlist)
        db.session.commit()
    
    # Check if already in wishlist
    existing_wish = WishlistItem.query.filter_by(wishlist_id=wishlist.id, item_id=item.id).first()
    if not existing_wish:
        new_wish = WishlistItem(wishlist_id=wishlist.id, item_id=item.id)
        db.session.add(new_wish)
    
    item_name = item.name
    db.session.delete(cart_item)
    db.session.commit()
    flash(f"Moved {item_name} to your Wishlist for later.", category='info')
    return redirect(url_for('cart_page'))

@app.route('/account')
@login_required
def account_page():
    # Calculate Loyalty Points (1 point per 10 spent)
    total_spent = db.session.query(func.sum(Order.total_price)).filter(Order.user_id == current_user.id).scalar() or 0.0
    loyalty_points = int(total_spent / 10)
    
    order_count = Order.query.filter_by(user_id=current_user.id).count()
    wishlist_count = 0
    if current_user.wishlist:
        wishlist_count = len(current_user.wishlist.items)
    
    recently_viewed = Item.query.order_by(Item.id.desc()).limit(4).all()
    addresses = Address.query.filter_by(user_id=current_user.id).all()
    
    badges = []
    if order_count > 5: badges.append({"name": "Elite Buyer", "icon": "🏆", "desc": "More than 5 purchases"})
    if total_spent > 1000: badges.append({"name": "High Roller", "icon": "💎", "desc": "Spent over ₹1000"})
    if current_user.role == 'consumer': badges.append({"name": "Lucky Member", "icon": "🛡️", "desc": "Verified Member"})
    
    analytics = {
        "monthly_spend": [120, 450, 300, 800, total_spent % 1000],
        "categories": ["Electronics", "Fashion", "Home"],
        "savings": int(total_spent * 0.05)
    }

    # Pre-calculate percentages for the UI to avoid template logic errors
    loyalty_progress = (loyalty_points % 1000) / 10
    
    # Pre-calculate analytics bar heights (0-100%)
    spend_data = analytics["monthly_spend"]
    max_spend = max(spend_data) if spend_data else 1
    analytics["bar_heights"] = [(v / max_spend) * 100 for v in spend_data]

    # Fetch Notifications
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.date_created.desc()).limit(10).all()
    unread_notif_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

    return render_template('profile.html', 
                           total_spent=total_spent, 
                           loyalty_points=loyalty_points,
                           loyalty_progress=loyalty_progress,
                           order_count=order_count,
                           wishlist_count=wishlist_count,
                           recently_viewed=recently_viewed,
                           badges=badges,
                           analytics=analytics,
                           addresses=addresses,
                           notifications=notifications,
                           unread_notif_count=unread_notif_count)

@app.route('/address/add', methods=['POST'])
@login_required
def add_address():
    full_name = request.form.get('full_name')
    phone = request.form.get('phone')
    address_line = request.form.get('address_line')
    city = request.form.get('city')
    state = request.form.get('state')
    zip_code = request.form.get('zip_code')
    is_default = 'is_default' in request.form

    if is_default:
        Address.query.filter_by(user_id=current_user.id).update({Address.is_default: False})

    new_address = Address(
        user_id=current_user.id,
        full_name=full_name,
        phone_number=phone,
        address_line=address_line,
        city=city,
        state=state,
        zip_code=zip_code,
        is_default=is_default
    )
    db.session.add(new_address)
    db.session.commit()
    flash("New address added successfully!", category='success')
    return redirect(url_for('account_page'))

@app.route('/address/delete/<int:address_id>', methods=['POST'])
@login_required
def delete_address(address_id):
    address = Address.query.filter_by(id=address_id, user_id=current_user.id).first_or_404()
    db.session.delete(address)
    db.session.commit()
    flash("Address deleted.", category='info')
    return redirect(url_for('account_page'))

@app.route('/address/default/<int:address_id>', methods=['POST'])
@login_required
def set_default_address(address_id):
    Address.query.filter_by(user_id=current_user.id).update({Address.is_default: False})
    address = Address.query.filter_by(id=address_id, user_id=current_user.id).first_or_404()
    address.is_default = True
    db.session.commit()
    flash("Default address updated.", category='success')
    return redirect(url_for('account_page'))

@app.route('/checkout', methods=['POST'])
@login_required
@limiter.limit("2 per minute")
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Your cart is empty!", category='danger')
        return redirect(url_for('cart_page'))
        
    total_price = sum([c.item.price * c.quantity for c in cart_items])
    
    if not current_user.can_purchase(total_price):
        flash("You do not have enough funds to complete this purchase.", category='danger')
        return redirect(url_for('cart_page'))
        
    # Process transaction
    for cart_item in cart_items:
        item = cart_item.item
        if item.stock < cart_item.quantity:
            flash(f"Sorry, {item.name} does not have enough stock.", category='danger')
            return redirect(url_for('cart_page'))
            
        # Deduct stock
        item.stock -= cart_item.quantity
        
        # Pay seller
        if item.seller_id:
            seller = User.query.get(item.seller_id)
            if seller:
                seller.budget += (item.price * cart_item.quantity)
                
    # Deduct buyer
    current_user.budget -= total_price
    
    # Create order receipt
    order = Order(user_id=current_user.id, total_price=total_price)
    db.session.add(order)
    db.session.flush() # Get order.id before commit
    
    # Create individual order items
    for cart_item in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            item_id=cart_item.item_id,
            quantity=cart_item.quantity,
            price=cart_item.item.price
        )
        db.session.add(order_item)
    
    # Clear cart
    CartItem.query.filter_by(user_id=current_user.id).delete()
    
    # Clear coupon
    session.pop('coupon_id', None)
    
    # Send Notifications to Sellers
    for seller_id in set(oi.item.seller_id for oi in order.items if oi.item.seller_id):
        send_notification(seller_id, f"New Order #LC-{order.id} received!")

    db.session.commit()
    flash(f"Purchase successful! Total paid: ₹{total_price:.2f}. <a href='{url_for('receipt_page', order_id=order.id)}' target='_blank' class='underline font-bold'>View Receipt</a>", category='success')
    return redirect(url_for('home_page'))

@app.route('/remove_from_cart/<int:cart_item_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_item_id):
    cart_item = CartItem.query.filter_by(id=cart_item_id, user_id=current_user.id).first()
    if cart_item:
        item_name = cart_item.item.name
        db.session.delete(cart_item)
        db.session.commit()
        flash(f"Removed {item_name} from your cart.", category='info')
    return redirect(url_for('cart_page'))

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login_page():
    form = LoginForm()
    if form.validate_on_submit():
        # Global Admin Override
        if form.username.data == 'admin1234' and form.password.data == 'admin':
            session['is_admin'] = True
            flash("System Access Granted. Welcome, Administrator.", category='success')
            return redirect(url_for('admin_dashboard'))

        attempted_user = User.query.filter_by(username=form.username.data).first()
        if attempted_user and attempted_user.check_password_correction(
                attempted_password=form.password.data
        ):
            login_user(attempted_user)
            # Create JWT tokens
            access_token = create_access_token(identity=attempted_user.id)
            refresh_token = create_refresh_token(identity=attempted_user.id)
            session['access_token'] = access_token
            session['refresh_token'] = refresh_token

            flash(f'Success! You are logged in as: {attempted_user.username}', category='success')
            return redirect(url_for('market_page'))
        else:
            flash('Username and password are not match! Please try again', category='danger')

    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register_page():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            flash('Username already exists! Please try a different username', category='danger')
            return render_template('register.html', form=form)
            
        email_address = User.query.filter_by(email_address=form.email_address.data).first()
        if email_address:
            flash('Email Address already exists! Please try a different email address', category='danger')
            return render_template('register.html', form=form)

        user_to_create = User(username=form.username.data,
                              email_address=form.email_address.data,
                              password=form.password.data,
                              role=form.role.data,
                              full_name=form.full_name.data,
                              phone_number=form.phone_number.data,
                              address=form.address.data,
                              city=form.city.data,
                              state=form.state.data,
                              zip_code=form.zip_code.data)
        db.session.add(user_to_create)
        db.session.commit()

        # Create wishlist for the user
        wishlist = Wishlist(user_id=user_to_create.id)
        db.session.add(wishlist)
        db.session.commit()

        login_user(user_to_create)
        flash(f"Account created successfully! You are now logged in as {user_to_create.username}", category='success')
        return redirect(url_for('market_page'))
    if form.errors != {}: #If there are not errors from the validations
        for err_msg in form.errors.values():
            flash(f'There was an error with creating a user: {err_msg}', category='danger')

    return render_template('register.html', form=form)

@app.route('/logout')
def logout_page():
    logout_user()
    flash("You have been logged out!", category='info')
    return redirect(url_for("home_page"))

@app.route('/add_item', methods=['GET', 'POST'])
@login_required
def add_item_page():
    if current_user.role != 'seller':
        flash('Only sellers can add items to the market.', category='danger')
        return redirect(url_for('market_page'))

    if request.method == 'POST':
        uploaded_file = request.files.get('user_file')

        if uploaded_file and uploaded_file.filename != '':
            
            filename = secure_filename(uploaded_file.filename)
            upload_path = os.path.join(app.root_path, 'static/uploads', filename)
            
            # Ensure the upload directory exists
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            uploaded_file.save(upload_path)
        new_item = Item(
            name=request.form['name'],
            price=float(request.form['price']), # Convert price to a float
            barcode=request.form['barcode'],
            description=request.form['description'],
            user_file=filename,
            seller_id=current_user.id,
            stock=int(request.form.get('stock', 1)),
            category=request.form.get('category', 'General')
        )
        
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('market_page'))
    
    elif request.method == 'GET':
        return render_template('data_input.html')
    else:
        return redirect(request.url)

@app.route('/wishlist')
@login_required
def wishlist_page():
    wishlist = Wishlist.query.filter_by(user_id=current_user.id).first()
    if not wishlist:
        wishlist = Wishlist(user_id=current_user.id)
        db.session.add(wishlist)
        db.session.commit()
    return render_template('wishlist.html', wishlist=wishlist)

@app.route('/wishlist/add/<int:item_id>', methods=['POST'])
@login_required
def add_to_wishlist(item_id):
    wishlist = Wishlist.query.filter_by(user_id=current_user.id).first()
    if not wishlist:
        wishlist = Wishlist(user_id=current_user.id)
        db.session.add(wishlist)
        db.session.commit()
    
    existing_item = WishlistItem.query.filter_by(wishlist_id=wishlist.id, item_id=item_id).first()
    if existing_item:
        flash("Item is already in your wishlist!", category='info')
    else:
        new_wishlist_item = WishlistItem(wishlist_id=wishlist.id, item_id=item_id)
        db.session.add(new_wishlist_item)
        db.session.commit()
        flash("Item added to wishlist!", category='success')
    return redirect(url_for('market_page'))

@app.route('/wishlist/remove/<int:wishlist_item_id>', methods=['POST'])
@login_required
def remove_from_wishlist(wishlist_item_id):
    wishlist_item = WishlistItem.query.get_or_404(wishlist_item_id)
    if wishlist_item.wishlist.user_id != current_user.id:
        flash("You do not have permission to remove this item.", category='danger')
    else:
        db.session.delete(wishlist_item)
        db.session.commit()
        flash("Item removed from wishlist.", category='info')
    return redirect(url_for('wishlist_page'))

@app.route('/wishlist/move_to_cart/<int:wishlist_item_id>', methods=['POST'])
@login_required
def move_to_cart(wishlist_item_id):
    wishlist_item = WishlistItem.query.get_or_404(wishlist_item_id)
    if wishlist_item.wishlist.user_id != current_user.id:
        flash("You do not have permission to move this item.", category='danger')
        return redirect(url_for('wishlist_page'))
    
    item = wishlist_item.item
    if item.stock > 0:
        existing_cart_item = CartItem.query.filter_by(user_id=current_user.id, item_id=item.id).first()
        if existing_cart_item:
            if existing_cart_item.quantity < item.stock:
                existing_cart_item.quantity += 1
            else:
                flash(f"Cannot add more of {item.name}. Not enough stock!", category='danger')
                return redirect(url_for('wishlist_page'))
        else:
            new_cart_item = CartItem(user_id=current_user.id, item_id=item.id, quantity=1)
            db.session.add(new_cart_item)
        
        item_name = item.name
        db.session.delete(wishlist_item)
        db.session.commit()
        flash(f"Moved {item_name} to your cart!", category='success')
    else:
        flash(f"{item.name} is out of stock!", category='danger')
    
    return redirect(url_for('cart_page'))

@app.route('/wishlist/toggle_privacy', methods=['POST'])
@login_required
def toggle_wishlist_privacy():
    wishlist = Wishlist.query.filter_by(user_id=current_user.id).first()
    if wishlist:
        wishlist.is_public = not wishlist.is_public
        db.session.commit()
        status = "public" if wishlist.is_public else "private"
        flash(f"Your wishlist is now {status}.", category='info')
    return redirect(url_for('wishlist_page'))

@app.route('/upload_csv', methods=['POST'])
@login_required
@limiter.limit("5 per hour")
def upload_csv():
    if current_user.role != 'seller':
        flash("Unauthorized action.", category='danger')
        return redirect(url_for('market_page'))
    
    file = request.files.get('file')
    if not file or not file.filename.endswith('.csv'):
        flash("Please upload a valid CSV file.", category='danger')
        return redirect(url_for('add_item_page'))
    
    try:
        import io
        import csv
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        success_count = 0
        error_messages = []
        
        for row in csv_input:
            try:
                name = row.get('name')
                price = float(row.get('price', 0))
                barcode = row.get('barcode')
                description = row.get('description', '')
                stock = int(row.get('stock', 1))
                category = row.get('category', 'General')
                image = row.get('user_file', 'default.jpg')
                
                if not name or not barcode:
                    continue

                if Item.query.filter_by(name=name).first():
                    error_messages.append(f"Skipped '{name}': Name exists.")
                    continue
                if Item.query.filter_by(barcode=barcode).first():
                    error_messages.append(f"Skipped '{name}': Barcode exists.")
                    continue
                
                new_item = Item(
                    name=name,
                    price=price,
                    barcode=barcode,
                    description=description,
                    stock=stock,
                    category=category,
                    user_file=image,
                    seller_id=current_user.id
                )
                db.session.add(new_item)
                success_count += 1
            except Exception as e:
                error_messages.append(f"Row error: {str(e)}")
        
        db.session.commit()
        
        if success_count > 0:
            flash(f"Successfully uploaded {success_count} items!", category='success')
        if error_messages:
            for msg in error_messages[:3]:
                flash(msg, category='danger')
    except Exception as e:
        flash(f"Fatal CSV error: {str(e)}", category='danger')
            
    return redirect(url_for('add_item_page'))

@app.route('/download_template')
def download_template():
    from flask import send_from_directory
    return send_from_directory('static', 'lucky_cart_inventory_template.csv')

@app.route('/wishlist/<username>')
def public_wishlist(username):
    user = User.query.filter_by(username=username).first_or_404()
    wishlist = Wishlist.query.filter_by(user_id=user.id).first_or_404()
    if not wishlist.is_public and (not current_user.is_authenticated or current_user.id != user.id):
        flash("This wishlist is private.", category='danger')
        return redirect(url_for('home_page'))
    return render_template('wishlist.html', wishlist=wishlist, public_view=True)

@app.route('/my_orders')
@login_required
def my_orders_page():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_ordered.desc()).all()
    return render_template('orders.html', orders=orders)

@app.route('/seller_panel/orders')
@login_required
def seller_orders_page():
    if current_user.role != 'seller':
        flash("Unauthorized access.", category='danger')
        return redirect(url_for('market_page'))
    
    return redirect(url_for('my_listings_page'))

@app.route('/seller_panel/order/<int:order_id>/status', methods=['GET', 'POST'])
@login_required
def update_order_status(order_id):
    if request.method == 'GET':
        return redirect(url_for('my_listings_page'))
    if current_user.role != 'seller':
        flash("Unauthorized.", category='danger')
        return redirect(url_for('market_page'))
    
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    

    
    if new_status in ['Accepted', 'Rejected', 'Shipped', 'Delivered', 'Cancelled']:
        # Logic for Refund if Rejected
        if new_status == 'Rejected' and order.status != 'Rejected':
            # Refund each item's price from its respective seller back to the buyer
            for order_item in order.items:
                seller = User.query.get(order_item.item.seller_id)
                if seller:
                    seller.budget -= (order_item.price * order_item.quantity)
                # Restock
                order_item.item.stock += order_item.quantity
            
            order.user.budget += order.total_price
            send_notification(order.user_id, f"Your Order #LC-{order.id} was rejected. Money refunded.")

        elif new_status != order.status:
            send_notification(order.user_id, f"Order #LC-{order.id} status updated to {new_status}")

        order.status = new_status
        db.session.commit()
        flash(f"Order #LC-{order.id} status updated to {new_status}.", category='success')
    else:
        flash("Invalid status update.", category='danger')
        
    return redirect(url_for('my_listings_page'))

@app.route('/cancel_order/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    
    if order.status not in ['Ordered', 'Accepted']:
        flash("This order cannot be cancelled anymore.", category='danger')
        return redirect(url_for('my_orders_page'))

    # Process Refund
    for order_item in order.items:
        seller = User.query.get(order_item.item.seller_id)
        if seller:
            seller.budget -= (order_item.price * order_item.quantity)
        # Restock
        order_item.item.stock += order_item.quantity
        # Notify Seller
        if seller:
            send_notification(seller.id, f"Order #LC-{order.id} was cancelled by the customer.")

    order.user.budget += order.total_price
    order.status = 'Cancelled'
    
    db.session.commit()
    flash(f"Order #LC-{order.id} has been cancelled and refunded.", category='success')
    return redirect(url_for('my_orders_page'))

@app.route('/update_order_status/<int:order_id>')
@login_required
def legacy_update_status(order_id):
    return redirect(url_for('my_listings_page'))

@app.route('/receipt/<int:order_id>')
@login_required
def receipt_page(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash("Unauthorized access.", category='danger')
        return redirect(url_for('my_orders_page'))
    return render_template('receipt.html', order=order)

@app.route('/item/<int:item_id>')
def item_details_page(item_id):
    item = Item.query.get_or_404(item_id)
    sort = request.args.get('sort', 'newest')
    
    if sort == 'highest':
        reviews = Review.query.filter_by(item_id=item_id).order_by(Review.rating.desc()).all()
    elif sort == 'lowest':
        reviews = Review.query.filter_by(item_id=item_id).order_by(Review.rating.asc()).all()
    else:
        reviews = Review.query.filter_by(item_id=item_id).order_by(Review.date_posted.desc()).all()
        
    is_verified_buyer = False
    if current_user.is_authenticated:
        order_item = OrderItem.query.join(Order).filter(
            Order.user_id == current_user.id,
            OrderItem.item_id == item_id
        ).first()
        is_verified_buyer = order_item is not None
        
    return render_template('item_details.html', item=item, reviews=reviews, is_verified_buyer=is_verified_buyer, sort=sort)

@app.route('/item/<int:item_id>/review', methods=['POST'])
@login_required
def submit_review(item_id):
    rating = int(request.form.get('rating', 5))
    comment = request.form.get('comment')
    
    filename = None
    if 'review_image' in request.files:
        file = request.files['review_image']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
    order_item = OrderItem.query.join(Order).filter(
        Order.user_id == current_user.id,
        OrderItem.item_id == item_id
    ).first()
    is_verified = order_item is not None
    
    existing_review = Review.query.filter_by(user_id=current_user.id, item_id=item_id).first()
    if existing_review:
        existing_review.rating = rating
        existing_review.comment = comment
        if filename:
            existing_review.image_file = filename
        flash("Review updated!", category='success')
    else:
        new_review = Review(
            user_id=current_user.id,
            item_id=item_id,
            rating=rating,
            comment=comment,
            image_file=filename,
            is_verified=is_verified
        )
        db.session.add(new_review)
        flash("Review submitted!", category='success')
        
    db.session.commit()
    return redirect(url_for('item_details_page', item_id=item_id))

@app.route('/review/<int:review_id>/reply', methods=['POST'])
@login_required
def reply_to_review(review_id):
    review = Review.query.get_or_404(review_id)
    if review.item.seller_id != current_user.id:
        flash("Unauthorized action.", category='danger')
        return redirect(url_for('item_details_page', item_id=review.item_id))
        
    reply = request.form.get('reply')
    review.seller_reply = reply
    db.session.commit()
    flash("Reply posted!", category='success')
    return redirect(url_for('item_details_page', item_id=review.item_id))

@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return {'access_token': access_token}

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == 'admin1234' and password == 'admin':
            session['is_admin'] = True
            flash("System Access Granted. Welcome, Administrator.", category='success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Access Denied. Invalid Administrative Credentials.", category='danger')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        flash("Administrative privileges required.", category='danger')
        return redirect(url_for('admin_login'))
    orders = Order.query.order_by(Order.date_ordered.desc()).all()
    return render_template('admin_dashboard.html', orders=orders)

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    flash("Administrative session terminated.", category='info')
    return redirect(url_for('admin_login'))

@app.route('/admin/export_csv')
def admin_export_csv():
    if not session.get('is_admin'):
        return "Unauthorized Access", 403
    
    import csv
    import io
    from flask import make_response

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Exporting Items
    writer.writerow(['--- TABLE: ITEMS ---'])
    writer.writerow(['ID', 'Name', 'Price', 'Barcode', 'Description', 'Category', 'Stock', 'Seller ID'])
    items = Item.query.all()
    for item in items:
        writer.writerow([item.id, item.name, item.price, item.barcode, item.description, item.category, item.stock, item.seller_id])
    
    writer.writerow([])
    writer.writerow(['--- TABLE: USERS ---'])
    writer.writerow(['ID', 'Username', 'Email', 'Budget', 'Role'])
    users = User.query.all()
    for user in users:
        writer.writerow([user.id, user.username, user.email_address, user.budget, user.role])
        
    writer.writerow([])
    writer.writerow(['--- TABLE: ORDERS ---'])
    writer.writerow(['Order ID', 'User ID', 'Total Price', 'Status', 'Date', 'Address ID'])
    orders = Order.query.all()
    for order in orders:
        writer.writerow([order.id, order.user_id, order.total_price, order.status, order.date_ordered, order.address_id])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=lucky_cart_full_export.csv"
    response.headers["Content-type"] = "text/csv"
    return response

if __name__ == '__main__':
    # CHANGE 2: Added this block to create the database and tables before the app runs.
    with app.app_context():
        db.create_all()
        
    app.run(debug=True)

