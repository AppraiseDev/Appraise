import sys

from collections import defaultdict, OrderedDict
from glob import iglob
from os.path import basename, join
from random import seed, shuffle

from bs4 import BeautifulSoup

def load_docs_from_sgml_file(file_path, encoding='utf-8'):
    """
    Loads documents from given SGML file.

    Returns dict mapping document ids to list of segments [segments].
    """
    soup = None

    with open(file_path, encoding=encoding) as _file:
        soup = BeautifulSoup(_file, features='lxml')

    all_docs = OrderedDict()
    for doc in soup.find_all('doc'):
        doc_id = doc.attrs['docid']
        if not doc_id in all_docs:
            all_docs[doc_id] = []

        for seg in doc.find_all('seg'):
            seg_id = seg.attrs['id']
            seg_text = seg.get_text()
            all_docs[doc_id].append(
                (seg_id, seg_text)
            )

    return all_docs


def _create_bad_ref(seg_text, ref_text, character_based=False):
    """
    Creates bad reference for given text.

    Segment length (a, b] to phrase length (excluding a, including b)
    mapping defined as follows:
        ( 0,   1] : 1
        ( 1,   5] : 2
        ( 5,   8] : 3
        ( 8,  15] : 4
        (15,  20] : 5
        (20, max] : 6

    For character-based languages, which do not support tokenisation
    by whitespace, the resulting phrase length will be doubled, and
    is interpreted as a character length.
    """
    seg_data = seg_text.split(' ')
    ref_data = ref_text.split(' ')

    if character_based:
        seg_data = [x for x in seg_text]
        ref_data = [x for x in ref_text]

    seg_len = len(seg_data)
    ref_len = len(ref_data)

    # Determine length of bad phrase, relative to segment length.
    _seg_to_bad_mapping = {
        (None, 1): 1,
        (1, 5): 2,
        (5, 8): 3,
        (8, 15): 4,
        (15, 20): 5,
        (20, None): 6
    }

    bad_len = None
    for seg_pair in _seg_to_bad_mapping:
        left, right = seg_pair

        # seg_len == right; left edge case
        if not left and seg_len == right:
            bad_len = _seg_to_bad_mapping[seg_pair]
            break

        # left < seg_len; right edge case
        if not right and left < seg_len:
            bad_len = _seg_to_bad_mapping[seg_pair]
            break

        # left < seg_len <= right; middle cases
        if left < seg_len and seg_len <= right:
            bad_len = _seg_to_bad_mapping[seg_pair]
            break

#    if seg_len == 1:
#        bad_len = 1
#    elif seg_len > 1 and seg_len <= 5:
#        bad_len = 2
#    elif seg_len > 5 and seg_len <= 8:
#        bad_len = 3
#    elif seg_len > 8 and seg_len <= 15:
#        bad_len = 4
#    elif seg_len > 15 and seg_len <= 20:
#        bad_len = 5
#    elif seg_len > 20:
#        bad_len = 6

    # Double length of bad phrase for character-based languages.
    if character_based:
        bad_len = 2 * bad_len

    raise NotImplementedError('Finish implementation of bad refs')


def create_bad_refs(docs, refs, character_based=False):
    """
    Creates bad references for given documents.

    For each segment in the given documents, this creates a so-called
    ``bad reference'' which is constructed by replacing an embedded
    phrase p with a randomly placed phrase p' of the same length,
    taken from a different segment contained in refs. The length of
    the phrase is relative to the full segment length.

    See _create_bad_ref() definition for length mapping details.
    """
    # Create mapping from f'{doc_id}_{seg_id}' to reference text.
    all_refs = {}
    for doc_id, doc in refs.items():
        for seg_id, ref_text in doc:
            all_refs[f'{doc_id}_{seg_id}'] = ref_text

    # Create randomized list of f'{doc_id}_{seg_id}' ids.
    all_keys = [x for x in all_refs]
    shuffle(all_keys)

    # Iterate through documents and create bad references.
    bad_docs = OrderedDict()
    for doc_id, doc in docs.items():
        if not doc_id in bad_docs:
            bad_docs[doc_id] = []

        for seg in doc:
            seg_id, seg_text = seg

            bad_id = all_keys.pop(0)
            while bad_id == f'{doc_id}_{seg_id}':
                all_keys.append(bad_id)

            bad_text = _create_bad_ref(
                seg_text, all_refs[bad_id],
                character_based=character_based)

            # Ensure that keys can be reused.
            all_keys.append(bad_id)

            bad_docs[doc_id].append(
                (seg_id, bad_text)
            )

    return bad_docs


def process_sgml_file(file_path):
    """
    Extracts document stats from given SGML file.

    Returns dict mapping number of segments to list of document [ids].
    Each referenced document has the respective number of segments.
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
    SRC_SGML = sys.argv[1]
    REF_SGML = sys.argv[2]
    SYS_PATH = sys.argv[3]
    SYS_GLOB = sys.argv[4]
    ENC = 'utf-8'

    ALL_DOCS = {}
    ALL_DOCS['SRC'] = load_docs_from_sgml_file(SRC_SGML, encoding=ENC)
    ALL_DOCS['REF'] = load_docs_from_sgml_file(REF_SGML, encoding=ENC)

    ALL_DOCS['SYS'] = {}
    for SYS_SGML in iglob(join(SYS_PATH, SYS_GLOB)):
        SYS_ID = basename(SYS_SGML)
        ALL_DOCS['SYS'][SYS_ID] = (
            load_docs_from_sgml_file(SYS_SGML, encoding=ENC)
        )

        ALL_DOCS['BAD'][SYS_ID] = (
            create_bad_refs(ALL_DOCS['SYS'][SYS_ID], ALL_DOCS['REF'])
        )

    DOC_STATS = process_sgml_file(sys.argv[1])

    for k in sorted(DOC_STATS.keys()):
        v = DOC_STATS[k]
        for _ in range(0):
            DOC_STATS[k].extend(v)
        print(f'{k} \t {v}')

# /Users/cfedermann/Downloads/wmt19-submitted-data/sgm/sources

    seed(123456)
    curr_len = 0
    while DOC_STATS.keys():
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
