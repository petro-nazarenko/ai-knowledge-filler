---
title: "Machine Learning Model Deployment Patterns"
type: guide
domain: machine-learning
level: advanced
status: active
version: v1.0
tags: [machine-learning, deployment, mlops, inference, model-serving]
related:
  - "[[Feature_Engineering_Best_Practices]]"
  - "[[Observability_Stack_Design]]"
  - "[[Docker_Multi_Stage_Builds]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Guide to deploying machine learning models in production — covering serving patterns, infrastructure options, monitoring, and MLOps best practices.

## Prerequisites

- Trained model artifact (sklearn, PyTorch, TensorFlow, etc.)
- Understanding of REST APIs
- Basic Docker knowledge

## Deployment Patterns

### Pattern 1: REST API Inference Service

Package model as a REST endpoint:

```python
from fastapi import FastAPI
import joblib
import numpy as np

app = FastAPI()
model = joblib.load("model.pkl")
scaler = joblib.load("scaler.pkl")

@app.post("/predict")
def predict(features: dict) -> dict:
    X = np.array([[features[f] for f in FEATURE_NAMES]])
    X_scaled = scaler.transform(X)
    prediction = model.predict(X_scaled)[0]
    confidence = float(model.predict_proba(X_scaled).max())
    return {"prediction": int(prediction), "confidence": confidence}
```

### Pattern 2: Batch Inference

For non-real-time predictions:

```python
# Process large datasets offline
def batch_predict(input_path: str, output_path: str):
    df = pd.read_parquet(input_path)
    features = preprocess(df)
    predictions = model.predict(features)
    df["prediction"] = predictions
    df.to_parquet(output_path)
```

Schedule with Airflow, dbt, or cron for nightly batch scoring.

### Pattern 3: Streaming Inference

Real-time inference on event streams:

```python
from kafka import KafkaConsumer, KafkaProducer

consumer = KafkaConsumer("user-events", group_id="ml-inference")
producer = KafkaProducer(...)

for message in consumer:
    event = json.loads(message.value)
    features = extract_features(event)
    prediction = model.predict([features])[0]
    producer.send("predictions", {"user_id": event["user_id"], "score": prediction})
```

## Model Serving Infrastructure

| Option | Latency | Scale | Complexity |
|--------|---------|-------|------------|
| FastAPI + Docker | Low | Manual | Low |
| Triton Inference Server | Very low | High | Medium |
| BentoML | Low | Auto | Low |
| Seldon Core (K8s) | Low | High | High |
| AWS SageMaker | Low-medium | Managed | Low |
| Ray Serve | Low | High | Medium |

## Model Versioning and Registry

```python
# MLflow model registry
import mlflow

with mlflow.start_run():
    mlflow.log_params({"n_estimators": 100, "max_depth": 5})
    mlflow.log_metric("accuracy", 0.92)
    mlflow.sklearn.log_model(model, "model")

# Transition to production
client = mlflow.tracking.MlflowClient()
client.transition_model_version_stage(
    name="fraud-detector",
    version="3",
    stage="Production",
)
```

## Canary Deployment

Gradually shift traffic to new model version:

```python
import random

def get_model(request):
    # 10% traffic to new model
    if random.random() < 0.10:
        return model_v2
    return model_v1
```

Monitor both model versions' metrics before full rollout.

## Model Monitoring

### Data Drift Detection

```python
from alibi_detect.cd import KSDrift

detector = KSDrift(reference_data, p_val=0.05)

def check_drift(batch: np.ndarray) -> bool:
    result = detector.predict(batch)
    return result["data"]["is_drift"]
```

### Metrics to Monitor

| Metric | Signal |
|--------|--------|
| Prediction distribution | Model drift |
| Input feature distributions | Data drift |
| Model confidence scores | Concept drift |
| Business outcome (labels) | True performance |
| Latency p50/p99 | Infrastructure health |

## A/B Testing Models

```python
@app.post("/predict")
def predict(features: dict, x_experiment: str = Header(None)):
    model_version = "v2" if x_experiment == "new-model" else "v1"
    model = load_model(model_version)
    result = model.predict(features)
    log_prediction(result, model_version, experiment=x_experiment)
    return result
```

## Conclusion

Start with REST API serving for simplicity. Move to dedicated serving infrastructure (Triton, Ray Serve) when latency or scale demands it. Invest in monitoring early — model performance degrades silently without alerting. Version models in a registry and use canary deployments to minimize risk.
