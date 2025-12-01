"""
Évaluation des performances du modèle de détection d'anomalies
"""
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
import numpy as np
import json
from pathlib import Path
from datetime import timedelta
from .models import SensorReading, AnomalyEvent


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


def create_test_dataset_from_simulator():
    """
    Crée un dataset de test basé sur les données du simulateur
    Utilise le fichier ground truth généré par anomaly_injector
    
    Returns:
        tuple: (ground_truth, predictions)
    """
    # Charger le ground truth depuis le fichier JSON
    ground_truth_file = Path('simulator/anomalies_ground_truth.json')
    
    if not ground_truth_file.exists():
        print("⚠️ Ground truth file not found. Run simulator first.")
        return [], []
    
    with open(ground_truth_file, 'r') as f:
        ground_truth_data = json.load(f)
    
    # Récupérer toutes les lectures
    all_readings = SensorReading.objects.order_by('timestamp')
    
    ground_truth = []
    predictions = []
    
    # Créer un dictionnaire pour recherche rapide
    gt_dict = {}
    for entry in ground_truth_data:
        key = f"{entry['plot_id']}_{entry['sensor_type']}_{entry['minute']}"
        gt_dict[key] = True
    
    simulated_minute = 0
    for reading in all_readings:
        # Ground truth : Vérifier dans le log
        key = f"{reading.plot_id}_{reading.sensor_type}_{simulated_minute}"
        is_gt_anomaly = gt_dict.get(key, False)
        ground_truth.append(1 if is_gt_anomaly else 0)
        
        # Prédiction : Analyser la lecture
        from .ml_module import anomaly_detector
        analysis = anomaly_detector.analyze_reading(reading)
        predictions.append(1 if analysis['has_anomaly'] else 0)
        
        simulated_minute += 1  # Approximation simple
    
    return ground_truth, predictions


def generate_evaluation_report():
    """
    Génère un rapport d'évaluation complet
    """
    print("📊 Génération du rapport d'évaluation...")
    
    ground_truth, predictions = create_test_dataset_from_simulator()
    
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