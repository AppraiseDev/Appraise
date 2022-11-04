import argparse
from collections import defaultdict
from functools import cmp_to_key
from random import shuffle
import numpy as np


LANGUAGE_CODES = {
    'eng': 'en',
    'deu': 'de',
    'ces': 'cs',
    'fra': 'fr',
    'isl': 'is',
    'zho': 'zh',
    'hau': 'ha',
    'jpn': 'ja',
    'rus': 'ru',
    'aeb': 'ae',
    'spa': 'es',
    'sgg': 'dsgs',
}

REPLACE_SYSTEM_NAMES = [
    ('translator-A', 'HUMAN'),
    ('dfki', 'DFKI-SLT'),
    ('UZH-test', 'UZH (baseline)'),
]


def compute_mean(sample):
    """Computes sample mean"""
    return sum(sample) / float(len(sample) or 1)


def permutation_test(pooled, a_size, b_size):
    shuffle(pooled)
    new_a = pooled[:a_size]
    new_b = pooled[-b_size:]
    mean_a = compute_mean(new_a)
    mean_b = compute_mean(new_b)
    return mean_a - mean_b


def permutation_test2(setA, setB):
    # print(len(setA), len(setB))
    new_a, new_b = myshuffle(setA, setB)
    mean_a = compute_mean(new_a)
    mean_b = compute_mean(new_b)
    t_sim = abs(mean_a - mean_b)
    # print(t_sim, mean_a, mean_b)
    return t_sim


def myshuffle(setA, setB):
    new_a = []
    new_b = []
    for i in range(len(setA)):
        coin = np.random.choice(2)
        if coin == 0:
            new_a.append(setA[i])
            new_b.append(setB[i])
        else:
            new_a.append(setB[i])
            new_b.append(setA[i])

    return (new_a, new_b)


def ar(setA, setB, trials=1000, alpha=0.1):
    mean_a = compute_mean(setA)
    mean_b = compute_mean(setB)
    t_obs = abs(mean_a - mean_b)

    # print("T_OBS: {0}".format(t_obs))

    # pooled = setA + setB

    inf = 0
    sup = 0
    by_chance = 0
    t_sims = []

    for _ in range(trials):
        t_sim = permutation_test2(setA, setB)

        if t_sim >= t_obs:
            by_chance += 1
        t_sims.append(t_sim)

    #        if t_sim<t_obs:
    #            inf = inf + 1
    #        elif t_sim>t_obs:
    #            sup = sup + 1
    #
    #    inf = inf / float(trials)
    #    sup = sup / float(trials)
    #
    #    p_value = round(min(inf, sup), 3)
    # print(sum(t_sims) / float(trials))
    p_value = float(by_chance + 1) / float(trials + 1)
    return t_obs, p_value


# pylint: disable=C0111,C0330,E1101
def filter_zero_scored_segments(language_data, excluded_systems, options):
    """
    Remove all evaluation items that have been zero for all systems
    :param exclude_systems: the ids of the systems that will be excluded from the filter
    :param language_data: all evaluation rows
    :param options: commandline parameters
    :return: the filtered data
    """
    segment_ids_filter = set()
    summed_score_by_segment = defaultdict(int)
    for row in language_data:
        system_id = row[1]

        # don't check if the system needs to be excluded
        if system_id in excluded_systems:
            continue
        if options['task_type'] == 'Document':
            segment_id = row[2] + ':' + row[7]
        else:
            segment_id = row[2]
        raw_score = row[6]
        summed_score_by_segment[segment_id] += raw_score

    for segment_id, summed_score in summed_score_by_segment.items():
        if summed_score == 0:
            segment_ids_filter.add(segment_id)

    print(f"The segment_ids were reduced from {len(summed_score_by_segment.keys())} to {len(summed_score_by_segment.keys()) - len(segment_ids_filter)} ")

    print("The following IDs were excluded: ", segment_ids_filter)

    filtered_language_data = []
    for row in language_data:
        if options['task_type'] == 'Document':
            segment_id = row[2] + ':' + row[7]
        else:
            segment_id = row[2]
        if segment_id not in segment_ids_filter:
            filtered_language_data.append(row)

    print(f"The items were reduced from {len(language_data)} to {len(filtered_language_data)}")

    return filtered_language_data


def get_data_by_domain(language_data):
    data_by_domain = defaultdict(list)
    for row in language_data:
        document_id = row[7]
        try:
            domain_id = document_id.split(".")[0]
            data_by_domain[domain_id].append(row)
        except IndexError:
            pass
    return data_by_domain


