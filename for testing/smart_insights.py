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
