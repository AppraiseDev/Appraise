import sys

from collections import defaultdict, OrderedDict
from glob import iglob
from os.path import basename, join
from random import choice, seed, shuffle

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
        if not left:
            if seg_len == right:
                bad_len = _seg_to_bad_mapping[seg_pair]
                break

        # left < seg_len; right edge case
        elif not right:
            if left < seg_len:
                bad_len = _seg_to_bad_mapping[seg_pair]
                break

        # left < seg_len <= right; middle cases
        elif left < seg_len <= right:
            bad_len = _seg_to_bad_mapping[seg_pair]
            break

    # Double length of bad phrase for character-based languages.
    if character_based:
        bad_len = 2 * bad_len

    # Determine random replacement position. For segments longer than
    # (bad_len + 1), we enforce that this cannot be sentence initial
    # or final, so positions 0 and (seg_len - bad_len -1) are invalid
    # and we use an embedded bad_pos in [1, (seg_len - bad_len - 1)].
    # This happens for all seg_len > 3.
    bad_pos = 0
    if seg_len - bad_len > 0:
        bad_pos = choice(range(seg_len - bad_len))

    elif seg_len > 3:
        bad_pos = choice([x+1 for x in range(seg_len-bad_len-1)])

    ref_pos = 0
    if ref_len - bad_len > 0:
        ref_pos = choice(range(ref_len - bad_len))

    bad_data = (
        seg_data[:bad_pos] +
        ref_data[ref_pos:ref_pos+bad_len] +
        seg_data[bad_pos+bad_len:]
    )
    bad_text = ' '.join(bad_data)
    if character_based:
        bad_text = ''.join(bad_data)

    return bad_text


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

    # Create list of f'{doc_id}_{seg_id}' ids, to be used for random
    # choice later when we want to identify a reference to work with.
    all_keys = list(all_refs.keys())

    # Iterate through documents and create bad references.
    bad_docs = OrderedDict()
    for doc_id, doc in docs.items():
        if not doc_id in bad_docs:
            bad_docs[doc_id] = []

        print(f'doc_id: {doc_id},\tdoc_len: {len(doc)}')
        for seg in doc:
            seg_id, seg_text = seg

            # Bad reference id may not be identical to current id.
            bad_id = choice(all_keys)
            while bad_id == f'{doc_id}_{seg_id}':
                bad_id = choice(all_keys)

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
    OUT_NAME = sys.argv[5]
    SRC_LANG = sys.argv[6]
    TGT_LANG = sys.argv[7]
    ENC = 'utf-8'

    RND_SEED = 123456
    seed(RND_SEED)

    ALL_DOCS = {}
    ALL_DOCS['SRC'] = load_docs_from_sgml_file(SRC_SGML, encoding=ENC)
    ALL_DOCS['REF'] = load_docs_from_sgml_file(REF_SGML, encoding=ENC)

    ALL_DOCS['SYS'] = {}
    ALL_DOCS['BAD'] = {}
    for SYS_SGML in iglob(join(SYS_PATH, SYS_GLOB)):
        SYS_ID = basename(SYS_SGML)
        ALL_DOCS['SYS'][SYS_ID] = (
            load_docs_from_sgml_file(SYS_SGML, encoding=ENC)
        )

        ALL_DOCS['BAD'][SYS_ID] = (
            create_bad_refs(ALL_DOCS['SYS'][SYS_ID], ALL_DOCS['REF'])
        )

    # pylint: disable-msg=invalid-name
    some_doc_id = choice(list(ALL_DOCS['SYS'].keys()))
    some_seg_id = choice(list(ALL_DOCS['SYS'][some_doc_id].keys()))
    some_sys_text = ALL_DOCS['SYS'][some_doc_id][some_seg_id]
    some_bad_text = ALL_DOCS['BAD'][some_doc_id][some_seg_id]
    print(some_doc_id, some_seg_id)

    for _s, _b in zip(some_sys_text, some_bad_text):
        print(_s)
        print(_b)
        print('---')

    DOC_STATS = {}
    for sys_id in ALL_DOCS['SYS']:
        for doc_id in ALL_DOCS['SYS'][sys_id]:
            doc_len = len(ALL_DOCS['SYS'][sys_id][doc_id])

            # We do not support documents longer than 70 segments.
            if doc_len > 70:
                continue

            if not doc_len in DOC_STATS.keys():
                DOC_STATS[doc_len] = []

            DOC_STATS[doc_len].append(
                (doc_len, doc_id, sys_id)
            )

    # Randomise system order
    for doc_len in DOC_STATS:
        shuffle(DOC_STATS[doc_len])

    print(sorted(DOC_STATS.keys()))
    total_docs = 0
    total_sys = set()
    for doc_len in sorted(DOC_STATS.keys()):
        print(f'{doc_len}:\t{len(DOC_STATS[doc_len])}')
        total_docs += len(DOC_STATS[doc_len])
        for x in DOC_STATS[doc_len]:
            total_sys.add(x[2])
        #print([f'{x[1]}_{x[2]}' for x in DOC_STATS[doc_len]])

    
    sampled_tasks = []
    curr_len = 0
    curr_task = []
    while DOC_STATS.keys():
        all_keys = list(DOC_STATS.keys())
        max_delta = 100 - curr_len
        valid_keys = [x for x in all_keys if x <= max_delta]

        if not valid_keys:
            print(curr_len)
            print(curr_task)
            print('------')
            sampled_tasks.append(tuple(curr_task))
            curr_len = 0
            curr_task = []
            continue

        if max_delta in valid_keys:
            curr_key = max_delta
        else:
            curr_key = choice(valid_keys)

        curr_len += curr_key
        curr_val = DOC_STATS[curr_key].pop(0)
        curr_task.append(curr_val)
        if not DOC_STATS[curr_key]:
            DOC_STATS.pop(curr_key)

    # Shuffle order of tasks
    shuffle(sampled_tasks)

    from time import sleep
    padded_tasks = []
    for task in sampled_tasks:
        task_docs = len(task)
        task_len = sum([x[0] for x in task])
        print(f'task_len: {task_len}')
        if task_len > 100:
            raise NotImplementedError('No support for tasks >100 items!')
        elif task_len < 100:
            pad_size = 100 - task_len
            pad_data = list(task)
            pad_pos = 0
            while pad_size > 0:
                print(f'pad_size: {pad_size}')
                print(f'pad_pos: {pad_pos}')
                pad_data.append(pad_data[pad_pos])
                pad_size -= pad_data[-1][0]
                pad_pos = (pad_pos + 1) % task_docs
            if pad_size < 0:
                print(f'pad_size: {pad_size}')
                print(f'pad_pos: {pad_pos}')

                last_doc = list(pad_data[-1])
                print(last_doc[0], '-->', last_doc[0]+pad_size)
                last_doc[0] += pad_size
                pad_data[-1] = tuple(last_doc)
                print(pad_data[-1])
            padded_tasks.append(pad_data)
            print(padded_tasks[-1])
            #sleep(1)
        else:
            padded_tasks.append(task)

    csv_data = []
    task_id = 0
    for task in padded_tasks:
        task_id += 1
        task_len = sum([x[0] for x in task])
        print(f'task_len: {task_len}')

        for doc in task:
            csv_data.append(','.join([str(task_id)] + [str(x) for x in doc]))

    with open(f'{OUT_NAME}.csv', mode='w') as _file:
        for csv_line in csv_data:
            _file.write(csv_line)
            _file.write('\n')

    json_data = []
    batch_id = 0
    for task in padded_tasks[:1]:
        # Remember, batch numbers are one-based
        task_data = OrderedDict({
          'batchNo': batch_id+1,
          'batchSize': 100,
          'sourceLanguage': SRC_LANG,
          'targetLanguage': TGT_LANG,
          'requiredAnnotations': 1,
          'randomSeed': RND_SEED,
        })

        source_id = basename(SRC_SGML)

        items_data = []
        _item = 0
        for doc_data in task:
            doc_len, doc_id, sys_id = doc_data

            target_id = sys_id

            _src = {}
            _ref = {}
            _bad = {}
            _tgt = {}

            for item_id, item_src in ALL_DOCS['SRC'][doc_id]:
                seg_id = f'{doc_id}_{item_id}'
                _src[seg_id] = item_src

            for item_id, item_ref in ALL_DOCS['REF'][doc_id]:
                seg_id = f'{doc_id}_{item_id}'
                _ref[seg_id] = item_ref

            for item_id, item_bad in ALL_DOCS['BAD'][sys_id][doc_id]:
                seg_id = f'{doc_id}_{item_id}'
                _bad[seg_id] = item_bad

            for item_id, item_tgt in ALL_DOCS['SYS'][sys_id][doc_id]:
                seg_id = f'{doc_id}_{item_id}'
                _tgt[seg_id] = item_tgt

            item_id = 0
            context_src = []
            context_ref = []
            context_bad = []
            context_tgt = []
            for seg_id in _src.keys():
                item_src = _src[seg_id]
                item_ref = _ref[seg_id]
                item_bad = _bad[seg_id]
                item_tgt = _tgt[seg_id]

                obj = OrderedDict()
                obj['_item'] = _item
                obj['_block'] = -1
                obj['sourceID'] = source_id
                obj['sourceContextLeft'] = ' '.join(context_src)
                obj['sourceText'] = item_src
                obj['targetID'] = target_id
                obj['targetContextLeft'] = ' '.join(context_tgt)
                obj['targetText'] = item_tgt
                obj['itemID'] = item_id
                obj['itemType'] = 'TGT'
                obj['documentID'] = doc_id
                obj['isCompleteDocument'] = False

                print(seg_id)
                print(' '.join(context_src))
                print(item_src)
                print('...')
                print(' '.join(context_tgt))
                print(item_tgt)
                print('---')

                context_src.append(item_src)
                context_ref.append(item_ref)
                context_bad.append(item_bad)
                context_tgt.append(item_tgt)

                items_data.append(obj)
                _item += 1
                item_id += 1

            obj = OrderedDict()
            obj['_item'] = _item
            obj['_block'] = -1
            obj['sourceID'] = source_id
            obj['sourceText'] = ' '.join(context_src) # full document
            obj['targetID'] = target_id
            obj['targetText'] = ' '.join(context_tgt) # full document
            obj['itemID'] = item_id
            obj['itemType'] = 'TGT'
            obj['documentID'] = doc_id
            obj['isCompleteDocument'] = True
            items_data.append(obj)

        output_data = OrderedDict({
            'task': task_data,
            'items': items_data
        })

        json_data.append(output_data)

        # write out JSON
        import json
        json_data = json.dumps(json_data, indent=2, sort_keys=True)
        #print(json_data)

        json_file_name = f'{OUT_NAME}.json'
        with open(json_file_name, mode='w', encoding='utf8') as out_file:
            sys.stdout.write('Creating {0} ... '.format(
                json_file_name, ending=''))
            out_file.write(str(json_data))
            sys.stdout.write('OK\n')

        batch_id += 1

    print(f'Total tasks: {len(sampled_tasks)}')
    print(f'Total docs:  {total_docs}')
    print(f'Total sys:   {len(total_sys)} {total_sys}')
