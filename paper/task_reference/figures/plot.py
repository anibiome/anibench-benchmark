# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Replay four paper figures from public aggregates; does not rerun empirical fitting."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

BASE = Path(__file__).resolve().parent

def plot_frontier(data, out):
    rows = data["rows"]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "svg.fonttype": "none",
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.8))
    colors = {0: "#16776B", 0.2: "#335C95", 0.8: "#956EAC", 1.0: "#B26A35"}
    for ax, level, floor in zip(axes, ["AB1", "AB2"], [1281, 5121]):
        for index, (rho, color) in enumerate(colors.items()):
            subset = [r for r in rows if r["level"] == level and r["repeat_correlation"] == rho]
            ax.plot([r["depth"] for r in subset], [r["minimum_balanced_N"] for r in subset],
                    marker=["s", "o", "^", "D"][index], linewidth=2, color=color,
                    linestyle=["-", (0, (5, 2)), (0, (1, 2)), (0, (4, 2, 1, 2))][index],
                    label=f"Repeat correlation {rho:g}")
        ax.axhline(floor, color="#697572", lw=1, linestyle=(0, (3, 3)))
        ax.set_xscale("log", base=2)
        ax.set_xticks([128, 512, 2048, 8192], labels=["128", "512", "2,048", "8,192"])
        ax.set(title=f"{level} conditional reference", xlabel="Modeled technical depth (variance-reduction factor)",
               ylabel="Minimum retained participants", xlim=(56, 10000))
        ax.grid(axis="y", color="#E4EAE8", linewidth=.7)
        ax.set_axisbelow(True)
        ax.ticklabel_format(axis="y", useOffset=False, style="plain")
        ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
    fig.suptitle("Depth cannot replace independent people", x=.065, ha="left", y=.975,
                 fontsize=20, fontweight="bold", color="#173D37")
    fig.text(.065, .908, "Derived boundaries · all required support · four technical repeats · both declared noise scenarios",
             color="#50655F", fontsize=10)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower left", bbox_to_anchor=(.057, .075), ncol=2, frameon=False, fontsize=9)
    fig.text(.065, .028, "Lines start where individual precision becomes feasible. Dashed: continuous large-depth person floor; balanced integer allocation rounds upward.\n"
             "Synthetic reference assumptions, not ideal-trial recommendations. Depth is not assay count, spend or actual sampling burden.",
             fontsize=8, color="#50655F")
    fig.subplots_adjust(left=.075, right=.97, top=.79, bottom=.285, wspace=.30)
    fig.savefig(out / "conditional_frontier.svg", metadata={"Date": None})
    fig.savefig(out / "conditional_frontier.png", dpi=220)
    plt.close(fig)

def plot_temporal(data, out):
    rows = data["rows"]
    methods = {
        "uniform_SRS": ("Random scattered epochs", "#14756B"),
        "hour_stratified_circular": ("One block per hour", "#7862A5"),
        "circular_block": ("One circular block", "#C07635"),
    }
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.spines.left": False, "axes.spines.bottom": False,
                         "svg.fonttype": "none", "savefig.facecolor": "white"})
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.6))
    for ax, target, title, limit in zip(axes, ["sleep_minutes", "REM_minutes"],
                                       ["Total sleep annotation", "REM annotation"], [20, 10]):
        for method, (label, color) in methods.items():
            r = sorted([r for r in rows if r["method"] == method and r["target"] == target],
                       key=lambda r: r["minutes"])
            ax.plot([x["minutes"] for x in r], [x["heldout_exact_design_RMSE"] for x in r],
                    color=color, marker="o", linewidth=2.3, markersize=5, label=label)
            ax.plot([x["minutes"] for x in r], [x["predicted_SE"] for x in r],
                    color=color, linestyle=(0, (3, 3)), linewidth=1.4, alpha=.75)
        ax.axhline(limit, color="#697272", lw=1, linestyle=(0, (1, 3)))
        ax.text(129, limit, f" {limit}-min target", fontsize=8, va="center", color="#596060")
        ax.set(title=title, xlabel="Minutes sampled within the same 8-hour record",
               ylabel="Estimation error (minutes; lower is better)", xlim=(26, 154), ylim=(0, None))
        ax.set_xticks([32, 64, 128])
        ax.grid(axis="y", color="#E5E9E8", linewidth=.6)
        ax.set_axisbelow(True)
        ax.tick_params(length=0)
    fig.suptitle("Equal recording time can reveal very different amounts", x=.055, ha="left",
                 y=.985, fontsize=19, fontweight="bold", color="#173B38")
    fig.text(.055, .911, "Temporal-sampling experiment · 22 held-out people · fixed sleep-stage annotation targets",
             color="#4D615F", fontsize=10)
    handles = [Line2D([0], [0], color=c, lw=2.3, marker="o", label=l) for l, c in methods.values()]
    handles += [Line2D([0], [0], color="#596060", ls=(0, (3, 3)), lw=1.4, label="Training-predicted error")]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(.049, .084), ncol=2,
               frameon=False, fontsize=9)
    fig.text(.055, .032, "Solid: held-out exact sampling RMSE. Dashed: training covariance estimate. Point estimates; uncertainty in the report.\n"
             "Circular blocks may wrap. This evaluates sampling of existing annotations, not EEG waveform quality or persistent traits.",
             fontsize=8, color="#596060")
    fig.subplots_adjust(left=.07, right=.965, bottom=.285, top=.79, wspace=.31)
    fig.savefig(out / "temporal_sampling.svg", metadata={"Date": None})
    fig.savefig(out / "temporal_sampling.png", dpi=220)
    plt.close(fig)

