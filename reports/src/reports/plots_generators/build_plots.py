import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# 1. Load data
xor_df = pd.read_csv("../xor.csv")
bloom_df = pd.read_csv("../bloom.csv")
cuckoo_df = pd.read_csv("../cuckoo.csv")

xor_df["type"] = "xor"
bloom_df["type"] = "bloom"
cuckoo_df["type"] = "cuckoo"

df = pd.concat([xor_df, bloom_df, cuckoo_df], ignore_index=True)

# 2. Calculate construction metrics
df["peak_mem_ratio"] = df["peak_memory_mb"] / df["mem_mb"]
df["build_throughput_m_s"] = df["size_millions"] / df["time_sec"]

# Create labels including bucketsize for Cuckoo
def make_label(row):
    if row["type"] == "xor":
        fp_val = row.get("fpp_size", row.get("fingerprint", None))
        return f"XOR{int(fp_val)}" if pd.notna(fp_val) else "XOR"

    elif row["type"] == "bloom":
        err_val = row.get("err_rate", None)
        if pd.notna(err_val) and err_val > 0:
            num_filters = int(round(-np.log2(err_val)))
            return f"BLOOM{num_filters}"
        return "BLOOM"

    elif row["type"] == "cuckoo":
        fp_val = row.get("fpp_size", row.get("fingerprint", row.get("tag_size", None)))
        b_val = row.get("bucketsize", row.get("bucket_size", None))

        if pd.notna(fp_val) and pd.notna(b_val):
            return f"CUCKOO{int(fp_val)}(b={int(b_val)})"
        elif pd.notna(fp_val):
            return f"CUCKOO{int(fp_val)}"
        elif pd.notna(b_val):
            return f"CUCKOO(b={int(b_val)})"
        return "CUCKOO"

df["config_label"] = df.apply(make_label, axis=1)

# Prepare 2x2 Subplots (Top: Peak Memory Ratio, Bottom: Build Throughput)
sizes = [10, 100]
fig, axes = plt.subplots(2, 2, figsize=(18, 11), sharex=False)

colors = {"xor": "#1f77b4", "bloom": "#ff7f0e", "cuckoo": "#2ca02c"}

for col_idx, size in enumerate(sizes):
    sub_df = df[df["size_millions"] == size].copy()

    if sub_df.empty:
        continue

    # Aggregate by configuration
    df_clean = (
        sub_df.groupby(["type", "config_label"], as_index=False)
        .agg({
            "peak_mem_ratio": "mean",
            "build_throughput_m_s": "mean",
            "time_sec": "mean",
            "peak_memory_mb": "mean",
            "mem_mb": "mean"
        })
        .sort_values(["type", "config_label"])
    )

    # --- PLOT 1: Peak Memory Overhead Ratio (Top Row) ---
    ax_top = axes[0, col_idx]
    sns.barplot(
        data=df_clean,
        x="config_label",
        y="peak_mem_ratio",
        hue="type",
        palette=colors,
        ax=ax_top,
        dodge=False
    )

    # Annotate absolute peak memory values (MB)
    for p, (_, row) in zip(ax_top.patches, df_clean.iterrows()):
        height = p.get_height()
        if pd.notna(height) and height > 0:
            ax_top.annotate(
                f"{height:.2f}x\n({int(row['peak_memory_mb'])} MB)",
                (p.get_x() + p.get_width() / 2.0, height),
                ha="center", va="bottom",
                fontsize=8, xytext=(0, 2), textcoords="offset points", weight="bold"
            )

    ax_top.set_title(f"Construction Peak Memory Factor ({size}M Elements)", fontsize=11, fontweight="bold")
    ax_top.set_xlabel("")
    ax_top.set_ylabel("Peak / Final Memory Ratio", fontsize=10)
    ax_top.grid(True, axis="y", linestyle="--", alpha=0.4)
    ax_top.legend(loc="upper left", fontsize=8, frameon=True)
    ax_top.margins(y=0.20)

    plt.setp(ax_top.get_xticklabels(), rotation=25, ha="right", rotation_mode="anchor")

    # --- PLOT 2: Build Throughput (Bottom Row) ---
    ax_bot = axes[1, col_idx]
    sns.barplot(
        data=df_clean,
        x="config_label",
        y="build_throughput_m_s",
        hue="type",
        palette=colors,
        ax=ax_bot,
        dodge=False
    )

    # Annotate absolute build time (seconds)
    for p, (_, row) in zip(ax_bot.patches, df_clean.iterrows()):
        height = p.get_height()
        if pd.notna(height) and height > 0:
            ax_bot.annotate(
                f"{height:.1f} M/s\n({row['time_sec']:.2f} s)",
                (p.get_x() + p.get_width() / 2.0, height),
                ha="center", va="bottom",
                fontsize=8, xytext=(0, 2), textcoords="offset points", weight="bold"
            )

    ax_bot.set_title(f"Construction Throughput ({size}M Elements)", fontsize=11, fontweight="bold")
    ax_bot.set_xlabel("Filter Configuration", fontsize=10)
    ax_bot.set_ylabel("Throughput (M elem/sec)", fontsize=10)
    ax_bot.grid(True, axis="y", linestyle="--", alpha=0.4)
    ax_bot.legend(loc="upper left", fontsize=8, frameon=True)
    ax_bot.margins(y=0.20)

    plt.setp(ax_bot.get_xticklabels(), rotation=25, ha="right", rotation_mode="anchor")

plt.suptitle("Construction Cost Analysis: Peak Memory Factor & Build Speed", fontsize=14, fontweight="bold", y=0.98)
plt.tight_layout()
plt.savefig("build.png", dpi=300, bbox_inches="tight")