# pylint: disable=C0103,C0111,C0330,E1101
import sys
from collections import defaultdict
from collections import OrderedDict
from glob import iglob
from json import dumps as json_dumps
from os.path import basename
from os.path import join
from random import choice
from random import seed
from random import shuffle
from typing import Any
from typing import Dict
from typing import List
from typing import Text
from typing import Tuple

from bs4 import BeautifulSoup  # type: ignore


MAX_TASK_SIZE = 100  # No support for tasks over 100 items
MAX_DOC_LENGTH = 70  # We do not support documents longer than 70 segments


def load_docs_from_sgml(
    file_path: str, encoding='utf-8'
) -> Dict[str, List[Tuple[str, str]]]:
    """
    Loads documents from given SGML file.

    Returns dict mapping document ids to list of segments [segments].
    Each segment is a tuple (segment id, segment text).
    """
    soup = None

    with open(file_path, encoding=encoding) as _file:
        soup = BeautifulSoup(_file, features='lxml')

    all_docs: Dict[str, List[Tuple[str, str]]] = OrderedDict()
    for curr_doc in soup.find_all('doc'):
        curr_doc_id = curr_doc.attrs['docid']
        if not curr_doc_id in all_docs:
            all_docs[curr_doc_id] = []

        for curr_seg in curr_doc.find_all('seg'):
            curr_seg_id = curr_seg.attrs['id']
            curr_seg_text = curr_seg.get_text()
            all_docs[curr_doc_id].append((curr_seg_id, curr_seg_text))

    return all_docs


def _create_bad_ref(seg_text: str, ref_text: str, character_based: bool = False) -> str:
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
        (20, None): 6,
    }

    bad_len = 0
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
        bad_pos = choice([x + 1 for x in range(seg_len - bad_len - 1)])

    ref_pos = 0
    if ref_len - bad_len > 0:
        ref_pos = choice(range(ref_len - bad_len))

    bad_data = (
        seg_data[:bad_pos]
        + ref_data[ref_pos : ref_pos + bad_len]
        + seg_data[bad_pos + bad_len :]
    )
    bad_text = ' '.join(bad_data)
    if character_based:
        bad_text = ''.join(bad_data)

    return bad_text


def create_bad_refs(
    docs: Dict[str, List[Tuple[str, str]]],
    refs: Dict[str, List[Tuple[str, str]]],
    character_based: bool = False,
) -> Dict[str, List[Tuple[str, str]]]:
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
    for curr_doc_id, curr_doc in refs.items():
        for curr_seg_id, curr_ref_text in curr_doc:
            all_refs[f'{curr_doc_id}_{curr_seg_id}'] = curr_ref_text

    # Create list of f'{doc_id}_{seg_id}' ids, to be used for random
    # choice later when we want to identify a reference to work with.
    all_keys = list(all_refs.keys())

    # Iterate through documents and create bad references.
    bad_docs: Dict[str, List[Tuple[str, str]]] = OrderedDict()
    for curr_doc_id, curr_doc in docs.items():
        if not curr_doc_id in bad_docs:
            bad_docs[curr_doc_id] = []

        print(f'doc_id: {curr_doc_id},\tdoc_len: {len(curr_doc)}')
        for curr_seg in curr_doc:
            curr_seg_id, curr_seg_text = curr_seg

            # Bad reference id may not be identical to current id.
            bad_id = choice(all_keys)
            while bad_id == f'{curr_doc_id}_{curr_seg_id}':
                bad_id = choice(all_keys)

            curr_bad_text = _create_bad_ref(
                curr_seg_text,
                all_refs[bad_id],
                character_based=character_based,
            )

            # Ensure that keys can be reused.
            all_keys.append(bad_id)

            bad_docs[curr_doc_id].append((curr_seg_id, curr_bad_text))

    return bad_docs


