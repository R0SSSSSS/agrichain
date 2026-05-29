"""
AgriChain AI Blueprint
======================
Exposes RESTful endpoints for the AI inference service.

Endpoints:
  POST /api/v1/ai/simulate-price  — Price risk simulation (Binary Search)
  POST /api/v1/ai/check-risk      — Direct order risk check
  POST /api/v1/ai/check-complaint — Complaint likelihood check
  GET  /api/v1/ai/status          — Health check for the AI subsystem
"""
from flask import Blueprint, request, jsonify
from ai_service import simulate_price_impact, predict_risk, predict_complaint, is_ready

ai_bp = Blueprint('ai_bp', __name__, url_prefix='/api/v1/ai')


@ai_bp.route('/status', methods=['GET'])
def api_status():
    return jsonify({"ai_ready": is_ready()})


@ai_bp.route('/simulate-price', methods=['POST'])
def api_simulate_price():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON payload required"}), 400

    product_name = data.get('product_name')
    proposed_price = data.get('proposed_price')
    if not product_name or proposed_price is None:
        return jsonify({"error": "product_name and proposed_price are required"}), 400

    try:
        proposed_price = float(proposed_price)
        quantity = float(data.get('quantity', 1))
    except (TypeError, ValueError):
        return jsonify({"error": "proposed_price and quantity must be numbers"}), 400

    result = simulate_price_impact(
        product_name=product_name,
        farmer_location=data.get('farmer_location', 'Unknown'),
        buyer_location=data.get('buyer_location', 'Unknown'),
        current_price=proposed_price,
        quantity=quantity,
        payment_method=data.get('payment_method', 'COD'),
        weather_condition=data.get('weather_condition'),
        packaging_type=data.get('packaging_type'),
        is_organic=data.get('is_organic', 0),
        farmer_experience_years=data.get('farmer_experience_years'),
        discount_applied=data.get('discount_applied', 0.0),
        shipping_distance_km=data.get('shipping_distance_km'),
    )
    return jsonify(result)


@ai_bp.route('/check-risk', methods=['POST'])
def api_check_risk():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON payload required"}), 400

    product_name = data.get('product_name')
    unit_price = data.get('unit_price', 0)
    quantity = data.get('quantity', 1)

    try:
        unit_price = float(unit_price)
        quantity = float(quantity)
        total_price = float(data.get('total_price', unit_price * quantity))
    except (TypeError, ValueError):
        return jsonify({"error": "Numeric fields must be numbers"}), 400

    risk, prob = predict_risk(
        product_name=product_name or '',
        farmer_location=data.get('farmer_location', 'Unknown'),
        buyer_location=data.get('buyer_location', 'Unknown'),
        unit_price=unit_price,
        quantity=quantity,
        total_price=total_price,
        payment_method=data.get('payment_method', 'COD'),
        weather_condition=data.get('weather_condition'),
        packaging_type=data.get('packaging_type'),
        is_organic=data.get('is_organic', 0),
        farmer_experience_years=data.get('farmer_experience_years'),
        discount_applied=data.get('discount_applied', 0.0),
        shipping_distance_km=data.get('shipping_distance_km'),
    )

    label = 'High Risk' if risk == 1 else 'Safe'
    return jsonify({
        "is_risk": risk,
        "risk_label": label,
        "risk_probability": prob
    })


@ai_bp.route('/check-complaint', methods=['POST'])
def api_check_complaint():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON payload required"}), 400

    try:
        total_price = float(data.get('total_price', 0))
        delivery_days = int(data.get('delivery_days', 3))
    except (TypeError, ValueError):
        return jsonify({"error": "total_price and delivery_days must be numbers"}), 400

    result, prob = predict_complaint(
        product_name=data.get('product_name', ''),
        total_price=total_price,
        payment_method=data.get('payment_method', 'COD'),
        delivery_days=delivery_days,
        weather_condition=data.get('weather_condition'),
        packaging_type=data.get('packaging_type'),
        shipping_distance_km=data.get('shipping_distance_km'),
        farmer_experience_years=data.get('farmer_experience_years'),
    )

    return jsonify({
        "will_complain": result,
        "complaint_probability": prob
    })
