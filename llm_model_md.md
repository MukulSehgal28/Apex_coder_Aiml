# Shop Insight Hub — Final ML Project Context Document

## Project Overview

Shop Insight Hub is a retail analytics and business intelligence platform designed for:

* grocery stores
* kirana stores
* local retail businesses
* small and medium retail operations

The platform combines:

* transaction analytics
* customer behavior analysis
* business intelligence
* machine learning-based customer segmentation

The project is hackathon-focused and prioritizes:

* business usefulness
* understandable machine learning outputs
* realistic retail analytics
* strong visualization quality

---

# Primary Machine Learning Objective

The main ML objective is:

```plaintext id="1"
Customer Segmentation using K-Means Clustering
```

The project focuses on identifying:

* premium customers
* regular customers
* discount hunters
* low engagement customers

using retail transaction behavior.

---

# Dataset Information

## Final Dataset Name

```plaintext id="2"
final_retail_sales.csv
```

---

# Dataset Status

The dataset is now:

```plaintext id="3"
FROZEN
```

No further modifications should be made to:

* rows
* columns
* discounts
* dates
* events
* customer behavior
* transaction logic

Future development must use the dataset exactly as it exists.

---

# Dataset Structure

## Total Rows

```plaintext id="4"
2224
```

## Total Columns

```plaintext id="5"
13
```

---

# Dataset Columns

| Column Name         | Description                       |
| ------------------- | --------------------------------- |
| Transaction_ID      | Unique transaction identifier     |
| Date                | Transaction date                  |
| Customer_ID         | Customer identifier               |
| Gender              | Customer gender                   |
| Age                 | Customer age                      |
| Product_Category    | Purchased product category        |
| Quantity            | Number of products purchased      |
| Price_Per_Unit      | Product unit price                |
| Total_Amount        | Transaction total before discount |
| Discount_Percentage | Applied discount percentage       |
| Final_Paid_Amount   | Final amount after discount       |
| Payment_Method      | Payment method used               |
| Is_Event            | Indicates event-based transaction |

---

# Dataset Logic

## Transaction Structure

The dataset follows:

```plaintext id="6"
1 row = 1 transaction
```

Customers may appear multiple times.

---

# Event Logic

The dataset contains synchronized retail event periods.

Rules:

* Event transactions contain discounts.
* Non-event transactions contain:

```plaintext id="7"
Discount_Percentage = 0
```

---

# Discount Rules

Maximum allowed discount:

```plaintext id="8"
25%
```

Discount ranges:

* No Event → 0%
* Small Promotions → 5–10%
* Medium Promotions → 10–18%
* Major Promotions → 18–25%

---

# Retail Behavior Simulation

The dataset intentionally simulates:

* premium customers
* regular customers
* discount hunters
* low engagement customers

using:

* spending behavior
* purchase frequency
* discount dependency
* event participation

---

# Machine Learning Strategy

## ML Algorithm

Primary ML model:

```plaintext id="9"
K-Means Clustering
```

---

# ML Objective

Perform:

```plaintext id="10"
Customer Segmentation
```

based on customer purchasing behavior.

---

# Clustering Philosophy

The ML pipeline should prioritize:

* interpretability
* business usefulness
* meaningful segmentation
* understandable outputs
* strong visualization

over mathematical complexity.

---

# Data Aggregation Strategy

The original transaction dataset should NOT be clustered directly.

Instead:

```plaintext id="11"
customer-level aggregated features
```

must be created.

---

# Aggregation Logic

Use:

```python id="12"
groupby("Customer_ID")
```

to generate:

```plaintext id="13"
1 row = 1 customer
```

---

# Recommended Clustering Features

## Core Features

| Feature            | Purpose                    |
| ------------------ | -------------------------- |
| Total Spending     | Identify premium customers |
| Purchase Frequency | Identify loyal customers   |
| Avg Discount Usage | Identify discount hunters  |

---

# Optional Feature

