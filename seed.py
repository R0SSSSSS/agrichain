"""
AgriChain Database Seeder
=========================
Creates all tables in the local SQLite database and populates them with
realistic demo data so the app is fully usable out of the box.

Run:  venv\\Scripts\\python.exe seed.py
"""

import os
import sys
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from app import app
from models import (
    db, User, Product, ProductReview, Order, OrderDelivery,
    OrderTimeline, OrderMessage, Notification, Complaint,
    ProductRating, DeliveryProof, ProductPriceHistory
)

# ── Helpers ────────────────────────────────────────────────────────────────────

def pwd(p):
    return generate_password_hash(p)

def ago(days=0, hours=0):
    return datetime.utcnow() - timedelta(days=days, hours=hours)

# ── Seed ───────────────────────────────────────────────────────────────────────

def seed():
    with app.app_context():
        print("[seed] Dropping and recreating all tables...")
        db.drop_all()
        db.create_all()

        # ── Users ──────────────────────────────────────────────────────────────
        print("[seed] Creating users...")

        admin   = User(username='admin',   password=pwd('agrichain123'), role='admin',  location='Platform Admin', disabled=False)
        vincent = User(username='vincent', password=pwd('password123'),  role='admin',  location='Surigao City',   disabled=False)

        mae   = User(username='mae',   password=pwd('password123'), role='farmer', location='Togbongon',   disabled=False)
        rozz  = User(username='Rozz',  password=pwd('password123'), role='farmer', location='Lianga',      disabled=False)
        ross  = User(username='ROSS',  password=pwd('password123'), role='farmer', location='Placer',      disabled=False)

        jelian = User(username='jelian', password=pwd('password123'), role='buyer', location='Togbongon', disabled=False)
        gian   = User(username='gian',   password=pwd('password123'), role='buyer', location='Madrid',    disabled=False)

        db.session.add_all([admin, vincent, mae, rozz, ross, jelian, gian])
        db.session.flush()

        # ── Products ───────────────────────────────────────────────────────────
        print("[seed] Creating products...")

        kangkong = Product(
            farmer_id=mae.id, name='Kangkong', quantity=99, price=50,
            unit='bundle', description='Fresh water spinach harvested daily from our backyard farm.',
            image='WATER-SPINACH_RESIZED1.jpg', is_deleted=False
        )
        apples = Product(
            farmer_id=mae.id, name='Apples', quantity=1000, price=25,
            unit='piece', description='Apples shipped from Bukidnon — sweet and crunchy.',
            image='BKS5305.jpg', is_deleted=False
        )
        rice = Product(
            farmer_id=rozz.id, name='Rice', quantity=99, price=100,
            unit='kg', description='Freshly harvested rice from Brgy Togbongon. No preservatives.',
            image='wheat.jpg', is_deleted=False
        )
        eggplant = Product(
            farmer_id=ross.id, name='Eggplant', quantity=200, price=35,
            unit='kg', description='Fresh eggplant straight from the farm. Great for adobo.',
            image=None, is_deleted=False
        )
        mango = Product(
            farmer_id=rozz.id, name='Mango', quantity=150, price=80,
            unit='piece', description='Sweet Carabao mangoes — export quality.',
            image=None, is_deleted=False
        )
        garlic = Product(
            farmer_id=ross.id, name='Garlic', quantity=50, price=120,
            unit='kg', description='Locally grown native garlic, strong aroma.',
            image=None, is_deleted=False
        )

        db.session.add_all([kangkong, apples, rice, eggplant, mango, garlic])
        db.session.flush()

        # ── Product Reviews ────────────────────────────────────────────────────
        print("[seed] Approving products...")

        reviews = [
            ProductReview(product_id=kangkong.id, status='Approved', admin_note='Looks good.',
                          reviewed_by=admin.id, created_at=ago(10), reviewed_at=ago(9)),
            ProductReview(product_id=apples.id,   status='Approved', admin_note='Approved.',
                          reviewed_by=admin.id, created_at=ago(10), reviewed_at=ago(9)),
            ProductReview(product_id=rice.id,     status='Approved', admin_note='Approved.',
                          reviewed_by=admin.id, created_at=ago(8),  reviewed_at=ago(7)),
            ProductReview(product_id=eggplant.id, status='Approved', admin_note='Approved.',
                          reviewed_by=admin.id, created_at=ago(6),  reviewed_at=ago(5)),
            ProductReview(product_id=mango.id,    status='Approved', admin_note='Approved.',
                          reviewed_by=admin.id, created_at=ago(5),  reviewed_at=ago(4)),
            ProductReview(product_id=garlic.id,   status='Pending',  admin_note=None,
                          reviewed_by=None,     created_at=ago(1),  reviewed_at=None),
        ]
        db.session.add_all(reviews)
        db.session.flush()

        # ── Orders ─────────────────────────────────────────────────────────────
        print("[seed] Creating orders...")

        # Delivered orders
        o1 = Order(buyer_id=jelian.id, product_id=kangkong.id, quantity=1,  status='Approved',
                   payment_method='COD',   total_price=50,   created_at=ago(8))
        o2 = Order(buyer_id=jelian.id, product_id=apples.id,  quantity=2,  status='Approved',
                   payment_method='COD',   total_price=50,   created_at=ago(7))
        o3 = Order(buyer_id=jelian.id, product_id=rice.id,    quantity=1,  status='Approved',
                   payment_method='GCash', total_price=100,  created_at=ago(5))
        o4 = Order(buyer_id=gian.id,   product_id=mango.id,   quantity=5,  status='Approved',
                   payment_method='COD',   total_price=400,  created_at=ago(4))
        o5 = Order(buyer_id=gian.id,   product_id=eggplant.id,quantity=10, status='Approved',
                   payment_method='GCash', total_price=350,  created_at=ago(3))
        # Pending (AI will score these)
        o6 = Order(buyer_id=jelian.id, product_id=mango.id,   quantity=20, status='Pending',
                   payment_method='COD',   total_price=1600, created_at=ago(0, 2))
        o7 = Order(buyer_id=gian.id,   product_id=kangkong.id,quantity=5,  status='Pending',
                   payment_method='COD',   total_price=250,  created_at=ago(0, 1))
        # Cancelled
        o8 = Order(buyer_id=jelian.id, product_id=garlic.id,  quantity=3,  status='Cancelled',
                   payment_method='COD',   total_price=360,  created_at=ago(2))

        db.session.add_all([o1, o2, o3, o4, o5, o6, o7, o8])
        db.session.flush()

        # ── Order Deliveries ────────────────────────────────────────────────────
        print("[seed] Creating deliveries...")

        deliveries = [
            OrderDelivery(order_id=o1.id, shipping_address='Togbongon P-1', contact_number='09518388101',
                          status='Delivered',          tracking_note='Delivered successfully.',
                          created_at=ago(8), updated_at=ago(7)),
            OrderDelivery(order_id=o2.id, shipping_address='Togbongon P-1', contact_number='09518388101',
                          status='Delivered',          tracking_note='Delivered successfully.',
                          created_at=ago(7), updated_at=ago(6)),
            OrderDelivery(order_id=o3.id, shipping_address='Togbongon P-1', contact_number='09518388101',
                          status='Delivered',          tracking_note='Delivered successfully.',
                          created_at=ago(5), updated_at=ago(4)),
            OrderDelivery(order_id=o4.id, shipping_address='Madrid, Surigao del Sur', contact_number='09633003839',
                          status='Delivered',          tracking_note='Delivered successfully.',
                          created_at=ago(4), updated_at=ago(3)),
            OrderDelivery(order_id=o5.id, shipping_address='Madrid, Surigao del Sur', contact_number='09633003839',
                          status='Out for Delivery',   tracking_note='Package is out for delivery.',
                          created_at=ago(3), updated_at=ago(0, 4)),
            OrderDelivery(order_id=o6.id, shipping_address='Togbongon P-1', contact_number='09518388101',
                          status='Address Confirmation', tracking_note='Please confirm your delivery address.',
                          created_at=ago(0, 2), updated_at=ago(0, 2)),
            OrderDelivery(order_id=o7.id, shipping_address='Madrid, Surigao del Sur', contact_number='09633003839',
                          status='Address Confirmation', tracking_note='Please confirm your delivery address.',
                          created_at=ago(0, 1), updated_at=ago(0, 1)),
            OrderDelivery(order_id=o8.id, shipping_address='Togbongon P-1', contact_number='09518388101',
                          status='Cancelled',          tracking_note='Order was cancelled.',
                          created_at=ago(2), updated_at=ago(2)),
        ]
        db.session.add_all(deliveries)

        # ── Order Timelines ─────────────────────────────────────────────────────
        print("[seed] Creating timelines...")

        timelines = [
            # o1
            OrderTimeline(order_id=o1.id, status='Order Placed',       note='Order was placed.', actor_id=jelian.id, created_at=ago(8)),
            OrderTimeline(order_id=o1.id, status='Preparing Order',    note='Seller is preparing.', actor_id=mae.id, created_at=ago(8, 2)),
            OrderTimeline(order_id=o1.id, status='Delivered',          note='Delivered.', actor_id=mae.id, created_at=ago(7)),
            # o3
            OrderTimeline(order_id=o3.id, status='Order Placed',       note='Order was placed.', actor_id=jelian.id, created_at=ago(5)),
            OrderTimeline(order_id=o3.id, status='Out for Delivery',   note='On the way.', actor_id=rozz.id, created_at=ago(4, 6)),
            OrderTimeline(order_id=o3.id, status='Delivered',          note='Delivered.', actor_id=rozz.id, created_at=ago(4)),
            # o6 pending
            OrderTimeline(order_id=o6.id, status='Order Placed',       note='Order was placed.', actor_id=jelian.id, created_at=ago(0, 2)),
            # o7 pending
            OrderTimeline(order_id=o7.id, status='Order Placed',       note='Order was placed.', actor_id=gian.id, created_at=ago(0, 1)),
            # o8 cancelled
            OrderTimeline(order_id=o8.id, status='Order Placed',       note='Order was placed.', actor_id=jelian.id, created_at=ago(2)),
            OrderTimeline(order_id=o8.id, status='Cancelled',          note='Buyer cancelled.', actor_id=jelian.id, created_at=ago(2, 1)),
        ]
        db.session.add_all(timelines)

        # ── Order Messages ──────────────────────────────────────────────────────
        print("[seed] Creating messages...")

        messages = [
            OrderMessage(order_id=o1.id, sender_id=mae.id,    receiver_id=jelian.id,
                         message='Please confirm your delivery address: Togbongon P-1', created_at=ago(8)),
            OrderMessage(order_id=o1.id, sender_id=jelian.id, receiver_id=mae.id,
                         message='Yes, that address is correct. Thank you!', created_at=ago(7, 22)),
            OrderMessage(order_id=o3.id, sender_id=rozz.id,   receiver_id=jelian.id,
                         message='Your Rice order is on the way. ETA: tomorrow.', created_at=ago(4, 8)),
            OrderMessage(order_id=o3.id, sender_id=jelian.id, receiver_id=rozz.id,
                         message='Great! I will be home all day.', created_at=ago(4, 7)),
            OrderMessage(order_id=o6.id, sender_id=rozz.id,   receiver_id=jelian.id,
                         message='Please confirm your delivery address for the Mango order.', created_at=ago(0, 2)),
        ]
        db.session.add_all(messages)

        # ── Product Ratings ─────────────────────────────────────────────────────
        print("[seed] Creating ratings...")

        ratings = [
            ProductRating(order_id=o1.id, product_id=kangkong.id, buyer_id=jelian.id, farmer_id=mae.id,
                          rating=5, comment='Super fresh! Will order again.', created_at=ago(7)),
            ProductRating(order_id=o2.id, product_id=apples.id,   buyer_id=jelian.id, farmer_id=mae.id,
                          rating=4, comment='Good quality, arrived on time.', created_at=ago(6)),
            ProductRating(order_id=o3.id, product_id=rice.id,     buyer_id=jelian.id, farmer_id=rozz.id,
                          rating=5, comment='Excellent rice, very fresh harvest!', created_at=ago(4)),
            ProductRating(order_id=o4.id, product_id=mango.id,    buyer_id=gian.id,   farmer_id=rozz.id,
                          rating=5, comment='Best mangoes I have ever tasted!', created_at=ago(3)),
        ]
        db.session.add_all(ratings)

        # ── Complaints ──────────────────────────────────────────────────────────
        print("[seed] Creating complaints...")

        complaint1 = Complaint(
            user_id=jelian.id, order_id=o8.id,
            subject='Order cancelled but no refund info given',
            message='My garlic order was cancelled but I have not received any communication about a refund.',
            status='In Review', resolution='We are looking into this for you.',
            created_at=ago(2), updated_at=ago(1)
        )
        db.session.add(complaint1)
        db.session.flush()

        # ── Notifications ───────────────────────────────────────────────────────
        print("[seed] Creating notifications...")

        notifications = [
            Notification(user_id=mae.id,    message='New order for Kangkong from jelian.',           is_read=True,  created_at=ago(8)),
            Notification(user_id=jelian.id,  message='Your Kangkong order was approved.',             is_read=True,  created_at=ago(8)),
            Notification(user_id=jelian.id,  message='Your Kangkong order has been delivered.',       is_read=True,  created_at=ago(7)),
            Notification(user_id=rozz.id,    message='New order for Rice from jelian.',               is_read=True,  created_at=ago(5)),
            Notification(user_id=jelian.id,  message='Your Rice order is out for delivery.',          is_read=True,  created_at=ago(4)),
            Notification(user_id=rozz.id,    message='New COD order for Mango. Please confirm address.', is_read=False, created_at=ago(0, 2)),
            Notification(user_id=jelian.id,  message='Your Mango order was placed.',                  is_read=False, created_at=ago(0, 2)),
            Notification(user_id=mae.id,     message='New COD order for Kangkong from gian.',         is_read=False, created_at=ago(0, 1)),
            Notification(user_id=gian.id,    message='Your Kangkong order was placed.',               is_read=False, created_at=ago(0, 1)),
            Notification(user_id=jelian.id,  message='Your complaint #1 is now In Review.',           is_read=False, created_at=ago(1)),
            # Farmer product approval notifications
            Notification(user_id=mae.id,    message='Your product Kangkong was approved.',            is_read=True,  created_at=ago(9)),
            Notification(user_id=mae.id,    message='Your product Apples was approved.',              is_read=True,  created_at=ago(9)),
            Notification(user_id=rozz.id,   message='Your product Rice was approved.',                is_read=True,  created_at=ago(7)),
            Notification(user_id=rozz.id,   message='Your product Mango was approved.',               is_read=True,  created_at=ago(4)),
            Notification(user_id=ross.id,   message='Your product Eggplant was approved.',            is_read=True,  created_at=ago(5)),
            Notification(user_id=ross.id,   message='Your product Garlic is pending admin review.',   is_read=False, created_at=ago(1)),
            Notification(user_id=admin.id,  message='New complaint #1 from jelian: Order cancelled but no refund info given.', is_read=False, created_at=ago(2)),
        ]
        db.session.add_all(notifications)

        # ── Price History ───────────────────────────────────────────────────────
        print("[seed] Creating price history...")
        price_histories = [
            ProductPriceHistory(product_id=kangkong.id, old_price=45, new_price=50, changed_at=ago(15)),
            ProductPriceHistory(product_id=rice.id,     old_price=90, new_price=100, changed_at=ago(10)),
            ProductPriceHistory(product_id=mango.id,    old_price=70, new_price=80, changed_at=ago(6)),
        ]
        db.session.add_all(price_histories)

        db.session.commit()

        print()
        print("=" * 55)
        print("  AgriChain database seeded successfully!")
        print("=" * 55)
        print()
        print("  Test accounts (password: password123 for all)")
        print()
        print("  ADMIN")
        print("    admin    / agrichain123  (master admin)")
        print("    vincent  / password123")
        print()
        print("  FARMERS")
        print("    mae      / password123   (Kangkong, Apples)")
        print("    Rozz     / password123   (Rice, Mango)")
        print("    ROSS     / password123   (Eggplant, Garlic)")
        print()
        print("  BUYERS")
        print("    jelian   / password123")
        print("    gian     / password123")
        print()
        print("  Run the app:  venv\\Scripts\\python.exe app.py")
        print()


if __name__ == '__main__':
    seed()
