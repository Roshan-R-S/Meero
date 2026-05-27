import itertools
import json
import os
import time
from importlib import import_module

from scripts import quick_train
from scripts import evaluate as eval_script


def run_sweep(grid, epochs=20):
    results = []
    for params in grid:
        vocab, embed, maxlen, lr = params
        print(f"Running config vocab={vocab} embed={embed} maxlen={maxlen} lr={lr}")
        out_prefix = f"models/sweep_v{vocab}_e{embed}_m{maxlen}_lr{lr}"
        model_path, tok_path, label_path = quick_train.train(vocab, embed, maxlen, epochs=epochs, lr=lr, out_prefix=out_prefix)
        # small sleep to ensure filesystem sync
        time.sleep(0.5)
        report = eval_script.evaluate(model_path, tok_path, label_path, "intents.json")
        print("-> accuracy:", report["accuracy"])
        results.append({
            "vocab": vocab,
            "embed": embed,
            "maxlen": maxlen,
            "lr": lr,
            "accuracy": report["accuracy"],
            "hallucination_rate": report["hallucination_rate"],
            "confidence_mean": report["confidence_mean"],
            "report": report,
        })
    return results


def main():
    # quick grid
    vocabs = [1000, 2000]
    embeds = [16, 32]
    maxlens = [20, 30]
    lrs = [0.001, 0.0005]

    grid = list(itertools.product(vocabs, embeds, maxlens, lrs))
    results = run_sweep(grid, epochs=25)

    with open("models/hp_sweep_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # print top results
    results.sort(key=lambda r: r["accuracy"], reverse=True)
    for r in results[:5]:
        print(r["vocab"], r["embed"], r["maxlen"], r["lr"], r["accuracy"])


if __name__ == '__main__':
    main()
