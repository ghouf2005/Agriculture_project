"""
Anomaly Injector – supports multiple anomalies per type + perfect farm-wide behavior
"""
import numpy as np
import json
import random
from pathlib import Path
import config
from datetime import timedelta


class AnomalyInjector:
    def __init__(self, log_file='anomalies_ground_truth.json'):
        self.anomaly_scenarios = {
            'irrigation_failure': {
                'type': 'moisture_drop',
                'params': {'drop_rate': 3.0, 'target_min': 25},
                'start_range': (120, 1200),
                'duration_range': (30, 45)
            },
            'heat_wave': {
                'type': 'temperature_spike',
                'params': {'increase': 10},
                'start_range': (540, 900),
                'duration_range': (30, 45)
            },
            'sensor_malfunction': {
                'type': 'erratic_readings',
                'params': {'variance': 6},
                'start_range': (240, 1080),  # avoid crowding the very start of the day
                'duration_range': (12, 18)   # slightly longer to balance counts
            },
            'dry_air': {
                'type': 'humidity_drop',
                'params': {'target': 25},
                'start_range': (360, 1080),
                'duration_range': (30, 45)
            }
        }

        self.farm_wide_scenarios = {"heat_wave", "dry_air"}
        self.balanced_local_scenarios = {"irrigation_failure", "sensor_malfunction"}
        self.base_windows = {}           # {scenario: [window1, window2, ...]}
        self.per_plot_windows = {}       # {plot_id: {scenario: [windows...]}}
        self.log_file = Path(log_file)
        self.ground_truth_log = []

        self._generate_base_windows()

    def _generate_windows(self, cfg, min_count=None, max_count=None):
        """Generate sparse random windows for a scenario"""
        min_ct = config.MIN_ANOMALIES_PER_TYPE if min_count is None else min_count
        max_ct = config.MAX_ANOMALIES_PER_TYPE if max_count is None else max_count
        n = random.randint(min_ct, max_ct)
        windows = []
        for _ in range(n):
            start = random.uniform(*cfg['start_range'])
            duration = random.uniform(*cfg['duration_range'])
            if start + duration > 1440:
                duration = 1440 - start - 1
            windows.append({
                'start': start,
                'end': start + duration,
                'type': cfg['type'],
                'params': cfg['params']
            })
        return windows

    def _generate_base_windows(self):
        # Force one window per scenario to balance shares
        for name, cfg in self.anomaly_scenarios.items():
            self.base_windows[name] = self._generate_windows(cfg, min_count=1, max_count=1)

    def configure_for_plots(self, plot_ids, plot_farm_map=None):
        plot_farm_map = plot_farm_map or {}
        self.per_plot_windows = {pid: {} for pid in plot_ids}

        balanced_templates = {}
        for scenario_name, cfg in self.anomaly_scenarios.items():
            if scenario_name in self.balanced_local_scenarios:
                balanced_templates[scenario_name] = self._generate_windows(cfg, min_count=1, max_count=1)

        for idx, plot_id in enumerate(plot_ids):
            farm_id = plot_farm_map.get(plot_id, f"farm_{plot_id}")

            for scenario_name, base_list in self.base_windows.items():
                if scenario_name in self.farm_wide_scenarios:
                    # Same timing for whole farm + small jitter
                    farm_windows = []
                    for win in base_list:
                        jitter = random.uniform(-10, 10)
                        farm_windows.append({
                            'start': max(0, win['start'] + jitter),
                            'end': max(0, win['end'] + jitter),
                            'type': win['type'],
                            'params': win['params']
                        })
                    self.per_plot_windows[plot_id][scenario_name] = farm_windows
                elif scenario_name in self.balanced_local_scenarios:
                    template = balanced_templates.get(scenario_name, [])
                    windows = []
                    for j, win in enumerate(template):
                        stagger = (idx * 20) + random.uniform(-5, 5)
                        start = max(0, win['start'] + stagger + j * 5)
                        end = max(start + 1, win['end'] + stagger + j * 5)
                        windows.append({
                            'start': start,
                            'end': end,
                            'type': win['type'],
                            'params': win['params']
                        })
                    self.per_plot_windows[plot_id][scenario_name] = windows
                else:
                    # Fully independent per plot
                    cfg = self.anomaly_scenarios[scenario_name]
                    max_ct = 1 if scenario_name == "sensor_malfunction" else None
                    self.per_plot_windows[plot_id][scenario_name] = self._generate_windows(cfg, max_count=max_ct)

    def get_active_anomalies(self, current_minute, plot_id=None):
        active = []
        windows = self.per_plot_windows.get(plot_id, self.base_windows)

        for scenario_name, win_list in windows.items():
            for win in win_list:
                if win['start'] <= current_minute < win['end']:
                    progress = (current_minute - win['start']) / (win['end'] - win['start'])
                    active.append({
                        'name': scenario_name,
                        'type': win['type'],
                        'params': win['params'],
                        'progress': progress
                    })
        return active

    # ——————— Anomaly effects ———————
    def apply_temperature_spike(self, v, p, prog): return v + p['increase'] * min(prog * 1.6, 1.0)
    def apply_humidity_drop(self, v, p, prog):     return v - (v - p['target']) * prog * 0.8
    def apply_moisture_drop(self, v, p, prog):
        if prog < 0.25: return v - p['drop_rate'] * 3.5
        return max(p['target_min'], v - p['drop_rate'] * 0.3)
    def apply_erratic_readings(self, v, p, _):     return v + np.random.uniform(-p['variance'], p['variance'])

    def modify_sensor_value(self, sensor_type, value, current_minute, plot_id=None):
        active = self.get_active_anomalies(current_minute, plot_id)
        if not active:
            return value, None

        modified = value
        triggered = None

        for anom in active:
            if sensor_type == "TEMPERATURE" and anom['type'] == "temperature_spike":
                modified = self.apply_temperature_spike(modified, anom['params'], anom['progress'])
                triggered = anom['name']
            elif sensor_type == "HUMIDITY" and anom['type'] == "humidity_drop":
                modified = self.apply_humidity_drop(modified, anom['params'], anom['progress'])
                triggered = anom['name']
            elif sensor_type == "MOISTURE" and anom['type'] == "moisture_drop":
                modified = self.apply_moisture_drop(modified, anom['params'], anom['progress'])
                triggered = anom['name']
            elif anom['type'] == "erratic_readings":
                modified = self.apply_erratic_readings(modified, anom['params'], anom['progress'])
                triggered = anom['name']

        if triggered:
            self.ground_truth_log.append({
                "minute": int(current_minute),
                "plot_id": plot_id,
                "sensor_type": sensor_type.upper(),
                "original_value": round(value, 2),
                "modified_value": round(modified, 2),
                "anomaly_name": triggered,
                "timestamp": (config.SIMULATION_START_DATETIME + timedelta(minutes=current_minute)).isoformat()
            })

        return modified, triggered

    def save_ground_truth(self):
        with open(self.log_file, 'w') as f:
            json.dump(self.ground_truth_log, f, indent=2)
        print(f"Ground truth saved → {self.log_file} ({len(self.ground_truth_log)} events)")