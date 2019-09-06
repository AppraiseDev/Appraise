"""
Appraise evaluation framework

See LICENSE for usage details
"""
import logging

from Appraise.settings import LOG_HANDLER

def _get_logger(name):
    """
    Initialises and returns named Django logger instance.
    """
    named_logger = logging.getLogger(name=name)
    named_logger.addHandler(LOG_HANDLER)
    return named_logger
