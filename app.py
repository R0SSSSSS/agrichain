from flask import Flask, Response, jsonify, render_template, request, redirect, url_for, flash
from config import Config
from models import Complaint, DeliveryProof, OrderDelivery, OrderMessage, OrderTimeline, ProductRating, ProductReview
from models import db, User, Product, Order, Notification  # ✅ Added Notification
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func, inspect, text
from sqlalchemy.exc import IntegrityError
from recommendation import get_similar_product_details
try:
    from demand_prediction import (
        build_product_feature_rows,
        load_demand_artifact,
        predict_demand_for_products,
        train_demand_model
    )
except ImportError:
    from demand_prediction import (
        train_demand_model as _legacy_train_demand_model
    )

    def _fallback_float(value, default=0):
        try:
            return float(value or default)
        except (TypeError, ValueError):
            return default

    def build_product_feature_rows(products, orders=None, include_label=False):
        orders_by_product = {}
        for order in orders or []:
            orders_by_product.setdefault(order.product_id, []).append(order)

        rows = []
        for product in products:
            product_orders = [
                order for order in orders_by_product.get(product.id, [])
                if (order.status or '').lower() not in {'cancelled', 'rejected'}
            ]
            approved_orders = [
                order for order in product_orders
                if (order.status or '').lower() == 'approved'
            ]
            order_count = len(product_orders)
            units_sold = sum(_fallback_float(order.quantity) for order in approved_orders)
            approved_revenue = sum(_fallback_float(order.total_price) for order in approved_orders)
            row = {
                'product_id': product.id,
                'product_name': product.name or 'Unknown Product',
                'location': product.farmer.location if product.farmer else 'Unknown Location',
                'unit': getattr(product, 'unit', None) or 'unit',
                'price': _fallback_float(product.price),
                'quantity': _fallback_float(product.quantity),
                'order_count': order_count,
                'units_sold': units_sold,
                'approved_revenue': approved_revenue,
                'avg_order_value': approved_revenue / len(approved_orders) if approved_orders else 0
            }
            if include_label:
                row['demand_label'] = 'High' if order_count >= 3 or units_sold >= 5 else 'Low'
            rows.append(row)

        return rows

    def load_demand_artifact(model_path=None):
        return None

    def train_demand_model(products, orders):
        model, name_encoder, location_encoder = _legacy_train_demand_model(products, orders)
        return {
            'legacy_model': model,
            'name_encoder': name_encoder,
            'location_encoder': location_encoder
        }

    def predict_demand_for_products(products, orders=None, artifact=None):
        if not artifact or not artifact.get('legacy_model'):
            return {product.id: 'Not enough data' for product in products}

        import pandas as pd

        predictions = {}
        model = artifact['legacy_model']
        name_encoder = artifact['name_encoder']
        location_encoder = artifact['location_encoder']

        for product in products:
            name = product.name or ''
            location = product.farmer.location if product.farmer else ''

            if name not in name_encoder.classes_ or location not in location_encoder.classes_:
                predictions[product.id] = 'Not enough similar data'
                continue

            input_data = pd.DataFrame([{
                'price': product.price or 0,
                'quantity': product.quantity or 0,
                'name': name_encoder.transform([name])[0],
                'location': location_encoder.transform([location])[0]
            }])
            prediction = model.predict(input_data)[0]
            predictions[product.id] = 'High Demand' if prediction == 1 else 'Low Demand'

        return predictions
try:
    from market_insights import build_market_rows, build_market_summary, build_price_insights
except Exception:
    from collections import defaultdict

    def _market_float(value, default=0):
        try:
            return float(value or default)
        except (TypeError, ValueError):
            return default

    def _market_product_key(product):
        name = (product.name or '').strip().lower()
        unit = (getattr(product, 'unit', None) or 'unit').strip().lower()
        return f"{name or f'product-{product.id}'}::{unit}"

    def _market_demand_trend(order_count, units_sold):
        if order_count >= 5 or units_sold >= 5:
            return 'High Demand'
        if order_count > 0:
            return 'Active Demand'
        return 'Low Demand'

    def _market_action(demand_trend, total_stock):
        if demand_trend == 'High Demand' and total_stock <= 10:
            return 'Increase supply'
        if demand_trend == 'High Demand':
            return 'Maintain supply'
        if demand_trend == 'Active Demand':
            return 'Monitor pricing'
        if total_stock >= 20:
            return 'Promote product'
        return 'Collect more data'

    def _market_reading(demand_trend, total_stock, listing_count):
        if demand_trend == 'High Demand' and total_stock <= 10:
            return 'Demand is strong but available stock is tight.'
        if demand_trend == 'High Demand':
            return 'Demand is strong and supply is still present.'
        if demand_trend == 'Active Demand':
            return 'Orders are starting to move. Keep monitoring price and stock.'
        if listing_count <= 1:
            return 'Market signal is still thin because there are few comparable listings.'
        return 'More listings and orders are needed for a stronger market signal.'

    def _market_next_step(demand_trend, total_stock):
        if demand_trend == 'High Demand' and total_stock <= 10:
            return 'Increase supply while buyers are active.'
        if demand_trend == 'High Demand':
            return 'Maintain supply and monitor new orders.'
        if demand_trend == 'Active Demand':
            return 'Watch the next few orders before changing price.'
        if total_stock >= 20:
            return 'Improve visibility or consider a competitive price.'
        return 'Collect more product and transaction data.'

    def build_market_rows(products, orders):
        orders_by_product = defaultdict(list)
        for order in orders:
            orders_by_product[order.product_id].append(order)

        groups = {}
        for product in products:
            key = _market_product_key(product)
            group = groups.setdefault(key, {
                'key': key,
                'name': product.name or 'Unnamed Product',
                'unit': product.unit or 'unit',
                'prices': [],
                'total_stock': 0,
                'listing_count': 0,
                'farmer_count': set(),
                'order_count': 0,
                'units_sold': 0,
                'approved_revenue': 0
            })
            group['prices'].append(_market_float(product.price))
            group['total_stock'] += _market_float(product.quantity)
            group['listing_count'] += 1
            if product.farmer:
                group['farmer_count'].add(product.farmer_id)

            for order in orders_by_product.get(product.id, []):
                status = (order.status or '').lower()
                if status in {'cancelled', 'rejected'}:
                    continue
                group['order_count'] += 1
                if status == 'approved':
                    group['units_sold'] += _market_float(order.quantity)
                    group['approved_revenue'] += _market_float(order.total_price)

        rows = []
        for group in groups.values():
            prices = group['prices']
            avg_price = sum(prices) / len(prices) if prices else 0
            demand_trend = _market_demand_trend(group['order_count'], group['units_sold'])
            rows.append({
                'key': group['key'],
                'name': group['name'],
                'unit': group['unit'],
                'avg_price': avg_price,
                'min_price': min(prices) if prices else 0,
                'max_price': max(prices) if prices else 0,
                'total_stock': group['total_stock'],
                'listing_count': group['listing_count'],
                'farmer_count': len(group['farmer_count']),
                'order_count': group['order_count'],
                'units_sold': group['units_sold'],
                'approved_revenue': group['approved_revenue'],
                'demand_trend': demand_trend,
                'market_action': _market_action(demand_trend, group['total_stock']),
                'ai_reading': _market_reading(demand_trend, group['total_stock'], group['listing_count']),
                'next_step': _market_next_step(demand_trend, group['total_stock'])
            })

        return sorted(rows, key=lambda row: (-row['units_sold'], -row['order_count'], row['name'].lower()))

    def build_market_summary(market_rows):
        if not market_rows:
            return {
                'product_types': 0,
                'total_stock': 0,
                'total_orders': 0,
                'total_units_sold': 0,
                'average_market_price': 0,
                'high_demand_count': 0
            }
        return {
            'product_types': len(market_rows),
            'total_stock': sum(row['total_stock'] for row in market_rows),
            'total_orders': sum(row['order_count'] for row in market_rows),
            'total_units_sold': sum(row['units_sold'] for row in market_rows),
            'average_market_price': sum(row['avg_price'] for row in market_rows) / len(market_rows),
            'high_demand_count': sum(1 for row in market_rows if row['demand_trend'] == 'High Demand')
        }

    def build_price_insights(products, market_rows):
        rows_by_key = {row['key']: row for row in market_rows}
        insights = {}
        for product in products:
            row = rows_by_key.get(_market_product_key(product))
            current_price = _market_float(product.price)
            if not row or row['listing_count'] < 2 or row['avg_price'] <= 0:
                insights[product.id] = {
                    'status': 'No comparison yet',
                    'avg_price': row['avg_price'] if row else 0,
                    'difference': 0,
                    'suggestion': 'Collect more market data',
                    'detail': 'Price guidance will improve after more similar listings appear.',
                    'next_step': 'Keep product details updated so future comparisons are accurate.'
                }
                continue

            avg_price = row['avg_price']
            difference = ((current_price - avg_price) / avg_price) * 100
            if current_price > avg_price * 1.15:
                status = 'Above Market'
                suggestion = 'Review price'
            elif current_price < avg_price * 0.85:
                status = 'Below Market'
                suggestion = 'Possible price increase'
            else:
                status = 'Fair Price'
                suggestion = 'Keep current price'

            insights[product.id] = {
                'status': status,
                'avg_price': avg_price,
                'difference': difference,
                'suggestion': suggestion,
                'detail': f'Your price is {abs(difference):.1f}% from the market average.',
                'next_step': suggestion
            }
        return insights
