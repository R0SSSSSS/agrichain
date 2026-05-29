"""
AgriChain AI Service
====================
Loads the v2 XGBoost models (risk + complaint) and exposes clean inference
functions used by both the Flask routes and internal helpers.

Risk Model  — 13 features (see metadata):
  product_name, farmer_location, buyer_location, weather_condition,
  packaging_type, is_organic, farmer_experience_years, unit_price,
  quantity, discount_applied, total_price, payment_method, shipping_distance_km

Complaint Model — 8 features:
  product_name, total_price, payment_method, delivery_days,
  weather_condition, packaging_type, shipping_distance_km, farmer_experience_years
"""

import os
import warnings
import joblib
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AI_BUNDLE_DIR = os.path.join(BASE_DIR, 'ai_model', 'v2', 'v2_agrichain_ai_bundle')

# Module-level singletons — loaded once at startup
_RISK_MODEL = None
_COMPLAINT_MODEL = None
_ENCODERS = None
_LOAD_ERROR = None  # Stores error string if models fail to load

# ── Feature column order must exactly match training ──────────────────────────
RISK_FEATURES = [
    'product_name', 'farmer_location', 'buyer_location', 'weather_condition',
    'packaging_type', 'is_organic', 'farmer_experience_years', 'unit_price',
    'quantity', 'discount_applied', 'total_price', 'payment_method',
    'shipping_distance_km',
]

COMPLAINT_FEATURES = [
    'product_name', 'total_price', 'payment_method', 'delivery_days',
    'weather_condition', 'packaging_type', 'shipping_distance_km',
    'farmer_experience_years',
]

# Defaults used when the live system doesn't have certain training-only features
_DEFAULTS = {
    'weather_condition': 'Sunny',
    'packaging_type': 'Standard',
    'is_organic': 0,
    'farmer_experience_years': 5,
    'discount_applied': 0.0,
    'shipping_distance_km': 300.0,  # median-ish value from dataset
    'delivery_days': 3,
}


# ── Model loading ─────────────────────────────────────────────────────────────

def load_models():
    """Load models once into module-level singletons. Thread-safe for reads."""
    global _RISK_MODEL, _COMPLAINT_MODEL, _ENCODERS, _LOAD_ERROR
    if _RISK_MODEL is not None:
        return True  # Already loaded

    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')  # Suppress sklearn version mismatch warning
            _RISK_MODEL = joblib.load(os.path.join(AI_BUNDLE_DIR, 'agrichain_risk_model.pkl'))
            _COMPLAINT_MODEL = joblib.load(os.path.join(AI_BUNDLE_DIR, 'agrichain_complaint_model.pkl'))
            _ENCODERS = joblib.load(os.path.join(AI_BUNDLE_DIR, 'agrichain_encoders.pkl'))
        print("[AI] AgriChain XGBoost models loaded successfully.")
        return True
    except Exception as exc:
        _LOAD_ERROR = str(exc)
        print(f"[AI] WARNING: Could not load AI models — {exc}")
        return False


def is_ready():
    load_models()
    return _RISK_MODEL is not None


# ── Encoding helpers ──────────────────────────────────────────────────────────

def _encode(key, value):
    """
    Encode a categorical value using the stored LabelEncoder.
    Returns -1 for unseen labels (handled gracefully by XGBoost).
    """
    encoder = _ENCODERS.get(key)
    if encoder is None:
        return -1
    if value in encoder.classes_:
        return int(encoder.transform([value])[0])
    return -1  # Unseen label — XGBoost tolerates this


def _build_risk_row(product_name, farmer_location, buyer_location,
                    unit_price, quantity, total_price, payment_method,
                    weather_condition=None, packaging_type=None,
                    is_organic=None, farmer_experience_years=None,
                    discount_applied=None, shipping_distance_km=None):
    """Build a single-row DataFrame matching the Risk model's feature schema."""
    row = {
        'product_name':          _encode('product_name', product_name),
        'farmer_location':       _encode('farmer_location', farmer_location or ''),
        'buyer_location':        _encode('buyer_location', buyer_location or ''),
        'weather_condition':     _encode('weather_condition', weather_condition or _DEFAULTS['weather_condition']),
        'packaging_type':        _encode('packaging_type', packaging_type or _DEFAULTS['packaging_type']),
        'is_organic':            int(is_organic) if is_organic is not None else _DEFAULTS['is_organic'],
        'farmer_experience_years': int(farmer_experience_years) if farmer_experience_years is not None else _DEFAULTS['farmer_experience_years'],
        'unit_price':            float(unit_price),
        'quantity':              float(quantity),
        'discount_applied':      float(discount_applied) if discount_applied is not None else _DEFAULTS['discount_applied'],
        'total_price':           float(total_price),
        'payment_method':        _encode('payment_method', payment_method or 'COD'),
        'shipping_distance_km':  float(shipping_distance_km) if shipping_distance_km is not None else _DEFAULTS['shipping_distance_km'],
    }
    return pd.DataFrame([row], columns=RISK_FEATURES)


