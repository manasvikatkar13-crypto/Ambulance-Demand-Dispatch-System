# Experimental Analysis & Limitations Report: KNN Demand Classifier

**Project:** AI-Based Emergency Ambulance Demand & Dispatch System  
**Document:** Step 8 Model Evaluation & Limitation Analysis  
**Model Evaluated:** K-Nearest Neighbors Classifier ($k=5$, distance-weighted, balanced training sample)  
**Status:** Experimental Mini-Project Evaluation (Not Production-Ready)  

---

## 1. Executive Summary & Experimental Setup

This report documents the experimental evaluation and technical limitations of the K-Nearest Neighbors (KNN) classification model implemented in `src/train_demand_classifier.py`.

### Experimental Parameters
* **Full Dataset Size:** 2,805,264 hourly township records across 69 zones.
* **Target Definition:**
  * **`HIGH` Demand:** $\ge 2$ ambulance calls in a given township-hour.
  * **`NORMAL` Demand:** $< 2$ ambulance calls (0 or 1 call).
* **Chronological Split:**
  * **Training Period (Earlier 80%):** 2015-12-10 to 2019-08-25 (2,243,880 rows).
  * **Testing Period (Later 20%):** 2019-08-26 to 2020-07-29 (561,384 rows).
* **Sampling Protocol (For Computational Feasibility):**
  * **Training Sample:** Balanced sample of 20,000 `NORMAL` records and 20,000 `HIGH` records ($N = 40,000$).
  * **Testing Sample:** Naturally imbalanced sample of 5,000 records ($4,927$ `NORMAL`, $73$ `HIGH`), preserving the real-world class distribution.

---

## 2. Experimental Results Table

> **Note on Evaluation:** These metrics reflect experimental evaluation on a sampled test set ($N=5,000$). The model is not deployed in live operations.

| Metric | KNN Classifier (Balanced Training) | Majority-Class Baseline |
| :--- | :---: | :---: |
| **Overall Accuracy** | **57.32%** | 98.54% |
| **Balanced Accuracy** | **68.22%** | 50.00% |
| **HIGH-Class Recall** | **79.45%** (58 / 73 caught) | 0.00% (0 / 73 caught) |
| **HIGH-Class Precision** | **2.66%** | 0.00% |
| **HIGH-Class F1-Score** | **5.16%** | 0.00% |
| **Actual HIGH Cases in Test** | **73** | 73 |
| **Predicted as HIGH** | **2,177** | 0 |

### Confusion Matrix Breakdown (Test Sample $N=5,000$)
* **True Positives (TP):** 58 (Actual HIGH correctly predicted as HIGH)
* **False Negatives (FN):** 15 (Actual HIGH missed, predicted as NORMAL)
* **False Positives (FP):** 2,119 (Actual NORMAL falsely flagged as HIGH)
* **True Negatives (TN):** 2,808 (Actual NORMAL correctly predicted as NORMAL)

---

## 3. In-Depth Analysis of Model Limitations

### 1. Severe Class Imbalance in Emergency Operations
In the full Montgomery County dataset:
* **NORMAL Class:** 2,764,626 records (**98.55%**)
* **HIGH Class:** 40,638 records (**1.45%**)

In emergency medical services, high-demand surges are rare, extreme events. For almost 99% of township-hours, an area experiences only 0 or 1 call. This extreme 68:1 imbalance fundamentally challenges standard machine learning classification algorithms.

### 2. Why Accuracy Alone is Misleading (The "Accuracy Paradox")
A naive model that always predicts `NORMAL` without inspecting the weather, time, or location achieves an impressive **98.54% overall accuracy**. However, that naive model catches **0 out of 73 emergencies (0% recall)**. 

Evaluating the system on overall accuracy alone provides a dangerous illusion of competence while failing completely at its clinical objective: detecting life-threatening demand spikes.

