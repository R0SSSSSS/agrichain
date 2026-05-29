# AgriChain AI Model Training - Kaggle Notebook Guide

You now have a **50,000-row** dataset (`dataset/realistic_agrichain_data.csv`) that I generated. I increased the size from 2,000 to 50,000 because Machine Learning models become **exponentially smarter** with more data. Even at 50,000 rows, this dataset is extremely light (less than 5MB) and will easily run on a Kaggle notebook using less than 1GB of RAM.

Here is the exact code you can paste into your **Kaggle Notebook cells** to train a highly accurate, lightweight Random Forest AI.

---

### Cell 1: Import Libraries and Load Data
First, upload your `realistic_agrichain_data.csv` to Kaggle, then run this block to load and prepare the data.

```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score

# 1. Load the dataset
# Make sure the path matches where Kaggle uploaded your file
df = pd.read_csv('/kaggle/input/agrichain-dataset/realistic_agrichain_data.csv')

print(f"Dataset loaded successfully with {len(df)} rows!")
df.head()
```

---

### Cell 2: Preprocess the Data (The "Brain" Preparation)
AI only understands numbers. We need to convert text (like "Mango" or "Manila") into numerical codes using a LabelEncoder.

```python
# 2. Preprocess Data
# We create a dictionary to save our encoders so we can reuse them later in your web app
encoders = {}
categorical_cols = ['product_name', 'farmer_location', 'buyer_location', 'payment_method']

df_encoded = df.copy()

for col in categorical_cols:
    le = LabelEncoder()
    df_encoded[col] = le.fit_transform(df[col])
    encoders[col] = le

# Convert target variables (if needed)
# For risk prediction, let's group 'Cancelled' and 'Rejected' into a single 'Failed' class (1), and 'Approved' as (0)
df_encoded['is_risk'] = df['order_status'].apply(lambda x: 0 if x == 'Approved' else 1)

print("Data successfully converted to numbers!")
```

---

### Cell 3: Train Model 1 - Fraud & Cancellation Risk AI
This model will learn to spot dangerous orders before they are processed.

```python
# Define Features (What the AI looks at)
X_risk = df_encoded[['product_name', 'farmer_location', 'buyer_location', 'unit_price', 'quantity', 'total_price', 'payment_method']]
# Define Target (What the AI predicts)
y_risk = df_encoded['is_risk']

# Split into 80% Training Data, 20% Testing Data
X_train, X_test, y_train, y_test = train_test_split(X_risk, y_risk, test_size=0.2, random_state=42)

# Build the AI Model
risk_model = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)

print("Training Risk AI...")
risk_model.fit(X_train, y_train)

# Test the accuracy
y_pred = risk_model.predict(X_test)
print("\n--- RISK MODEL ACCURACY ---")
print(f"Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%")
print(classification_report(y_test, y_pred))
```

---

### Cell 4: Train Model 2 - Complaint Prediction AI
This model tells the Admin which orders are likely to result in a customer complaint.

```python
# Define Features
X_complaint = df_encoded[['product_name', 'total_price', 'payment_method', 'delivery_days', 'is_risk']]
# Define Target
y_complaint = df_encoded['has_complaint']

# Split
X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(X_complaint, y_complaint, test_size=0.2, random_state=42)

# Build the Model
complaint_model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, class_weight='balanced', n_jobs=-1)

print("Training Complaint AI...")
complaint_model.fit(X_train_c, y_train_c)

# Test the accuracy
y_pred_c = complaint_model.predict(X_test_c)
print("\n--- COMPLAINT MODEL ACCURACY ---")
print(f"Accuracy: {accuracy_score(y_test_c, y_pred_c) * 100:.2f}%")
print(classification_report(y_test_c, y_pred_c))
```

---

### Cell 5: Exporting the Model to Root Directory
Save the trained models and encoders right to the root Kaggle directory so they can be easily downloaded to your Flask app.