def plot_molecular(data, out):
    rows = data['rows']
    titles = ['F. prausnitzii abundance','Butanoate pathway abundance']
    units = ['Organismal relative fraction','Released relative pathway abundance']
    labels = {'mean':'Training mean','ridge':'Ridge regression','raw':'Inverse estimator'}
    colors = {'mean':'#456A7B','ridge':'#8D9299','raw':'#212B46'}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(12.8,6.3));fig.subplots_adjust(left=.15,right=.98,bottom=.31,top=.71,wspace=.47)
    for i,ax in enumerate(axes):
        subset=rows[i*3:i*3+3]
        for y,(row,lane) in enumerate(zip(subset,('mean','ridge','raw'))):
            lo,hi=row['bootstrap_95_lower'],row['bootstrap_95_upper'];x=row['rmse']
            ax.errorbar(x,y,xerr=[[x-lo],[hi-x]],fmt='o' if lane!='raw' else 'D',color=colors[lane],capsize=5,elinewidth=2,markersize=8)
            ax.annotate(f'{x:.3g}',(x,y),xytext=(0,14),textcoords='offset points',ha='center',fontsize=10,color=colors[lane],weight='bold')
        ax.set_yticks(range(3),list(labels.values()));ax.set_ylim(2.5,-.6);ax.set_xlim(0,max(r['bootstrap_95_upper'] for r in subset)*1.12)
        ax.set_title(titles[i],loc='left',fontsize=13,pad=22,weight='bold');ax.set_xlabel('Prediction error (RMSE)\n'+units[i],labelpad=12)
        ax.grid(axis='x',alpha=.16);ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0,pad=10)
    fig.text(.035,.95,'The inverse estimator underperformed simple baselines',ha='left',fontsize=20,weight='bold',color='#18202B')
    fig.text(.035,.875,'M04 · Four linked metabolite inputs · 53 train / 21 calibration / 32 held-out people',fontsize=12,color='#505965')
    fig.text(.035,.055,'Points: held-out error. Lines: 95% person-bootstrap intervals from 1,000 refits.\nThis tests one estimator on two released microbial outputs; it does not rank study quality or measure treatment benefit.',fontsize=10,color='#505965',linespacing=1.6)
    fig.savefig(out/'molecular_validation.svg',metadata={'Date':None});fig.savefig(out/'molecular_validation.png',dpi=220);plt.close(fig)


