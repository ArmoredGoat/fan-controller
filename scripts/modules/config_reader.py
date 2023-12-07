#!/usr/bin/env python

import configparser
import ast
import os

"""
ArmoredGoat's Fan Controller for 4-pin fans.

Based on the script read_RPM.py (2016-01-20; Public Domain) found under 
https://abyz.me.uk/rpi/pigpio/examples.html as "RPM Monitor"
"""

def represents_int(string):
    """
    Function to check if a string is representing an integer and convert it if
    applicable.
    """

    # Try to convert string to integer. Output True if possible. If not, output
    # False.
    try: 
        int(string)
    except ValueError:
        return False
    else:
        return True

def expand_path(path):
    """
    Function to expand a given path containing variables or '~'.
    """

    # Check if path starts with ~ or contains variables and expand it 
    # accordingly.
    if path.startswith('~'):
        path = os.path.expanduser(path)
    if '$' in path:
        path = os.path.expandvars(path)
    
    return path


def read_config(path='~/.config/fan-controller/fan-controller.conf'):
    """
    Function to parse config file and return parsed config as dictionary.
    """

    # Expand path when containing variables or ~.
    path = expand_path(path)

    # Create ConfigParser object and read config file at given path.
    config = configparser.ConfigParser()
    config.read(path)

    # Create dictionary to hold read key=value pairs.
    config_dictionary = {}

    # Loop through config container.
    for section in config.sections():
        for option in config.options(section):
            # Get string of current key.
            value = config.get(section, option)

            # If value starts and end with square brackets, e.g. a list,
            # convert it to a list object by take the string literal.
            if value.startswith('[') and value.endswith(']'):
                value = ast.literal_eval(value)

            # Check if value is an integer and convert it to avoid
            # writing int(config['KEY']) everytime it is an integer.
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