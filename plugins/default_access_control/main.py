"""
Access control utilities

An access control is a marking that complies with the structure described here:
https://www.fas.org/sgp/othergov/intel/capco_reg.pdf

For example:
    SECRET//ABC//XYZ//USA or TOP SECRET or UNCLASSIFIED//FOUO

Classification Validation:
    A string is made of tokens separated by a delimiter

'SECRET//ABC//XYZ//USA'  is made of 4 tokens  [ Token(SECRET), Token(ABC), Token(XYZ), Token(USA) ]

This simple logic is this: for a user to have access:
    1. They must have a classification equal to or higher than that required
    2. They must have at least all controls that are required (in any order)
"""
import json
import logging

from . import tokens as all_tokens

logger = logging.getLogger('ozp-center.' + str(__name__))


tokens_list = [
    # Classification Tokens
    {'type': 'Classification',
     'data': {'short_name': 'U',
             'long_name': 'Unclassified',
             'level': 1}
    },
    {'type': 'Classification',
     'data': {'short_name': 'C',
             'long_name': 'Confidential',
             'level': 2}
    },
    {'type': 'Classification',
     'data': {'short_name': 'S',
             'long_name': 'Secret',
             'level': 3}
    },
    {'type': 'Classification',
     'data': {'short_name': 'TS',
             'long_name': 'Top Secret',
             'level': 4}
    },
    # Dissemination Control Tokens
    {'type': 'DisseminationControl',
     'data': {'short_name': 'FOUO',
             'long_name': 'FOR OFFICIAL USE ONLY'}
    }
]


class PluginMain(object):
    plugin_name = 'default_access_control'
    plugin_description = 'DefaultAccessControlPlugin'
    plugin_type = 'access_control'

    def __init__(self, settings=None, requests=None):
        '''
        Settings: Object reference to ozp settings
        '''
        self.settings = settings
        self.requests = requests

        self.tokens = [self._convert_dict_to_token(input) for input in tokens_list]

    def _convert_dict_to_token(self, input):
        """
        Converts Dictionary into Token
        """
        type = input.get('type')
        data = input.get('data')

        if type is None or data is None:
            return all_tokens.InvalidFormatToken()

        token_type_class = all_tokens.InvalidFormatToken

        if type == 'Classification':
            token_type_class = all_tokens.ClassificationToken
        elif type == 'DisseminationControl':
            token_type_class = all_tokens.DisseminationControlToken
        else:
            return token_type_class()

        return token_type_class(**data)

    def _split_tokens(self, input_marking, delimiter='//'):
        """
        This method is responsible for converting a String into Tokens
        """
        long_name_lookup = {}
        for token in self.tokens:
            long_name_lookup[token.long_name.upper()] = token

        short_name_lookup = {}
        for token in self.tokens:
            short_name_lookup[token.short_name.upper()] = token

        markings = input_marking.split(delimiter)

        output_tokens = []
        for marking in markings:
            current_token = None

            if marking.upper() in long_name_lookup:
                current_token = long_name_lookup[marking.upper()]
            else:
                if marking.upper() in short_name_lookup:
                    current_token = short_name_lookup[marking.upper()]
                else:
                    current_token = all_tokens.UnknownToken(long_name=marking)

            output_tokens.append(current_token)
        return output_tokens

    def has_access(self, user_accesses_json, marking):
        return True

    def future_has_access(self, user_accesses_json, marking):
        """
        Determine if a user has access to a given access control

        Ultimately, this will likely invoke a separate service to do the check.
        For now, some basic logic will suffice

        Assume the access control is of the format:
        <CLASSIFICATION>//<CONTROL>//<CONTROL>//...

        i.e.: a single classification followed by additional marking categories
        separated by //

        Args:
            user_accesses_json (string): user accesses in json (clearances, formal_accesses, visas)
            marking: a valid (string): a valid security marking
        """
        if not marking:
            return False
        markings = marking.split('//')
        # get the user's access_control data
        try:
            user_accesses = json.loads(user_accesses_json)
        except ValueError:
            logger.error('Error parsing JSON data: {0!s}'.format(user_accesses_json))
            return False

        # check clearances
        clearances = user_accesses['clearances']
        required_clearance = markings[0]

        if required_clearance not in clearances:
            return False

        # just combine all of the user's formal accesses and visas
        user_controls = user_accesses['formal_accesses']
        user_controls += user_accesses['visas']

        required_controls = markings[1:]
        missing_controls = [i for i in required_controls if i not in user_controls]
        if not missing_controls:
            return True
        else:
            return False

    def validate_marking(self, marking):
        """
        This function is responsible for validating a marking string

        Assume the access control is of the format:
        <CLASSIFICATION>//<CONTROL>//<CONTROL>//...

        """
        if not marking:
            return False
        tokens = self._split_tokens(marking)

        if not isinstance(tokens[0], all_tokens.ClassificationToken):
            return False

        return True