def process_sgml(file_path: str) -> Dict[int, List[str]]:
    """
    Extracts document stats from given SGML file.

    Returns dict mapping number of segments to list of document [ids].
    Each referenced document has the respective number of segments.
    """
    soup = None

    with open(file_path) as _file:
        soup = BeautifulSoup(_file, features='lxml')

    all_docs = []
    stats: Dict[int, List[str]] = defaultdict(list)
    for curr_doc in soup.find_all('doc'):
        curr_doc_id = curr_doc.attrs['docid']
        seg_count = len(curr_doc.find_all('seg'))
        stats[seg_count].append(curr_doc_id)
        all_docs.append(seg_count)

    curr_len = 0
    for doc in all_docs:
        if curr_len + doc > REQUIRED_SEGS:
            print(curr_len)
            curr_len = 0
        curr_len += doc
    print(curr_len)

    return stats


if __name__ == "__main__":
    SRC_SGML = sys.argv[1]  # Path to source .sgm file
    REF_SGML = sys.argv[2]  # Path to reference .sgm file
    SYS_PATH = sys.argv[3]  # Path to the directory with system outputs
    SYS_GLOB = sys.argv[4]  # Pattern for .sgm files, e.g '*.sgm'
    OUT_NAME = sys.argv[5]  # Prefix for .csv and .json output files
    SRC_LANG = sys.argv[6]  # Code for source language, e.g. eng
    TGT_LANG = sys.argv[7]  # Code for target language, e.g. deu
    TASK_MAX = int(sys.argv[8])  # Maximum number of tasks
    CONTROLS = sys.argv[9].lower() not in ['', '0', 'false', 'off']
    ENC = 'utf-8'

    RND_SEED = 123456
    seed(RND_SEED)

    print(f'Quality control={CONTROLS}')
    if CONTROLS:
        REQUIRED_SEGS = 80
    else:
        REQUIRED_SEGS = 100
    print(f'Setting REQUIRED_SEGS={REQUIRED_SEGS}')

    print(f'Loading source docs from {SRC_SGML}')
    SRC_DOCS = load_docs_from_sgml(SRC_SGML, encoding=ENC)
    print(f'Loading reference docs from {SRC_SGML}')
    REF_DOCS = load_docs_from_sgml(REF_SGML, encoding=ENC)

    SYS_DOCS: Dict[str, Dict[str, List[Tuple[str, str]]]] = {}
    BAD_DOCS: Dict[str, Dict[str, List[Tuple[str, str]]]] = {}
    for SYS_SGML in iglob(join(SYS_PATH, SYS_GLOB)):
        SYS_ID = basename(SYS_SGML)
        print(f'Loading outputs of {SYS_ID}')

        SYS_DOCS[SYS_ID] = load_docs_from_sgml(SYS_SGML, encoding=ENC)
        BAD_DOCS[SYS_ID] = create_bad_refs(SYS_DOCS[SYS_ID], REF_DOCS)

    # pylint: disable-msg=invalid-name
    some_sys_id = choice(list(SYS_DOCS.keys()))
    some_doc_id = choice(list(SYS_DOCS[some_sys_id].keys()))
    some_sys_text = SYS_DOCS[some_sys_id][some_doc_id]
    some_bad_text = BAD_DOCS[some_sys_id][some_doc_id]
    print(some_sys_id, some_doc_id)

    for _s, _b in zip(some_sys_text, some_bad_text):
        print(_s)
        print(_b)
        print('---')

    DOC_STATS: Dict[int, List[Tuple[int, str, str]]] = {}
    for sys_id in SYS_DOCS:
        for doc_id in SYS_DOCS[sys_id]:
            doc_len = len(SYS_DOCS[sys_id][doc_id])

            # We do not support documents longer than 70 segments.
            if doc_len > MAX_DOC_LENGTH:
                continue

            if not doc_len in DOC_STATS.keys():
                DOC_STATS[doc_len] = []

            DOC_STATS[doc_len].append((doc_len, doc_id, sys_id))

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

    all_systems = list(total_sys)
    sampled_tasks: List[Tuple[Tuple[int, str, str], ...]] = []
    CURR_LEN = 0
    CURR_SYS = 0
    curr_task: List[Tuple[int, str, str]] = []
    while DOC_STATS.keys():
        ALL_KEYS = list(DOC_STATS.keys())
        max_delta = REQUIRED_SEGS - CURR_LEN
        valid_keys = [x for x in ALL_KEYS if x <= max_delta]

        if not valid_keys:
            print(CURR_LEN)
            print(curr_task)
            print('------')
            sampled_tasks.append(tuple(curr_task))
            CURR_LEN = 0
            curr_task = []
            continue

        if max_delta in valid_keys:
            curr_key = max_delta
        else:
            curr_key = choice(valid_keys)

        CURR_LEN += curr_key

        curr_val = DOC_STATS[curr_key].pop(0)  # This takes a random system.

        # Below code would pick systems one after the other
        #
        # curr_val = None
        # for iter_val in DOC_STATS[curr_key]:
        #    if iter_val[2] == all_systems[CURR_SYS]:
        #        curr_val = iter_val
        #        DOC_STATS[curr_key].remove(iter_val)
        #        break
        #
        # if not curr_val:
        #    curr_val = DOC_STATS[curr_key].pop(0)
        #    CURR_SYS = all_systems.index(curr_val[2])
        # CURR_SYS = (CURR_SYS + 1) % len(all_systems)

        curr_task.append(curr_val)
        if not DOC_STATS[curr_key]:
            DOC_STATS.pop(curr_key)

    # Shuffle order of tasks
    shuffle(sampled_tasks)

    padded_tasks: List[Tuple[Tuple[int, str, str], ...]] = []
    for tid, task in enumerate(sampled_tasks):
        task_docs = len(task)
        task_len = sum([x[0] for x in task])
        print(f'task_len: {task_len}')
        if task_len > MAX_TASK_SIZE:
            raise NotImplementedError(
                'No support for tasks >{0} items!'.format(MAX_TASK_SIZE)
            )

        elif task_len < MAX_TASK_SIZE:
            pad_size = MAX_TASK_SIZE - task_len
            pad_data: List[Tuple[int, str, str]] = list(task)
            pad_pos = 0
            while pad_size > 0:
                print(f'pad_size: {pad_size}')
                print(f'pad_pos: {pad_pos}')
                pad_data.append(tuple(list(pad_data[pad_pos]) + [True]))  # type: ignore
                print(pad_data[-1])
                pad_size -= pad_data[-1][0]
                pad_pos = (pad_pos + 1) % task_docs
            if pad_size < 0:
                print(f'pad_size: {pad_size}')
                print(f'pad_pos: {pad_pos}')

                last_doc: Tuple[int, str, str] = pad_data[-1]
                print(last_doc[0], '-->', last_doc[0] + pad_size)
                fixed_doc = (last_doc[0] + pad_size, *last_doc[1:])
                pad_data[-1] = fixed_doc
                print(pad_data[-1][0])
            padded_tasks.append(tuple(pad_data))
            print(padded_tasks[-1])

        else:
            print(f'WARNING: no control items in task no. {tid}')
            # raise NotImplementedError('Needs isControl=True update!')
            padded_tasks.append(tuple(task))  # TODO: does this ever occur?

    csv_data = []
    task_id = 0
    for task in padded_tasks:
        task_id += 1
        task_len = sum([x[0] for x in task])
        print(f'task_len: {task_len}')

        for _doc in task:
            _data = [str(task_id)]
            for x in _doc:  # type: ignore
                _data.append(str(x))

            if _data[-1] != 'True':
                _data.append('False')  # isControl=False
            print(_data)
            csv_data.append(','.join(_data))

    with open(f'{OUT_NAME}.csv', mode='w') as _file:
        for csv_line in csv_data:
            _file.write(csv_line)
            _file.write('\n')

    json_data = []
    batch_id = 0
    for task in padded_tasks[:TASK_MAX]:
        # Remember, batch numbers are one-based
        task_data = OrderedDict(
            {
                'batchNo': batch_id + 1,
                'batchSize': 100,
                'sourceLanguage': SRC_LANG,
                'targetLanguage': TGT_LANG,
                'requiredAnnotations': 1,
                'randomSeed': RND_SEED,
            }
        )

        source_id = basename(SRC_SGML)

        items_data = []
        _item = 0
        for doc_data in task:
            doc_len, doc_id, sys_id, *rest = doc_data  # type: ignore

            isControl = rest is not None and rest

            target_id = sys_id

            _src = {}
            _ref = {}
            _bad = {}
            _tgt = {}

            for item_id, item_src in SRC_DOCS[doc_id]:
                seg_id = f'{doc_id}_{item_id}'
                _src[seg_id] = item_src

            for item_id, item_ref in REF_DOCS[doc_id]:
                seg_id = f'{doc_id}_{item_id}'
                _ref[seg_id] = item_ref

            for item_id, item_bad in BAD_DOCS[sys_id][doc_id]:
                seg_id = f'{doc_id}_{item_id}'
                _bad[seg_id] = item_bad

            for item_id, item_tgt in SYS_DOCS[sys_id][doc_id]:
                seg_id = f'{doc_id}_{item_id}'
                _tgt[seg_id] = item_tgt

            seg_counter = 0
            context_src: List[Text] = []
            context_ref: List[Text] = []
            context_bad: List[Text] = []
            context_tgt: List[Text] = []
            for seg_id in _src:
                if seg_counter >= doc_len:  # Padding tasks are shorter!
                    break
                item_src = _src[seg_id]
                item_ref = _ref[seg_id]
                item_bad = _bad[seg_id]
                item_tgt = _tgt[seg_id]

                target_text = item_tgt
                target_type = 'TGT'
                if (
                    CONTROLS and isControl
                ):  # Do not generate any BAD items if QC is disabled
                    randomCoinFlip = choice(
                        [False, False, True, True, True]
                    )  # 60:40 chance
                    if randomCoinFlip:
                        target_text = item_bad
                        target_type = 'BAD'

                obj: Dict[str, Any] = OrderedDict()
                obj['_item'] = _item
                obj['_block'] = -1
                obj['sourceID'] = source_id
                obj['sourceContextLeft'] = ' '.join(context_src)
                obj['sourceText'] = item_src
                obj['targetID'] = target_id
                obj['targetContextLeft'] = ' '.join(context_tgt)
                obj['targetText'] = target_text
                obj['itemID'] = seg_counter
                obj['itemType'] = target_type
                obj['documentID'] = doc_id
                obj['isCompleteDocument'] = False

                print(seg_id)
                print(' '.join(context_src))
                print(item_src)
                print('...')
                print(' '.join(context_tgt))
                print(item_tgt.encode('utf-8'))
                print('---')

                context_src.append(item_src)
                context_ref.append(item_ref)
                context_bad.append(item_bad)
                context_tgt.append(target_text)

                items_data.append(obj)
                _item += 1
                seg_counter += 1

            obj = OrderedDict()
            obj['_item'] = _item
            obj['_block'] = -1
            obj['sourceID'] = source_id
            obj['sourceText'] = ' '.join(context_src)  # full document
            obj['targetID'] = target_id
            obj['targetText'] = ' '.join(context_tgt)  # full document
            obj['itemID'] = item_id
            obj['itemType'] = 'TGT'
            obj['documentID'] = doc_id
            obj['isCompleteDocument'] = True
            items_data.append(obj)

        output_data = OrderedDict({'task': task_data, 'items': items_data})

        json_data.append(output_data)

        # write out JSON
        json_text = json_dumps(json_data, indent=2, sort_keys=True)

        json_file_name = f'{OUT_NAME}.json'
        with open(json_file_name, mode='w', encoding='utf8') as out_file:
            sys.stdout.write('Creating {0} ... '.format(json_file_name, ending=''))  # type: ignore
            out_file.write(str(json_text))
            sys.stdout.write('OK\n')

        batch_id += 1

    print(f'Total tasks: {len(sampled_tasks)}')
    print(f'Total docs:  {total_docs}')
    print(f'Total sys:   {len(total_sys)} {total_sys}')