def reformat_system_id(systemID):
    for old_name, new_name in REPLACE_SYSTEM_NAMES:
        systemID = systemID.replace(old_name, new_name)
        systemID = systemID[:51].replace('_', '\_')
    return systemID


def add_arguments(parser):
    parser.add_argument(
        'campaign_name',
        type=str,
        help='Name of the campaign you want to process data for',
    )
    parser.add_argument(
        '--completed-only',
        action='store_true',
        help='Include completed tasks only in the computation',
    )
    parser.add_argument(
        '--csv-file',
        type=str,
        help='CSV file containing annotation data',
    )
    parser.add_argument(
        '--exclude-ids',
        type=str,
        help='User IDs which should be ignored',
    )
    parser.add_argument(
        '--task-type',
        type=str,
        default='Direct',
        help='Task type, e.g. Document, default: Direct',
    )
    parser.add_argument(
        '--no-sigtest',
        action='store_true',
        help='Do not run significance testing',
    )
    parser.add_argument(
        '--show-p-values',
        action='store_true',
        help='Show p-values for significance testing',
    )
    parser.add_argument(
        '--use-ar',
        action='store_true',
        help='Use approximate randomization',
    )

    parser.add_argument(
        '--filter-zero-scored-segments',
        action='store_true',
        help='Filter out segments which have been scored only with zero',
    )

    parser.add_argument(
        '--filter-exclude-systems',
        action='append',
        help='Exclude systems from the filter',
    )

    parser.add_argument(
        '--separate-domains',
        action='store_true',
        help='Produce separate results for every domain. Domain ids are indicated in the beginning of the document id separated by a dot'
    )
    return parser
    # TODO: add argument to specify batch user


