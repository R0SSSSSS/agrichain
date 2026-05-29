# AgriChain AI — Use Case Summary

## Overview

AgriChain integrates two custom-trained **XGBoost machine learning models** loaded from the
`ai_model/v2/v2_agrichain_ai_bundle/` directory. These models were trained on a synthetic
dataset of **100,000 orders** that mirrors real agricultural supply-chain dynamics —
including location pairs, weather conditions, pricing, packaging types, and payment methods.

The AI system is designed to give **farmers real-time, data-driven guidance** on pricing
and order quality, and to help the platform proactively flag risky transactions before
they result in cancellations or complaints.

---

## Model 1 — Order Risk / Cancellation Predictor

| Property | Detail |
|---|---|
| **File** | `agrichain_risk_model.pkl` |
| **Type** | XGBoost Classifier |
| **Training accuracy** | ~70% |
| **Output** | `risk = 0` (Safe) or `risk = 1` (High Risk) + probability |

### Features used (13 total)

| Feature | Description |
|---|---|
| `product_name` | The crop being sold |
| `farmer_location` | Where the farmer is based |
| `buyer_location` | Where the buyer is located |
| `weather_condition` | Sunny, Rainy, etc. |
| `packaging_type` | Standard, Bulk Sacks, etc. |
| `is_organic` | 0 or 1 |
| `farmer_experience_years` | Years of experience |
| `unit_price` | Price per unit in ₱ |
| `quantity` | Units ordered |
| `discount_applied` | Discount amount |
| `total_price` | Total order value in ₱ |
| `payment_method` | COD, GCash, etc. |
| `shipping_distance_km` | Distance between farmer and buyer |

### Where it appears in the UI

#### 1. Farmer Orders Page (`/farmer-orders`)
When a farmer views their incoming orders, every **Pending** order gets an **AI Risk badge** loaded asynchronously:

```
✓ Safe          ← green badge — model predicts low cancellation risk
⚠ High Risk 77% ← red badge — model predicts order likely to be cancelled
```

The badge shows the raw probability percentage so the farmer can decide whether to
approve or discuss the order with the buyer first.

**Data flow:**
```
Page load → JS reads data-attributes from each <tr> (product, price, locations, payment)
          → POST /api/v1/ai/check-risk
          → badge updates from "checking…" → Safe or High Risk XX%
```

#### 2. Add Product Page (`/add-product`) — Price Simulation
When a farmer is listing a product and types in a price, the AI runs a **binary-search
price simulation** 850ms after they stop typing. It tests whether the entered price is
likely to result in cancelled orders:

```
Price ₱50  → ✅ Safe — cancellation risk: 35%
Price ₱350 → ⚠️ Warning — try ₱218.40 (38% lower) to reduce risk
Price ₱999 → 🚨 Danger — price is too extreme; location/payment concerns outweigh price
```

If the model returns a "Warning" status, it shows a **💡 Suggested ceiling price** with
an **Apply** button that auto-fills the form with the safer price.

**Binary search algorithm:**
```
1. Run risk model at current_price → if SAFE, done
2. Check floor_price = 0.5 × current_price → if still DANGEROUS, return danger
3. Binary search in [floor, current] for 8 iterations (±0.4% precision)
4. Return highest price where model predicts Safe
```

---

## Model 2 — Complaint Predictor

| Property | Detail |
|---|---|
| **File** | `agrichain_complaint_model.pkl` |
| **Type** | XGBoost Classifier |
| **Training accuracy** | ~75% accuracy / F1: 0.067 (class-imbalance issue) |
| **Output** | `will_complain = 0 or 1` + probability |

> **Note:** Complaints are rare events in the dataset (<5% of orders). The model has
> high overall accuracy but low F1 because most orders never generate complaints.
> Treat complaint predictions as **advisory signals**, not definitive verdicts.

### Features used (8 total)

| Feature | Description |
|---|---|
| `product_name` | The crop |
| `total_price` | Full order value |
| `payment_method` | COD, GCash, etc. |
| `delivery_days` | Estimated delivery time |
| `weather_condition` | Condition during fulfillment |
| `packaging_type` | Packaging method |
| `shipping_distance_km` | Distance between farmer and buyer |
| `farmer_experience_years` | Farmer's experience level |

### Where it is used

The complaint model is exposed via the REST API at `/api/v1/ai/check-complaint` and is
available for future integration — for example, flagging high-risk deliveries to admins
before a complaint is filed, or alerting the farmer to take extra care with packaging.

---

## REST API Endpoints

All endpoints are prefixed `/api/v1/ai` and are **auth-exempt** (no login required —
pure ML inference, no database access).

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/v1/ai/status` | Health check — returns `{"ai_ready": true/false}` |
| `POST` | `/api/v1/ai/simulate-price` | Binary-search price optimizer for farmers |
| `POST` | `/api/v1/ai/check-risk` | Direct order risk score |
| `POST` | `/api/v1/ai/check-complaint` | Complaint likelihood prediction |

### Example: `/api/v1/ai/simulate-price`

**Request:**
```json
{
  "product_name": "Mango",
  "proposed_price": 350.00,
  "quantity": 20,
  "farmer_location": "Lianga",
  "buyer_location": "Madrid",
  "payment_method": "COD"
}
```

**Response (Warning):**
```json
{
  "status": "warning",
  "risk_probability": 0.71,
  "suggested_price": 218.40,
  "reduction_percent": 37.6,
  "message": "High cancellation risk (71.0%). Lowering to ₱218.40 (37.6% drop) is predicted to significantly reduce risk."
}
```

### Example: `/api/v1/ai/check-risk`

**Request:**
```json
{
  "product_name": "Eggplant",
  "unit_price": 69.84,
  "quantity": 464,
  "farmer_location": "Libjo",
  "buyer_location": "Madrid",
  "payment_method": "COD"
}
```

**Response:**
```json
{
  "is_risk": 1,
  "risk_label": "High Risk",
  "risk_probability": 0.769
}
```

---

## Architecture

```
Flask App (app.py)
│
├── ai_routes.py  ←  Blueprint registered at /api/v1/ai
│     └── calls ai_service.py functions
│
└── ai_service.py
      ├── load_models()        → loads .pkl files once at startup into memory
      ├── predict_risk()       → returns (risk, probability)
      ├── predict_complaint()  → returns (will_complain, probability)
      └── simulate_price_impact() → binary-search price optimizer

Model files (loaded once, shared across requests):
  ai_model/v2/v2_agrichain_ai_bundle/
  ├── agrichain_risk_model.pkl
  ├── agrichain_risk_model_metadata.json
  ├── agrichain_complaint_model.pkl
  ├── agrichain_complaint_model_metadata.json
  └── agrichain_encoders.pkl   ← LabelEncoders for all categorical features
```

**Performance:**
- Models load in ~2 seconds on first request
- Subsequent inferences: <15ms per prediction
- Binary-search price simulation (8 iterations): <120ms

---

## Training Summary

| Model | Rows | Algorithm | Train Acc | Test Acc |
|---|---|---|---|---|
| Risk | 100,000 | XGBoost | ~73% | ~70% |
| Complaint | 100,000 | XGBoost | ~77% | ~75% |

The dataset was generated synthetically using distributions calibrated to Philippine
agricultural trade patterns — Surigao Del Sur locations, local crop varieties, COD-heavy
payment patterns, and seasonal weather cycles.

To retrain: see `dataset/kaggle_training_guide.md`.
