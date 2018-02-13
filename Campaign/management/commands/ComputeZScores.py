from collections import defaultdict, OrderedDict
from json import loads
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from Campaign.models import Campaign
from EvalData.models import DirectAssessmentTask, DirectAssessmentResult

# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Computes system scores over all results'

    def add_arguments(self, parser):
        parser.add_argument(
          'campaign_name', type=str,
          help='Name of the campaign you want to process data for'
        )
        parser.add_argument(
          '--completed-only', action='store_true',
          help='Include completed tasks only in the computation'
        )
        parser.add_argument(
          '--csv-file', type=str,
          help='CSV file containing annotation data'
        )
        parser.add_argument(
          '--exclude-ids', type=str,
          help='User IDs which should be ignored'
        )
        parser.add_argument(
          '--no-sigtest', action='store_true',
          help='Do not run significance testing'
        )
        # TODO: add argument to specify batch user

    def handle(self, *args, **options):
        campaign_name = options['campaign_name']
        completed_only = options['completed_only']
        csv_file = options['csv_file']
        exclude_ids = [x.lower() for x in options['exclude_ids'].split(',')] \
          if options['exclude_ids'] else []

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
            
            user_means = defaultdict(float)
            user_variances = defaultdict(float)
            for user_name, user_data in user_scores.items():
                user_mean = sum(user_data) / float(len(user_data) or 1)
                user_means[user_name] = user_mean

                n = sum([(x - user_mean)**2 for x in user_data])
                d = float((len(user_data) - 1) or 1)
                s_squared = n / d

                from math import sqrt
                user_variances[user_name] = sqrt(s_squared)

            for system_item in language_data:
                user_id = system_item[0]
                system_id = system_item[1]
                segment_id = system_item[2]
                raw_score = system_item[6]

                z_n = (raw_score - user_means[user_id])
                z_d = float(user_variances[user_id] or 1)
                z_score = z_n / z_d

                system_z_scores[system_id].append((segment_id, z_score))
                system_raw_scores[system_id].append((segment_id, raw_score))
            
            print('\n[{0}-->{1}]'.format(*language_pair))
            normalized_scores = defaultdict(list)
            for s, v in system_z_scores.items():
                print('{0}: {1}'.format(s, len(v)))

            averaged_raw_scores = defaultdict(list)
            for key, value in system_raw_scores.items():
                print('{0}-->{1}'.format(key, len(value)))
                scores_by_segment = defaultdict(list)
                for segment_id, score in value:
                    scores_by_segment[segment_id].append(score)

                for segment_id, scores in scores_by_segment.items():
                    averaged_raw_score = sum(scores) / float(len(scores) or 1)
                    averaged_raw_scores[key].append(averaged_raw_score)

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

                normalized_score = sum(averaged_scores) / float(len(averaged_scores) or 1)
                normalized_scores[normalized_score] = (key, len(value), normalized_score, averaged_raw_score)
            
            for key in sorted(normalized_scores, reverse=True):
                value = normalized_scores[key]
                print('{0:03.2f} {1}'.format(key, value))

            if options['no_sigtest']:
                continue

            # if scipy is available, perform sigtest for all pairs of systems
            try:
                import scipy
            
            except ImportError:
                print("NO SCIPY")
                continue

            from scipy.stats import mannwhitneyu, bayes_mvs
            from itertools import combinations_with_replacement
            system_ids = []
            for key in sorted(normalized_scores, reverse=True):
                data = normalized_scores[key]
                system_id = data[0]
                system_ids.append(system_id)

            wins_for_system = defaultdict(list)
            p_level = 0.05
            for (sysA, sysB) in combinations_with_replacement(system_ids, 2):
                sysA_scores = [x[1] for x in system_z_scores[sysA]]
                sysB_scores = [x[1] for x in system_z_scores[sysB]]
                # t_statistic, p_value = mannwhitneyu(sysA_scores, sysB_scores, alternative="two-sided")
                t_statistic, p_value = mannwhitneyu(sysA_scores, sysB_scores, alternative="greater")

                if p_value < p_level:
                    wins_for_system[sysA].append(sysB)

