from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def build_product_text(product):
    name = str(product.name or "")
    description = str(product.description or "")
    price = str(product.price or "")
    unit = str(getattr(product, "unit", "") or "")
    
    # Combine useful fields into one text
    return f"{name} {description} {price} {unit}"


def _to_float(value, default=0):
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def _word_set(value):
    return {
        word.strip().lower()
        for word in str(value or "").replace(",", " ").split()
        if len(word.strip()) > 2
    }


def _recommendation_reason(target, product, score):
    reasons = []

    target_unit = getattr(target, "unit", None) or "unit"
    product_unit = getattr(product, "unit", None) or "unit"
    if target_unit == product_unit:
        reasons.append(f"same selling unit ({product_unit})")

    target_words = _word_set(f"{target.name} {target.description}")
    product_words = _word_set(f"{product.name} {product.description}")
    overlap = sorted(target_words.intersection(product_words))
    if overlap:
        reasons.append(f"shared listing keywords: {', '.join(overlap[:3])}")

    target_price = _to_float(target.price)
    product_price = _to_float(product.price)
    if target_price and product_price:
        if product_price < target_price:
            reasons.append("lower listed price")
        elif abs(product_price - target_price) / target_price <= 0.20:
            reasons.append("similar price range")

    if getattr(target, "farmer", None) and getattr(product, "farmer", None):
        if target.farmer.location == product.farmer.location:
            reasons.append("same farmer area")

    if not reasons:
        reasons.append("closest match based on product text similarity")

    return {
        "match_percent": round(float(score) * 100),
        "reason": "; ".join(reasons[:3]),
        "buyer_tip": "Compare stock, unit, and delivery address before placing another order."
    }


def get_similar_products(products, target_product_id, top_n=5):
    """
    products: list of Product objects from database
    target_product_id: selected product id
    top_n: number of recommendations
    """

    return [
        item["product"]
        for item in get_similar_product_details(products, target_product_id, top_n)
    ]


def get_similar_product_details(products, target_product_id, top_n=5):
    if not products:
        return []

    # Prepare text data
    product_texts = [build_product_text(product) for product in products]
    product_ids = [product.id for product in products]

    # Make sure target product exists
    if target_product_id not in product_ids:
        return []

    # Convert text into TF-IDF vectors
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(product_texts)

    # Compute similarity
    similarity_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)

    # Find index of target product
    target_index = product_ids.index(target_product_id)
    target_product = products[target_index]

    # Get similarity scores for target product
    similarity_scores = list(enumerate(similarity_matrix[target_index]))

    # Sort by similarity, highest first
    similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)

    # Skip the first one because it is the same product
    similar_items = similarity_scores[1:top_n+1]

    recommendations = []
    for index, score in similar_items:
        product = products[index]
        details = _recommendation_reason(target_product, product, score)
        recommendations.append({
            "product": product,
            "score": float(score),
            **details
        })

    return recommendations
