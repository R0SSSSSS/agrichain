def _to_number(value, default=0):
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def _stock_status(quantity):
    quantity = _to_number(quantity)

    if quantity <= 0:
        return "Out of Stock"
    if quantity <= 5:
        return "Low Stock"
    if quantity <= 20:
        return "Stable Stock"
    return "Good Stock"


def _suggest_action(demand, quantity, order_count):
    quantity = _to_number(quantity)

    if demand not in ("High Demand", "Low Demand"):
        return "Collect more sales data"
    if quantity <= 0:
        return "Restock product"
    if demand == "High Demand" and quantity <= 5:
        return "Restock soon"
    if demand == "High Demand":
        return "Maintain supply"
    if order_count == 0:
        return "Promote product"
    if demand == "Low Demand":
        return "Review price"
    return "Monitor product"


def _format_quantity(value):
    value = float(_to_number(value))
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _price_detail(price_info, unit):
    status = price_info.get("status", "No comparison yet")
    avg_price = _to_number(price_info.get("avg_price"))
    difference = _to_number(price_info.get("difference"))

    if status == "No comparison yet" or avg_price <= 0:
        return "Market comparison will improve after more farmers list similar products."

    direction = "above" if difference > 0 else "below"
    return (
        f"Listed {abs(difference):.1f}% {direction} the market average "
        f"of PHP {avg_price:.2f} per {unit}."
    )


def _advice_for_product(product, insight, price_info, demand):
    unit = product.unit or "unit"
    stock_status = insight.get("stock_status", "Good Stock")
    suggested_action = insight.get("suggested_action", "Monitor product")
    units_sold = _to_number(insight.get("units_sold"))
    order_count = int(_to_number(insight.get("orders")))
    price_status = price_info.get("status", "No comparison yet")
    price_suggestion = price_info.get("suggestion", "Collect more market data")
    price_detail = _price_detail(price_info, unit)

    evidence = [
        demand,
        f"{_format_quantity(units_sold)} {unit} sold",
        f"{order_count} order{'s' if order_count != 1 else ''}",
        stock_status,
        price_status
    ]

    if stock_status == "Out of Stock":
        return {
            "score": 100,
            "tone": "danger",
            "product": product,
            "title": "Restock before accepting more demand",
            "detail": (
                f"{product.name} has no available stock. Demand is currently "
                f"{demand.lower()}, so buyers may move to another listing."
            ),
            "next_step": "Update the product quantity after harvest or temporarily pause promotion.",
            "impact": "Prevents missed sales and buyer disappointment.",
            "evidence": evidence
        }

    if demand == "High Demand" and stock_status == "Low Stock":
        return {
            "score": 95,
            "tone": "danger",
            "product": product,
            "title": "Prioritize restocking this product",
            "detail": (
                f"{product.name} is moving well but stock is low. The system "
                "flags this as a high-risk point for lost sales."
            ),
            "next_step": "Prepare more supply, then update the listing quantity.",
            "impact": "Keeps a high-demand item available while buyers are active.",
            "evidence": evidence
        }

    if price_status == "Above Market":
        return {
            "score": 82,
            "tone": "warning",
            "product": product,
            "title": "Review price competitiveness",
            "detail": price_detail,
            "next_step": "Compare nearby listings and consider a smaller price adjustment.",
            "impact": "Can improve buyer conversion when similar products are cheaper.",
            "evidence": evidence
        }

    if price_status == "Below Market" and demand == "High Demand":
        return {
            "score": 78,
            "tone": "opportunity",
            "product": product,
            "title": "Consider a careful price increase",
            "detail": price_detail,
            "next_step": "Raise the price gradually and watch if orders stay active.",
            "impact": "May increase revenue without hurting demand.",
            "evidence": evidence
        }

    if suggested_action == "Promote product":
        return {
            "score": 70,
            "tone": "warning",
            "product": product,
            "title": "Improve listing visibility",
            "detail": (
                f"{product.name} has not converted into enough orders yet. "
                "The listing may need clearer value or better timing."
            ),
            "next_step": "Refresh the photo, description, or offer a small bundle.",
            "impact": "Helps buyers understand why the product is worth choosing.",
            "evidence": evidence
        }

    if demand == "High Demand":
        return {
            "score": 62,
            "tone": "success",
            "product": product,
            "title": "Protect supply for an active product",
            "detail": (
                f"{product.name} is showing high demand and has enough stock "
                "for now."
            ),
            "next_step": "Maintain supply and monitor new orders before changing price.",
            "impact": "Supports steady sales without unnecessary changes.",
            "evidence": evidence
        }

    return {
        "score": 40,
        "tone": "neutral",
        "product": product,
        "title": "Keep collecting sales signals",
        "detail": (
            f"{product.name} needs more transaction activity before the AI "
            "can give a stronger direction."
        ),
        "next_step": "Keep the listing accurate and watch demand after the next orders.",
        "impact": "Builds better data for future demand predictions.",
        "evidence": evidence
    }


