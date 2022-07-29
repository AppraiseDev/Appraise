#!/usr/bin/env python3

import argparse
import json
import sys

from collections import defaultdict
from collections import Counter


def main():
    args = parse_user_args()
    tasks = json.load(args.json_file)

    items_count = 0
    items_by_type = defaultdict(int)
    doc_items_count = 0
    targets = defaultdict(list)
    for i in range(len(tasks)):
        # print(f"Task {i}:")
        bad_items = []

        for item in tasks[i]["items"]:
            item_type = item["itemType"]
            if item.get("isCompleteDocument", False):
                doc_items_count += 1
            else:
                items_by_type[item_type] += 1
                items_count += 1

                if item_type == "BAD":
                    bad_items.append(item["documentID"])

                target_id = item["targetID"]
                doc_id = item["documentID"]
                item_id = item["itemID"]
                targets[target_id].append((doc_id, item_type))

        print(f"Task {i}: {len(bad_items)} BAD items in {len(set(bad_items))} doc(s)")

    for system, docids_and_itypes in targets.items():
        docids = [p[0] for p in docids_and_itypes]
        uniq_docids = sorted(list(set(docids)))
        print(f"System {system}")
        print(
            f"  will be evaluated on {len(uniq_docids)} unique docs: {' '.join(str(d) for d in uniq_docids)}"
        )
        for docid in uniq_docids:
            count_tgt = sum(
                1
                for _docid, _itype in docids_and_itypes
                if _docid == docid and _itype == "TGT"
            )
            count_bad = sum(
                1
                for _docid, _itype in docids_and_itypes
                if _docid == docid and _itype == "BAD"
            )
            print(
                f"    {docid} occurs {docids.count(docid)} times: {count_tgt} regular docs + {count_bad} with a BAD item"
            )
        # counts = [count for _, count in Counter(docids).most_common()]
        # print(f"  (#repeats, #documents): {Counter(counts).most_common()}")

    print(f"Total number of tasks: {len(tasks):,}")
    print(f"Total number of segment items: {items_count:,}")
    for itype, count in items_by_type.items():
        perc = count / float(items_count)
        print(f" {itype} items: {count:,} = {perc:.1%}")
    print(f"Total number of document items: {doc_items_count:,}")

    print("Done")


def parse_user_args():
    parser = argparse.ArgumentParser(
        description='Prints statistics for a single JSON batches file.'
    )
    parser.add_argument(
        'json_file',
        help='JSON batches',
        nargs='?',
        type=argparse.FileType('r'),
        default=sys.stdin,
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
