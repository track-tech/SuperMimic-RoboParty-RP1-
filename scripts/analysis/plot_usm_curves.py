"""Plot G1 vs RP1 SuperMimic training curves into one PNG.

    python plot_usm_curves.py --runs <g1_dir> <rp1_dir> --out curves.png
"""
import argparse
import csv
import os
import sys


def load(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    cols = {}
    for key in rows[0]:
        vals = []
        for r in rows:
            try:
                vals.append(float(r[key]))
            except ValueError:
                vals.append(float("nan"))
        cols[key] = vals
    return cols


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--labels", nargs="+", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--keys", nargs="+",
                    default=["term_frac", "ep_ret_norm", "wm_err8", "ep_len"])
    args = ap.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = args.labels or [os.path.basename(os.path.normpath(p)) for p in args.runs]
    runs = [load(os.path.join(p, "train_log.csv") if os.path.isdir(p) else p) for p in args.runs]

    fig, axes = plt.subplots(2, 2, figsize=(12, 7.5))
    axes = axes.ravel()
    for ax, key in zip(axes, args.keys):
        for data, label in zip(runs, labels):
            if key not in data:
                continue
            ax.plot(data["iteration"], data[key], label=label, linewidth=1.2)
        ax.set_title(key)
        ax.set_xlabel("iteration")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle("SuperMimic on three Roboparty/Unitree humanoids")
    fig.tight_layout()
    fig.savefig(args.out, dpi=130)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    sys.exit(main())
