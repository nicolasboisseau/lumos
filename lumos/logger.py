#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Logger functions for lumos.
'''
import os
import logging
from logging.handlers import RotatingFileHandler

import click


# State variable to know if the logger is enabled
ENABLED = False
# State variable to know if parallelism is enabled
PARALLELISM = False


def setup(temp_directory, enabled, parallelism):
    '''
    Sets-up the logger inside of the working temporary directory. If parallelism is enabled, no logs are stored (they will be printed to the console by default).

            Parameters:
                    temp_directory (Path): The path to the temporary directory.
                    enabled (bool): Whether or not the logger is enabled.
                    parallelism (bool): Whether or not parallel computation is enabled for the current run of the program.
    '''

    # Set the global state variables of the module
    global ENABLED
    global PARALLELISM
    ENABLED = enabled
    PARALLELISM = parallelism

    if ENABLED and not PARALLELISM:

        # Define log format
        log_formatter = logging.Formatter(
            '%(asctime)s %(levelname)s:\t%(message)s')

        # Create logger
        app_log = logging.getLogger('root')

        # Create a rotating log file for regular execution (3 files * 2MB max)
        my_handler = RotatingFileHandler(
            temp_directory + "/lumos.log",
            mode='a',
            maxBytes=10*1024*1024,
            backupCount=2,
            encoding=None,
            delay=0
        )

        my_handler.setFormatter(log_formatter)
        my_handler.setLevel(logging.DEBUG)

        app_log.setLevel(logging.DEBUG)
        app_log.addHandler(my_handler)

    else:
        # Don't log anything, as the logger is disabled
        pass


def p_print(text, newline=True, color=None):
    '''
    Parallel print: Handles printing to the console, according to if parallelism is being used or not.

            Parameters:
                    text (string): The text to be printed.
                    newline (bool): If there should be a newline after the message.
    '''
    if ENABLED and not PARALLELISM:
        click.secho(text, nl=newline, fg=color)


def err_print(text, newline=True, color='bright_red'):
    '''
    Error print: Handles error printing to the console, no matter if parallelism is being used or not.

            Parameters:
                    text (string): The text to be printed.
                    newline (bool): If there should be a newline after the message.
    '''
    click.secho(text, nl=newline, fg=color)


def debug(text):
    '''
    Stores the message as a DEBUG log in the log file (according to if parallelism is being used or not).

            Parameters:
                    text (string): The message to be stored.
    '''
    if ENABLED and not PARALLELISM:
        logging.getLogger('root').debug(text)


def info(text):
    '''
    Stores the message as an INFO log in the log file (according to if parallelism is being used or not).

            Parameters:
                    text (string): The message to be stored.
    '''
    if ENABLED and not PARALLELISM:
        logging.getLogger('root').info(text)


def warning(text):
    '''
    Stores the message as a WARNING log in the log file (according to if parallelism is being used or not).

            Parameters:
                    text (string): The message to be stored.
    '''
    if ENABLED and not PARALLELISM:
        logging.getLogger('root').warning(text)


def error(text):
    '''
    Stores the message as an ERROR log in the log file (according to if parallelism is being used or not).

            Parameters:
                    text (string): The message to be stored.
    '''
    if ENABLED and not PARALLELISM:
        logging.getLogger('root').error(text)


def critical(text):
    '''
    Stores the message as a CRITICAL log in the log file (according to if parallelism is being used or not).

            Parameters:
                    text (string): The message to be stored.
    '''
    if ENABLED and not PARALLELISM:
        logging.getLogger('root').critical(text)
