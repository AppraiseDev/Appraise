from collections import defaultdict
from collections import OrderedDict
from functools import cmp_to_key
from json import loads
from random import seed
from random import shuffle

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from Campaign.models import Campaign
from EvalData.models import DirectAssessmentResult
from EvalData.models import DirectAssessmentTask


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


import numpy as np


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
class Command(BaseCommand):
    help = 'Computes system scores over all results'

    def add_arguments(self, parser):
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
            '--combo-systems',
            type=str,
            help='Systems to combine into oracle system',
        )
        parser.add_argument(
            '--combo-refs',
            type=str,
            help='References to combine into oracle system',
        )
        parser.add_argument(
            '--use-ar',
            action='store_true',
            help='Use approximate randomization',
        )

        # TODO: add argument to specify batch user

    def handle(self, *args, **options):
        campaign_name = options['campaign_name']
        completed_only = options['completed_only']
        csv_file = options['csv_file']
        exclude_ids = (
            [x.lower() for x in options['exclude_ids'].split(',')]
            if options['exclude_ids']
            else []
        )
        show_p_values = options['show_p_values']

        combo_systems = (
            options['combo_systems'].split(',')
            if options['combo_systems']
            else (
                'MSR_Redmond_20180212.txt',
                'MSRA_ML_20180212.txt',
                'MSRA_NLC_20180211.txt',
            )
        )

        combo_refs = (
            options['combo_refs'].split(',')
            if options['combo_refs']
            else (
                'Pactera-human-translation.txt',
                'Unbabel-postedited.txt',
            )
        )

        if csv_file:
            _msg = 'Processing annotations in file {0}\n\n'.format(csv_file)
            self.stdout.write(_msg)

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
                    if _user_id.lower() in exclude_ids:
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

                    _data = tuple(csv_line[:6]) + (_score,) + tuple(_rest)
                    system_data.append(_data)

        else:
            # Identify Campaign instance for given name
            campaign = Campaign.objects.filter(campaignName=campaign_name).first()
            if not campaign:
                _msg = 'Failure to identify campaign {0}'.format(campaign_name)
                self.stdout.write(_msg)
                return

            system_data = DirectAssessmentResult.get_system_data(campaign.id)

        # TODO: get_system_data() returns a full dump of all annotations for
        #   the current campaign. This needs to be sliced by language pairs
        #   and then by users. Based on these slices, we can compute means
        #   for each user and then standardize their respective raw scores.
        #   Once the scores have been standardized, we can report system
        #   quality in best-to-worst order, per individual language pairs.
        #
        # Data keys are as follows:
        # UserID, SystemID, SegmentID, Type, Source, Target, Score

        # print(len(system_data))

        data_by_language_pair = defaultdict(list)
        for system_item in system_data:
            language_pair = system_item[4:6]
            data_by_language_pair[language_pair].append(system_item)

        for language_pair, language_data in data_by_language_pair.items():
            user_scores = defaultdict(list)
            system_z_scores = defaultdict(list)
            system_raw_scores = defaultdict(list)
            for system_item in language_data:
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

            for system_item in language_data:
                user_id = system_item[0]
                system_id = system_item[1]
                segment_id = system_item[2]
                raw_score = system_item[6]

                z_n = raw_score - user_means[user_id]
                z_d = float(user_variances[user_id] or 1)
                z_score = z_n / z_d
                # if user_id == 'zhoeng2802' and segment_id == '625':
                #    print(z_score, raw_score, user_means[user_id], z_n, z_d, user_id, system_id, segment_id)

                system_z_scores[system_id].append((segment_id, z_score))
                system_raw_scores[system_id].append((segment_id, raw_score))

            combo_z_scores = defaultdict(list)
            combo_raw_scores = defaultdict(list)

            for systemID in combo_systems:
                if not systemID in system_z_scores.keys():
                    continue

                for item in system_z_scores[systemID]:
                    segmentID = item[0]
                    zScore = item[1]
                    combo_z_scores[segmentID].append((zScore, systemID))

                for item in system_raw_scores[systemID]:
                    segmentID = item[0]
                    rScore = item[1]
                    combo_raw_scores[segmentID].append((rScore, systemID))

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

            for segmentID, systemID in combo_max_systemIDs:
                print(segmentID, systemID)

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
            refs_systems = combo_refs

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

            from scipy.stats import mannwhitneyu, bayes_mvs  # type: ignore
            from itertools import combinations_with_replacement

            system_ids = []
            for key in sorted(normalized_scores, reverse=True):
                data = normalized_scores[key]
                system_id = data[0]
                system_ids.append(system_id)

            wins_for_system = defaultdict(list)
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
                else:
                    if p_value < p_level:
                        wins_for_system[sysA].append(sysB)

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
                sorted_by_wins.append(tuple(data))

            print('-' * 80)
            print(
                'Wins                                         System ID  Z Score H Score  R Score'
            )

            def sort_by_wins_and_z_score(x, y):
                if x[0] == y[0]:
                    if x[4] > y[4]:
                        return 1
                    elif x[4] == y[4]:
                        return 0
                    else:
                        return -1
                elif x[0] > y[0]:
                    return 1
                else:
                    return -1

            last_wins_count = None
            for values in sorted(
                sorted_by_wins,
                key=cmp_to_key(sort_by_wins_and_z_score),
                reverse=True,
            ):
                # values = normalized_scores[key]
                wins = values[0]
                better_than = values[1]
                systemID = values[2]
                dataPoints = values[3]
                zScore = values[4]
                rScore = values[5]
                hScore = values[6]

                if last_wins_count != wins:
                    print('-' * 80)

                output = '{0:02d} {1:>51} {2:>+2.5f} {3:>1.5f} {4:>2.5f}'.format(
                    wins, systemID[:51], zScore, hScore, rScore
                ).replace('+', ' ')
                print(output)

                last_wins_count = wins

            print('-' * 80)

            # CHRIFE:
            # DISABLE VERBOSE OUTPUT
            continue

            for sysX in system_ids:
                # print(sysX)
                sysX_scores = [x[1] for x in system_z_scores[sysX]]
                # print(bayes_mvs(sysX_scores))

            vsystems = defaultdict(list)
            for system_id in system_ids:
                key = system_id[:4].upper()
                vsystems[key].extend(system_z_scores[system_id])

            for (sysA, sysB) in combinations_with_replacement(
                ['GOOG', 'CAND', 'PROD'], 2
            ):
                sysA_scores = [x[1] for x in vsystems[sysA]]
                sysB_scores = [x[1] for x in vsystems[sysB]]
                # t_statistic, p_value = mannwhitneyu(sysA_scores, sysB_scores, alternative="two-sided")
                t_statistic, p_value = mannwhitneyu(
                    sysA_scores, sysB_scores, alternative="greater"
                )
                if len(sysA_scores) > 200 and len(sysB_scores) > 200:
                    print(len(sysA_scores), len(sysB_scores))
                    print(
                        '{0} > {1} {2:02.25f} {3:>10} {4}'.format(
                            sysA,
                            sysB,
                            p_value,
                            t_statistic,
                            p_value < p_level,
                        )
                    )

        # CHRIFE:
        # TEMPORARILY DISABLE PAIRWISE CMPS
        return

        # z scores for CAND and PROD only
        data_by_language_pair = defaultdict(list)
        for system_item in system_data:
            if system_item[1].startswith('GOOG'):
                continue

            language_pair = system_item[4:6]
            data_by_language_pair[language_pair].append(system_item)

        for language_pair, language_data in data_by_language_pair.items():
            user_scores = defaultdict(list)
            system_z_scores = defaultdict(list)
            for system_item in language_data:
                user_scores[system_item[0]].append(system_item[6])

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

            for system_item in language_data:
                user_id = system_item[0]
                system_id = system_item[1]
                segment_id = system_item[2]
                raw_score = system_item[6]

                z_n = raw_score - user_means[user_id]
                z_d = float(user_variances[user_id] or 1)
                z_score = z_n / z_d

                system_z_scores[system_id].append((segment_id, z_score))

            print('\n[{0}-->{1}]'.format(*language_pair))
            normalized_scores = defaultdict(list)
            for s, v in system_z_scores.items():
                print('{0}: {1}'.format(s, len(v)))

            for key, value in system_z_scores.items():
                #                if key.startswith('GOOG'):
                #                    continue

                scores_by_segment = defaultdict(list)
                for segment_id, score in value:
                    scores_by_segment[segment_id].append(score)

                averaged_scores = []
                for segment_id, scores in scores_by_segment.items():
                    averaged_score = sum(scores) / float(len(scores) or 1)
                    averaged_scores.append(averaged_score)

                normalized_score = sum(averaged_scores) / float(
                    len(averaged_scores) or 1
                )
                normalized_scores[normalized_score] = (
                    key,
                    len(value),
                    normalized_score,
                )

            for key in sorted(normalized_scores, reverse=True):
                value = normalized_scores[key]
                print('{0:03.2f} {1}'.format(key, value))

        # z scores for CAND and GOOG only
        data_by_language_pair = defaultdict(list)
        for system_item in system_data:
            if system_item[1].startswith('PROD'):
                continue

            language_pair = system_item[4:6]
            data_by_language_pair[language_pair].append(system_item)

        for language_pair, language_data in data_by_language_pair.items():
            user_scores = defaultdict(list)
            system_z_scores = defaultdict(list)
            for system_item in language_data:
                user_scores[system_item[0]].append(system_item[6])

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

            for system_item in language_data:
                user_id = system_item[0]
                system_id = system_item[1]
                segment_id = system_item[2]
                raw_score = system_item[6]

                z_n = raw_score - user_means[user_id]
                z_d = float(user_variances[user_id] or 1)
                z_score = z_n / z_d

                system_z_scores[system_id].append((segment_id, z_score))

            print('\n[{0}-->{1}]'.format(*language_pair))
            normalized_scores = defaultdict(list)
            for s, v in system_z_scores.items():
                print('{0}: {1}'.format(s, len(v)))

            for key, value in system_z_scores.items():
                scores_by_segment = defaultdict(list)
                for segment_id, score in value:
                    scores_by_segment[segment_id].append(score)

                averaged_scores = []
                for segment_id, scores in scores_by_segment.items():
                    averaged_score = sum(scores) / float(len(scores) or 1)
                    averaged_scores.append(averaged_score)

                normalized_score = sum(averaged_scores) / float(
                    len(averaged_scores) or 1
                )
                normalized_scores[normalized_score] = (
                    key,
                    len(value),
                    normalized_score,
                )

            for key in sorted(normalized_scores, reverse=True):
                value = normalized_scores[key]
                print('{0:03.2f} {1}'.format(key, value))

        # z scores for GOOG and PROD only
        data_by_language_pair = defaultdict(list)
        for system_item in system_data:
            if system_item[1].startswith('CAND'):
                continue

            language_pair = system_item[4:6]
            data_by_language_pair[language_pair].append(system_item)

        for language_pair, language_data in data_by_language_pair.items():
            user_scores = defaultdict(list)
            system_z_scores = defaultdict(list)
            for system_item in language_data:
                user_scores[system_item[0]].append(system_item[6])

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

            for system_item in language_data:
                user_id = system_item[0]
                system_id = system_item[1]
                segment_id = system_item[2]
                raw_score = system_item[6]

                z_n = raw_score - user_means[user_id]
                z_d = float(user_variances[user_id] or 1)
                z_score = z_n / z_d

                system_z_scores[system_id].append((segment_id, z_score))

            print('\n[{0}-->{1}]'.format(*language_pair))
            normalized_scores = defaultdict(list)
            for s, v in system_z_scores.items():
                print('{0}: {1}'.format(s, len(v)))

            for key, value in system_z_scores.items():
                scores_by_segment = defaultdict(list)
                for segment_id, score in value:
                    scores_by_segment[segment_id].append(score)

                averaged_scores = []
                for segment_id, scores in scores_by_segment.items():
                    averaged_score = sum(scores) / float(len(scores) or 1)
                    averaged_scores.append(averaged_score)

                normalized_score = sum(averaged_scores) / float(
                    len(averaged_scores) or 1
                )
                normalized_scores[normalized_score] = (
                    key,
                    len(value),
                    normalized_score,
                )

            for key in sorted(normalized_scores, reverse=True):
                value = normalized_scores[key]
                print('{0:03.2f} {1}'.format(key, value))
