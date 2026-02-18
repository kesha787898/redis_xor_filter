import numpy as np
import pandas as pd

# 1. Load data
xor_df = pd.read_csv("../xor.csv")
bloom_df = pd.read_csv("../bloom.csv")
cuckoo_df = pd.read_csv("../cuckoo.csv")

xor_df["type"] = "xor"
bloom_df["type"] = "bloom"
cuckoo_df["type"] = "cuckoo"

df = pd.concat([xor_df, bloom_df, cuckoo_df], ignore_index=True)

# 2. Fallback FPR calculation for 0-error measurements
def calculate_theoretical_fpr(row):
    if row["type"] == "xor":
        fp_val = row.get("fpp_size", row.get("fingerprint", None))
        if pd.notna(fp_val) and fp_val > 0:
            return 2.0 ** (-fp_val)

    elif row["type"] == "bloom":
        err_val = row.get("err_rate", None)
        if pd.notna(err_val) and err_val > 0:
            return err_val

    elif row["type"] == "cuckoo":
        fp_val = row.get("fpp_size", row.get("fingerprint", row.get("tag_size", None)))
        b_val = row.get("bucketsize", row.get("bucket_size", 4))
        if pd.isna(b_val):
            b_val = 4
        if pd.notna(fp_val) and fp_val > 0:
            return (2.0 * b_val) * (2.0 ** (-fp_val))

    return np.nan

df["theoretical_fpr"] = df.apply(calculate_theoretical_fpr, axis=1)
df["effective_fpr"] = np.where(df["quality_FPR"] > 0, df["quality_FPR"], df["theoretical_fpr"])

# Filter valid rows
df = df[(df["latency_mean_ns"] > 0) & (df["effective_fpr"] > 0)]

# 3. Create Name label
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

df["name"] = df.apply(make_label, axis=1)

# 4. Calculate metrics
df["bits_per_element"] = (df["mem_mb"] * 1024 * 1024 * 8) / (df["size_millions"] * 1e6)
df["build_time_per_element_ns"] = (df["time_sec"] * 1e9) / (df["size_millions"] * 1e6)
df["peak_mem_ratio"] = df["peak_memory_mb"] / df["mem_mb"]

# 5. Group and format table (separated by Dataset Size)
for size in [10, 100]:
    sub_df = df[df["size_millions"] == size].copy()
    if sub_df.empty:
        continue

    summary_df = (
        sub_df.groupby(["type", "name"], as_index=False)
        .agg({
            "bits_per_element": "mean",
            "effective_fpr": "mean",
            "latency_mean_ns": "mean",
            "build_time_per_element_ns": "mean",
            "peak_memory_mb": "mean",
            "peak_mem_ratio": "mean"
        })
        .sort_values(["type", "name"])
    )

    # Format output columns
    summary_df["bits/elem"] = summary_df["bits_per_element"].apply(lambda x: f"{x:.2f}")
    summary_df["FPP"] = summary_df["effective_fpr"].apply(lambda x: f"{x:.2e}")
    summary_df["latency"] = summary_df["latency_mean_ns"].apply(lambda x: f"{x:.1f} ns")
    summary_df["build_time_per_element"] = summary_df["build_time_per_element_ns"].apply(lambda x: f"{x:.2f} ns")
    summary_df["peak_memory"] = summary_df.apply(
        lambda r: f"{r['peak_memory_mb']:.1f} MB ({r['peak_mem_ratio']:.2f}x)", axis=1
    )

    result_table = summary_df[["name", "bits/elem", "FPP", "latency", "build_time_per_element", "peak_memory"]]

    print(f"\n### Dataset Size: {size}M Elements")
    print(result_table.to_string(index=False))