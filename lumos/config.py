'''
YAML configuration module.
'''

import yaml


def load_config_string(string):
    '''
    Parse a YAML string and replace the current configuration.

            Parameters:
                    string (String): The YAML-formatted string containing the configuration to be stored.
    '''
    loaded_config = yaml.safe_load(string)
    return loaded_config


def load_config_file(path):
    '''
    Load a YAML file and replace the current configuration.

            Parameters:
                    path (Path): The path to the YAML configuration file to be loaded.
    '''
    with open(path, 'r', encoding="utf-8") as file:
        loaded_config = yaml.safe_load(file)

    return loaded_config
