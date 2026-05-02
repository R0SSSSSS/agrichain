import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

def train_demand_model(products, orders):
    data = []

    for product in products:
        total_orders = sum(
            1 for order in orders
            if order.product_id == product.id and (order.status or "").lower() not in {"cancelled", "rejected"}
        )
        demand = "High" if total_orders >= 3 else "Low"

        data.append({
            "price": product.price or 0,
            "quantity": product.quantity or 0,
            "name": product.name or "",
            "location": product.farmer.location if product.farmer else "",
            "demand": demand
        })

    if len(data) < 3:
        return None, None, None

    df = pd.DataFrame(data)

    name_encoder = LabelEncoder()
    location_encoder = LabelEncoder()

    df["name"] = name_encoder.fit_transform(df["name"])
    df["location"] = location_encoder.fit_transform(df["location"])
    df["demand"] = df["demand"].map({"Low": 0, "High": 1})

    X = df[["price", "quantity", "name", "location"]]
    y = df["demand"]

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)

    return model, name_encoder, location_encoder


def predict_product_demand(product, model, name_encoder, location_encoder):
    if not model:
        return "Not enough data"

    name = product.name or ""
    location = product.farmer.location if product.farmer else ""

    if name not in name_encoder.classes_ or location not in location_encoder.classes_:
        return "Not enough similar data"

    input_data = [[
        product.price or 0,
        product.quantity or 0,
        name_encoder.transform([name])[0],
        location_encoder.transform([location])[0]
    ]]

    prediction = model.predict(input_data)[0]

    return "High Demand" if prediction == 1 else "Low Demand"
