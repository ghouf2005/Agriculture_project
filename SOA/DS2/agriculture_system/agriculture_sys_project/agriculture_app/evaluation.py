"""
Évaluation des performances du modèle de détection d'anomalies
"""
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
import numpy as np
import json
from pathlib import Path
from datetime import timedelta
from collections import Counter
from .models import SensorReading


def evaluate_model_performance(ground_truth_labels, predicted_labels):
    """
    Calcule les métriques de performance
    
    Args:
        ground_truth_labels: Liste des vraies étiquettes (0=normal, 1=anomalie)
        predicted_labels: Liste des prédictions (0=normal, 1=anomalie)
    
    Returns:
        dict: Métriques (precision, recall, f1, confusion_matrix)
    """
    precision = precision_score(ground_truth_labels, predicted_labels, zero_division=0)
    recall = recall_score(ground_truth_labels, predicted_labels, zero_division=0)
    f1 = f1_score(ground_truth_labels, predicted_labels, zero_division=0)
    cm = confusion_matrix(ground_truth_labels, predicted_labels)
    
    # Calcul du False Positive Rate
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
    
    return {
        'precision': round(precision, 3),
        'recall': round(recall, 3),
        'f1_score': round(f1, 3),
        'false_positive_rate': round(fpr, 3),
        'confusion_matrix': cm.tolist(),
        'true_positives': int(tp),
        'false_positives': int(fp),
        'true_negatives': int(tn),
        'false_negatives': int(fn)
    }


def _load_ground_truth_map():
    """Charge le log du simulateur et retourne un set clé (plot, sensor, minute)."""
    # Base dir = DS2 (parent of agriculture_system and simulator)
    base_dir = Path(__file__).resolve().parents[3]
    ground_truth_file = base_dir / 'simulator' / 'anomalies_ground_truth.json'
    if not ground_truth_file.exists():
        print(f"⚠️ Ground truth file not found at {ground_truth_file}. Run simulator first.")
        return None
    data = json.loads(ground_truth_file.read_text())
    return {(e['plot_id'], e['sensor_type'], e['minute']) for e in data}


def create_test_dataset_from_simulator(limit=None):
    """
    Dataset de test pour le modèle ML uniquement, basé sur le ground truth du simulateur.
    Mapping lecture→minute est approximé via l'ordre des lectures et le nombre de plots/senseurs.
    """
    gt_set = _load_ground_truth_map()
    if gt_set is None:
        return [], [], {}

    all_readings = list(SensorReading.objects.order_by('timestamp'))
    if limit:
        all_readings = all_readings[:limit]

    if not all_readings:
        print("⚠️ Aucune lecture en base pour l'évaluation")
        return [], [], {}

    # Caler le temps simulé : minute 0 = première lecture arrondie à la minute
    start_ts = all_readings[0].timestamp.replace(second=0, microsecond=0)

    ground_truth = []
    predictions = []

    from .ml_module import anomaly_detector

    for reading in all_readings:
        # Minutes écoulées depuis le début de la simulation (aligné avec ground truth)
        delta_minutes = int((reading.timestamp - start_ts).total_seconds() // 60)
        key = (reading.plot_id, reading.sensor_type, delta_minutes)
        is_gt_anomaly = key in gt_set
        ground_truth.append(1 if is_gt_anomaly else 0)

        analysis = anomaly_detector.analyze_reading(reading)
        predictions.append(1 if analysis['has_anomaly'] else 0)

    stats = {
        "total_readings": len(all_readings),
        "gt_anomalies": sum(ground_truth),
        "pred_anomalies": sum(predictions),
    }

    return ground_truth, predictions, stats


def generate_evaluation_report(limit=None):
    """
    Génère un rapport d'évaluation complet pour le modèle ML uniquement
    """
    print("📊 Génération du rapport d'évaluation...")
    
    ground_truth, predictions, stats = create_test_dataset_from_simulator(limit=limit)
    
    if len(ground_truth) == 0:
        print("⚠️ Aucune donnée disponible pour l'évaluation")
        return None
    
    metrics = evaluate_model_performance(ground_truth, predictions)
    
    print("\n" + "="*60)
    print("📈 RAPPORT D'ÉVALUATION DU MODÈLE")
    print("="*60)
    print(f"Total d'échantillons : {len(ground_truth)}")
    print(f"Anomalies réelles : {sum(ground_truth)}")
    print(f"Anomalies détectées : {sum(predictions)}")
    if stats:
        print(f"Total lectures DB : {stats['total_readings']}")
    print(f"\n--- Métriques ---")
    print(f"Précision : {metrics['precision']:.1%}")
    print(f"Rappel : {metrics['recall']:.1%}")
    print(f"F1-Score : {metrics['f1_score']:.3f}")
    print(f"Taux de faux positifs : {metrics['false_positive_rate']:.1%}")
    print(f"\n--- Matrice de confusion ---")
    print(f"Vrais positifs : {metrics['true_positives']}")
    print(f"Faux positifs : {metrics['false_positives']}")
    print(f"Vrais négatifs : {metrics['true_negatives']}")
    print(f"Faux négatifs : {metrics['false_negatives']}")
    print("="*60)
    
    return metrics