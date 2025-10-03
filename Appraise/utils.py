"""
Appraise evaluation framework

See LICENSE for usage details
"""

import logging

from Appraise.settings import LOG_HANDLER
from Appraise.settings import LOG_LEVEL


def _get_logger(name):
    """
    Initialises and returns named Django logger instance.
    """
    named_logger = logging.getLogger(name=name)
    named_logger.setLevel(LOG_LEVEL)
    named_logger.addHandler(LOG_HANDLER)
    return named_logger


def _compute_user_total_annotation_time(timestamps):
    """
    Computes total annotation time for a single user based on pairs of start and
    end timestamps excluding overlapping portions of annotations.

    :param timestamps: list of (start_timestamp, end_timestamp) pairs
    :return: total annotation time in seconds
    """
    # Sort timestamps by start timestamp
    timestamps = sorted(timestamps, key=lambda x: x[0])

    def _clamp_time(seconds):
        # if a segment takes longer than 10 minutes, set it to 5 minutes
        # it's likely due to inactivity
        if seconds >= 10 * 60:
            return 5 * 60
        else:
            return seconds

    total_annotation_time = 0
    previous_end_timestamp = None
    for start_timestamp, end_timestamp in timestamps:
        # If there is no previous end timestamp or the current start timestamp is after the previous end timestamp
        if previous_end_timestamp is None or start_timestamp >= previous_end_timestamp:
            # Add the duration of the current annotation to the total annotation time
            total_annotation_time += _clamp_time(end_timestamp - start_timestamp)

        # If the current start timestamp is before the previous end timestamp
        else:
            # Add the duration of the non-overlapping portion of the current annotation to the total annotation time
            total_annotation_time += _clamp_time(end_timestamp - previous_end_timestamp)

        # Update the previous end timestamp
        previous_end_timestamp = end_timestamp

    return total_annotation_time
