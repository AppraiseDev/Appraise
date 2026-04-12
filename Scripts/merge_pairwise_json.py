"""Merge two aligned pairwise Appraise JSON batch files into one.

Each input file must have the same batches and items (matched by
segmentID).  The shared targetID (e.g. "uplift4") is kept once;
the unique targetID from each file is added, producing items with
all three targets.

Usage:
    python merge_pairwise_json.py file_a.json file_b.json -o merged.json
    python merge_pairwise_json.py file_a.json file_b.json -o merged.json --seed 42
    python merge_pairwise_json.py file_a.json file_b.json -o merged.json --no-shuffle
"""

import argparse
import json
import random
import sys


def merge(data_a, data_b):
    if len(data_a) != len(data_b):
        sys.exit(
            f"Error: batch count mismatch ({len(data_a)} vs {len(data_b)})"
        )

    merged = []

    for batch_idx, (batch_a, batch_b) in enumerate(zip(data_a, data_b)):
        items_a = batch_a["items"]
        items_b = batch_b["items"]

        if len(items_a) != len(items_b):
            sys.exit(
                f"Error: item count mismatch in batch {batch_idx} "
                f"({len(items_a)} vs {len(items_b)})"
            )

        # Discover targetIDs from first item of each file
        tids_a = {t["targetID"] for t in items_a[0]["targets"]}
        tids_b = {t["targetID"] for t in items_b[0]["targets"]}
        shared = tids_a & tids_b
        unique_a = tids_a - shared
        unique_b = tids_b - shared

        if not shared:
            sys.exit(
                f"Error: no shared targetID between files "
                f"(file A: {tids_a}, file B: {tids_b})"
            )

        # Determine a stable ordering: unique_a targets, unique_b targets, shared targets
        target_order = sorted(unique_a) + sorted(unique_b) + sorted(shared)

        item_all_counter = 0
        merged_items = []

        for item_a, item_b in zip(items_a, items_b):
            if item_a["segmentID"] != item_b["segmentID"]:
                sys.exit(
                    f"Error: segmentID mismatch in batch {batch_idx}: "
                    f"{item_a['segmentID']} vs {item_b['segmentID']}"
                )

            targets_a = {t["targetID"]: t for t in item_a["targets"]}
            targets_b = {t["targetID"]: t for t in item_b["targets"]}

            merged_targets = []
            for target_idx, tid in enumerate(target_order):
                # Pick from whichever file has this targetID
                src = targets_a if tid in targets_a else targets_b
                t = src[tid].copy()
                t["_itemAll"] = item_all_counter
                t["_target"] = target_idx
                merged_targets.append(t)
                item_all_counter += 1

            merged_item = item_a.copy()
            merged_item["targets"] = merged_targets
            merged_item["targetsSize"] = len(merged_targets)
            merged_items.append(merged_item)

        merged_batch = {
            "items": merged_items,
            "task": batch_a["task"].copy(),
        }
        merged.append(merged_batch)

    return merged


def shuffle_targets(data, seed=None):
    """Shuffle target order per document, keeping it consistent within a document.

    A document is all consecutive items up to and including one with
    isCompleteDocument=true.  All items in the same document get the
    same shuffled target order.
    """
    rng = random.Random(seed)
    num_targets = len(data[0]["items"][0]["targets"])
    order = list(range(num_targets))

    for batch in data:
        item_all_counter = 0
        # Pick a fresh order for the first document
        rng.shuffle(order)

        for item in batch["items"]:
            shuffled = [item["targets"][i] for i in order]
            for target_idx, t in enumerate(shuffled):
                t["_target"] = target_idx
                t["_itemAll"] = item_all_counter
                item_all_counter += 1
            item["targets"] = shuffled

            # End of document — pick a new order for the next one
            if item.get("isCompleteDocument"):
                order = list(range(num_targets))
                rng.shuffle(order)

    return data


def main():
    parser = argparse.ArgumentParser(
        description="Merge two aligned pairwise Appraise JSON batch files."
    )
    parser.add_argument("file_a", help="First pairwise JSON file")
    parser.add_argument("file_b", help="Second pairwise JSON file")
    parser.add_argument(
        "-o", "--output", required=True, help="Output merged JSON file"
    )
    parser.add_argument(
        "--no-shuffle", action="store_true",
        help="Disable shuffling of target order within documents",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for deterministic shuffling",
    )
    args = parser.parse_args()

    with open(args.file_a, encoding="utf-8") as f:
        data_a = json.load(f)
    with open(args.file_b, encoding="utf-8") as f:
        data_b = json.load(f)

    merged = merge(data_a, data_b)

    if not args.no_shuffle:
        shuffle_targets(merged, seed=args.seed)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    total_items = sum(len(b["items"]) for b in merged)
    target_ids = sorted(
        {t["targetID"] for b in merged for i in b["items"] for t in i["targets"]}
    )
    print(
        f"Wrote {args.output}: {len(merged)} batches, "
        f"{total_items} items, targets={target_ids}"
    )


if __name__ == "__main__":
    main()
