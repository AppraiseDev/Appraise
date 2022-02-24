# pylint: disable=C0103,C0111,C0330,E1101
import sys
from collections import defaultdict
from collections import OrderedDict
from glob import iglob
from json import dumps as json_dumps
from os.path import basename
from os.path import join
from random import choice
from random import randint
from random import seed
from random import shuffle
from typing import Any
from typing import Dict
from typing import List
from typing import Text
from typing import Tuple

from lxml import etree


MAX_TASK_SIZE = 100  # No support for tasks over 100 items
MAX_DOC_LENGTH = 70  # We do not support documents longer than 70 segments

MISSING_TRANSLATION_MESSAGE = ("NO TRANSLATION AVAILABLE",)
DEFAULT_TRANSLATOR = "DEFAULT"
# If False, documents with control items will be very last ones in each batch
SHUFFLE_DOCS_WITH_CONTROL_ITEMS = True
# If True, add references as additional system outputs
INCLUDE_REFERENCES_AS_SYSTEMS = True
REFERENCE_AS_SYSTEM_PREFIX = 'translator-'


def unwrap_xml(
    xml_file,
    missing_message=MISSING_TRANSLATION_MESSAGE,
    encoding='utf-8',
):
    """
    Unwraps an xml file in WMT format, producing source and (if present) reference files

    :param xml_file: The xml file (or fd)
    :param missing_message: The message to insert when no reference

    :returns: src_lang, src_lines, ref_lang, ref_lines, hyp_lang, hyp_lines

    ref_lines maps translator to document to tuples of segment id and line text
    hyp_lines maps system to document to tuples of segment id and line text

    ref_lang and hyp_lang may be None, and then their lines are empty
    note: a single language is assumed for each of sources, refs and hyps

    This function has been extracted from
    https://github.com/wmt-conference/wmt-format-tools/wmtformat/unwrap.py with
    some modifications
    """
    tree = etree.parse(xml_file)

    # Find and check  the documents (src, ref, hyp)
    src_langs, ref_langs, hyp_langs, translators, systems = (
        set(),
        set(),
        set(),
        set(),
        set(),
    )

    for src_doc in tree.getroot().findall(".//src"):
        src_langs.add(src_doc.get("lang"))

    for ref_doc in tree.getroot().findall(".//ref"):
        ref_langs.add(ref_doc.get("lang"))
        translator = ref_doc.get("translator")
        if translator:
            translators.add(translator)

    for hyp_doc in tree.getroot().findall(".//hyp"):
        hyp_langs.add(hyp_doc.get("lang"))
        systems.add(hyp_doc.get("system"))

    if len(src_langs) > 1:
        raise RuntimeError("Multiple source languages found")

    if len(src_langs) == 0:
        raise RuntimeError("No source languages found")

    src_lang = src_langs.pop()
    src_docs = OrderedDict()

    if len(ref_langs) > 1:
        raise RuntimeError("Multiple reference languages found")

    translators = list(translators)
    if len(ref_langs) > 0:
        if len(translators) == 0:
            print("No translator identifiers found")
            translators.append(DEFAULT_TRANSLATOR)
        ref_lang = ref_langs.pop()
        ref_docs = OrderedDict(
            (translator, OrderedDict()) for translator in translators
        )
    else:
        print("No references found")
        ref_lang = None
        ref_docs = OrderedDict()

    if len(hyp_langs) > 1:
        raise RuntimeError("Multiple hypothesis languages found")

    systems = list(systems)
    if len(hyp_langs) > 0:
        hyp_docs = OrderedDict((system, OrderedDict()) for system in systems)
        hyp_lang = hyp_langs.pop()
    else:
        hyp_docs = OrderedDict()
        hyp_lang = None

    # Extract text
    src_sent_count, doc_count = 0, 0
    for doc in tree.getroot().findall(".//doc"):
        doc_id = doc.get("id")
        src = []
        if "testsuite" in doc.attrib:
            continue
        doc_count += 1
        src_sents = {int(seg.get("id")): seg.text for seg in doc.findall(".//src//seg")}

        def get_sents(doc):
            return {
                int(seg.get("id")): seg.text if seg.text else ""
                for seg in doc.findall(f".//seg")
            }

        if ref_lang:
            _ref_docs = doc.findall(".//ref")
            trans_to_ref = {}

            # If no translator identifiers, we just read one reference (if any)
            # If there are translator identifiers, we add a reference for each translator
            if len(translators) == 1 and DEFAULT_TRANSLATOR in translators:
                if len(_ref_docs):
                    trans_to_ref[DEFAULT_TRANSLATOR] = get_ref_sents(_ref_docs[0])
                else:
                    trans_to_ref[DEFAULT_TRANSLATOR] = {}
            else:
                trans_to_ref = {
                    ref_doc.get("translator"): get_sents(ref_doc)
                    for ref_doc in _ref_docs
                }

        if hyp_lang:
            _hyp_docs = doc.findall(".//hyp")
            system_to_ref = {
                hyp_doc.get("system"): get_sents(hyp_doc) for hyp_doc in _hyp_docs
            }

        for seg_id in sorted(src_sents.keys()):
            src.append([seg_id, src_sents[seg_id]])
            src_sent_count += 1
            if ref_lang:
                for translator in translators:
                    if doc_id not in ref_docs[translator]:
                        ref_docs[translator][doc_id] = []

                    # _ref_text = trans_to_ref.get(translator, {translator: {}}).get(
                    _ref_text = trans_to_ref[translator].get(seg_id, missing_message)
                    ref_docs[translator][doc_id].append((seg_id, _ref_text))

                    if _ref_text == MISSING_TRANSLATION_MESSAGE:
                        print(
                            f'Warning: missing reference for translator {translator}, '
                            f'document {doc_id}, segment {seg_id}'
                        )
            if hyp_lang:
                for system in systems:
                    if doc_id not in hyp_docs[system]:
                        hyp_docs[system][doc_id] = []

                    # _hyp_text = system_to_ref.get(system, {system: {}}).get(
                    _hyp_text = system_to_ref[system].get(seg_id, missing_message)
                    hyp_docs[system][doc_id].append((seg_id, _hyp_text))

                    if _hyp_text == MISSING_TRANSLATION_MESSAGE:
                        print(
                            f'Warning: missing translation from {system}, '
                            f'document {doc_id}, segment {seg_id}'
                        )

        src_docs[doc_id] = src

    print(
        f"Extracted {doc_count} document(s) containing {src_sent_count} sentences in {src_lang}"
    )

    return src_lang, src_docs, ref_lang, ref_docs, hyp_lang, hyp_docs


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
        _xs = max(1, seg_len - bad_len - 1)
        bad_pos = choice([x + 1 for x in range(_xs)])

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

    # print(seg_text)
    # print(bad_text)
    # print('------------')
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


