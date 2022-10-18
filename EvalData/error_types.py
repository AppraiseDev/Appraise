"""
Appraise evaluation framework

See LICENSE for usage details
"""
from collections import OrderedDict

ERROR_TYPES = {
    'BasicErrorTypes': [
        {
            'name': 'Accuracy',
            'var': 'accuracy',
            'description': 'the candidate translation does not accurately correspond'
            ' to the source text, introduced by distorting, omitting, or adding to'
            ' the message',
        },
        {
            'name': 'Terminology',
            'var': 'terminology',
            'description': 'a term does not conform to normative domain or a target'
            ' term is not the correct, normative equivalent of the corresponding term'
            ' in the source',
        },
        {
            'name': 'Fluency',
            'var': 'fluency',
            'description': 'related to the linguistic well-formedness of the text,'
            ' including problems with, grammaticality, idiomaticity, and mechanical'
            ' correctness',
        },
        {
            'name': 'Style',
            'var': 'style',
            'description': 'occurring in a text that can be grammatical but are'
            ' inappropriate because they exhibit inappropriate language style',
        },
        {
            'name': 'Locale conventions',
            'var': 'locale',
            'description': 'the translation product violates locale-specific content'
            ' or formatting requirements for numbers, currency, measurements, time,'
            ' address, etc.',
        },
        {
            'name': 'Not a translation',
            'var': 'not-a-translation',
            'description': 'the target text is not a translation of the source text',
        },
        {
            'name': 'Source',
            'var': 'other',
            'description': 'there is a major error in the source text',
        },
        {'name': 'Other', 'var': 'other', 'description': 'any other issues'},
    ],
}
