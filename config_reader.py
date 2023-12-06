#!/usr/bin/env python

import configparser
import ast

def read_config(path):
    """
    Function to parse config file and return parsed config as dictionary.
    """
    def represents_int(s):
        try: 
            int(s)
        except ValueError:
            return False
        else:
            return True
    
    # Create ConfigParser object and read config file at given path.
    config = configparser.ConfigParser()
    config.read(path)

    # Create dictionary to hold read key=value pairs.
    config_dictionary = {}

    # Loop through config file and append dictionary.
    for section in config.sections():
        for option in config.options(section):
            value = config.get(section, option)
            # If value starts and end with square brackets, e.g. a list,
            # convert it to a list object by take the string literal.
            if value.startswith('[') and value.endswith(']'):
                value = ast.literal_eval(value)
            # Check if value is an integer and convert it to avoid
            # writing int(config['KEY´]) everytime it is an integer.
            if type(value) is str and represents_int(value):
                value = int(value)
            # Convert the strings containing 'True' or 'False' to booleans. 
            if type(value) is str and value.lower() == 'true':
                value = True
            elif type(value) is str and value.lower() == 'false':
                value = False
            # ConfigParser convert all keys to lowercase. To match the given
            # names in the config file and to be compliant with Python's naming
            # convention for static variables, convert them to uppercase.
            config_dictionary[option.upper()] = value

    return config_dictionary