"""
AI-Based Emergency Ambulance Demand & Dispatch System
Unit and Integration Tests for ML Model Evaluation Dashboard (Step 17)
"""

import unittest
import json
import urllib.request
import urllib.error
from fastapi import HTTPException

from api.evaluation import (
    get_model_evaluations,
    get_single_model_evaluation,
    ModelEvaluationResponse,
    ModelMetricsItem,
)
from api.main import (
    get_model_evaluation_summary,
    get_model_evaluation_detail,
)


class TestModelEvaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.live_server_available = False
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2) as res:
                if res.status == 200:
                    cls.live_server_available = True
        except Exception:
            cls.live_server_available = False

    def test_direct_evaluation_engine(self):
        """Test the underlying get_model_evaluations engine directly."""
        resp = get_model_evaluations()
        self.assertIsInstance(resp, ModelEvaluationResponse)
        self.assertEqual(len(resp.models), 4)
        self.assertEqual(resp.selected_model_id, "random_forest")
        self.assertEqual(resp.metadata.test_sample_size, 5000)
        self.assertEqual(resp.metadata.test_high_count, 73)
        self.assertEqual(resp.metadata.test_normal_count, 4927)

        # Check all models have valid confusion matrix sums
        for m in resp.models:
            cm = m.confusion_matrix
            self.assertEqual(cm.tp + cm.fn + cm.fp + cm.tn, 5000)
            self.assertEqual(cm.actual_high, 73)
            self.assertEqual(cm.actual_normal, 4927)
            self.assertGreaterEqual(m.overall_accuracy, 0.0)
            self.assertLessEqual(m.overall_accuracy, 1.0)

    def test_random_forest_candidate_metrics(self):
        """Verify the exact empirical results for selected Random Forest model."""
        rf = get_single_model_evaluation("random_forest")
        self.assertIsNotNone(rf)
        self.assertTrue(rf.is_selected_candidate)
        self.assertEqual(rf.model_id, "random_forest")

        # Exact historical numbers from reports/classifier_comparison.csv
        self.assertEqual(rf.confusion_matrix.tp, 47)
        self.assertEqual(rf.confusion_matrix.fn, 26)
        self.assertEqual(rf.confusion_matrix.fp, 467)
        self.assertEqual(rf.confusion_matrix.tn, 4460)
        self.assertAlmostEqual(rf.overall_accuracy, 0.9014, places=3)
        self.assertAlmostEqual(rf.balanced_accuracy, 0.7745, places=3)
        self.assertAlmostEqual(rf.high_recall, 0.6438, places=3)
        self.assertAlmostEqual(rf.high_precision, 0.0914, places=3)
        self.assertAlmostEqual(rf.high_f1_score, 0.1601, places=3)

    def test_majority_baseline_accuracy_paradox(self):
        """Verify that Majority Baseline has 98.54% accuracy but 0% recall and 73 missed surges."""
        base = get_single_model_evaluation("majority_baseline")
        self.assertIsNotNone(base)
        self.assertFalse(base.is_selected_candidate)
        self.assertEqual(base.confusion_matrix.tp, 0)
        self.assertEqual(base.confusion_matrix.fn, 73)
        self.assertEqual(base.confusion_matrix.fp, 0)
        self.assertEqual(base.confusion_matrix.tn, 4927)
        self.assertAlmostEqual(base.overall_accuracy, 0.9854, places=3)
        self.assertAlmostEqual(base.high_recall, 0.0, places=3)
        self.assertAlmostEqual(base.high_f1_score, 0.0, places=3)

    def test_knn_metrics(self):
        """Verify KNN high recall (79.45%) but high false alarms (2,119)."""
        knn = get_single_model_evaluation("knn")
        self.assertIsNotNone(knn)
        self.assertEqual(knn.confusion_matrix.tp, 58)
        self.assertEqual(knn.confusion_matrix.fp, 2119)
        self.assertAlmostEqual(knn.high_recall, 0.7945, places=3)
        self.assertAlmostEqual(knn.high_precision, 0.0266, places=3)

    def test_hist_gb_metrics(self):
        """Verify HistGradientBoosting high recall (83.56%) and balanced accuracy (80.07%)."""
        hgb = get_single_model_evaluation("hist_gradient_boosting")
        self.assertIsNotNone(hgb)
        self.assertEqual(hgb.confusion_matrix.tp, 61)
        self.assertEqual(hgb.confusion_matrix.fn, 12)
        self.assertEqual(hgb.confusion_matrix.fp, 1154)
        self.assertAlmostEqual(hgb.balanced_accuracy, 0.8007, places=3)

    def test_endpoint_function_summary(self):
        """Test the FastAPI endpoint function directly."""
        resp = get_model_evaluation_summary()
        self.assertEqual(len(resp.models), 4)
        self.assertEqual(resp.selected_model_id, "random_forest")
        self.assertIn("accuracy", resp.guidance.why_accuracy_is_misleading.lower())

    def test_endpoint_function_detail_and_404(self):
        """Test single model retrieval and 404 exception on unknown model."""
        item = get_model_evaluation_detail("random_forest")
        self.assertEqual(item.model_id, "random_forest")

        with self.assertRaises(HTTPException) as ctx:
            get_model_evaluation_detail("invalid_architecture_xyz")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_live_http_endpoints_if_running(self):
        """Test HTTP responses over network if FastAPI server is currently running."""
        if not self.live_server_available:
            self.skipTest("Live server not running at http://127.0.0.1:8000; skipping network tests.")

        # Test GET /evaluation/models
        req = urllib.request.Request("http://127.0.0.1:8000/evaluation/models")
        with urllib.request.urlopen(req, timeout=5) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertEqual(len(data["models"]), 4)
            self.assertEqual(data["selected_model_id"], "random_forest")

        # Test GET /evaluation/models/random_forest
        req_rf = urllib.request.Request("http://127.0.0.1:8000/evaluation/models/random_forest")
        with urllib.request.urlopen(req_rf, timeout=5) as res:
            self.assertEqual(res.status, 200)
            rf_data = json.loads(res.read().decode("utf-8"))
            self.assertEqual(rf_data["model_id"], "random_forest")
            self.assertEqual(rf_data["confusion_matrix"]["tp"], 47)

        # Test GET /evaluation/models/unknown -> 404
        req_404 = urllib.request.Request("http://127.0.0.1:8000/evaluation/models/unknown_model")
        try:
            urllib.request.urlopen(req_404, timeout=5)
            self.fail("Expected HTTPError 404 for unknown model")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)


if __name__ == "__main__":
    unittest.main()
