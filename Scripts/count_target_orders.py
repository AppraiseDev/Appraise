"""Count how many times each target order appears, per item and per document.

Works with both pairwise (2 targets) and 3-way (3 targets) batch JSON files.

Usage:
    python count_target_orders.py batch.json
"""

import argparse
import json
from collections import Counter


def count_orders(data):
    item_counts = Counter()
    doc_counts = Counter()

    for batch in data:
        doc_order = None
        for item in batch["items"]:
            order = tuple(t["targetID"] for t in item["targets"])
            item_counts[order] += 1

            if doc_order is None:
                doc_order = order

            if item.get("isCompleteDocument"):
                doc_counts[doc_order] += 1
                doc_order = None

    return item_counts, doc_counts


def print_counts(counts, label):
    total = sum(counts.values())
    print(f"\n{label} ({total} total):")
    for order, count in counts.most_common():
        pct = 100.0 * count / total
        print(f"  {' > '.join(order):40s}  {count:5d}  ({pct:5.1f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="Count target order frequencies in Appraise batch JSON."
    )
    parser.add_argument("file", help="Batch JSON file")
    args = parser.parse_args()

    with open(args.file, encoding="utf-8") as f:
        data = json.load(f)

    item_counts, doc_counts = count_orders(data)
    print_counts(item_counts, "Item-level order counts")
    print_counts(doc_counts, "Document-level order counts")


if __name__ == "__main__":
    main()