### 3. Balanced Training: The Precision-Recall Trade-off
When trained on the natural imbalanced dataset, the 5 nearest neighbors in KNN were virtually always `NORMAL`, leading to 0% recall. 

Balancing the training sample (50% NORMAL / 50% HIGH) successfully taught the model the signature of emergency surges:
* **The Benefit:** HIGH recall jumped from **0.0% to 79.45%** (catching 58 out of 73 surges), and balanced accuracy rose to **68.22%**.
* **The Cost (False Alarms):** Because the real world is 98.5% normal, an artificially sensitive model triggers frequent false alarms. Out of 2,177 predicted HIGH events, only 58 were real surges, causing precision to drop to **2.66%**.

### 4. Why This Model is Not Ready for Autonomous Dispatch
In a real-world Emergency Medical Services (EMS) control room, a model with a 2.66% precision would cause **severe alarm fatigue**:
* Dispatchers would receive over 2,000 surge alerts when only 58 actually occurred.
* If ambulances were physically repositioned for every alert, fleet fuel, maintenance, and crew burnout would skyrocket, leaving regular coverage zones depleted.
* Therefore, this experimental KNN model cannot be used as an automated decision-maker.

### 5. Single County-Level Weather Station Limitation
All 69 townships were mapped to a single representative weather coordinate in central Montgomery County (`Lat: 40.17° N, Lng: -75.32° W`):
* **Microclimate Omission:** Localized weather events (such as flash downpours, icy river road patches in Upper Merion, or fog along the Schuylkill River) are not captured by a single central reading.
* While macro-weather (blizzards, heatwaves) is captured, hyper-local storm cells that cause traffic pileups remain invisible to the model.

### 6. Historical Weather vs. Operational Forecast Weather
* **Retrospective Testing:** This experiment used **observed historical weather** recorded after the events occurred.
* **Operational Reality:** In an actual live dispatch system, true future weather is unknown. Dispatchers must rely on **numerical weather forecast models**, which carry forecast uncertainty and error margins (e.g., predicted rain timing differing by 2 hours).

### 7. The Need for Additional Modeling & Threshold Tuning
KNN is a non-parametric instance-based learner with inherent limitations in high-dimensional tabular spaces:
* **Distance Sensitivity:** Euclidean distance degrades as one-hot encoded features increase (curse of dimensionality).
* **Future Model Exploration:** Advanced ensemble architectures (e.g., Gradient Boosted Trees / XGBoost / LightGBM) or cost-sensitive neural networks should be evaluated.
* **Decision Threshold Tuning:** Rather than hardcoded binary voting, models should output calibrated probability estimates, allowing dispatch leadership to adjust the risk threshold according to available fleet capacity.

### 8. AI as Decision Support, Never an Autonomous Replacement
In life-critical emergency infrastructure:
* An AI model must function as **Decision Support System (DSS)**—surfacing visual risk indicators, hotspot heatmaps, and staffing recommendations.
* Experienced emergency dispatchers possess qualitative domain context (e.g., active highway construction, major sports events, road closures, hospital diversions) that tabular AI features cannot capture.
* **Final ambulance dispatch authority must always remain with human dispatch professionals.**

---

## 4. Proposed Future Improvements

1. **Cost-Sensitive Learning:** Assign a higher penalty matrix ($\text{Cost}_{\text{FN}} \gg \text{Cost}_{\text{FP}}$) rather than simple data resampling.
2. **Probability Calibration:** Implement Platt Scaling or Isotonic Regression on ensemble tree models to output reliable posterior surge probabilities $P(\text{HIGH} | X)$.
3. **Spatial Clustering:** Group adjacent small townships into regional EMS response sectors to reduce extreme sparsity.
4. **Integration with Poisson Regression:** Combine classification alerts with continuous expected rate predictions ($\lambda$) from Step 7 for hybrid dispatch planning.

---
*Report compiled for the AI-Based Emergency Ambulance Demand & Dispatch System Mini-Project (College Evaluation & Viva Reference).*
