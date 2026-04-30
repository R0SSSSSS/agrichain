from flask import Flask, Response, render_template, request, redirect, url_for, flash
from config import Config
from models import Complaint, OrderDelivery, OrderMessage, ProductReview
from models import db, User, Product, Order, Notification  # ✅ Added Notification
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
from recommendation import get_similar_products
from demand_prediction import train_demand_model, predict_product_demand
from market_insights import build_market_rows, build_market_summary, build_price_insights
from smart_insights import build_farmer_summary, build_product_insights
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

app = Flask(__name__)
app.config.from_object(Config)

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
        'category': 'Logistics',
        'summary': (
            'The National Sectoral Committee on Fruits and Vegetables backed a '
            'mitigation plan for fuel supply concerns that may affect farm '
            'logistics, production costs, and market stability.'
        ),
        'impact': 'Sellers should monitor transport costs when setting delivery and product prices.',
        'source': 'Philippine Council for Agriculture and Fisheries',
        'url': 'https://pcaf.da.gov.ph/index.php/2026/04/08/nsc-fv-backs-mitigation-plan-vs-fuel-concerns-endorses-key-agri-budget-proposal/'
    }
]

CROP_NEWS_HIGHLIGHTS = [
    {'label': 'Export crops to watch', 'value': 'Banana, mango, avocado, durian'},
    {'label': 'Protected vegetable focus', 'value': 'Chili, tomato, bell pepper'},
    {'label': 'Farmer planning signal', 'value': 'Track logistics and weather risks'}
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

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
            location='Platform Admin'
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
    return bool(product.review and product.review.status == 'Approved')

def get_approved_products():
    ensure_product_reviews()
    return (
        Product.query
        .join(ProductReview)
        .filter(ProductReview.status == 'Approved')
        .all()
    )

def send_notifications(users, message):
    recipients = [user for user in users if user.role != 'admin']
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
    writer.writerow(['Product', 'Orders', 'Units Sold', 'Stock', 'Demand Trend', 'Revenue'])

    for row in build_market_rows(products, orders):
        writer.writerow([
            row['name'],
            row['order_count'],
            row['units_sold'],
            row['total_stock'],
            row['demand_trend'],
            f"{row['approved_revenue']:.2f}"
        ])

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
            'impact': 'Live news item. Review the source before using it for planting, pricing, or logistics decisions.',
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
    return render_template('index.html', products=products)

@app.route('/analytics')
@login_required
def analytics():
    if current_user.role == 'admin':
        return redirect(url_for('admin') + '#reports')
    if current_user.role != 'farmer':
        return redirect('/marketplace')

    orders = Order.query.all()
    products = Product.query.all()
    market_rows = build_market_rows(products, orders)
    market_summary = build_market_summary(market_rows)
    total_sales = sum((o.total_price or 0) for o in orders if o.status == 'Approved')
    total_orders = len(orders)
    return render_template(
        'analytics.html',
        total_sales=total_sales,
        total_orders=total_orders,
        market_rows=market_rows,
        market_summary=market_summary
    )

@app.route('/market_insights')
@login_required
def market_insights():
    if current_user.role == 'admin':
        return redirect(url_for('admin') + '#reports')

    products = Product.query.all()
    orders = Order.query.all()
    market_rows = build_market_rows(products, orders)
    market_summary = build_market_summary(market_rows)

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

    products = Product.query.filter_by(farmer_id=current_user.id).all()
    ensure_product_reviews(products)
    orders = Order.query.join(Product).filter(Product.farmer_id == current_user.id).all()
    earnings = sum((o.total_price or 0) for o in orders if o.status == 'Approved')

    all_products = Product.query.all()
    all_orders = Order.query.all()
    model, name_encoder, location_encoder = train_demand_model(all_products, all_orders)
    market_rows = build_market_rows(all_products, all_orders)

    demand_predictions = {}
    for product in products:
        demand_predictions[product.id] = predict_product_demand(
            product,
            model,
            name_encoder,
            location_encoder
        )

    product_insights = build_product_insights(products, orders, demand_predictions)
    smart_summary = build_farmer_summary(product_insights)
    price_insights = build_price_insights(products, market_rows)

    return render_template(
        'dashboard.html',
        products=products,
        earnings=earnings,
        demand_predictions=demand_predictions,
        price_insights=price_insights,
        product_insights=product_insights,
        smart_summary=smart_summary
    )

@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        return redirect('/login')

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
        notification_recipient_count=sum(1 for user in users if user.role != 'admin')
    )

