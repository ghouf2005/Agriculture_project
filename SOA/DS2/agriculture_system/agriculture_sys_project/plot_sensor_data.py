# plot_sensor_data.py
# New version: per sensor, colored by plot, with anomalies highlighted
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("synthetic_dataset_with_labels.csv")


COLORS = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple", "tab:brown"]


def plot_sensor_by_plot(sensor_type):
    sub_all = df[df["sensor_type"] == sensor_type].copy()
    if sub_all.empty:
        print(f"⚠ No data for sensor_type={sensor_type}")
        return

    # Sort by timestamp to have chronological curves
    sub_all = sub_all.sort_values(["plot", "timestamp"])

    plt.figure(figsize=(12, 6))

    plots = sorted(sub_all["plot"].unique())

    for i, plot_id in enumerate(plots):
        sub = sub_all[sub_all["plot"] == plot_id].reset_index(drop=True)

        x = range(len(sub))
        y = sub["value"].values

        plt.plot(
            x,
            y,
            label=f"Plot {plot_id}",
            color=COLORS[i % len(COLORS)],
            alpha=0.85,
        )

        # Anomaly points for this plot
        anomalies = sub[sub["is_anomaly"] == 1]
        if not anomalies.empty:
            ax = anomalies.index
            ay = anomalies["value"].values
            plt.scatter(
                ax,
                ay,
                s=30,
                edgecolors="red",
                facecolors="none",
                linewidths=1.5,
                label=f"Anomalies (Plot {plot_id})" if i == 0 else None,  # avoid label spam
            )

    plt.title(f"{sensor_type} readings per plot (with anomalies)")
    plt.xlabel("Time index (per plot)")
    plt.ylabel("Sensor value")
    plt.legend()
    plt.grid(True)
    out_name = f"{sensor_type.lower()}_per_plot_with_anomalies.png"
    plt.savefig(out_name)
    print(f"📈 Saved {out_name}")


if __name__ == "__main__":
    plot_sensor_by_plot("TEMPERATURE")
    plot_sensor_by_plot("HUMIDITY")
    plot_sensor_by_plot("MOISTURE")