def plot_native_mean(data, out):
    """Display existing canonical percentages only; never recompute a study score."""
    domains = [('molecular', 'Molecular'), ('physiological', 'Physiological'),
               ('digital', 'Digital'), ('cognitive', 'Cognitive'), ('neural', 'Structural brain')]
    studies = [('MIPACT', 'MIPACT', '#14756B'), ('DIRECT_PLUS', 'DIRECT PLUS', '#705BA1')]
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'svg.fonttype': 'none',
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.spines.left': False, 'axes.spines.bottom': False})
    fig, ax = plt.subplots(figsize=(11.8, 7.2))
    for i, (domain, label) in enumerate(domains):
        if i % 2 == 0:
            ax.axhspan(i * 1.7 - .62, i * 1.7 + .62, color='#F3F6F5', zorder=0)
        for j, (study, name, color) in enumerate(studies):
            row = next(r for r in data['rows'] if r['study'] == study and r['domain'] == domain)
            y = i * 1.7 + (j - .5) * .52
            lo, hi, confirmed = row['lower_percent'], row['upper_percent'], row['maximum_confirmed_pass_percent']
            ax.plot([lo, confirmed], [y, y], color=color, linewidth=4, solid_capstyle='butt', zorder=3)
            if hi > confirmed:
                ax.plot([confirmed, hi], [y, y], color=color, linewidth=2, linestyle=(0, (3, 3)), alpha=.75, zorder=2)
                ax.plot(hi, y, marker='o', markerfacecolor='white', markeredgecolor=color, markersize=5, zorder=4)
            ax.plot(lo, y, marker='o' if j == 0 else 's', color=color, markersize=6, zorder=5)
            value = f'{lo:g}%' if lo == hi else f'{lo:g}–{hi:g}%'
            ax.text(106, y, value, ha='left', va='center', weight='bold', color=color, fontsize=10)
    ax.set_yticks([i * 1.7 for i in range(5)], [x[1] for x in domains])
    ax.set_ylim(7.55, -.85)
    ax.set_xlim(-2, 123)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel('Own-population mean precision tasks met (%) · two fixed tasks per domain', labelpad=13)
    ax.tick_params(axis='both', length=0, pad=9)
    ax.grid(axis='x', color='#DDE5E2', linewidth=.7)
    ax.set_axisbelow(True)
    handles = [Line2D([0], [0], marker='o' if j == 0 else 's', color=c, lw=0, label=n)
               for j, (_, n, c) in enumerate(studies)]
    handles += [Line2D([0], [0], color='#53625E', lw=3, label='Range of confirmed passes across scenarios'),
                Line2D([0], [0], color='#53625E', lw=2, ls=(0, (3, 3)), label='Additional unresolved task mass')]
    fig.legend(handles=handles, loc='lower left', bbox_to_anchor=(.057, .105), ncol=2, frameon=False, fontsize=9)
    fig.text(.065, .952, 'What do the reported data resolve?', fontsize=21, weight='bold', color='#173B38')
    fig.text(.065, .905, 'MIPACT and DIRECT PLUS · 10-target pilot · default SE limits · all six coherent scenarios', color='#50655F', fontsize=10)
    fig.text(.065, .035,
             'Ranges are scenario / unknown-task outer bounds, not confidence intervals. Missing cognitive and brain precision stays unknown.\n'
             'Each study concerns its own population and source operator; cross-operator comparison is conditional.\n'
             'This selected mean-precision pilot does not rank whole-study quality, treatment benefit, or AB1 attainment.',
             fontsize=8.5, color='#50655F', linespacing=1.5)
    fig.subplots_adjust(left=.17, right=.96, top=.85, bottom=.255)
    fig.savefig(out / 'native_mean_pilot.svg', metadata={'Date': None})
    fig.savefig(out / 'native_mean_pilot.png', dpi=220)
    plt.close(fig)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path, help='New output directory; existing paths are never overwritten')
    args = parser.parse_args()
    manifest = json.loads((BASE / 'manifest.json').read_text())
    data = {}
    for name, expected in manifest['data_sha256'].items():
        content = (BASE / name).read_bytes()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError('Figure data identity mismatch: ' + name)
        data[name] = json.loads(content)
    args.out.mkdir(parents=True, exist_ok=False)
    for name, render in [('conditional_frontier', plot_frontier), ('temporal_sampling', plot_temporal), ('molecular_validation', plot_molecular), ('native_mean_pilot', plot_native_mean)]:
        with plt.rc_context():
            plt.rcParams['svg.hashsalt'] = 'anibench-task-reference-figures-v1'
            render(data[name + '.json'], args.out)
    receipt = {'contract': 'anibench.aggregate-figure-replay.v1', 'matplotlib_version': matplotlib.__version__,
               'data_sha256': manifest['data_sha256'], 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'empirical_fits_reexecuted': False,
               'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.out.iterdir())}}
    (args.out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'figures': 4, 'empirical_fits_reexecuted': False}))

if __name__ == '__main__':
    main()