| Feature                  | Purpose              |
| ------------------------ | -------------------- |
| Total Quantity Purchased | Basket size behavior |

---

# Recommended Final Feature Set

Preferred clustering inputs:

```plaintext id="14"
1. Total Spending
2. Purchase Frequency
3. Avg Discount Usage
```

Optional:

```plaintext id="15"
4. Total Quantity Purchased
```

---

# Recommended Customer Clusters

## Cluster 1 — Premium Customers

Behavior:

* high spending
* high purchase frequency
* low discount dependency

Business Strategy:

* loyalty rewards
* premium targeting

---

# Cluster 2 — Regular Customers

Behavior:

* stable medium spending
* balanced shopping behavior

Business Strategy:

* bundle recommendations
* retention campaigns

---

# Cluster 3 — Discount Hunters

Behavior:

* high discount dependency
* event-driven shopping

Business Strategy:

* targeted promotions
* controlled discount strategies

---

# Cluster 4 — Low Engagement Customers

Behavior:

* low spending
* low purchase frequency

Business Strategy:

* re-engagement campaigns
* WhatsApp offers
* coupon outreach

---

# Machine Learning Workflow

## Step 1

Load dataset:

```python id="16"
pd.read_csv()
```

---

## Step 2

Perform feature aggregation:

```python id="17"
groupby("Customer_ID")
```

---

## Step 3

Generate clustering features:

* Total Spending
* Purchase Frequency
* Avg Discount Usage

---

## Step 4

Scale features:

```python id="18"
StandardScaler()
```

---

## Step 5

Find optimal cluster count:

```python id="19"
Elbow Method
```

---

## Step 6

Apply:

```python id="20"
KMeans()
```

---

## Step 7

Assign business-friendly cluster labels:

* Premium Customers
* Regular Customers
* Discount Hunters
* Low Engagement Customers

---

# Recommended Cluster Count

Preferred:

```plaintext id="21"
K = 4
```

---

# Visualization Strategy

The project will use:

```plaintext id="22"
Kaggle Notebooks
```

for:

* model building
* experimentation
* visualization
* ML demonstrations

The project does NOT use:

```plaintext id="23"
Power BI
```

---

# Recommended Python Libraries

## Core Libraries

```python id="24"
pandas
numpy
matplotlib
scikit-learn
```

Optional:

```python id="25"
plotly
seaborn
```

---

# Recommended Visualizations

## Scatter Plot

X-axis:

```plaintext id="26"
Total Spending
```

Y-axis:

```plaintext id="27"
Purchase Frequency
```

Color:

```plaintext id="28"
Cluster
```

---

# Additional Recommended Visualizations

* customer distribution pie charts
* cluster comparison bar charts
* spending analysis charts
* discount usage analysis
* customer behavior comparisons

---

# Expected Business Insights

Examples:

* Premium customers contribute highest revenue.
* Discount hunters mainly purchase during events.
* Regular customers generate stable recurring sales.
* Low engagement customers require reactivation campaigns.

---

# Technical Stack

## Backend

* Python
* Flask
* Flask-SQLAlchemy

## Database

* PostgreSQL
* SQLite fallback

## Data Science

* Pandas
* Scikit-learn
* Matplotlib

## Frontend

* HTML
* CSS
* Bootstrap
* JavaScript

---

# Important Development Constraints

## DO NOT:

* modify the frozen dataset
* overengineer the ML pipeline
* create unnecessary features
* use unnecessary algorithms
* complicate cluster interpretation

---

# Project Philosophy

The project prioritizes:

* explainable machine learning
* understandable business insights
* retail realism
* lightweight architecture
* presentation quality
* practical business value

over enterprise-scale ML complexity.

---

# Final Project Goal

Deliver a retail analytics system capable of:

* customer segmentation
* business intelligence
* customer behavior visualization
* actionable business recommendations

using:

```plaintext id="29"
K-Means clustering on realistic retail transaction data
```