def build_product_insights(products, orders, demand_predictions):
    insights = {}

    for product in products:
        product_orders = [order for order in orders if order.product_id == product.id]
        approved_orders = [
            order for order in product_orders
            if (order.status or "").lower() == "approved"
        ]

        units_sold = sum(_to_number(order.quantity) for order in approved_orders)
        revenue = sum(_to_number(order.total_price) for order in approved_orders)
        demand = demand_predictions.get(product.id, "Not enough data")

        insights[product.id] = {
            "orders": len(product_orders),
            "units_sold": units_sold,
            "revenue": revenue,
            "stock_status": _stock_status(product.quantity),
            "suggested_action": _suggest_action(
                demand,
                product.quantity,
                len(product_orders)
            )
        }

    return insights


def build_farmer_summary(product_insights):
    insights = list(product_insights.values())

    return {
        "low_stock_count": sum(
            1 for insight in insights
            if insight["stock_status"] in ("Low Stock", "Out of Stock")
        ),
        "total_units_sold": sum(insight["units_sold"] for insight in insights),
        "total_product_revenue": sum(insight["revenue"] for insight in insights),
        "needs_action_count": sum(
            1 for insight in insights
            if insight["suggested_action"] not in ("Maintain supply", "Monitor product")
        )
    }


def build_farmer_ai_advice(products, product_insights, price_insights, demand_predictions):
    if not products:
        return {
            "signal_label": "No product signals yet",
            "signal_detail": "Add products and sales records to generate AI-assisted guidance.",
            "priority_items": [],
            "opportunity_count": 0,
            "risk_count": 0
        }

    advice_items = []
    for product in products:
        insight = product_insights.get(product.id, {})
        price_info = price_insights.get(product.id, {})
        demand = demand_predictions.get(product.id, "Not enough data")
        advice_items.append(_advice_for_product(product, insight, price_info, demand))

    advice_items = sorted(advice_items, key=lambda item: item["score"], reverse=True)
    risk_count = sum(1 for item in advice_items if item["tone"] in ("danger", "warning"))
    opportunity_count = sum(1 for item in advice_items if item["tone"] == "opportunity")
    strong_signal_count = sum(
        1 for item in advice_items
        if "High Demand" in item.get("evidence", [])
    )

    if risk_count:
        signal_label = "Action needed"
        signal_detail = "Focus first on stock shortages and price mismatches."
    elif opportunity_count:
        signal_label = "Revenue opportunity"
        signal_detail = "Some products may support better pricing or stronger promotion."
    elif strong_signal_count:
        signal_label = "Healthy demand"
        signal_detail = "Current products are showing useful sales activity."
    else:
        signal_label = "Early signal"
        signal_detail = "The system needs more orders to make stronger recommendations."

    return {
        "signal_label": signal_label,
        "signal_detail": signal_detail,
        "priority_items": advice_items[:4],
        "opportunity_count": opportunity_count,
        "risk_count": risk_count
    }