@app.route('/admin/products/<int:product_id>/review', methods=['POST'])
@login_required
def admin_review_product(product_id):
    if current_user.role != 'admin':
        return redirect('/login')

    product = Product.query.get_or_404(product_id)
    ensure_product_reviews([product])
    review = ProductReview.query.filter_by(product_id=product.id).first()

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

    users_query = User.query.filter(User.role != 'admin')
    if audience == 'farmers':
        users_query = users_query.filter(User.role == 'farmer')
    elif audience == 'buyers':
        users_query = users_query.filter(User.role == 'buyer')

    count = send_notifications(users_query.all(), f"{notification_type}: {message}")
    db.session.commit()

    flash(f"Notification sent to {count} user{'s' if count != 1 else ''}.", "success")
    return redirect(url_for('admin') + '#notifications')

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if current_user.role != 'farmer':          # ✅ Role guard
        return redirect('/marketplace')
    
    if request.method == 'POST':
        file = request.files.get('image')
    
        if file and file.filename != '':
            filename = secure_filename(file.filename)  # ✅ sanitizes spaces & special chars
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
        else:
            filename = None
            
        product = Product(
            farmer_id=current_user.id,
            name=request.form['name'],
            quantity=request.form['quantity'],
            price=request.form['price'],
            description=request.form['description'],
            image=filename
        )
        db.session.add(product)
        db.session.flush()
        db.session.add(ProductReview(product_id=product.id, status='Pending'))
        db.session.add(Notification(
            user_id=current_user.id,
            message=f"{product.name} was submitted for admin review."
        ))
        db.session.commit()
        flash("Product submitted for admin review.", "success")
        return redirect('/dashboard')
    return render_template('add_product.html')

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

    all_products = get_approved_products()
    recommended_products = get_similar_products(all_products, product_id, top_n=4)
    
    if request.method == 'POST':
        if (product.quantity or 0) <= 0:
            flash(f"{product.name} is currently out of stock.", "error")
            return redirect('/marketplace')

        shipping_address = request.form.get('shipping_address', '').strip()
        contact_number = request.form.get('contact_number', '').strip()

        if not shipping_address:
            flash("Please enter your delivery address.", "error")
            return redirect(url_for('order', product_id=product_id))

        payment_method = 'COD'
        total = (product.price or 0) * 1
        order = Order(
            buyer_id=current_user.id,
            product_id=product_id,
            quantity=1,
            payment_method=payment_method,
            total_price=total
        )
        db.session.add(order)
        db.session.flush()

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
            message=f"New COD order for {product.name}. Please confirm the buyer address."
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
        recommended_products=recommended_products
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

            if new_status not in DELIVERY_STATUSES:
                flash("Invalid delivery status.", "error")
                return redirect(url_for('order_detail', order_id=order.id))

            delivery.status = new_status
            delivery.tracking_note = tracking_note or f"Tracking updated to {new_status}."
            db.session.add(Notification(
                user_id=order.buyer_id,
                message=f"Tracking updated for order #{order.id}: {new_status}"
            ))
            db.session.commit()
            flash("Delivery tracking updated.", "success")
            return redirect(url_for('order_detail', order_id=order.id))

    if delivery_was_missing:
        db.session.commit()

    messages = OrderMessage.query.filter_by(order_id=order.id).order_by(OrderMessage.created_at.asc()).all()

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
        delivery_statuses=DELIVERY_STATUSES,
        current_step=current_step
    )

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
    return render_template('farmer_orders.html', orders=orders)

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

    if order.status == 'Approved':
        flash("Order already approved. Stock was not deducted again.", "info")
        return redirect('/farmer_orders')

    order_quantity = order.quantity or 0
    available_quantity = product.quantity or 0

    if order_quantity <= 0:
        flash("Invalid order quantity.", "error")
        return redirect('/farmer_orders')

    if available_quantity < order_quantity:
        flash(
            f"Not enough stock for {product.name}. Available: {available_quantity}, ordered: {order_quantity}.",
            "error"
        )
        return redirect('/farmer_orders')

    product.quantity = available_quantity - order_quantity
    order.status = 'Approved'
    delivery = ensure_delivery(order)
    delivery.status = 'Preparing Order'
    delivery.tracking_note = 'Seller approved the order and is preparing it for delivery.'
    db.session.add(Notification(
        user_id=order.buyer_id,
        message=f"Your order for {product.name} was approved and is being prepared."
    ))
    db.session.commit()
    flash(f"Order approved. {product.name} stock is now {product.quantity}.", "success")
    return redirect('/farmer_orders')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        ensure_product_reviews()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
