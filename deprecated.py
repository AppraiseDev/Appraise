"""
Appraise evaluation framework

See LICENSE for usage details

Keeps a registry of deprecated methods.

Use @add_deprecated_method decorator to mark method as deprecated. This
needs to be placed closest relative to the deprecated method for now.

Use get_deprecated_methods() to retrieve set of deprecated methods.
"""

from typing import Set


_DEPRECATED_METHOD_REGISTRY: Set[str] = set()


def add_deprecated_method(func):
    """
    Add deprecated method to registry.
    """
    _DEPRECATED_METHOD_REGISTRY.add(func.__name__)
    return func


def get_deprecated_methods():
    """
    Get deprecated methods from registry.
    """
    return _DEPRECATED_METHOD_REGISTRY
