import sys

from collections import defaultdict
from random import seed, shuffle

from bs4 import BeautifulSoup


def process_sgml_file(file_path):
    """
    Extracts document stats from given SGML file.

    Returns dict mapping number of segments n to list of document ids [ids].
    Each of the documents referenced by those ids contains the respective
    number of segments n.
    """
    soup = None

    with open(file_path) as _file:
        soup = BeautifulSoup(_file, features='lxml')

    all_docs = []
    stats = defaultdict(list)
    for doc in soup.find_all('doc'):
        doc_id = doc.attrs['docid']
        seg_count = len(doc.find_all('seg'))
        stats[seg_count].append(doc_id)
        all_docs.append(seg_count)

    curr_len = 0
    for doc in all_docs:
        if curr_len + doc > 100:
            print(curr_len)
            curr_len = 0
        curr_len += doc
    print(curr_len)

    return stats

if __name__ == "__main__":
    DOC_STATS = process_sgml_file(sys.argv[1])

    for k in sorted(DOC_STATS.keys()):
        v = DOC_STATS[k]
        for _ in range(0):
            DOC_STATS[k].extend(v)
        print(f'{k} \t {v}')

# /Users/cfedermann/Downloads/wmt19-submitted-data/sgm/sources

    seed(123456)
    curr_len = 0
    while len(DOC_STATS.keys()):
        all_keys = list(DOC_STATS.keys())
        max_delta = 100 - curr_len
        valid_keys = [x for x in all_keys if x <= max_delta]

        if not valid_keys:
            print(curr_len)
            curr_len = 0
            continue

        if max_delta in valid_keys:
            curr_key = max_delta
        else:
            shuffle(valid_keys)
            curr_key = valid_keys[0]

        curr_len += curr_key
        curr_val = DOC_STATS[curr_key].pop(0)
        if not DOC_STATS[curr_key]:
            DOC_STATS.pop(curr_key)
    
    raise ValueError

    all_docs = []
    for doc_len in sorted(DOC_STATS.keys()):
        for doc_id in DOC_STATS[doc_len]:
            all_docs.append((doc_len, doc_id))

    seed(123456)
    shuffle(all_docs)
    print(f'Identified {len(all_docs)} documents')

    tasks = []
    next_task = []
    next_len = 0
    for doc_len, doc_id in all_docs:
        if next_len + doc_len > 100:
            tasks.append(tuple(next_task))
            next_task = []
            next_len = 0

        next_task.append((doc_len, doc_id))
        next_len += doc_len

    for task in tasks:
        task_len = sum(x[0] for x in task)
        task_docs = len(task)
        task_ids = tuple(x[1] for x in task)
        print(f'{task_len:03d}: {task_docs}')