def _build_complaint_row(product_name, total_price, payment_method, delivery_days,
                         weather_condition=None, packaging_type=None,
                         shipping_distance_km=None, farmer_experience_years=None):
    """Build a single-row DataFrame matching the Complaint model's feature schema."""
    row = {
        'product_name':           _encode('product_name', product_name),
        'total_price':            float(total_price),
        'payment_method':         _encode('payment_method', payment_method or 'COD'),
        'delivery_days':          int(delivery_days),
        'weather_condition':      _encode('weather_condition', weather_condition or _DEFAULTS['weather_condition']),
        'packaging_type':         _encode('packaging_type', packaging_type or _DEFAULTS['packaging_type']),
        'shipping_distance_km':   float(shipping_distance_km) if shipping_distance_km is not None else _DEFAULTS['shipping_distance_km'],
        'farmer_experience_years': int(farmer_experience_years) if farmer_experience_years is not None else _DEFAULTS['farmer_experience_years'],
    }
    return pd.DataFrame([row], columns=COMPLAINT_FEATURES)


# ── Public inference API ──────────────────────────────────────────────────────

def predict_risk(product_name, farmer_location, buyer_location,
                 unit_price, quantity, total_price, payment_method,
                 **kwargs):
    """
    Returns (risk: int, probability: float).
    risk=1 means High Risk (likely Cancelled/Rejected), risk=0 means Safe.
    Falls back to (0, 0.0) if models are unavailable.
    """
    if not is_ready():
        return 0, 0.0

    try:
        df = _build_risk_row(
            product_name, farmer_location, buyer_location,
            unit_price, quantity, total_price, payment_method, **kwargs
        )
        risk = int(_RISK_MODEL.predict(df)[0])
        prob = float(_RISK_MODEL.predict_proba(df)[0][1])
        return risk, round(prob, 3)
    except Exception as exc:
        print(f"[AI] Risk prediction error: {exc}")
        return 0, 0.0


def predict_complaint(product_name, total_price, payment_method, delivery_days, **kwargs):
    """
    Returns (will_complain: int, probability: float).
    will_complain=1 means the order is likely to generate a complaint.
    """
    if not is_ready():
        return 0, 0.0

    try:
        df = _build_complaint_row(product_name, total_price, payment_method, delivery_days, **kwargs)
        result = int(_COMPLAINT_MODEL.predict(df)[0])
        prob = float(_COMPLAINT_MODEL.predict_proba(df)[0][1])
        return result, round(prob, 3)
    except Exception as exc:
        print(f"[AI] Complaint prediction error: {exc}")
        return 0, 0.0


def simulate_price_impact(product_name, farmer_location, buyer_location,
                           current_price, quantity, payment_method, **kwargs):
    """
    Binary-search the price range [0.5*P, P] to find the highest price
    at which the Risk model returns 0 (Safe).

    Returns a dict with keys: status, message, [suggested_price, reduction_percent].
    """
    if not is_ready():
        return {"status": "unavailable", "message": "AI models are not loaded."}

    quantity = float(quantity)
    current_risk, current_prob = predict_risk(
        product_name, farmer_location, buyer_location,
        current_price, quantity, current_price * quantity, payment_method, **kwargs
    )

    if current_risk == 0:
        return {
            "status": "safe",
            "risk_probability": current_prob,
            "message": f"Price looks safe. Estimated cancellation risk: {current_prob*100:.1f}%."
        }

    # Check if even the floor price helps
    floor = current_price * 0.5
    floor_risk, _ = predict_risk(
        product_name, farmer_location, buyer_location,
        floor, quantity, floor * quantity, payment_method, **kwargs
    )
    if floor_risk == 1:
        return {
            "status": "danger",
            "risk_probability": current_prob,
            "message": f"Very high risk ({current_prob*100:.1f}%). Lowering price alone may not help — consider the buyer's location or payment method."
        }

    # Binary search for the price-safety boundary
    low, high = floor, current_price
    optimal_price = floor
    for _ in range(8):  # 8 iterations → ±0.4% precision
        mid = (low + high) / 2.0
        risk, _ = predict_risk(
            product_name, farmer_location, buyer_location,
            mid, quantity, mid * quantity, payment_method, **kwargs
        )
        if risk == 0:
            optimal_price = mid
            low = mid  # Try going higher
        else:
            high = mid  # Need to go lower

    reduction_pct = ((current_price - optimal_price) / current_price) * 100
    return {
        "status": "warning",
        "risk_probability": current_prob,
        "suggested_price": round(optimal_price, 2),
        "reduction_percent": round(reduction_pct, 1),
        "message": (
            f"High cancellation risk ({current_prob*100:.1f}%). "
            f"Lowering to ₱{optimal_price:.2f} ({reduction_pct:.1f}% drop) "
            f"is predicted to significantly reduce risk."
        )
    }