if __name__ == "__main__":
    if len(sys.argv) < 8:
        print('Example usage:')
        print(
            f'  {sys.argv[0]} newstest2021.en-de.all.xml batches.en-de enu deu 50 True False'
        )
        exit()

    XML_FILE = sys.argv[1]  # Path to .xml file with sources, references and outputs
    OUT_NAME = sys.argv[2]  # Prefix for .csv and .json output files
    SRC_LANG = sys.argv[3]  # Code for source language, e.g. eng
    TGT_LANG = sys.argv[4]  # Code for target language, e.g. deu
    TASK_MAX = int(sys.argv[5])  # Maximum number of tasks
    CONTROLS = sys.argv[6].lower() not in ['', '0', 'false', 'off']  # Generate QC items
    CHARLANG = sys.argv[7].lower() in ['1', 'true', 'on']  # Character-based
    print(f'Character based={CHARLANG}')

    ENC = 'utf-8'

    RND_SEED = 123456
    seed(RND_SEED)

    print(f'Quality control={CONTROLS}')
    if CONTROLS:
        REQUIRED_SEGS = 80
    else:
        REQUIRED_SEGS = 100
    print(f'Setting REQUIRED_SEGS={REQUIRED_SEGS}')

    SYS_DOCS: Dict[str, Dict[str, List[Tuple[str, str]]]] = OrderedDict()
    BAD_DOCS: Dict[str, Dict[str, List[Tuple[str, str]]]] = OrderedDict()
    print(f'Loading docs from {XML_FILE}')
    src_lang, SRC_DOCS, ref_lang, REF_DOCS, hyp_lang, SYS_DOCS = unwrap_xml(
        XML_FILE, encoding=ENC
    )

    # This reference will be used for generating BAD items
    REF_ID = sorted(list(REF_DOCS.keys()))[0]
    print(f'Using reference "{REF_ID}"')

    # Add references as additional system outputs
    if INCLUDE_REFERENCES_AS_SYSTEMS:
        for ref_id in sorted(list(REF_DOCS.keys())):
            sys_id = REFERENCE_AS_SYSTEM_PREFIX + ref_id
            print(f'Adding reference "{ref_id}" as system output "{sys_id}"')
            SYS_DOCS[sys_id] = REF_DOCS[ref_id]

    # List of system names that can be iterated deterministically
    SYS_IDS = sorted(list(SYS_DOCS.keys()))

    for sys_id in SYS_IDS:
        print(f'Generating bad references for {sys_id}')
        BAD_DOCS[sys_id] = create_bad_refs(
            SYS_DOCS[sys_id], REF_DOCS[REF_ID], character_based=CHARLANG
        )

    # pylint: disable-msg=invalid-name
    some_sys_id = choice(SYS_IDS)
    some_doc_id = choice(sorted(list(SYS_DOCS[some_sys_id].keys())))
    some_sys_text = SYS_DOCS[some_sys_id][some_doc_id]
    some_bad_text = BAD_DOCS[some_sys_id][some_doc_id]
    print(some_sys_id, some_doc_id)

    for _s, _b in zip(some_sys_text, some_bad_text):
        print(_s)
        print(_b)
        print('---')

    DOC_STATS: Dict[int, List[Tuple[int, str, str]]] = OrderedDict()
    for sys_id in SYS_IDS:
        for doc_id in SYS_DOCS[sys_id].keys():
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

    print(DOC_STATS.keys())
    total_docs = 0
    total_sys = set()
    for doc_len in DOC_STATS.keys():
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
        ALL_KEYS = sorted(list(DOC_STATS.keys()))
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

        source_id = basename(XML_FILE)

        items_data: List[List[Dict[str, Any]]] = []  # Keeps items grouped into document
        _item = 0
        doc_counter = 0
        for doc_data in task:
            items_data.append([])  # Add a new bucket for items from this documents
            has_control_item = False

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

            for item_id, item_ref in REF_DOCS[REF_ID][doc_id]:
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

                # Do not generate any BAD items if QC is disabled
                if CONTROLS and isControl:
                    randomCoinFlip = choice(
                        [False, False, True, True, True]  # 60:40 chance
                    )
                    if randomCoinFlip:
                        target_text = item_bad
                        target_type = 'BAD'
                        has_control_item = True

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

                # print(seg_id)
                # print(' '.join(context_src))
                # print(item_src)
                # print('...')
                # print(' '.join(context_tgt))
                # print(item_tgt.encode('utf-8'))
                # print('---')

                context_src.append(item_src)
                context_ref.append(item_ref)
                context_bad.append(item_bad)
                context_tgt.append(target_text)

                items_data[-1].append(obj)
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
            items_data[-1].append(obj)

            if has_control_item and SHUFFLE_DOCS_WITH_CONTROL_ITEMS:
                # Move the document with control items to a random position so
                # that they are not accumulated as very last documents
                _bad_doc = items_data.pop()
                _pos = randint(0, len(items_data) - 1)
                print(f'  Moving the last QC document to position {_pos}')
                items_data.insert(_pos, _bad_doc)

        # Extract items from documents
        _items_data = [item for doc_items in items_data for item in doc_items]
        # Re-assign _item numbers
        if SHUFFLE_DOCS_WITH_CONTROL_ITEMS:
            _item = 0
            for i in range(len(_items_data)):
                _items_data[i]['_item'] = _item
                if _items_data[i]['isCompleteDocument'] == False:
                    _item += 1

        output_data = OrderedDict({'task': task_data, 'items': _items_data})

        json_data.append(output_data)

        # write out JSON
        json_text = json_dumps(json_data, indent=2, sort_keys=True)

        json_file_name = f'{OUT_NAME}.json'
        with open(json_file_name, mode='w', encoding='utf8') as out_file:
            sys.stdout.write(
                'Creating {0}, batch no. {1} ... '.format(json_file_name, batch_id + 1),
            )
            out_file.write(str(json_text))
            sys.stdout.write('OK\n')

        batch_id += 1

    print(f'Total tasks: {len(sampled_tasks)}')
    print(f'Total docs:  {total_docs}')
    print(f'Total sys:   {len(total_sys)} {sorted(list(total_sys))}')