from smart_insights import build_farmer_ai_advice, build_farmer_summary, build_product_insights
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape
from io import StringIO
from urllib.parse import quote
from urllib.request import Request, urlopen
import csv
import hmac
import re
import os
import time
import xml.etree.ElementTree as ET

app = Flask(__name__, static_folder='Static', static_url_path='/static')
app.config.from_object(Config)

from ai_routes import ai_bp
from ai_service import load_models as _load_ai_models
app.register_blueprint(ai_bp)

DELIVERY_STATUSES = [
    'Address Confirmation',
    'Preparing Order',
    'Ready for Pickup/Delivery',
    'Out for Delivery',
    'Delivered'
]
PRODUCT_REVIEW_STATUSES = ['Pending', 'Approved', 'Rejected']
COMPLAINT_STATUSES = ['Open', 'In Review', 'Resolved', 'Dismissed']
NOTIFICATION_AUDIENCES = ['all', 'farmers', 'buyers']
IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
LOW_STOCK_THRESHOLD = 5
PENDING_ORDER_STATUS = 'Pending'
APPROVED_ORDER_STATUS = 'Approved'
CLOSED_ORDER_STATUSES = {'Cancelled', 'Rejected'}
PRODUCT_UNITS = [
    ('kg', 'Kilogram (kg)'),
    ('piece', 'Piece'),
    ('bundle', 'Bundle'),
    ('sack', 'Sack'),
    ('crate', 'Crate'),
    ('tray', 'Tray'),
    ('dozen', 'Dozen'),
    ('liter', 'Liter'),
    ('custom', 'Other')
]

CROP_NEWS_ITEMS = [
    {
        'title': 'Fruit-led exports narrowed the Philippine farm trade gap',
        'date': 'February 7, 2026',
        'category': 'Fruit Exports',
        'summary': (
            'The Department of Agriculture reported stronger December 2025 '
            'agricultural exports, led by tropical fruits such as bananas, '
            'mangoes, durian, and other high-value crops.'
        ),
        'impact': 'Good signal for farmers growing export-ready fruits and premium crops.',
        'source': 'Department of Agriculture',
        'url': 'https://www.da.gov.ph/fruit-led-export-surge-narrows-philippines-farm-trade-gap/'
    },
    {
        'title': 'DA promotes more high-value crops after banana rebound',
        'date': 'February 10, 2026',
        'category': 'High-Value Crops',
        'summary': (
            'Philippine agriculture entered 2026 with stronger momentum, with '
            'banana recovery, avocado market access, and durian expansion cited '
            'as opportunities for wider crop diversification.'
        ),
        'impact': 'Farmers can watch demand for avocado, durian, banana, and mango.',
        'source': 'Department of Agriculture',
        'url': 'https://www.da.gov.ph/da-eyes-steadier-agricultural-growth-after-2025-gains/'
    },
    {
        'title': 'Climate-smart farming support targets vegetables',
        'date': 'February 6, 2026',
        'category': 'Vegetables',
        'summary': (
            'The DA is scaling support for greenhouses, rainshelters, drip '
            'irrigation, and water systems for high-value vegetables including '
            'chili, tomato, and bell pepper.'
        ),
        'impact': 'Useful for growers planning year-round production through heat and rain.',
        'source': 'Philippine News Agency',
        'url': 'https://www.pna.gov.ph/articles/1268554'
    },
    {
        'title': 'Fruits and vegetables sector prepares for fuel cost risks',
        'date': 'April 8, 2026',
        'category': 'Transport Costs',
        'summary': (
            'The National Sectoral Committee on Fruits and Vegetables backed a '
            'mitigation plan for fuel supply concerns that may affect farm '
            'transport costs, production costs, and market stability.'
        ),
        'impact': 'Sellers should monitor transport costs when setting product prices.',
        'source': 'Philippine Council for Agriculture and Fisheries',
        'url': 'https://pcaf.da.gov.ph/index.php/2026/04/08/nsc-fv-backs-mitigation-plan-vs-fuel-concerns-endorses-key-agri-budget-proposal/'
    }
]

CROP_NEWS_HIGHLIGHTS = [
    {'label': 'Export crops to watch', 'value': 'Banana, mango, avocado, durian'},
    {'label': 'Protected vegetable focus', 'value': 'Chili, tomato, bell pepper'},
    {'label': 'Farmer planning signal', 'value': 'Track weather and transport cost risks'}
]

CROP_NEWS_KEYWORDS = [
    'agriculture', 'agricultural', 'crop', 'crops', 'fruit', 'fruits',
    'vegetable', 'vegetables', 'farm', 'farmer', 'farmers', 'banana',
    'mango', 'durian', 'pineapple', 'coconut', 'rice', 'corn', 'tomato',
    'onion', 'chili', 'avocado', 'harvest', 'planting', 'philippines'
]

CROP_NEWS_FEEDS = [
    {
        'name': 'Department of Agriculture',
        'url': 'https://www.da.gov.ph/feed/'
    },
    {
        'name': 'Google News - PH Agriculture',
        'url': (
            'https://news.google.com/rss/search?q='
            + quote('Philippines agriculture crops fruits vegetables')
            + '&hl=en-PH&gl=PH&ceid=PH:en'
        )
    }
]

CROP_NEWS_CACHE = {
    'items': [],
    'last_fetch': 0,
    'last_updated': None,
    'is_live': False,
    'error': None
}
CROP_NEWS_CACHE_SECONDS = 600
REGISTER_ALLOWED_ROLES = {'farmer', 'buyer'}
DATABASE_READY = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def ensure_database_ready():
    global DATABASE_READY
    if DATABASE_READY:
        return

    db.create_all()
    ensure_product_unit_schema()
    ensure_product_reviews()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    DATABASE_READY = True

@app.before_request
def prevent_disabled_account_access():
    if request.endpoint == 'static':
        return

    # AI inference routes are pure ML — no DB needed
    if request.endpoint and request.endpoint.startswith('ai_bp.'):
        return

    ensure_database_ready()

    if (
        current_user.is_authenticated
        and current_user.role != 'admin'
        and current_user.disabled
        and request.endpoint not in {'logout', 'static'}
    ):
        logout_user()
        flash("Your account was suspended by admin.", "error")
        return redirect('/login')

def can_access_order(order):
    if current_user.role == 'admin':
        return True

    if order.buyer_id == current_user.id:
        return True

    return order.product and order.product.farmer_id == current_user.id

def get_message_receiver(order):
    if current_user.id == order.buyer_id:
        return order.product.farmer_id
    return order.buyer_id

def ensure_delivery(order):
    if order.delivery:
        return order.delivery

    delivery = OrderDelivery(
        order_id=order.id,
        shipping_address=order.buyer.location or 'Address not recorded',
        tracking_note='Order record created. Please confirm the address with the seller.'
    )
    db.session.add(delivery)
    return delivery

def allowed_image_file(filename):
    return (
        bool(filename)
        and '.' in filename
        and filename.rsplit('.', 1)[1].lower() in IMAGE_EXTENSIONS
    )

def uploaded_file_size(file):
    try:
        current_position = file.stream.tell()
        file.stream.seek(0, os.SEEK_END)
        size = file.stream.tell()
        file.stream.seek(current_position)
        return size
    except (AttributeError, OSError):
        return 0

def validate_image_upload(file, required=False):
    if not file or file.filename == '':
        return "Please upload an image file." if required else None

    if not allowed_image_file(file.filename):
        return "Upload a PNG, JPG, JPEG, GIF, or WEBP image."

    if file.mimetype and not file.mimetype.startswith('image/'):
        return "The selected file must be an image."

    file_size = uploaded_file_size(file)
    if file_size and file_size > MAX_IMAGE_BYTES:
        return "Image must be 5MB or smaller."

    return None

def save_image_file(file, subfolder=''):
    if not file or file.filename == '':
        return None

    upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(upload_dir, exist_ok=True)

    base_filename = secure_filename(file.filename)
    filename = f"{int(time.time())}_{base_filename}"
    file.save(os.path.join(upload_dir, filename))
    return f"{subfolder}/{filename}" if subfolder else filename