def handle(options):
    # campaign_name = options['campaign_name']
    # completed_only = options['completed_only']
    csv_file = options['csv_file']
    exclude_ids = (
        [x.lower() for x in options['exclude_ids'].split(',')]
        if options['exclude_ids']
        else []
    )
    show_p_values = options['show_p_values']

    _msg = 'Processing annotations in file {0}\n\n'.format(csv_file)
    # self.stdout.write(_msg)

    # Need to load data from CSV file and bring into same
    # format as would have been produced by the call to
    # get_system_scores().
    #
    # CSV has this format
    # zhoeng0802,GOOG_WMT2009_Test.chs-enu.txt,678,CHK,zho,eng,76,1511470503.271,1511470509.224
    system_data = []

    import csv

    with open(csv_file) as input_file:
        csv_reader = csv.reader(input_file)
        for csv_line in csv_reader:
            if len(csv_line) == 0:
                continue
            _user_id = csv_line[0]
            # modified for wmt-slt to use only first 8 chars of username
            if _user_id.lower()[:8] in exclude_ids:
                continue

            _system_id = csv_line[1]
            _segment_id = csv_line[2]
            _type = csv_line[3]
            _src = csv_line[4]
            _tgt = csv_line[5]
            _score = int(csv_line[6])
            _rest = csv_line[7:]

            if _type not in ('TGT', 'CHK'):
                continue

            # #remove document-level scores
            # if _segment_id == _rest[0].split("-")[1]:
            #     print(".")
            #     continue

            _data = tuple(csv_line[:6]) + (_score,) + tuple(_rest)
            system_data.append(_data)


    # TODO: get_system_data() returns a full dump of all annotations for
    #   the current campaign. This needs to be sliced by language pairs
    #   and then by users. Based on these slices, we can compute means
    #   for each user and then standardize their respective raw scores.
    #   Once the scores have been standardized, we can report system
    #   quality in best-to-worst order, per individual language pairs.
    #
    # Data keys are as follows:
    # UserID, SystemID, SegmentID, Type, Source, Target, Score

    # print(len(system_data)

    data_by_language_pair = defaultdict(list)
    for system_item in system_data:
        language_pair = system_item[4:6]
        data_by_language_pair[language_pair].append(system_item)

    latex_data = []
    tsv_data = []

    for language_pair, language_data in data_by_language_pair.items():
        segment_ids = set()
        if options['filter_zero_scored_segments']:
            print("Filtering...")
            language_data = filter_zero_scored_segments(language_data, options['filter_exclude_systems'], options)

        data_by_domain = {'both_domains': language_data}
        if options['separate_domains']:
            data_by_domain.update(get_data_by_domain(language_data))

        for domain_id, domain_data in data_by_domain.items():
            print(f"====== Results for {domain_id} =======")

            user_scores = defaultdict(list)
            system_z_scores = defaultdict(list)
            system_raw_scores = defaultdict(list)
            for system_item in domain_data:
                user_scores[system_item[0]].append(system_item[6])

            try:
                a = len(user_scores['zhoeng2802'])
                b = sum(user_scores['zhoeng2802'])
                c = float(b) / a
                print(b, a, c)

            except ZeroDivisionError:
                pass

            user_means = defaultdict(float)
            user_variances = defaultdict(float)
            for user_name, user_data in user_scores.items():
                user_mean = sum(user_data) / float(len(user_data) or 1)
                user_means[user_name] = user_mean

                n = sum([(x - user_mean) ** 2 for x in user_data])
                d = float((len(user_data) - 1) or 1)
                s_squared = n / d

                from math import sqrt

                user_variances[user_name] = sqrt(s_squared)

            # print(user_means['zhoeng2802'])
            # print(user_variances['zhoeng2802'])
            # print((63 - user_means['zhoeng2802']) / user_variances['zhoeng2802'])

            for system_item in domain_data:
                user_id = system_item[0]
                system_id = system_item[1]
                if options['task_type'] == 'Document':
                    segment_id = system_item[2] + ':' + system_item[7]
                else:
                    segment_id = system_item[2]
                raw_score = system_item[6]
                segment_ids.add(segment_id)

                # z_n = raw_score - user_means[user_id]
                # z_d = float(user_variances[user_id] or 1)
                # z_score = z_n / z_d

                # dirty disabling of the normalization, clusters should be calculated based on raw scores
                z_score = raw_score
                # # if user_id == 'zhoeng2802' and segment_id == '625':
                # #    print(z_score, raw_score, user_means[user_id], z_n, z_d, user_id, system_id, segment_id)
                #
                system_z_scores[system_id].append((segment_id, z_score))
                system_raw_scores[system_id].append((segment_id, raw_score))

            combo_z_scores = defaultdict(list)
            combo_raw_scores = defaultdict(list)

            combo_max_systemIDs = []
            for segmentID, zScores in combo_z_scores.items():
                bestScore = max(zScores, key=lambda x: x[0])
                bestSystem = None
                for zScore, systemID in zScores:
                    if zScore == bestScore[0]:
                        bestSystem = systemID
                        break

                system_z_scores["COMBO_MAX"].append((segmentID, bestScore[0]))
                combo_max_systemIDs.append((segmentID, bestSystem))

            # for segmentID, systemID in combo_max_systemIDs:
            #     print(segmentID, systemID)

            for segmentID, rawScores in combo_raw_scores.items():
                bestScore = max(rawScores, key=lambda x: x[0])
                bestSystem = None
                for rawScore, systemID in rawScores:
                    if rawScore == bestScore:
                        bestSystem = systemID
                        break

                system_raw_scores["COMBO_MAX"].append((segmentID, bestScore[0]))

            refs_z_scores = defaultdict(list)
            refs_raw_scores = defaultdict(list)
            refs_systems = []

            for systemID in refs_systems:
                if not systemID in system_z_scores.keys():
                    continue

                for item in system_z_scores[systemID]:
                    segmentID = item[0]
                    zScore = item[1]
                    refs_z_scores[segmentID].append(zScore)

                for item in system_raw_scores[systemID]:
                    segmentID = item[0]
                    rScore = item[1]
                    refs_raw_scores[segmentID].append(rScore)

            for segmentID, zScores in refs_z_scores.items():
                system_z_scores["REFS_MAX"].append((segmentID, max(zScores)))

            for segmentID, rawScores in refs_raw_scores.items():
                system_raw_scores["REFS_MAX"].append((segmentID, max(rawScores)))

            print('\n[{0}-->{1}]'.format(*language_pair))
            normalized_scores = defaultdict(list)
            for s, v in system_z_scores.items():
                print('{0}: {1}'.format(s, len(v)))

            averaged_raw_scores = defaultdict(list)
            averaged_h_scores = defaultdict(list)
            for key, value in system_raw_scores.items():
                print('{0}-->{1}'.format(key, len(value)))
                scores_by_segment = defaultdict(list)
                for segment_id, score in value:
                    scores_by_segment[segment_id].append(score)

                for segment_id, scores in scores_by_segment.items():
                    averaged_raw_score = sum(scores) / float(len(scores) or 1)
                    averaged_raw_scores[key].append(averaged_raw_score)

                    averaged_h_score = min(round(averaged_raw_score / 25.0) + 1, 4)
                    averaged_h_scores[key].append(averaged_h_score)

            for key, value in system_z_scores.items():
                scores_by_segment = defaultdict(list)
                for segment_id, score in value:
                    scores_by_segment[segment_id].append(score)

                averaged_scores = []
                for segment_id, scores in scores_by_segment.items():
                    averaged_score = sum(scores) / float(len(scores) or 1)
                    averaged_scores.append(averaged_score)

                _raw_scores = averaged_raw_scores[key]
                averaged_raw_score = sum(_raw_scores) / float(len(_raw_scores) or 1)

                _h_scores = averaged_h_scores[key]
                averaged_h_score = sum(_h_scores) / float(len(_h_scores) or 1)

                normalized_score = sum(averaged_scores) / float(
                    len(averaged_scores) or 1
                )

                normalized_scores[normalized_score] = (
                    key,
                    len(value),
                    normalized_score,
                    averaged_raw_score,
                    averaged_h_score,
                )

            for key in sorted(normalized_scores, reverse=True):
                value = normalized_scores[key]
                print('{0:03.2f} {1}'.format(key, value))

            if options['no_sigtest']:
                continue

            # if scipy is available, perform sigtest for all pairs of systems
            try:
                import scipy  # type: ignore

            except ImportError:
                print("NO SCIPY")
                continue

            sorted_by_wins = significance_test(normalized_scores, options, show_p_values, system_z_scores)
            pair = '{0}-{1}'.format(
                LANGUAGE_CODES[language_pair[0]], LANGUAGE_CODES[language_pair[1]]
            )

            if options['separate_domains']:
                domain_latex = f" ({domain_id})"
            else:
                domain_latex = ""

            # latex_data.append(
            #     '{\\bf  \\tto{'
            #     + source_language
            #     + '}{'
            #     + target_language
            #     + '}'
            #     + domain_latex
            #     + '} \\\\[0.5mm] ')
            latex_data.append('\\begin{tabular}{crl}')
            latex_data.append('\multicolumn{3}{c}{' + domain_id + '}\\\\')
            latex_data.append('\\toprule')
            latex_data.append('Rank & Ave. & System\\\\ \\midrule')

            tsv_data.append('pair\tsystem\trank\tave\tave_z')

            print('-' * 80)
            print(
                'Wins                                         System ID  Z Score H Score  R Score'
            )

            def sort_by_z_score(x, y):
                if x[4] > y[4]:
                    return 1
                elif x[4] == y[4]:
                    return 0
                else:
                    return -1

            total_systems = len(sorted_by_wins)
            min_wins_current_cluster = total_systems
            current_system = 0
            last_wins_count = None
            for values in sorted(
                    sorted_by_wins,
                    key=cmp_to_key(sort_by_z_score),
                    reverse=True,
            ):
                current_system += 1

                # values = normalized_scores[key]
                wins = values[0]
                better_than = values[1]
                systemID = values[2]
                dataPoints = values[3]
                zScore = values[4]
                rScore = values[5]
                hScore = values[6]
                losses = values[7]
                worse_than = values[8]

                # ChriFe: note that this could possibly mix up things as wins
                #   is computed irrespective of order. So, possible that a system
                #   beats systems higher up in the table, but not all systems
                #   in the lower cluster. This will become clear when creating
                #   the matrix tables...

                #                if last_wins_count != wins:
                #                    print('-' * 80)

                output = '{0:02d} {1:>51} {2:>+2.5f} {3:>1.5f} {4:>2.5f}'.format(
                    wins, systemID[:51], zScore, hScore, rScore
                ).replace('+', ' ')
                print(output)

                min_wins_current_cluster = min(wins, min_wins_current_cluster)

                add_cluster_boundary = False
                remaining_systems = len(sorted_by_wins) - current_system
                if min_wins_current_cluster == remaining_systems:
                    print('-' * 80)
                    add_cluster_boundary = True

                # Rank range is determined as follows:
                #
                # top-rank:   # of losses + 1       (e.g., 3 if two systems are sig better)
                # worst=rank: # systems - # of wins (e.g., 5 if 9 total systems but better than 4)
                top_rank = losses + 1
                worst_rank = total_systems - wins

                ranks = (
                    '{0}-{1}'.format(top_rank, worst_rank)
                    if top_rank != worst_rank
                    else str(top_rank)
                )
                _latex_data = (
                    '\\Uncon{}',
                    ranks,
                    '{0:.1f}'.format(rScore),
                    '{0:.3f}'.format(zScore),
                    reformat_system_id(systemID),
                    '\\\\ \\hline' if add_cluster_boundary else '\\\\',
                )
                latex_data.append('{1} & {3} & {4}{5}'.format(*_latex_data))

                tsv_data.append(
                    '\t'.join(
                        (
                            pair,
                            systemID[:51].replace('_', '\_'),
                            ranks,
                            '{0:.1f}'.format(rScore),
                            '{0:.3f}'.format(zScore),
                        )
                    )
                )

                last_wins_count = wins

            # latex_data.append('\\hline')
            latex_data.append('\\bottomrule')
            latex_data.append('\\end{tabular}')
            latex_data.append('')

        print()
        print('\n'.join(latex_data))
        print()
        print(f"segment ids: {len(segment_ids)}")


