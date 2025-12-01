"""
Injecteur d'anomalies pour tester le système de détection
Version améliorée avec logging des ground truth
"""
import numpy as np
import json
from pathlib import Path


class AnomalyInjector:
    """
    Injecte des anomalies contrôlées dans les données capteurs
    """
    
    def __init__(self, log_file='anomalies_ground_truth.json'):
        # Définir les scénarios d'anomalies (minute_début, minute_fin, type, paramètres)
        self.anomaly_scenarios = {
            'irrigation_failure': {
                'start': 180,      # Commence à 3h de simulation
                'end': 300,        # Termine à 5h
                'type': 'moisture_drop',
                'params': {'drop_rate': 2.5, 'target_min': 30}
            },
            'heat_wave': {
                'start': 600,      # Commence à 10h
                'end': 720,        # Termine à 12h
                'type': 'temperature_spike',
                'params': {'increase': 10}
            },
            'sensor_malfunction': {
                'start': 900,      # Commence à 15h
                'end': 960,        # Termine à 16h
                'type': 'erratic_readings',
                'params': {'variance': 20}
            },
            'dry_air': {
                'start': 400,      # Commence à 6h40
                'end': 500,        # Termine à 8h20
                'type': 'humidity_drop',
                'params': {'target': 25}
            }
        }
        
        # ✨ NOUVEAU : Logger les anomalies injectées
        self.log_file = Path(log_file)
        self.ground_truth_log = []
    
    def get_active_anomalies(self, current_minute):
        """
        Retourne la liste des anomalies actives au moment donné
        """
        active = []
        
        for name, config in self.anomaly_scenarios.items():
            if config['start'] <= current_minute < config['end']:
                duration = config['end'] - config['start']
                elapsed = current_minute - config['start']
                progress = elapsed / duration if duration > 0 else 0
                
                active.append({
                    'name': name,
                    'type': config['type'],
                    'params': config['params'],
                    'progress': progress
                })
        
        return active
    
    def apply_moisture_drop(self, current_value, params, progress):
        """
        Simule une chute d'humidité du sol (panne d'irrigation)
        """
        drop_rate = params.get('drop_rate', 2.0)
        target_min = params.get('target_min', 30)
        
        # Chute rapide au début
        if progress < 0.2:
            new_value = current_value - drop_rate * 3
        # Stabilisation à un niveau bas
        else:
            new_value = max(target_min, current_value - drop_rate * 0.3)
        
        return new_value
    
    def apply_temperature_spike(self, current_value, params, progress):
        """
        Simule une vague de chaleur
        """
        increase = params.get('increase', 8)
        # Augmentation progressive
        spike = increase * min(progress * 1.5, 1.0)
        return current_value + spike
    
    def apply_erratic_readings(self, current_value, params, progress):
        """
        Simule un capteur défectueux
        """
        variance = params.get('variance', 15)
        noise = np.random.uniform(-variance, variance)
        return current_value + noise
    
    def apply_humidity_drop(self, current_value, params, progress):
        """
        Simule une baisse d'humidité de l'air
        """
        target = params.get('target', 30)
        # Descente progressive
        drop = (current_value - target) * progress * 0.15
        return current_value - drop
    
    def modify_sensor_value(self, sensor_type, value, current_minute, plot_id=None):
        """
        Applique les anomalies actives à une valeur de capteur
        
        Args:
            sensor_type: Type de capteur ('MOISTURE', 'TEMPERATURE', 'HUMIDITY')
            value: Valeur normale du capteur
            current_minute: Minute actuelle de simulation
            plot_id: ID du plot (optionnel, pour logging)
        
        Returns:
            (modified_value, anomaly_name or None)
        """
        active_anomalies = self.get_active_anomalies(current_minute)
        
        if not active_anomalies:
            return value, None
        
        modified_value = value
        detected_anomaly = None
        
        for anomaly in active_anomalies:
            anom_type = anomaly['type']
            params = anomaly['params']
            progress = anomaly['progress']
            
            # Appliquer selon le type de capteur et d'anomalie
            if sensor_type == 'MOISTURE' and anom_type == 'moisture_drop':
                modified_value = self.apply_moisture_drop(modified_value, params, progress)
                detected_anomaly = anomaly['name']
            
            elif sensor_type == 'TEMPERATURE' and anom_type == 'temperature_spike':
                modified_value = self.apply_temperature_spike(modified_value, params, progress)
                detected_anomaly = anomaly['name']
            
            elif anom_type == 'erratic_readings':
                modified_value = self.apply_erratic_readings(modified_value, params, progress)
                detected_anomaly = anomaly['name']
            
            elif sensor_type == 'HUMIDITY' and anom_type == 'humidity_drop':
                modified_value = self.apply_humidity_drop(modified_value, params, progress)
                detected_anomaly = anomaly['name']
        
        # ✨ NOUVEAU : Logger le ground truth
        if detected_anomaly:
            self.log_ground_truth(
                minute=current_minute,
                plot_id=plot_id,
                sensor_type=sensor_type,
                original_value=value,
                modified_value=modified_value,
                anomaly_name=detected_anomaly
            )
        
        return modified_value, detected_anomaly
    
    def log_ground_truth(self, minute, plot_id, sensor_type, original_value, modified_value, anomaly_name):
        """
        ✨ NOUVEAU : Enregistre les anomalies injectées pour évaluation
        """
        self.ground_truth_log.append({
            'minute': minute,
            'plot_id': plot_id,
            'sensor_type': sensor_type,
            'original_value': round(original_value, 2),
            'modified_value': round(modified_value, 2),
            'anomaly_name': anomaly_name,
            'is_anomaly': True
        })
    
    def save_ground_truth(self):
        """
        ✨ NOUVEAU : Sauvegarde le log des anomalies dans un fichier JSON
        """
        with open(self.log_file, 'w') as f:
            json.dump(self.ground_truth_log, f, indent=2)
        
        print(f"✅ Ground truth saved to {self.log_file}")
        print(f"   Total anomalies logged: {len(self.ground_truth_log)}")
    
    def get_ground_truth_summary(self):
        """
        ✨ NOUVEAU : Retourne un résumé des anomalies injectées
        """
        if not self.ground_truth_log:
            return "No anomalies logged yet"
        
        by_type = {}
        by_scenario = {}
        
        for entry in self.ground_truth_log:
            sensor = entry['sensor_type']
            scenario = entry['anomaly_name']
            
            by_type[sensor] = by_type.get(sensor, 0) + 1
            by_scenario[scenario] = by_scenario.get(scenario, 0) + 1
        
        return {
            'total_anomalies': len(self.ground_truth_log),
            'by_sensor_type': by_type,
            'by_scenario': by_scenario
        }