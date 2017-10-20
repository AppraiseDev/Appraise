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
        # TODO: add argument to specify batch user

    def handle(self, *args, **options):
        campaign_name = options['campaign_name']
        completed_only = options['completed_only']

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
            
            print('[{0}-->{1}]'.format(*language_pair))
            normalized_scores = defaultdict(list)

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

            # if scipy is available, perform sigtest for all pairs of systems
            try:
                import scipy
            
            except ImportError:
                sys.exit(-1)

            from scipy.stats import mannwhitneyu
            from itertools import combinations
            system_ids = list(sorted(normalized_scores, reverse=True))

            p_level = 0.05
            for (sysA, sysB) in combinations(system_ids, 2):
                sysA_scores = system_z_scores[sysA]
                sysB_scores = system_z_scores[sysB]
                t_statistic, p_value = mannwhitneyu(sysA_scores, sysB_scores)
                print('{0}>{1} {2}'.format(sysA, sysB, p_value < p_level))