#                if len(sysA_scores) > 200 and len(sysB_scores) > 200:
#                    print(len(sysA_scores), len(sysB_scores))
#                    print('{0:>40}>{1:>40} {2:02.25f} {3:>10} {4}'.format(sysA, sysB, p_value, t_statistic, p_value < p_level))

            sorted_by_wins = []
            for key, values in normalized_scores.items():
                systemID = values[0]
                wins = wins_for_system[systemID]
                data = (len(wins), wins, *values)
                sorted_by_wins.append(data)

            last_wins_count = None
            for values in sorted(sorted_by_wins, reverse=True):
                #values = normalized_scores[key]
                wins = values[0]
                better_than = values[1]
                systemID = values[2]
                dataPoints = values[3]
                zScore = values[4]
                rScore = values[5]

                if last_wins_count != wins:
                    print('-' * 62)

                output = '{0:02d} {1:>40} {2:>+2.5f} {3:>+2.5f}'.format(
                  wins, systemID, zScore, rScore
                ).replace('+', ' ')
                print(output)

                last_wins_count = wins

            # CHRIFE:
            # DISABLE VERBOSE OUTPUT
            return

            for sysX in system_ids:
                #print(sysX)
                sysX_scores = [x[1] for x in system_z_scores[sysX]]
                #print(bayes_mvs(sysX_scores))

            vsystems = defaultdict(list)
            for system_id in system_ids:
                key = system_id[:4].upper()
                vsystems[key].extend(system_z_scores[system_id])

            for (sysA, sysB) in combinations_with_replacement(['GOOG','CAND','PROD'], 2):
                sysA_scores = [x[1] for x in vsystems[sysA]]
                sysB_scores = [x[1] for x in vsystems[sysB]]
                # t_statistic, p_value = mannwhitneyu(sysA_scores, sysB_scores, alternative="two-sided")
                t_statistic, p_value = mannwhitneyu(sysA_scores, sysB_scores, alternative="greater")
                if len(sysA_scores) > 200 and len(sysB_scores) > 200:
                    print(len(sysA_scores), len(sysB_scores))
                    print('{0} > {1} {2:02.25f} {3:>10} {4}'.format(sysA, sysB, p_value, t_statistic, p_value < p_level))

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

                n = sum([(x - user_mean)**2 for x in user_data])
                d = float((len(user_data) - 1) or 1)
                s_squared = n / d

                from math import sqrt
                user_variances[user_name] = sqrt(s_squared)

            for system_item in language_data:
                user_id = system_item[0]
                system_id = system_item[1]
                segment_id = system_item[2]
                raw_score = system_item[6]

                z_n = (raw_score - user_means[user_id])
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

                normalized_score = sum(averaged_scores) / float(len(averaged_scores) or 1)
                normalized_scores[normalized_score] = (key, len(value), normalized_score)
            
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

                n = sum([(x - user_mean)**2 for x in user_data])
                d = float((len(user_data) - 1) or 1)
                s_squared = n / d

                from math import sqrt
                user_variances[user_name] = sqrt(s_squared)

            for system_item in language_data:
                user_id = system_item[0]
                system_id = system_item[1]
                segment_id = system_item[2]
                raw_score = system_item[6]

                z_n = (raw_score - user_means[user_id])
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

                normalized_score = sum(averaged_scores) / float(len(averaged_scores) or 1)
                normalized_scores[normalized_score] = (key, len(value), normalized_score)
            
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

                n = sum([(x - user_mean)**2 for x in user_data])
                d = float((len(user_data) - 1) or 1)
                s_squared = n / d

                from math import sqrt
                user_variances[user_name] = sqrt(s_squared)

            for system_item in language_data:
                user_id = system_item[0]
                system_id = system_item[1]
                segment_id = system_item[2]
                raw_score = system_item[6]

                z_n = (raw_score - user_means[user_id])
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

                normalized_score = sum(averaged_scores) / float(len(averaged_scores) or 1)
                normalized_scores[normalized_score] = (key, len(value), normalized_score)
            
            for key in sorted(normalized_scores, reverse=True):
                value = normalized_scores[key]
                print('{0:03.2f} {1}'.format(key, value))