def parse_positive_float(value, default=0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default

def format_quantity(value):
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return '0'

    if number.is_integer():
        return str(int(number))

    return f"{number:.2f}".rstrip('0').rstrip('.')

def get_product_unit(form):
    selected_unit = (form.get('unit') or 'unit').strip().lower()
    custom_unit = (form.get('custom_unit') or '').strip().lower()

    if selected_unit == 'custom' and custom_unit:
        return custom_unit[:30]

    allowed_units = {unit for unit, label in PRODUCT_UNITS if unit != 'custom'}
    return selected_unit if selected_unit in allowed_units else 'unit'

def quote_table_name(name):
    return f"`{name}`" if db.engine.dialect.name == 'mysql' else name

def add_column_if_missing(connection, table_name, columns, column_name, definition):
    if column_name not in columns:
        connection.execute(text(f"ALTER TABLE {quote_table_name(table_name)} ADD COLUMN {column_name} {definition}"))

def ensure_product_unit_schema():
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    with db.engine.begin() as connection:
        if 'user' in table_names:
            user_columns = {column['name'] for column in inspector.get_columns('user')}
            add_column_if_missing(connection, 'user', user_columns, 'disabled', 'BOOLEAN DEFAULT 0')

        if 'product' in table_names:
            product_columns = {column['name'] for column in inspector.get_columns('product')}
            add_column_if_missing(connection, 'product', product_columns, 'unit', "VARCHAR(30) DEFAULT 'unit'")
            add_column_if_missing(connection, 'product', product_columns, 'is_deleted', 'BOOLEAN DEFAULT 0')

            if db.engine.dialect.name == 'mysql':
                connection.execute(text("ALTER TABLE product MODIFY quantity FLOAT"))

        if 'order' in table_names and db.engine.dialect.name == 'mysql':
            connection.execute(text("ALTER TABLE `order` MODIFY quantity FLOAT"))

        if 'order_message' in table_names:
            order_message_columns = {column['name'] for column in inspector.get_columns('order_message')}
            add_column_if_missing(connection, 'order_message', order_message_columns, 'image', "VARCHAR(200)")

app.jinja_env.filters['qty'] = format_quantity

def get_reserved_quantity(product_id, exclude_order_id=None):
    query = Order.query.filter(
        Order.product_id == product_id,
        Order.status == PENDING_ORDER_STATUS
    )
    if exclude_order_id:
        query = query.filter(Order.id != exclude_order_id)

    return float(query.with_entities(func.coalesce(func.sum(Order.quantity), 0)).scalar() or 0)

def get_available_quantity(product, exclude_order_id=None):
    if not product or product.is_deleted:
        return 0

    stock = float(product.quantity or 0)
    reserved = get_reserved_quantity(product.id, exclude_order_id)
    return max(stock - reserved, 0)

def build_product_availability(products):
    product_ids = [product.id for product in products if product.id]
    reserved_by_product = {product_id: 0 for product_id in product_ids}

    if product_ids:
        rows = (
            db.session.query(Order.product_id, func.coalesce(func.sum(Order.quantity), 0))
            .filter(Order.product_id.in_(product_ids), Order.status == PENDING_ORDER_STATUS)
            .group_by(Order.product_id)
            .all()
        )
        reserved_by_product.update({product_id: float(quantity or 0) for product_id, quantity in rows})

    return {
        product.id: {
            'reserved': reserved_by_product.get(product.id, 0),
            'available': max(float(product.quantity or 0) - reserved_by_product.get(product.id, 0), 0)
        }
        for product in products
    }

def add_order_timeline(order, status, note, actor=None):
    db.session.add(OrderTimeline(
        order_id=order.id,
        status=status,
        note=note,
        actor_id=(actor.id if actor and getattr(actor, 'is_authenticated', False) else None)
    ))

def ensure_order_timeline(order):
    if not order.id:
        return

    if OrderTimeline.query.filter_by(order_id=order.id).count() == 0:
        db.session.add(OrderTimeline(
            order_id=order.id,
            status='Order Placed',
            note='Order record was created.',
            actor_id=order.buyer_id,
            created_at=order.created_at or datetime.utcnow()
        ))

def build_rating_summary(products):
    product_ids = [product.id for product in products if product.id]
    summary = {product.id: {'avg': 0, 'count': 0} for product in products}

    if not product_ids:
        return summary

    rows = (
        db.session.query(ProductRating.product_id, func.avg(ProductRating.rating), func.count(ProductRating.id))
        .filter(ProductRating.product_id.in_(product_ids))
        .group_by(ProductRating.product_id)
        .all()
    )

    for product_id, avg_rating, count in rows:
        summary[product_id] = {'avg': float(avg_rating or 0), 'count': int(count or 0)}

    return summary

def notify_low_stock(product):
    if not product or not product.farmer_id:
        return

    quantity = float(product.quantity or 0)
    if quantity <= LOW_STOCK_THRESHOLD:
        unit = product.unit or 'unit'
        label = 'out of stock' if quantity <= 0 else f"low on stock: {format_quantity(quantity)} {unit} left"
        db.session.add(Notification(
            user_id=product.farmer_id,
            message=f"Low stock alert: {product.name} is {label}."
        ))

def order_can_be_rated(order):
    return (
        order
        and order.buyer_id == current_user.id
        and order.delivery
        and order.delivery.status == 'Delivered'
        and not order.rating
    )

def is_admin_master_login(username, password):
    admin_username = app.config.get('ADMIN_USERNAME', 'admin')
    admin_master_key = app.config.get('ADMIN_MASTER_KEY', '')
    return (
        bool(admin_master_key)
        and hmac.compare_digest((username or '').strip().lower(), admin_username.lower())
        and hmac.compare_digest(password or '', admin_master_key)
    )

def get_or_create_admin_user():
    admin_username = app.config.get('ADMIN_USERNAME', 'admin')
    admin_master_key = app.config.get('ADMIN_MASTER_KEY', '')

    user = User.query.filter_by(username=admin_username).first()
    if not user:
        user = User(
            username=admin_username,
            password=generate_password_hash(admin_master_key),
            role='admin',
            location='Platform Admin',
            disabled=False
        )
        db.session.add(user)
        db.session.commit()
        return user

    changed = False
    if user.role != 'admin':
        user.role = 'admin'
        changed = True
    if not user.location:
        user.location = 'Platform Admin'
        changed = True
    if user.disabled:
        user.disabled = False
        changed = True

    if changed:
        db.session.commit()

    return user

def ensure_product_reviews(products=None):
    products = list(products if products is not None else Product.query.all())
    product_ids = [product.id for product in products if product.id]

    if not product_ids:
        return []

    existing_ids = {
        review.product_id
        for review in ProductReview.query.filter(ProductReview.product_id.in_(product_ids)).all()
    }

    new_reviews = []
    for product in products:
        if product.id not in existing_ids:
            review = ProductReview(product_id=product.id, status='Pending')
            db.session.add(review)
            new_reviews.append(review)

    if new_reviews:
        db.session.commit()

    return new_reviews

def product_is_approved(product):
    return bool(product and not product.is_deleted and product.review and product.review.status == 'Approved')

def get_approved_products():
    ensure_product_reviews()
    return (
        Product.query
        .join(ProductReview)
        .filter(ProductReview.status == 'Approved', Product.is_deleted == False)
        .all()
    )

def get_product_preview_url(product):
    if current_user.role == 'buyer':
        return url_for('order', product_id=product.id)
    if current_user.role == 'admin':
        return url_for('admin') + '#products'
    return url_for('marketplace')

def serialize_product_preview(product):
    unit = product.unit or 'unit'
    return {
        'name': product.name or 'Unnamed Product',
        'price': float(product.price or 0),
        'unit': unit,
        'location': product.farmer.location if product.farmer else 'Location not listed',
        'farmer': product.farmer.username if product.farmer else 'Unknown farmer',
        'image': url_for('static', filename=f'uploads/{product.image}') if product.image else '',
        'url': get_product_preview_url(product)
    }

def product_price_key(product):
    name = (product.name or '').strip().lower()
    unit = (getattr(product, 'unit', None) or 'unit').strip().lower()
    return f"{name or f'product-{product.id}'}::{unit}"

def build_farmer_price_comparison_rows(farmer_products, market_products, farmer_id):
    own_groups = {}
    for product in farmer_products:
        key = product_price_key(product)
        group = own_groups.setdefault(key, {
            'name': product.name or 'Unnamed Product',
            'unit': product.unit or 'unit',
            'prices': []
        })
        group['prices'].append(float(product.price or 0))

    market_groups = {}
    for product in market_products:
        key = product_price_key(product)
        group = market_groups.setdefault(key, {
            'prices': [],
            'other_prices': [],
            'other_farmers': set()
        })
        price = float(product.price or 0)
        group['prices'].append(price)
        if product.farmer_id != farmer_id:
            group['other_prices'].append(price)
            if product.farmer_id:
                group['other_farmers'].add(product.farmer_id)

    rows = []
    for key, own in own_groups.items():
        own_prices = own['prices']
        own_avg_price = sum(own_prices) / len(own_prices) if own_prices else 0
        market = market_groups.get(key, {})
        peer_prices = market.get('other_prices', [])
        peer_avg_price = sum(peer_prices) / len(peer_prices) if peer_prices else 0
        price_difference = (
            ((own_avg_price - peer_avg_price) / peer_avg_price) * 100
            if peer_avg_price else 0
        )

        if not peer_prices:
            price_position = 'No peer match'
            price_tone = 'gray'
        elif price_difference > 15:
            price_position = 'Above peers'
            price_tone = 'amber'
        elif price_difference < -15:
            price_position = 'Below peers'
            price_tone = 'blue'
        else:
            price_position = 'Within range'
            price_tone = 'green'

        rows.append({
            'name': own['name'],
            'unit': own['unit'],
            'own_avg_price': own_avg_price,
            'own_min_price': min(own_prices) if own_prices else 0,
            'own_max_price': max(own_prices) if own_prices else 0,
            'market_avg_price': peer_avg_price,
            'min_price': min(peer_prices) if peer_prices else 0,
            'max_price': max(peer_prices) if peer_prices else 0,
            'listing_count': len(peer_prices),
            'farmer_count': len(market.get('other_farmers', set())),
            'has_comparison': bool(peer_prices),
            'price_difference': price_difference,
            'price_position': price_position,
            'price_tone': price_tone
        })

    return sorted(rows, key=lambda row: (not row['has_comparison'], row['name'].lower(), row['unit'].lower()))

def build_price_comparison_summary(rows):
    peer_prices = [row['market_avg_price'] for row in rows if row['market_avg_price']]
    return {
        'product_types': len(rows),
        'comparable_groups': sum(1 for row in rows if row['has_comparison']),
        'peer_listing_count': sum(row['listing_count'] for row in rows),
        'average_market_price': sum(peer_prices) / len(peer_prices) if peer_prices else 0
    }

def send_notifications(users, message):
    recipients = [user for user in users if user.role != 'admin' and not user.disabled]
    for user in recipients:
        db.session.add(Notification(user_id=user.id, message=message))
    return len(recipients)

def build_admin_report(products, orders, complaints):
    market_rows = build_market_rows(products, orders)
    approved_orders = [
        order for order in orders
        if (order.status or '').lower() == 'approved'
    ]

    return {
        'total_sales': sum((order.total_price or 0) for order in approved_orders),
        'total_orders': len(orders),
        'approved_orders': len(approved_orders),
        'pending_orders': sum(1 for order in orders if order.status == 'Pending'),
        'total_products': len(products),
        'pending_products': sum(
            1 for product in products
            if product.review and product.review.status == 'Pending'
        ),
        'open_complaints': sum(
            1 for complaint in complaints
            if complaint.status in ['Open', 'In Review']
        ),
        'market_rows': market_rows,
        'market_summary': build_market_summary(market_rows)
    }

def make_report_csv(products, orders):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Product', 'Unit', 'Orders', 'Quantity Sold', 'Available Stock', 'Demand Trend', 'Revenue'])

    for row in build_market_rows(products, orders):
        writer.writerow([
            row['name'],
            row['unit'],
            row['order_count'],
            format_quantity(row['units_sold']),
            format_quantity(row['total_stock']),
            row['demand_trend'],
            f"{row['approved_revenue']:.2f}"
        ])

    return output.getvalue()

def make_training_csv(products, orders):
    output = StringIO()
    rows = build_product_feature_rows(products, orders, include_label=True)
    fieldnames = [
        'product_id',
        'product_name',
        'location',
        'unit',
        'price',
        'quantity',
        'order_count',
        'units_sold',
        'approved_revenue',
        'avg_order_value',
        'demand_label'
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for row in rows:
        writer.writerow(row)

    return output.getvalue()

def clean_feed_text(value, max_length=220):
    text = unescape(value or '')
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    if len(text) <= max_length:
        return text

    return text[:max_length].rsplit(' ', 1)[0] + '...'

def parse_feed_date(value):
    if not value:
        return None

    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None

def format_feed_date(value):
    parsed = parse_feed_date(value)
    if parsed:
        return parsed.strftime('%B %d, %Y')
    return 'Latest update'

def get_child_text(element, names):
    for name in names:
        child = element.find(name)
        if child is not None and child.text:
            return child.text.strip()
    return ''

def classify_crop_news(title, summary):
    text = f'{title} {summary}'.lower()

    if any(word in text for word in ['banana', 'mango', 'durian', 'pineapple', 'coconut', 'avocado', 'fruit']):
        return 'Fruits'
    if any(word in text for word in ['vegetable', 'tomato', 'onion', 'chili', 'pepper']):
        return 'Vegetables'
    if any(word in text for word in ['rice', 'corn', 'crop', 'harvest', 'planting']):
        return 'Crops'
    if any(word in text for word in ['price', 'market', 'supply', 'import', 'export']):
        return 'Market'

    return 'Agriculture'

def is_crop_news(title, summary):
    text = f'{title} {summary}'.lower()
    return any(keyword in text for keyword in CROP_NEWS_KEYWORDS)

def fetch_feed_items(feed):
    request = Request(
        feed['url'],
        headers={'User-Agent': 'AgriChain crop news reader/1.0'}
    )

    with urlopen(request, timeout=6) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    entries = root.findall('.//item')

    if not entries:
        entries = root.findall('{http://www.w3.org/2005/Atom}entry')

    items = []
    for entry in entries[:12]:
        title = get_child_text(entry, ['title', '{http://www.w3.org/2005/Atom}title'])
        summary = get_child_text(entry, [
            'description',
            'summary',
            '{http://www.w3.org/2005/Atom}summary',
            '{http://www.w3.org/2005/Atom}content'
        ])
        link = get_child_text(entry, ['link', '{http://www.w3.org/2005/Atom}id'])
        atom_link = entry.find('{http://www.w3.org/2005/Atom}link')

        if atom_link is not None and atom_link.get('href'):
            link = atom_link.get('href')

        published = get_child_text(entry, [
            'pubDate',
            'published',
            'updated',
            '{http://www.w3.org/2005/Atom}published',
            '{http://www.w3.org/2005/Atom}updated'
        ])

        clean_title = clean_feed_text(title, 140)
        clean_summary = clean_feed_text(summary)

        if not clean_title or not is_crop_news(clean_title, clean_summary):
            continue

        items.append({
            'title': clean_title,
            'date': format_feed_date(published),
            'published_at': parse_feed_date(published),
            'category': classify_crop_news(clean_title, clean_summary),
            'summary': clean_summary or 'Open the source to read the full crop and agriculture update.',
            'impact': 'Live news item. Review the source before using it for planting or pricing decisions.',
            'source': feed['name'],
            'url': link or feed['url']
        })

    return items

def get_live_crop_news(force_refresh=False):
    now = time.time()
    cache_is_fresh = now - CROP_NEWS_CACHE['last_fetch'] < CROP_NEWS_CACHE_SECONDS

    if CROP_NEWS_CACHE['items'] and cache_is_fresh and not force_refresh:
        return CROP_NEWS_CACHE

    live_items = []
    errors = []

    for feed in CROP_NEWS_FEEDS:
        try:
            live_items.extend(fetch_feed_items(feed))
        except Exception as exc:
            errors.append(f"{feed['name']}: {exc}")

    deduped_items = []
    seen_urls = set()
    for item in live_items:
        key = item['url'] or item['title']
        if key in seen_urls:
            continue
        seen_urls.add(key)
        deduped_items.append(item)

    deduped_items.sort(
        key=lambda item: item['published_at'] or datetime.min,
        reverse=True
    )

    if deduped_items:
        CROP_NEWS_CACHE.update({
            'items': deduped_items[:8],
            'last_fetch': now,
            'last_updated': datetime.now().strftime('%B %d, %Y %I:%M %p'),
            'is_live': True,
            'error': None
        })
    else:
        CROP_NEWS_CACHE.update({
            'items': CROP_NEWS_ITEMS,
            'last_fetch': now,
            'last_updated': datetime.now().strftime('%B %d, %Y %I:%M %p'),
            'is_live': False,
            'error': '; '.join(errors) if errors else 'No matching live crop news found.'
        })

    return CROP_NEWS_CACHE

@app.route('/')
def home():
    return redirect('/login')

@app.route('/notifications')
@login_required
def notifications():
    notes = Notification.query.filter_by(user_id=current_user.id).all()
    return render_template('notifications.html', notes=notes)

@app.route('/complaints', methods=['GET', 'POST'])
@login_required
def complaints():
    if current_user.role == 'admin':
        return redirect(url_for('admin') + '#complaints')

    if current_user.role == 'farmer':
        user_orders = (
            Order.query
            .join(Product)
            .filter(Product.farmer_id == current_user.id)
            .order_by(Order.created_at.desc())
            .all()
        )
    else:
        user_orders = (
            Order.query
            .filter_by(buyer_id=current_user.id)
            .order_by(Order.created_at.desc())
            .all()
        )

    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        order_id = request.form.get('order_id') or None
        linked_order = None

        if order_id:
            try:
                order_id = int(order_id)
            except ValueError:
                flash("Choose a valid order.", "error")
                return redirect(url_for('complaints'))

            linked_order = Order.query.get(order_id)
            if not linked_order or not can_access_order(linked_order):
                flash("Choose an order connected to your account.", "error")
                return redirect(url_for('complaints'))

        if not subject or not message:
            flash("Please add a subject and describe the concern.", "error")
            return redirect(url_for('complaints'))

        complaint = Complaint(
            user_id=current_user.id,
            order_id=linked_order.id if linked_order else None,
            subject=subject,
            message=message
        )
        db.session.add(complaint)
        db.session.flush()

        admins = User.query.filter_by(role='admin').all()
        for admin_user in admins:
            db.session.add(Notification(
                user_id=admin_user.id,
                message=f"New complaint #{complaint.id}: {subject}"
            ))

        db.session.commit()
        flash("Complaint submitted. Admin will review it.", "success")
        return redirect(url_for('complaints'))

    user_complaints = (
        Complaint.query
        .filter_by(user_id=current_user.id)
        .order_by(Complaint.created_at.desc())
        .all()
    )
    return render_template(
        'complaints.html',
        complaints=user_complaints,
        orders=user_orders
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        role = request.form.get('role')
        admin_username = app.config.get('ADMIN_USERNAME', 'admin')

        if role not in REGISTER_ALLOWED_ROLES:
            return render_template('register.html', error="Please choose Farmer or Buyer to create an account.")

        if username.strip().lower() == admin_username.lower():
            return render_template('register.html', error="That username is reserved for admin login.")

        # ✅ Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('register.html', error="Username already taken. Please choose another.")
        
        user = User(
            username=request.form['username'],
            password=generate_password_hash(request.form['password']),
            role=role,
            location=request.form['location']
        )
        db.session.add(user)
        
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return render_template('register.html', error="Username already taken. Please choose another.")

        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        if is_admin_master_login(username, password):
            admin_user = get_or_create_admin_user()
            login_user(admin_user)
            return redirect('/admin')

        user = User.query.filter_by(username=username).first()
        if user and user.role != 'admin' and check_password_hash(user.password, password):
            if user.disabled:
                return render_template('login.html', error="This account is currently suspended. Please contact support.")
            login_user(user)
            return redirect('/dashboard') if user.role == 'farmer' else redirect('/marketplace')
    return render_template('login.html', error="Invalid username or password." if request.method == 'POST' else None)

@app.route('/logout')
def logout():
    logout_user()
    return redirect('/login')

@app.route('/marketplace')
@login_required
def marketplace():
    if current_user.role == 'admin':
        return redirect(url_for('admin') + '#products')

    products = get_approved_products()
    availability = build_product_availability(products)
    rating_summary = build_rating_summary(products)
    return render_template(
        'index.html',
        products=products,
        availability=availability,
        rating_summary=rating_summary
    )

@app.route('/search_products')
@login_required
def search_products():
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify([])

    ensure_product_reviews()
    products = (
        Product.query
        .join(ProductReview)
        .filter(
            ProductReview.status == 'Approved',
            Product.is_deleted == False,
            Product.quantity > 0,
            Product.name.ilike(f'%{query}%')
        )
        .order_by(Product.name.asc())
        .limit(6)
        .all()
    )

    return jsonify([
        serialize_product_preview(product)
        for product in products
        if get_available_quantity(product) > 0
    ][:6])

@app.route('/analytics')
@login_required
def analytics():
    if current_user.role == 'admin':
        return redirect(url_for('admin') + '#reports')
    if current_user.role != 'farmer':
        return redirect('/marketplace')

    def pct(value, maximum):
        if not maximum:
            return 0
        return min(round((float(value or 0) / float(maximum)) * 100), 100)

    products = Product.query.filter_by(farmer_id=current_user.id, is_deleted=False).all()
    product_ids = [product.id for product in products]
    orders = (
        Order.query.filter(Order.product_id.in_(product_ids)).all()
        if product_ids else []
    )
    approved_orders = [
        order for order in orders
        if (order.status or '').lower() == 'approved'
    ]

    market_products = get_approved_products()
    seller_rows = build_market_rows(products, orders)
    market_rows = build_market_rows(market_products, [])
    market_rows_by_key = {
        row.get('key') or f"{row['name'].lower()}::{row['unit'].lower()}": row
        for row in market_rows
    }

    total_sales = sum((order.total_price or 0) for order in approved_orders)
    total_orders = len(orders)
    total_units_sold = sum(row['units_sold'] for row in seller_rows)
    total_stock = sum(row['total_stock'] for row in seller_rows)
    average_order_value = total_sales / len(approved_orders) if approved_orders else 0

    max_revenue = max([row['approved_revenue'] for row in seller_rows] + [1])
    max_orders = max([row['order_count'] for row in seller_rows] + [1])
    max_quantity = max(
        [max(row['total_stock'], row['units_sold']) for row in seller_rows] + [1]
    )

    chart_rows = []
    for row in seller_rows:
        row_key = row.get('key') or f"{row['name'].lower()}::{row['unit'].lower()}"
        market_row = market_rows_by_key.get(row_key)
        market_avg_price = market_row['avg_price'] if market_row else 0
        price_difference = (
            ((row['avg_price'] - market_avg_price) / market_avg_price) * 100
            if market_avg_price else 0
        )

        if not market_row or market_avg_price <= 0 or market_row.get('listing_count', 0) <= 1:
            price_position = 'No comparison'
            price_tone = 'gray'
        elif price_difference > 15:
            price_position = 'Above market'
            price_tone = 'amber'
        elif price_difference < -15:
            price_position = 'Below market'
            price_tone = 'blue'
        else:
            price_position = 'Fair price'
            price_tone = 'green'

        price_meter_pct = 50
        if market_avg_price:
            price_meter_pct = max(0, min(round(50 + price_difference), 100))

        chart_rows.append({
            **row,
            'revenue_pct': pct(row['approved_revenue'], max_revenue),
            'orders_pct': pct(row['order_count'], max_orders),
            'sold_pct': pct(row['units_sold'], max_quantity),
            'stock_pct': pct(row['total_stock'], max_quantity),
            'market_avg_price': market_avg_price,
            'price_difference': price_difference,
            'price_position': price_position,
            'price_tone': price_tone,
            'price_meter_pct': price_meter_pct
        })

    status_counts = {
        'Approved': sum(1 for order in orders if order.status == 'Approved'),
        'Pending': sum(1 for order in orders if order.status == 'Pending'),
        'Closed': sum(1 for order in orders if order.status in CLOSED_ORDER_STATUSES)
    }
    max_status_count = max(list(status_counts.values()) + [1])
    order_status_chart = [
        {'label': 'Approved', 'count': status_counts['Approved'], 'pct': pct(status_counts['Approved'], max_status_count), 'tone': 'green'},
        {'label': 'Pending', 'count': status_counts['Pending'], 'pct': pct(status_counts['Pending'], max_status_count), 'tone': 'amber'},
        {'label': 'Closed', 'count': status_counts['Closed'], 'pct': pct(status_counts['Closed'], max_status_count), 'tone': 'red'}
    ]

    demand_counts = {
        'High Demand': sum(1 for row in seller_rows if row['demand_trend'] == 'High Demand'),
        'Active Demand': sum(1 for row in seller_rows if row['demand_trend'] == 'Active Demand'),
        'Low Demand': sum(1 for row in seller_rows if row['demand_trend'] == 'Low Demand')
    }
    max_demand_count = max(list(demand_counts.values()) + [1])
    demand_chart = [
        {'label': 'High Demand', 'count': demand_counts['High Demand'], 'pct': pct(demand_counts['High Demand'], max_demand_count), 'tone': 'green'},
        {'label': 'Active Demand', 'count': demand_counts['Active Demand'], 'pct': pct(demand_counts['Active Demand'], max_demand_count), 'tone': 'blue'},
        {'label': 'Low Demand', 'count': demand_counts['Low Demand'], 'pct': pct(demand_counts['Low Demand'], max_demand_count), 'tone': 'gray'}
    ]

    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year
    trend_months = []
    for offset in range(5, -1, -1):
        month = current_month - offset
        year = current_year
        while month <= 0:
            month += 12
            year -= 1
        month_date = datetime(year, month, 1)
        trend_months.append({
            'key': month_date.strftime('%Y-%m'),
            'label': month_date.strftime('%b'),
            'revenue': 0
        })

    trend_by_key = {month['key']: month for month in trend_months}
    for order in approved_orders:
        order_date = order.created_at or datetime.utcnow()
        order_key = order_date.strftime('%Y-%m')
        if order_key in trend_by_key:
            trend_by_key[order_key]['revenue'] += order.total_price or 0

    max_trend_revenue = max([month['revenue'] for month in trend_months] + [1])
    for month in trend_months:
        month['pct'] = pct(month['revenue'], max_trend_revenue)

    return render_template(
        'analytics.html',
        total_sales=total_sales,
        total_orders=total_orders,
        total_units_sold=total_units_sold,
        total_stock=total_stock,
        average_order_value=average_order_value,
        chart_rows=chart_rows,
        order_status_chart=order_status_chart,
        demand_chart=demand_chart,
        trend_months=trend_months
    )

@app.route('/market_insights')
@login_required
def market_insights():
    if current_user.role == 'admin':
        return redirect(url_for('admin') + '#reports')
    if current_user.role != 'farmer':
        return redirect(url_for('marketplace'))

    farmer_products = Product.query.filter_by(farmer_id=current_user.id, is_deleted=False).all()
    ensure_product_reviews(farmer_products)
    market_products = get_approved_products()
    market_rows = build_farmer_price_comparison_rows(
        farmer_products,
        market_products,
        current_user.id
    )
    market_summary = build_price_comparison_summary(market_rows)

    return render_template(
        'market_insights.html',
        market_rows=market_rows,
        market_summary=market_summary
    )

@app.route('/crop_news')
@login_required
def crop_news():
    if current_user.role == 'admin':
        return redirect(url_for('admin') + '#reports')

    news_data = get_live_crop_news(force_refresh=request.args.get('refresh') == '1')

    return render_template(
        'crop_news.html',
        news_items=news_data['items'],
        highlights=CROP_NEWS_HIGHLIGHTS,
        news_last_updated=news_data['last_updated'],
        news_is_live=news_data['is_live'],
        news_error=news_data['error']
    )

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'farmer':          # ✅ Role guard
        return redirect('/marketplace')

    products = Product.query.filter_by(farmer_id=current_user.id, is_deleted=False).all()
    ensure_product_reviews(products)
    orders = Order.query.join(Product).filter(Product.farmer_id == current_user.id).all()
    earnings = sum((o.total_price or 0) for o in orders if o.status == 'Approved')

    all_products = Product.query.filter_by(is_deleted=False).all()
    all_orders = Order.query.filter(Order.status != 'Cancelled').all()
    demand_artifact = load_demand_artifact(app.config.get('DEMAND_MODEL_PATH'))
    if demand_artifact is None:
        demand_artifact = train_demand_model(all_products, all_orders)

    market_rows = build_market_rows(get_approved_products(), [])
    demand_predictions = predict_demand_for_products(
        products,
        all_orders,
        demand_artifact
    )

    product_insights = build_product_insights(products, orders, demand_predictions)
    smart_summary = build_farmer_summary(product_insights)
    price_insights = build_price_insights(products, market_rows)
    farmer_ai_advice = build_farmer_ai_advice(
        products,
        product_insights,
        price_insights,
        demand_predictions
    )

    return render_template(
        'dashboard.html',
        products=products,
        availability=build_product_availability(products),
        earnings=earnings,
        demand_predictions=demand_predictions,
        price_insights=price_insights,
        product_insights=product_insights,
        smart_summary=smart_summary,
        farmer_ai_advice=farmer_ai_advice
    )

@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        return redirect(url_for('marketplace'))

    products = Product.query.order_by(Product.id.desc()).all()
    ensure_product_reviews(products)
    orders = Order.query.all()
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    users = User.query.order_by(User.username.asc()).all()
    report = build_admin_report(products, orders, complaints)

    products = sorted(
        products,
        key=lambda product: (
            PRODUCT_REVIEW_STATUSES.index(product.review.status)
            if product.review and product.review.status in PRODUCT_REVIEW_STATUSES
            else 0,
            -(product.id or 0)
        )
    )

    return render_template(
        'admin.html',
        products=products,
        complaints=complaints,
        users=users,
        orders=orders,
        report=report,
        product_review_statuses=PRODUCT_REVIEW_STATUSES,
        complaint_statuses=COMPLAINT_STATUSES,
        notification_audiences=NOTIFICATION_AUDIENCES,
        notification_recipient_count=sum(1 for user in users if user.role != 'admin' and not user.disabled)
    )

@app.route('/admin/products/<int:product_id>/review', methods=['POST'])
@login_required
def admin_review_product(product_id):
    if current_user.role != 'admin':
        return redirect('/login')

    product = Product.query.get_or_404(product_id)
    ensure_product_reviews([product])
    review = ProductReview.query.filter_by(product_id=product.id).first()

    if product.is_deleted:
        flash("Deleted products cannot be reviewed.", "error")
        return redirect(url_for('admin') + '#products')

    action = request.form.get('action')
    note = request.form.get('admin_note', '').strip()

    if action == 'approve':
        review.status = 'Approved'
        notification_message = f"Your product {product.name} was approved and is now visible in the marketplace."
    elif action == 'reject':
        review.status = 'Rejected'
        notification_message = f"Your product {product.name} needs changes before it can be listed."
        if note:
            notification_message += f" Note: {note}"
    else:
        flash("Invalid product review action.", "error")
        return redirect(url_for('admin') + '#products')

    review.admin_note = note
    review.reviewed_by = current_user.id
    review.reviewed_at = datetime.utcnow()
    db.session.add(Notification(user_id=product.farmer_id, message=notification_message))
    db.session.commit()

    flash(f"Product {review.status.lower()}.", "success")
    return redirect(url_for('admin') + '#products')

@app.route('/admin/reports/download')
@login_required
def admin_download_report():
    if current_user.role != 'admin':
        return redirect('/login')

    products = Product.query.all()
    orders = Order.query.all()
    csv_data = make_report_csv(products, orders)
    filename = f"agrichain-sales-demand-report-{datetime.now().strftime('%Y%m%d')}.csv"

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@app.route('/admin/reports/training-data/download')
@login_required
def admin_download_training_data():
    if current_user.role != 'admin':
        return redirect('/login')

    products = Product.query.filter_by(is_deleted=False).all()
    orders = Order.query.all()
    csv_data = make_training_csv(products, orders)
    filename = f"agrichain-demand-training-data-{datetime.now().strftime('%Y%m%d')}.csv"

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@app.route('/admin/complaints/<int:complaint_id>', methods=['POST'])
@login_required
def admin_update_complaint(complaint_id):
    if current_user.role != 'admin':
        return redirect('/login')

    complaint = Complaint.query.get_or_404(complaint_id)
    status = request.form.get('status')
    resolution = request.form.get('resolution', '').strip()

    if status not in COMPLAINT_STATUSES:
        flash("Invalid complaint status.", "error")
        return redirect(url_for('admin') + '#complaints')

    complaint.status = status
    complaint.resolution = resolution
    if status in ['Resolved', 'Dismissed']:
        complaint.resolved_at = datetime.utcnow()
    else:
        complaint.resolved_at = None

    message = f"Your complaint #{complaint.id} was updated to {status}."
    if resolution:
        message += f" Resolution: {resolution}"
    db.session.add(Notification(user_id=complaint.user_id, message=message))
    db.session.commit()

    flash("Complaint updated.", "success")
    return redirect(url_for('admin') + '#complaints')

@app.route('/admin/notifications/send', methods=['POST'])
@login_required
def admin_send_notification():
    if current_user.role != 'admin':
        return redirect('/login')

    audience = request.form.get('audience')
    notification_type = request.form.get('notification_type', 'Announcement')
    message = request.form.get('message', '').strip()

    if audience not in NOTIFICATION_AUDIENCES:
        flash("Choose a valid notification audience.", "error")
        return redirect(url_for('admin') + '#notifications')

    if not message:
        flash("Notification message cannot be empty.", "error")
        return redirect(url_for('admin') + '#notifications')

    users_query = User.query.filter(User.role != 'admin', User.disabled == False)
    if audience == 'farmers':
        users_query = users_query.filter(User.role == 'farmer')
    elif audience == 'buyers':
        users_query = users_query.filter(User.role == 'buyer')

    count = send_notifications(users_query.all(), f"{notification_type}: {message}")
    db.session.commit()

    flash(f"Notification sent to {count} user{'s' if count != 1 else ''}.", "success")
    return redirect(url_for('admin') + '#notifications')

@app.route('/admin/users/<int:user_id>/status', methods=['POST'])
@login_required
def admin_update_user_status(user_id):
    if current_user.role != 'admin':
        return redirect('/login')

    user = User.query.get_or_404(user_id)
    action = request.form.get('action')

    if user.role == 'admin':
        flash("Admin accounts cannot be suspended here.", "error")
        return redirect(url_for('admin') + '#users')

    if action == 'suspend':
        user.disabled = True
        db.session.add(Notification(
            user_id=user.id,
            message="Your AgriChain account was suspended by admin. Please contact support."
        ))
        flash(f"{user.username} was suspended.", "success")
    elif action == 'activate':
        user.disabled = False
        db.session.add(Notification(
            user_id=user.id,
            message="Your AgriChain account was reactivated by admin."
        ))
        flash(f"{user.username} was reactivated.", "success")
    else:
        flash("Choose a valid user action.", "error")
        return redirect(url_for('admin') + '#users')

    db.session.commit()
    return redirect(url_for('admin') + '#users')

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if current_user.role != 'farmer':          # ✅ Role guard
        return redirect('/marketplace')
    
    if request.method == 'POST':
        file = request.files.get('image')
    
        image_error = validate_image_upload(file)
        if image_error:
            flash(image_error, "error")
            return redirect('/add_product')

        filename = save_image_file(file) if file and file.filename != '' else None

        quantity = parse_positive_float(request.form.get('quantity'))
        price = parse_positive_float(request.form.get('price'))
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash("Product name is required.", "error")
            return redirect('/add_product')

        if quantity <= 0 or price <= 0:
            flash("Quantity and price must be greater than zero.", "error")
            return redirect('/add_product')
            
        product = Product(
            farmer_id=current_user.id,
            name=name,
            quantity=quantity,
            price=price,
            unit=get_product_unit(request.form),
            description=description,
            image=filename
        )
        db.session.add(product)
        db.session.flush()
        db.session.add(ProductReview(product_id=product.id, status='Pending'))
        db.session.add(Notification(
            user_id=current_user.id,
            message=f"{product.name} was submitted for admin review."
        ))
        notify_low_stock(product)
        db.session.commit()
        flash("Product submitted for admin review.", "success")
        return redirect('/dashboard')
    unit_values = [value for value, label in PRODUCT_UNITS if value != 'custom']
    return render_template(
        'add_product.html',
        product_units=PRODUCT_UNITS,
        product_unit_values=unit_values
    )

@app.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if current_user.role != 'farmer':
        return redirect('/marketplace')

    product = Product.query.get_or_404(product_id)
    if product.farmer_id != current_user.id or product.is_deleted:
        flash("You can only edit your active products.", "error")
        return redirect('/dashboard')

    ensure_product_reviews([product])

    if request.method == 'POST':
        file = request.files.get('image')
        image_error = validate_image_upload(file)
        if image_error:
            flash(image_error, "error")
            return redirect(url_for('edit_product', product_id=product.id))

        quantity = parse_positive_float(request.form.get('quantity'))
        price = parse_positive_float(request.form.get('price'))
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash("Product name is required.", "error")
            return redirect(url_for('edit_product', product_id=product.id))

        if quantity <= 0 or price <= 0:
            flash("Quantity and price must be greater than zero.", "error")
            return redirect(url_for('edit_product', product_id=product.id))

        product.name = name
        product.quantity = quantity
        product.price = price
        product.unit = get_product_unit(request.form)
        product.description = description

        if file and file.filename != '':
            product.image = save_image_file(file)

        product.review.status = 'Pending'
        product.review.admin_note = 'Product was edited by the seller and needs review again.'
        product.review.reviewed_by = None
        product.review.reviewed_at = None

        admins = User.query.filter_by(role='admin').all()
        for admin_user in admins:
            db.session.add(Notification(
                user_id=admin_user.id,
                message=f"{product.name} was edited and needs admin review."
            ))

        db.session.add(Notification(
            user_id=current_user.id,
            message=f"{product.name} was updated and sent back for admin review."
        ))
        notify_low_stock(product)
        db.session.commit()

        flash("Product updated and sent for admin review.", "success")
        return redirect('/dashboard')

    unit_values = [value for value, label in PRODUCT_UNITS if value != 'custom']
    return render_template(
        'add_product.html',
        product=product,
        product_units=PRODUCT_UNITS,
        product_unit_values=unit_values,
        form_title='Edit Product',
        form_subtitle='Changes will need admin approval before the product appears in the marketplace again.',
        submit_label='Update Product'
    )

@app.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    if current_user.role != 'farmer':
        return redirect('/marketplace')

    product = Product.query.get_or_404(product_id)
    if product.farmer_id != current_user.id:
        flash("You can only delete your own products.", "error")
        return redirect('/dashboard')

    product.is_deleted = True
    ensure_product_reviews([product])
    if product.review:
        product.review.status = 'Rejected'
        product.review.admin_note = 'Deleted by seller.'
        product.review.reviewed_at = datetime.utcnow()

    pending_orders = [order for order in product.orders if order.status == PENDING_ORDER_STATUS]
    for pending_order in pending_orders:
        pending_order.status = 'Rejected'
        delivery = ensure_delivery(pending_order)
        delivery.tracking_note = 'Seller removed the product listing before approving the order.'
        ensure_order_timeline(pending_order)
        add_order_timeline(
            pending_order,
            'Order Rejected',
            'Seller deleted the product listing before approving the order.',
            current_user
        )
        db.session.add(Notification(
            user_id=pending_order.buyer_id,
            message=f"Your pending order #{pending_order.id} for {product.name} was rejected because the product was removed."
        ))

    db.session.add(Notification(
        user_id=current_user.id,
        message=f"{product.name} was removed from the marketplace."
    ))
    db.session.commit()

    flash("Product removed. Pending orders for it were rejected.", "success")
    return redirect('/dashboard')

# ✅ Single, correct order route
@app.route('/order/<int:product_id>', methods=['GET', 'POST'])
@login_required
def order(product_id):
    if current_user.role == 'admin':
        return redirect(url_for('admin') + '#products')

    product = Product.query.get_or_404(product_id)
    ensure_product_reviews([product])

    if current_user.role != 'buyer':
        flash("Only buyers can place orders.", "error")
        return redirect('/marketplace')

    if not product_is_approved(product):
        flash("This product is still waiting for admin approval.", "error")
        return redirect('/marketplace')

    available_quantity = get_available_quantity(product)
    if available_quantity <= 0:
        flash(f"{product.name} is currently out of stock or fully reserved by pending orders.", "error")
        return redirect('/marketplace')

    all_products = get_approved_products()
    recommendation_details = get_similar_product_details(all_products, product_id, top_n=4)
    recommended_products = [item['product'] for item in recommendation_details]
    
    if request.method == 'POST':
        order_quantity = parse_positive_float(request.form.get('quantity'), default=0)
        available_quantity = get_available_quantity(product)

        if order_quantity <= 0:
            flash("Please enter a valid order quantity.", "error")
            return redirect(url_for('order', product_id=product_id))

        if order_quantity > available_quantity:
            flash("Requested quantity is above the available amount for this product.", "error")
            return redirect(url_for('order', product_id=product_id))

        shipping_address = request.form.get('shipping_address', '').strip()
        contact_number = request.form.get('contact_number', '').strip()

        if not shipping_address:
            flash("Please enter your delivery address.", "error")
            return redirect(url_for('order', product_id=product_id))

        payment_method = 'COD'
        total = (product.price or 0) * order_quantity
        order = Order(
            buyer_id=current_user.id,
            product_id=product_id,
            quantity=order_quantity,
            payment_method=payment_method,
            total_price=total
        )
        db.session.add(order)
        db.session.flush()
        add_order_timeline(
            order,
            'Order Placed',
            f"Buyer placed an order for {format_quantity(order_quantity)} {product.unit or 'unit'}.",
            current_user
        )

        delivery = OrderDelivery(
            order_id=order.id,
            shipping_address=shipping_address,
            contact_number=contact_number,
            status='Address Confirmation',
            tracking_note='Order placed. Seller will confirm the delivery address.'
        )
        db.session.add(delivery)

        address_message = OrderMessage(
            order_id=order.id,
            sender_id=product.farmer_id,
            receiver_id=current_user.id,
            message=f"Please confirm your delivery address: {shipping_address}"
        )
        db.session.add(address_message)
        
        notification = Notification(
            user_id=product.farmer_id,
            message=f"New COD order for {format_quantity(order_quantity)} {product.unit or 'unit'} of {product.name}. Please confirm the buyer address."
        )
        db.session.add(notification)

        buyer_notification = Notification(
            user_id=current_user.id,
            message=f"Your order for {product.name} was placed. Seller will confirm your address."
        )
        db.session.add(buyer_notification)

        db.session.commit()
        flash("Order placed using Cash on Delivery.", "success")
        return redirect(url_for('order_detail', order_id=order.id))
    
    return render_template(
        'payment.html',
        product=product,
        available_quantity=available_quantity,
        recommended_products=recommended_products,
        recommendation_details=recommendation_details
    )

# ✅ Added missing /orders route
@app.route('/orders')
@login_required
def orders():
    if current_user.role == 'admin':
        return redirect(url_for('admin') + '#complaints')

    buyer_orders = Order.query.filter_by(buyer_id=current_user.id).all()
    for buyer_order in buyer_orders:
        ensure_delivery(buyer_order)
    db.session.commit()
    return render_template('orders.html', orders=buyer_orders)

@app.route('/order_detail/<int:order_id>', methods=['GET', 'POST'])
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)

    if not can_access_order(order):
        flash("You cannot view this order.", "error")
        return redirect('/marketplace')

    delivery_was_missing = order.delivery is None
    delivery = ensure_delivery(order)
    timeline_was_missing = OrderTimeline.query.filter_by(order_id=order.id).count() == 0
    ensure_order_timeline(order)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'message':
            message_text = request.form.get('message', '').strip()

            if not message_text:
                flash("Message cannot be empty.", "error")
                return redirect(url_for('order_detail', order_id=order.id))

            receiver_id = get_message_receiver(order)
            db.session.add(OrderMessage(
                order_id=order.id,
                sender_id=current_user.id,
                receiver_id=receiver_id,
                message=message_text
            ))
            db.session.add(Notification(
                user_id=receiver_id,
                message=f"New message about order #{order.id}"
            ))
            db.session.commit()
            return redirect(url_for('order_detail', order_id=order.id))

        if action == 'confirm_address':
            if current_user.id != order.buyer_id:
                flash("Only the buyer can confirm the delivery address.", "error")
                return redirect(url_for('order_detail', order_id=order.id))

            delivery.tracking_note = 'Buyer confirmed the delivery address. Seller can prepare the order.'
            add_order_timeline(
                order,
                'Address Confirmed',
                delivery.tracking_note,
                current_user
            )
            db.session.add(OrderMessage(
                order_id=order.id,
                sender_id=current_user.id,
                receiver_id=order.product.farmer_id,
                message='I confirm that the delivery address is correct.'
            ))
            db.session.add(Notification(
                user_id=order.product.farmer_id,
                message=f"Buyer confirmed address for order #{order.id}"
            ))
            db.session.commit()
            flash("Address confirmed.", "success")
            return redirect(url_for('order_detail', order_id=order.id))

        if action == 'update_delivery':
            if current_user.role != 'admin' and order.product.farmer_id != current_user.id:
                flash("Only the seller can update delivery tracking.", "error")
                return redirect(url_for('order_detail', order_id=order.id))

            if order.status == 'Pending':
                flash("Approve the order before updating delivery tracking.", "error")
                return redirect(url_for('order_detail', order_id=order.id))

            new_status = request.form.get('delivery_status')
            tracking_note = request.form.get('tracking_note', '').strip()
            proof_file = request.files.get('proof_image')

            if new_status not in DELIVERY_STATUSES:
                flash("Invalid delivery status.", "error")
                return redirect(url_for('order_detail', order_id=order.id))

            proof_required = new_status == 'Delivered' and not order.delivery_proof
            image_error = validate_image_upload(proof_file, required=proof_required)
            if image_error:
                flash(image_error, "error")
                return redirect(url_for('order_detail', order_id=order.id))

            proof_image = save_image_file(proof_file, 'delivery_proofs') if proof_file and proof_file.filename != '' else None
            delivery.status = new_status
            delivery.tracking_note = tracking_note or f"Tracking updated to {new_status}."

            if proof_image:
                if order.delivery_proof:
                    order.delivery_proof.image = proof_image
                    order.delivery_proof.note = delivery.tracking_note
                    order.delivery_proof.uploaded_by = current_user.id
                    order.delivery_proof.created_at = datetime.utcnow()
                else:
                    db.session.add(DeliveryProof(
                        order_id=order.id,
                        image=proof_image,
                        note=delivery.tracking_note,
                        uploaded_by=current_user.id
                    ))

            add_order_timeline(
                order,
                new_status,
                delivery.tracking_note,
                current_user
            )
            buyer_message = f"Tracking update: {new_status}. {delivery.tracking_note}"
            if proof_image:
                buyer_message += " Photo attached."
            db.session.add(OrderMessage(
                order_id=order.id,
                sender_id=current_user.id,
                receiver_id=order.buyer_id,
                message=buyer_message,
                image=proof_image
            ))
            db.session.add(Notification(
                user_id=order.buyer_id,
                message=f"Tracking updated for order #{order.id}: {new_status}{' with photo' if proof_image else ''}"
            ))
            db.session.commit()
            flash("Delivery tracking updated.", "success")
            return redirect(url_for('order_detail', order_id=order.id))

    if delivery_was_missing or timeline_was_missing:
        db.session.commit()

    messages = OrderMessage.query.filter_by(order_id=order.id).order_by(OrderMessage.created_at.asc()).all()
    timeline_entries = (
        OrderTimeline.query
        .filter_by(order_id=order.id)
        .order_by(OrderTimeline.created_at.asc())
        .all()
    )

    current_step = (
        DELIVERY_STATUSES.index(delivery.status)
        if delivery.status in DELIVERY_STATUSES
        else 0
    )

    return render_template(
        'order_detail.html',
        order=order,
        delivery=delivery,
        messages=messages,
        timeline_entries=timeline_entries,
        can_rate_order=order_can_be_rated(order),
        delivery_statuses=DELIVERY_STATUSES,
        current_step=current_step
    )

@app.route('/orders/<int:order_id>/receipt')
@login_required
def order_receipt(order_id):
    order = Order.query.get_or_404(order_id)
    if not can_access_order(order):
        flash("You cannot view this receipt.", "error")
        return redirect('/marketplace')

    delivery = ensure_delivery(order)
    if delivery.status != 'Delivered':
        flash("Receipt becomes available after delivery.", "error")
        return redirect(url_for('order_detail', order_id=order.id))

    if order.delivery is None:
        db.session.commit()

    return render_template('receipt.html', order=order, delivery=delivery)

@app.route('/orders/<int:order_id>/rate', methods=['POST'])
@login_required
def rate_order(order_id):
    order = Order.query.get_or_404(order_id)
    ensure_delivery(order)

    if not order_can_be_rated(order):
        flash("This order cannot be rated right now.", "error")
        return redirect(url_for('order_detail', order_id=order.id))

    try:
        rating_value = int(request.form.get('rating', 0))
    except (TypeError, ValueError):
        rating_value = 0

    if rating_value < 1 or rating_value > 5:
        flash("Choose a rating from 1 to 5.", "error")
        return redirect(url_for('order_detail', order_id=order.id))

    comment = request.form.get('comment', '').strip()
    db.session.add(ProductRating(
        order_id=order.id,
        product_id=order.product_id,
        buyer_id=current_user.id,
        farmer_id=order.product.farmer_id,
        rating=rating_value,
        comment=comment
    ))
    db.session.add(Notification(
        user_id=order.product.farmer_id,
        message=f"New {rating_value}-star rating for {order.product.name} on order #{order.id}."
    ))
    db.session.commit()

    flash("Thanks for rating this order.", "success")
    return redirect(url_for('order_detail', order_id=order.id))

@app.route('/farmer_orders')
@login_required
def farmer_orders():
    if current_user.role != 'farmer':          # ✅ Role guard
        return redirect('/marketplace')
    products = Product.query.filter_by(farmer_id=current_user.id).all()
    product_ids = [p.id for p in products]
    orders = Order.query.filter(Order.product_id.in_(product_ids)).all()
    for farmer_order in orders:
        ensure_delivery(farmer_order)
    db.session.commit()
    return render_template(
        'farmer_orders.html',
        orders=orders,
        availability=build_product_availability(products)
    )

@app.route('/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if current_user.role != 'buyer' or order.buyer_id != current_user.id:
        flash("You can only cancel your own orders.", "error")
        return redirect('/orders')

    if order.status != PENDING_ORDER_STATUS:
        flash("Only pending orders can be cancelled.", "error")
        return redirect(url_for('order_detail', order_id=order.id))

    ensure_order_timeline(order)
    order.status = 'Cancelled'
    delivery = ensure_delivery(order)
    delivery.tracking_note = 'Buyer cancelled the order before seller approval.'
    add_order_timeline(
        order,
        'Order Cancelled',
        'Buyer cancelled the order before seller approval.',
        current_user
    )
    db.session.add(Notification(
        user_id=order.product.farmer_id,
        message=f"Order #{order.id} for {order.product.name} was cancelled by the buyer."
    ))
    db.session.commit()

    flash("Order cancelled.", "success")
    return redirect('/orders')

@app.route('/reject_order/<int:order_id>', methods=['POST'])
@login_required
def reject_order(order_id):
    if current_user.role != 'farmer':
        return redirect('/marketplace')

    order = Order.query.get_or_404(order_id)
    product = order.product

    if not product or product.farmer_id != current_user.id:
        flash("You can only reject orders for your own products.", "error")
        return redirect('/farmer_orders')

    if order.status != PENDING_ORDER_STATUS:
        flash("Only pending orders can be rejected.", "error")
        return redirect('/farmer_orders')

    reason = request.form.get('reason', '').strip()
    ensure_order_timeline(order)
    order.status = 'Rejected'
    delivery = ensure_delivery(order)
    note = reason or 'Seller rejected the order before approval.'
    delivery.tracking_note = note
    add_order_timeline(order, 'Order Rejected', note, current_user)
    message = f"Your order #{order.id} for {product.name} was rejected by the seller."
    if reason:
        message += f" Reason: {reason}"
    db.session.add(Notification(user_id=order.buyer_id, message=message))
    db.session.commit()

    flash("Order rejected.", "success")
    return redirect('/farmer_orders')

@app.route('/approve_order/<int:order_id>', methods=['POST'])
@login_required
def approve_order(order_id):
    if current_user.role != 'farmer':
        return redirect('/marketplace')

    order = Order.query.get_or_404(order_id)
    product = order.product

    if not product or product.farmer_id != current_user.id:
        flash("You can only approve orders for your own products.", "error")
        return redirect('/farmer_orders')

    if order.status != PENDING_ORDER_STATUS:
        flash(f"Only pending orders can be approved. Current status: {order.status}.", "info")
        return redirect('/farmer_orders')

    order_quantity = order.quantity or 0
    stock_quantity = float(product.quantity or 0)
    available_quantity = get_available_quantity(product, exclude_order_id=order.id)

    if order_quantity <= 0:
        flash("Invalid order quantity.", "error")
        return redirect('/farmer_orders')

    if available_quantity < order_quantity:
        flash(
            f"Not enough stock for {product.name}. Available: {format_quantity(available_quantity)} {product.unit or 'unit'}, ordered: {format_quantity(order_quantity)} {product.unit or 'unit'}.",
            "error"
        )
        return redirect('/farmer_orders')

    product.quantity = stock_quantity - order_quantity
    order.status = APPROVED_ORDER_STATUS
    delivery = ensure_delivery(order)
    delivery.status = 'Preparing Order'
    delivery.tracking_note = 'Seller approved the order and is preparing it for delivery.'
    ensure_order_timeline(order)
    add_order_timeline(
        order,
        'Order Approved',
        'Seller approved the order and stock was deducted.',
        current_user
    )
    add_order_timeline(
        order,
        'Preparing Order',
        delivery.tracking_note,
        current_user
    )
    db.session.add(Notification(
        user_id=order.buyer_id,
        message=f"Your order for {product.name} was approved and is being prepared."
    ))
    notify_low_stock(product)
    db.session.commit()
    flash(f"Order approved. {product.name} stock is now {format_quantity(product.quantity)} {product.unit or 'unit'}.", "success")
    return redirect('/farmer_orders')

if __name__ == '__main__':
    with app.app_context():
        ensure_database_ready()
        _load_ai_models()   # Pre-load XGBoost models so AI is ready on first request
    app.run(debug=True)
