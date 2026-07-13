# 06: ML Pipelines and Graph Analytics

> **Level:** Advanced  
> **Prerequisites:** Module 03, 05  
> **Time:** 60 minutes  
> **What You'll Learn:** How to use Machine Learning and Graph Algorithms to gain intelligent insights from your inventory.

## Introduction
**What:** Applying data science to network data.  
**Why:** Once you have a clean graph database, you can do more than just simple queries. You can find vulnerabilities, predict outages, and optimize routing.  
**Example:** Using an algorithm to identify the "most critical" router in the network—the one that, if it fails, causes the most damage.

## Core Concepts

### Concept 1: Graph Analytics (Algorithms)
- **Centrality (PageRank):** Finds the most important nodes. In a telecom network, this identifies the core backbone routers handling the most traffic.
- **Shortest Path (Dijkstra):** Finds the fastest or cheapest route between two nodes. Used to automatically route a new customer connection.
- **Community Detection:** Finds clusters of heavily connected devices.

### Concept 2: Machine Learning Pipelines
- **What:** The automated process of training an AI model.
- **Why:** To predict things. E.g., predicting hardware failure based on temperature logs and age.
- **Stack:** Scikit-learn, TensorFlow, PyTorch.

### Concept 3: Graph Neural Networks (GNNs)
- **What:** Advanced AI that natively understands graph structures.
- **Why:** Traditional ML looks at flat rows of data. GNNs look at a node *and its neighbors* to make predictions.

## Practical Example

**Building:** A conceptual ML Pipeline to predict Router Failure using Scikit-Learn.  
**Why:** Shows how ETL output connects to ML input.

```python
# STANDARD LIBRARY
import logging

# THIRD-PARTY (pip install pandas scikit-learn)
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

def train_failure_prediction_model(db_data_path: str) -> None:
    """
    Train an ML model to predict if a router will fail.
    
    What: An ML Training Pipeline.
    Why: To move from reactive to proactive maintenance.
    """
    
    # 1. LOAD DATA (Extracted from our DB)
    # Features might include: age_months, average_temp, traffic_load
    df = pd.read_csv(db_data_path)
    
    # 2. PREPARE DATA
    # 'failed_next_month' is our target variable (1=Yes, 0=No)
    X = df[['age_months', 'average_temp', 'traffic_load']] # Features
    y = df['failed_next_month']                            # Target
    
    # Split into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    
    # 3. TRAIN MODEL
    logging.info("Training Random Forest model...")
    model = RandomForestClassifier()
    model.fit(X_train, y_train)
    
    # 4. EVALUATE
    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    print(f"Model Accuracy: {accuracy * 100:.2f}%")
    
    # In production, we would save this model and load it in our API
    # import joblib; joblib.dump(model, 'router_model.pkl')

# Example usage
# train_failure_prediction_model('router_history.csv')
```

## Best Practices

**✅ DO:**
- **Use Graph Data Science Libraries** - Why: Neo4j has a GDS (Graph Data Science) plugin that runs algorithms like PageRank natively in the database, which is millions of times faster than pulling data into Python.
- **Deploy Models as APIs** - Why: Wrap your trained ML model in a FastAPI endpoint so the network monitoring tool can send it live data and get predictions.

**❌ DON'T:**
- **Train Models on Live Production DBs** - Why bad: Heavy mathematical calculations will crash the database. | Fix: Export the data or use a read-replica for training.

## Common Mistakes

**Mistake:** Data Leakage.
**Why:** Including data from the *future* in your training set. E.g., using "repair_cost" as a feature to predict "will_it_fail". You only know the repair cost *after* it fails!
**Fix:** Strictly separate historical features from future targets.

## Practice Exercises

**Exercise 1:** Choose the Algorithm
- Requirements: Which Graph Algorithm would you use to find out which router sits on the most communication paths between other routers? (Hint: It's a type of Centrality).

<details>
<summary>Solution</summary>

**Betweenness Centrality**
**Why it works:** Betweenness Centrality calculates how many shortest paths pass through a node. A router with high betweenness is a critical chokepoint in the network. If it goes down, the network fractures.
</details>

## What's Next
**Learned:** ✅ Graph Algorithms, ✅ ML Pipeline stages, ✅ Predictive maintenance concepts.  
**Next:** Module 07: Practical Project - Let's build a complete data pipeline!  
**Check:** What is the difference between shortest path and centrality?
