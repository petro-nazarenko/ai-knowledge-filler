---
title: "Feature Engineering Best Practices for ML Pipelines"
type: reference
domain: machine-learning
level: intermediate
status: active
version: v1.0
tags: [feature-engineering, machine-learning, ml-pipeline, data-preprocessing, mlops]
related:
  - "[[ML_Model_Deployment_Patterns]]"
  - "[[ETL_Pipeline_Design_for_Data_Warehousing]]"
  - "[[Data_Modeling_Patterns_Analytical_Databases]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Reference for feature engineering best practices in machine learning pipelines — covering transformation types, pipelines, feature stores, and avoiding common pitfalls.

## Feature Types and Transformations

### Numerical Features

```python
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler

# Standard scaling (mean=0, std=1) — for neural networks, linear models
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X[["age", "income"]])

# Min-max scaling (0–1) — for algorithms sensitive to magnitude
minmax = MinMaxScaler()

# Robust scaling (uses median/IQR) — for data with outliers
robust = RobustScaler()
```

### Categorical Features

```python
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder

# One-hot encoding — nominal categories (no order)
ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
ohe.fit_transform(df[["country", "payment_method"]])

# Ordinal encoding — ordered categories
oe = OrdinalEncoder(categories=[["low", "medium", "high"]])
oe.fit_transform(df[["risk_level"]])

# Target encoding — high-cardinality categories
# Replace category with mean of target variable
```

### Temporal Features

```python
def extract_temporal_features(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    dt = pd.to_datetime(df[date_col])
    df["hour"] = dt.dt.hour
    df["day_of_week"] = dt.dt.dayofweek
    df["month"] = dt.dt.month
    df["is_weekend"] = dt.dt.dayofweek >= 5
    df["days_since_epoch"] = (dt - pd.Timestamp("2020-01-01")).dt.days
    return df
```

### Interaction Features

```python
# Polynomial features
from sklearn.preprocessing import PolynomialFeatures

poly = PolynomialFeatures(degree=2, interaction_only=True)
X_interactions = poly.fit_transform(X[["age", "income", "tenure"]])

# Manual interactions
df["age_x_income"] = df["age"] * df["income"]
df["income_per_year_tenure"] = df["income"] / (df["tenure"] + 1)
```

## Sklearn Pipeline

Package transformations into reproducible pipelines:

```python
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer

numeric_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
])

categorical_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
    ("ohe", OneHotEncoder(handle_unknown="ignore")),
])

preprocessor = ColumnTransformer([
    ("num", numeric_transformer, NUMERIC_COLS),
    ("cat", categorical_transformer, CATEGORICAL_COLS),
])

full_pipeline = Pipeline([
    ("preprocessor", preprocessor),
    ("classifier", RandomForestClassifier(n_estimators=100)),
])

# Fit once, apply identically to train/test/production
full_pipeline.fit(X_train, y_train)
```

## Feature Store

Centralize feature computation and serving:

```
Offline Store (training):  Feature computation → Parquet/Delta → Training
Online Store (serving):    Latest features → Redis/DynamoDB → Inference
```

Tools: Feast, Tecton, Hopsworks, AWS SageMaker Feature Store

## Common Pitfalls

### Data Leakage
Fitting scaler on full dataset (including test) leaks future information:

```python
# WRONG — scaler sees test data
scaler.fit(X_all)
X_train_scaled = scaler.transform(X_train)

# CORRECT — fit only on train
scaler.fit(X_train)
X_train_scaled = scaler.transform(X_train)
X_test_scaled = scaler.transform(X_test)
```

### Train-Serve Skew
Different transformations applied at training vs serving time. Solution: serialize the fitted pipeline and use same artifact in production.

```python
import joblib
joblib.dump(full_pipeline, "pipeline.pkl")
# In production:
pipeline = joblib.load("pipeline.pkl")
prediction = pipeline.predict(new_data)
```

## Feature Selection

```python
from sklearn.feature_selection import SelectKBest, f_classif

# Filter method: statistical test
selector = SelectKBest(f_classif, k=20)
X_selected = selector.fit_transform(X_train, y_train)

# Wrapper method: recursive feature elimination
from sklearn.feature_selection import RFE
rfe = RFE(estimator=RandomForestClassifier(), n_features_to_select=15)
```

## Conclusion

Wrap all transformations in sklearn Pipelines to prevent leakage and ensure train/serve consistency. Use a feature store when multiple models share features. Serialize fitted pipelines as production artifacts — never recompute transformation parameters at serving time.
