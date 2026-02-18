import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# 1. Load data
xor_df = pd.read_csv("../xor.csv")
bloom_df = pd.read_csv("../bloom.csv")
cuckoo_df = pd.read_csv("../cuckoo.csv")
ping_df = pd.read_csv("../ping.csv")

xor_df["type"] = "xor"
bloom_df["type"] = "bloom"
cuckoo_df["type"] = "cuckoo"
ping_df["type"] = "ping"

# Если в ping.csv нет колонки size_millions, дублируем значения для всех анализируемых размеров
sizes = [10, 100]
if "size_millions" not in ping_df.columns:
    ping_dfs = []
    for s in sizes:
        temp = ping_df.copy()
        temp["size_millions"] = s
        ping_dfs.append(temp)
    ping_df = pd.concat(ping_dfs, ignore_index=True)

df = pd.concat([xor_df, bloom_df, cuckoo_df, ping_df], ignore_index=True)

# 2. Format filter names
def get_filter_name(row):
    f_type = row["type"]
    if f_type == "xor":
        fp = row.get("fpp_size", row.get("fingerprint", None))
        return f"XOR-{int(fp)}" if pd.notna(fp) else "XOR"
    elif f_type == "bloom":
        err = row.get("err_rate", None)
        if pd.notna(err) and err > 0:
            k = int(round(-np.log2(err)))
            return f"Bloom-{k}"
        return "Bloom"
    elif f_type == "cuckoo":
        b = row.get("bucketsize", row.get("bucket_size", None))
        fp = row.get("fpp_size", row.get("fingerprint", row.get("tag_size", None)))
        if pd.notna(b) and pd.notna(fp):
            return f"Cuckoo{int(fp)} (b={int(b)})"
        elif pd.notna(b):
            return f"Cuckoo (b={int(b)})"
        return "Cuckoo"
    elif f_type == "ping":
        return "Ping"
    return f_type.upper()

df["filter_name"] = df.apply(get_filter_name, axis=1)

# Convert latency from nanoseconds to microseconds (µs)
df["latency_mean_us"] = df["latency_mean_ns"] / 1000.0
if "latency_std_ns" in df.columns:
    df["latency_std_us"] = df["latency_std_ns"] / 1000.0
if "latency_p50_ns" in df.columns:
    df["latency_p50_us"] = df["latency_p50_ns"] / 1000.0
if "latency_p99_ns" in df.columns:
    df["latency_p99_us"] = df["latency_p99_ns"] / 1000.0

# 3. Grouping
agg_dict = {"latency_mean_us": "mean"}
for col in ["latency_std_us", "latency_p50_us", "latency_p99_us"]:
    if col in df.columns:
        agg_dict[col] = "mean"

df_clean = (
    df.groupby(["size_millions", "type", "filter_name"], as_index=False)
    .agg(agg_dict)
    .sort_values(["type", "filter_name"])
)

# 4. Plotting
fig, axes = plt.subplots(1, 2, figsize=(18, 7.5), sharey=True)

colors = {
    "xor": "#1f77b4",
    "bloom": "#ff7f0e",
    "cuckoo": "#2ca02c",
    "ping": "#d62728"
}

for idx, size in enumerate(sizes):
    ax = axes[idx]
    sub_df = df_clean[df_clean["size_millions"] == size].copy()

    if sub_df.empty:
        ax.set_title(f"Dataset Size: {size}M Elements (No Data)")
        continue

    x_positions = np.arange(len(sub_df))
    filter_labels = sub_df["filter_name"].values
    filter_colors = [colors[t] for t in sub_df["type"]]

    # 1. Bars: Mean Latency + Std Error Bars
    ax.bar(
        x_positions,
        sub_df["latency_mean_us"],
        yerr=sub_df["latency_std_us"] if "latency_std_us" in sub_df else None,
        capsize=4,
        color=filter_colors,
        alpha=0.7,
        edgecolor="black",
        linewidth=0.8
    )

    # 2. Diamonds: Median (p50)
    if "latency_p50_us" in sub_df.columns:
        ax.scatter(
            x_positions,
            sub_df["latency_p50_us"],
            color="black",
            marker="D",
            s=35,
            zorder=6
        )

    # 3. Red Crosses: 99th Percentile (p99)
    if "latency_p99_us" in sub_df.columns:
        ax.scatter(
            x_positions,
            sub_df["latency_p99_us"],
            color="red",
            marker="x",
            s=55,
            linewidths=2,
            zorder=6
        )

    ax.set_xticks(x_positions)
    ax.set_xticklabels(filter_labels, rotation=45, ha="right", fontsize=9, fontweight="bold")
    ax.set_title(f"Dataset Size: {size}M Elements", fontsize=12, fontweight="bold")
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)

    if idx == 0:
        ax.set_ylabel("Latency (µs)", fontsize=11)

# Custom legend block inside the first subplot
legend_elements = [
    Patch(facecolor=colors["xor"], alpha=0.7, edgecolor="black", label="XOR Filter"),
    Patch(facecolor=colors["bloom"], alpha=0.7, edgecolor="black", label="Bloom Filter"),
    Patch(facecolor=colors["cuckoo"], alpha=0.7, edgecolor="black", label="Cuckoo Filter"),
    Patch(facecolor=colors["ping"], alpha=0.7, edgecolor="black", label="Ping"),
    Patch(facecolor="gray", alpha=0.5, edgecolor="black", label="Bar: Mean Latency"),
    Line2D([0], [0], color="black", marker="", linestyle="-", linewidth=1.5, label="Error Bar: ± Std"),
    Line2D([0], [0], color="black", marker="D", linestyle="None", markersize=6, label="Diamond: Median (p50)"),
    Line2D([0], [0], color="red", marker="x", linestyle="None", markersize=8, markeredgewidth=2, label="Cross: Tail Latency (p99)")
]

axes[0].legend(
    handles=legend_elements,
    loc="upper left",
    fontsize=8.5,
    frameon=True,
    facecolor="white",
    edgecolor="gray",
    framealpha=0.95
)

plt.suptitle("Operation Latency by Filter Type (Mean, Median p50, Std, p99)", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig("latency.png", dpi=300, bbox_inches="tight")