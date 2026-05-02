from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def build_product_text(product):
    name = str(product.name or "")
    description = str(product.description or "")
    price = str(product.price or "")
    unit = str(getattr(product, "unit", "") or "")
    
    # Combine useful fields into one text
    return f"{name} {description} {price} {unit}"

def get_similar_products(products, target_product_id, top_n=5):
    """
    products: list of Product objects from database
    target_product_id: selected product id
    top_n: number of recommendations
    """

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

    # Get similarity scores for target product
    similarity_scores = list(enumerate(similarity_matrix[target_index]))

    # Sort by similarity, highest first
    similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)

    # Skip the first one because it is the same product
    similar_items = similarity_scores[1:top_n+1]

    # Return matching Product objects
    recommended_products = [products[i] for i, score in similar_items]
    return recommended_products