```python
import joblib

# Save the trained models in the root directory
joblib.dump(risk_model, 'agrichain_risk_model.pkl')
joblib.dump(complaint_model, 'agrichain_complaint_model.pkl')
joblib.dump(encoders, 'agrichain_encoders.pkl')

print("Models successfully saved to root directory!")
```

---

### Cell 6: Generate AI Evaluation Images (Heatmaps & Charts)
*Note: Random Forest Models don't have "Loss Curves" per epoch like Deep Learning Neural Networks do. Instead, we use Confusion Matrices and Feature Importance charts which are much better for evaluating tabular data!*

```python
import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix

# Create the eval folder
os.makedirs('eval', exist_ok=True)

# 1. Risk Model Confusion Matrix Heatmap
plt.figure(figsize=(6,5))
cm_risk = confusion_matrix(y_test, y_pred)
sns.heatmap(cm_risk, annot=True, fmt='d', cmap='Reds')
plt.title('Risk Model - Confusion Matrix Heatmap')
plt.ylabel('Actual Actual Risk (0=Safe, 1=Risk)')
plt.xlabel('AI Predicted Risk')
plt.tight_layout()
plt.savefig('eval/risk_confusion_matrix.png', dpi=300)
plt.close()

# 2. Complaint Model Confusion Matrix Heatmap
plt.figure(figsize=(6,5))
cm_complaint = confusion_matrix(y_test_c, y_pred_c)
sns.heatmap(cm_complaint, annot=True, fmt='d', cmap='Blues')
plt.title('Complaint Model - Confusion Matrix Heatmap')
plt.ylabel('Actual Complaint (0=None, 1=Complaint)')
plt.xlabel('AI Predicted Complaint')
plt.tight_layout()
plt.savefig('eval/complaint_confusion_matrix.png', dpi=300)
plt.close()

# 3. Feature Importance (What the AI thinks is most important!)
plt.figure(figsize=(8,5))
importances = risk_model.feature_importances_
sns.barplot(x=importances, y=X_risk.columns, palette='viridis')
plt.title('Risk Model - Feature Importance')
plt.xlabel('Importance Score')
plt.tight_layout()
plt.savefig('eval/risk_feature_importance.png', dpi=300)
plt.close()

print("Evaluation images successfully generated and saved to the 'eval' folder!")
```

---

### Cell 7: Auto-Download Script to Local Laptop
*Note: Because Kaggle runs on a cloud server, it cannot directly write to a folder like `C:\` on your laptop for security reasons. However, this script will bundle all your models and images into one ZIP file and force your browser to **automatically download it** as soon as you run the cell!*

```python
import os
import shutil
import base64
from IPython.display import HTML, display

# 1. Put everything into a single folder to bundle it
os.makedirs('agrichain_ai_bundle', exist_ok=True)

# Copy the models
shutil.copy('agrichain_risk_model.pkl', 'agrichain_ai_bundle/')
shutil.copy('agrichain_complaint_model.pkl', 'agrichain_ai_bundle/')
shutil.copy('agrichain_encoders.pkl', 'agrichain_ai_bundle/')

# Copy the images
if os.path.exists('eval'):
    shutil.copytree('eval', 'agrichain_ai_bundle/eval', dirs_exist_ok=True)

# 2. Zip the entire bundle
shutil.make_archive('agrichain_ai_bundle', 'zip', 'agrichain_ai_bundle')

# 3. Force Auto-Download using Javascript!
def auto_download(filename):
    with open(filename, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    html = f'''
    <a download="{filename}" href="data:application/zip;base64,{b64}" id="autodownload" style="display:none">Download</a>
    <script>
    document.getElementById("autodownload").click();
    </script>
    '''
    return HTML(html)

print("✅ Bundling complete! Your browser should automatically start downloading 'agrichain_ai_bundle.zip' now...")
print("Once downloaded, simply extract it to your chosen directory on your laptop!")
display(auto_download('agrichain_ai_bundle.zip'))
```
