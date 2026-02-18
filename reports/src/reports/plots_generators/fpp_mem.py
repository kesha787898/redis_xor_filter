from math import ceil, log, log2

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
df = df[df["quality_FP"] > 0]

# Calculate bits per element
df["bits_per_element"] = (df["mem_mb"] * 1024 * 1024 * 8) / (df["size_millions"] * 10 ** 6)

# Prepare figure with 2 subplots (10M and 100M)
sizes = [10, 100]
fig, axes = plt.subplots(1, 2, figsize=(18, 7), sharey=True)

colors = {"xor": "#1f77b4", "bloom": "#ff7f0e", "cuckoo": "#2ca02c"}

for idx, size in enumerate(sizes):
    ax = axes[idx]
    sub_df = df[df["size_millions"] == size].copy()

    if sub_df.empty:
        ax.set_title(f"Dataset Size: {size}M Elements (No Data)", fontsize=12)
        continue

    # Take the best FPR for each memory configuration
    df_clean = sub_df.sort_values("bits_per_element").copy()

    # 2. Scatter plot of experimental points
    sns.scatterplot(
        data=df_clean,
        x="bits_per_element",
        y="quality_FPR",
        hue="type",
        palette=colors,
        style="type",
        s=110,
        zorder=5,
        ax=ax
    )

    # 3. Custom Point Annotations
    for _, row in df_clean.iterrows():
        x_val = row["bits_per_element"]
        y_val = row["quality_FPR"]

        if row["type"] == "xor":
            fp_val = row.get("fpp_size", row.get("fingerprint", None))
            if pd.notna(fp_val):
                ax.annotate(
                    f"XOR{int(fp_val)}",
                    (x_val, y_val),
                    xytext=(6, -12),
                    textcoords="offset points",
                    fontsize=8,
                    color=colors["xor"],
                    weight="bold"
                )

        elif row["type"] == "bloom":
            err_val = row.get("err_rate", y_val)
            if pd.notna(err_val) and err_val > 0:
                bpe = -log(err_val) / (log(2) ** 2)
                k = ceil(log(2) * bpe)
                label = f"BLOOM{k}"
            else:
                label = "BLOOM"

            ax.annotate(
                label,
                (x_val, y_val),
                xytext=(6, 6),
                textcoords="offset points",
                fontsize=8,
                color=colors["bloom"],
                weight="bold"
            )

        elif row["type"] == "cuckoo":
            fp_val = row.get("fpp_size", row.get("fingerprint", row.get("tag_size", 8)))
            b_val = row.get("bucketsize", row.get("bucket_size", None))

            label = f"CUCKOO(b={int(b_val)})" if pd.notna(b_val) else "CUCKOO"
            ax.annotate(
                label,
                (x_val, y_val),
                xytext=(6, -6),
                textcoords="offset points",
                fontsize=8,
                color=colors["cuckoo"],
                weight="bold"
            )

    # 4. Generate curve fits formatted directly in power-of-2 exponent
    max_b = max(df_clean["bits_per_element"].max() + 2, 45)
    x_range = np.linspace(df_clean["bits_per_element"].min(), max_b, 200)

    for filter_type in ["xor", "bloom", "cuckoo"]:
        type_sub = df_clean[df_clean["type"] == filter_type]
        if len(type_sub) >= 2:
            x_pts = type_sub["bits_per_element"].values
            y_pts = np.log2(type_sub["quality_FPR"].values)
            if filter_type == "h":
                slope, intercept = np.polyfit(x_pts, y_pts, 1)
                sign = "+" if intercept > 0 else "-"
                label_str = f"{filter_type} fit: $2^{{{slope:.3f}b {sign} {abs(intercept):.2f}}}$"

            else:
                slope = np.sum(x_pts * y_pts) / np.sum(x_pts ** 2)
                label_str = f"{filter_type} fit: $2^{{{slope:.3f}b}}$"
                intercept=0

            ax.plot(
                x_range,
                2 ** (intercept + slope * x_range),
                linestyle="--",
                color=colors[filter_type],
                linewidth=2,
                label=label_str
            )

    # Theoretical curves
    ax.plot(
        x_range,
        2 ** (-x_range),
        linestyle=":",
        color="black",
        linewidth=2,
        label="Shannon Limit: $2^{-1.000b}$"
    )
    ax.plot(
        x_range,
        2 ** (-np.log(2) * x_range),
        linestyle="-.",
        color=colors["bloom"],
        alpha=0.35,
        label="Bloom Theory: $2^{-0.693b}$"
    )
    ax.plot(
        x_range,
        2 ** (-(1 / 1.23) * x_range),
        linestyle="-.",
        color=colors["xor"],
        alpha=0.35,
        label="XOR Theory: $2^{-0.813b}$"
    )

    # Cuckoo Theory for Fixed Fingerprint f=8: FPR = 2*b_bucket / 2^f
    cuckoo_sub = df_clean[
        df_clean["type"] == cuckoo_sub_type if (cuckoo_sub_type := "cuckoo") in df_clean["type"].values else "cuckoo"]

    # Axis and Plot Formatting
    ax.set_yscale("log")
    ax.set_ylim(bottom=1e-6, top=0.5)
    ax.set_xlim(left=0, right=max_b)

    ax.set_xlabel("Bits per element ($b$)", fontsize=11)
    if idx == 0:
        ax.set_ylabel("False Positive Rate (FPR)", fontsize=11)

    ax.set_title(f"Dataset Size: {size}M Elements", fontsize=12, fontweight="bold")
    ax.grid(True, which="both", linestyle="--", alpha=0.4)
    ax.legend(loc="lower right", fontsize=8, frameon=True)

plt.suptitle(
    "XOR Filter vs Bloom Filter vs Cuckoo Filter Performance & Theoretical Bounds",
    fontsize=14,
    fontweight="bold",
    y=0.98
)
plt.tight_layout()
plt.savefig("fpp.png", dpi=300, bbox_inches="tight")