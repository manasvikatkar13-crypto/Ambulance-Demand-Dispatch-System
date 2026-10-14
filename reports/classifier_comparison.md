# Demand Classifier Architecture Comparison Report

**Project:** AI-Based Emergency Ambulance Demand & Dispatch System  
**Document:** Model Architecture Comparative Evaluation  
**Date Cutoff:** Train through 2019-08-25 | Test from 2019-08-26 onward  
**Test Sample Size:** 5,000 records (73 actual HIGH demand events)  

---

## 1. Executive Summary

This report compares three distinct classification models against a majority baseline for detecting high-demand ambulance hours (`demand >= 2` calls in a single zone-hour).

All models were evaluated on the **exact same chronological, naturally imbalanced test sample** ($N=5,000$, 1.46% HIGH demand).

---

## 2. Model Performance Comparison Table

| Model Architecture | Accuracy | Balanced Accuracy | HIGH Recall | HIGH Precision | HIGH F1-Score | True Positives (TP) | False Negatives (FN) | False Positives (FP) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Majority-Class Baseline** | 98.54% | 50.00% | 0.00% | 0.00% | 0.00% | 0 | 73 | 0 |
| **KNN (k=5, Distance-Weighted)** | 57.32% | 68.22% | 79.45% | 2.66% | 5.16% | 58 | 15 | 2119 |
| **Random Forest (Class-Weighted)** | 90.14% | 77.45% | 64.38% | 9.14% | 16.01% | 47 | 26 | 467 |
| **HistGradientBoosting (Class-Weighted)** | 76.68% | 80.07% | 83.56% | 5.02% | 9.47% | 61 | 12 | 1154 |

---

## 3. Analysis of the Precision-Recall Trade-off

### 1. The Majority-Class Baseline Trap
* **Baseline Accuracy:** 98.54% (looks deceptively high).
* **The Failure:** It caught **0 out of 73 emergencies (0% recall)**. In an emergency dispatch system, this model is completely useless.

### 2. KNN vs. Random Forest vs. HistGradientBoosting
1. **K-Nearest Neighbors (KNN with Balanced Training):**
   * **Strengths:** High recall (79.45%, catching 58 of 73 surges).
   * **Weaknesses:** Flooded with **2,119 false positives** (only 2.66% precision). Distance in high-dimensional one-hot encoded spaces causes boundary confusion.
2. **Random Forest (Class-Weighted) — Top Candidate Model:**
   * **Strengths:** Achieves the **highest F1-Score (16.01%)**, cuts false alarms by **over 77%** (from 2,119 down to 467), and retains an overall accuracy of **90.14%** with solid recall (64.38%, 47 of 73 surges caught).
   * **Selection Rationale:** Best practical balance between emergency detection and dispatch alarm fatigue.
3. **HistGradientBoosting (Class-Weighted):**
   * **Strengths:** Achieves the **highest Balanced Accuracy (80.07%)** and **highest Recall (83.56%)**, missing only 12 surges.
   * **Weaknesses:** Higher false positive count (1,154) than Random Forest.

---

## 4. Candidate Model Selection & Limitations

* **Selected Candidate:** `Random Forest (Class-Weighted)`
* **Saved Artifact:** `models/demand_classifier_candidate.joblib`
* **Explicit Selection Criterion:** Maximizing F1-score and minimizing dispatch false alarm fatigue while preserving strong minority surge recall.
* **Important Operational Limitation:**
  * Even with Random Forest, precision is 9.14% (meaning roughly 1 in 11 alerts is an actual surge).
  * In live emergency healthcare operations, this model must serve as a **Decision Support Advisory**, alerting human supervisors to stage reserve vehicles, rather than triggering autonomous vehicle relocations.

---
*Report compiled for AI-Based Emergency Ambulance Demand & Dispatch System (Mini-Project Evaluation).*
