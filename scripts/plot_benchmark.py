import json
import matplotlib.pyplot as plt
import numpy as np
import glob


def plot_results():
    files = glob.glob("benchmark_results_*.json")
    if not files:
        print("No benchmark result files found.")
        return

    data = []
    for f in files:
        with open(f, "r") as fp:
            data.append(json.load(fp))

    # Sort by numpy version
    data.sort(key=lambda x: x["numpy_version"])

    versions = [f"numpy=={d['numpy_version']}" for d in data]
    scipy_times = [d["scipy_local_time"] * 1000 for d in data]
    fast_setup_times = [d["fast_rbf_setup_time"] * 1000 for d in data]
    fast_predict_times = [d["fast_rbf_predict_time"] * 1000 for d in data]

    x = np.arange(len(versions))
    width = 0.15

    with plt.xkcd():
        fig, ax = plt.subplots(figsize=(12, 7))

        # Plot 3 bars
        rects1 = ax.bar(
            x - width, scipy_times, width, label="Scipy RBF (Total)", color="tab:blue"
        )
        rects2 = ax.bar(
            x,
            fast_setup_times,
            width,
            label="FastRBF (Setup, one time)",
            color="tab:gray",
        )
        rects3 = ax.bar(
            x + width,
            fast_predict_times,
            width,
            label="FastRBF (Predict)",
            color="tab:orange",
        )

        ax.set_ylabel("Time (ms)")
        ax.set_title(
            "Interpolation Performance Comparison\n(Grid: 200x200, Neighbors: 30, Machine: Apple M1)",
            fontsize=14,
        )
        ax.set_xticks(x)
        ax.set_xticklabels(versions)
        ax.legend()
        ax.set_yscale("log")

        def autolabel(rects):
            for rect in rects:
                height = rect.get_height()
                ax.annotate(
                    f"{height:.1f}ms",
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=12,
                )

        autolabel(rects1)
        autolabel(rects2)
        autolabel(rects3)

        # Add speedup annotation between Scipy and FastRBF Predict
        for i, (s, f) in enumerate(zip(scipy_times, fast_predict_times)):
            speedup = s / f
            # Position the text above the Predict bar, but high enough
            ax.text(
                i + width,
                f * 1.5,
                f"{speedup:.1f}x\nSpeedup",
                ha="center",
                va="bottom",
                fontweight="bold",
                color="tab:red",
            )

        plt.tight_layout()
        plt.savefig("benchmark_plot.png")
        print("Plot saved to benchmark_plot.png")

    # Also print a summary table
    print("\nSummary Table (ms):")
    print(
        f"{'Version':<15} | {'Scipy (ms)':<12} | {'Setup (ms)':<12} | {'Predict (ms)':<15} | {'Speedup':<10}"
    )
    print("-" * 75)
    for d in data:
        s = d["scipy_local_time"] * 1000
        setup = d["fast_rbf_setup_time"] * 1000
        pred = d["fast_rbf_predict_time"] * 1000
        speedup = s / pred
        print(
            f"numpy=={d['numpy_version']:<8} | {s:<12.2f} | {setup:<12.2f} | {pred:<15.4f} | {speedup:.1f}x"
        )


if __name__ == "__main__":
    plot_results()