def significance_test(normalized_scores, options, show_p_values, system_z_scores):
    from scipy.stats import mannwhitneyu, bayes_mvs  # type: ignore
    from itertools import combinations_with_replacement
    system_ids = []
    for key in sorted(normalized_scores, reverse=True):
        data = normalized_scores[key]
        system_id = data[0]
        system_ids.append(system_id)
    wins_for_system = defaultdict(list)
    losses_for_system = defaultdict(list)
    p_level = 0.05
    for (sysA, sysB) in combinations_with_replacement(system_ids, 2):
        sysA_ids = set([x[0] for x in system_z_scores[sysA]])
        sysB_ids = set([x[0] for x in system_z_scores[sysB]])
        good_ids = set.intersection(sysA_ids, sysB_ids)

        # print("LEN(good_ids) = {0:d}".format(len(good_ids)))

        sysA_scores = []
        sbsA = defaultdict(list)
        for x in system_z_scores[sysA]:
            if not x[0] in good_ids:
                continue
            segmentID = x[0]
            zScore = x[1]
            # print(zScore)
            sbsA[segmentID].append((segmentID, zScore))
        for segmentID in sbsA.keys():
            average_z_score_for_segment = sum(
                [x[1] for x in sbsA[segmentID]]
            ) / float(len(sbsA[segmentID]))
            sysA_scores.append((segmentID, average_z_score_for_segment))

        sysB_scores = []
        sbsB = defaultdict(list)
        for x in system_z_scores[sysB]:
            if not x[0] in good_ids:
                continue
            segmentID = x[0]
            zScore = x[1]
            sbsB[segmentID].append((segmentID, zScore))
        for segmentID in sbsB.keys():
            average_z_score_for_segment = sum(
                [x[1] for x in sbsB[segmentID]]
            ) / float(len(sbsB[segmentID]))
            sysB_scores.append((segmentID, average_z_score_for_segment))

        sysA_sorted = [x[1] for x in sorted(sysA_scores, key=lambda x: x[0])]
        sysB_sorted = [x[1] for x in sorted(sysB_scores, key=lambda x: x[0])]

        #                sysA_scores = [x[1] for x in system_z_scores[sysA]]
        # sysB_scores = [x[1] for x in system_z_scores[sysB]]
        # t_statistic, p_value = mannwhitneyu(sysA_scores, sysB_scores, alternative="two-sided")

        if options['use_ar']:
            if sysA != sysB:
                t_statistic, p_value = ar(sysA_sorted, sysB_sorted, trials=1000)
            else:
                t_statistic, p_value = 0, 1
        else:
            t_statistic, p_value = mannwhitneyu(
                sysA_sorted, sysB_sorted, alternative="greater"
            )

        if options['use_ar']:
            if p_value < p_level:
                if sysA != sysB:
                    wins_for_system[sysA].append(sysB)
                    losses_for_system[sysB].append(sysA)
        else:
            if p_value < p_level:
                wins_for_system[sysA].append(sysB)
                losses_for_system[sysB].append(sysA)

        if show_p_values:
            if options['use_ar']:
                print(
                    '{0:>40}>{1:>40} {2:02.5f} {3:1.8f} {4}'.format(
                        sysA,
                        sysB,
                        p_value,
                        t_statistic,
                        p_value < p_level,
                    )
                )
            else:
                print(
                    '{0:>40}>{1:>40} {2:02.25f} {3:>10} {4}'.format(
                        sysA,
                        sysB,
                        p_value,
                        t_statistic,
                        p_value < p_level,
                    )
                )
    sorted_by_wins = []
    for key, values in normalized_scores.items():
        systemID = values[0]
        wins = wins_for_system[systemID]
        data = [len(wins), wins]
        data.extend(values)
        losses = losses_for_system[systemID]
        data.extend([len(losses), losses_for_system[systemID]])
        sorted_by_wins.append(tuple(data))
    return sorted_by_wins


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser = add_arguments(parser)
    options = vars(parser.parse_args())
    handle(options)
