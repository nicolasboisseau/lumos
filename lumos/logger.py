#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Logger functions for lumos.
'''
from logging.handlers import RotatingFileHandler
import logging
import os


# State variable to know if the current lumos session is using parallelism
IS_IN_PARALLEL = True


def setup(temp_directory, is_in_parallel):
    '''
    Sets-up the logger inside of the working temporary directory. If parallelism is enabled, no logs are stored (they will be printed to the console by default).

            Parameters:
                    temp_directory (Path): The path to the temporary directory.
                    parallelism (bool): Whether or not parallel computation is enabled for the current run of the program.
    '''

    # Set the global state variable of the module
    global IS_IN_PARALLEL
    IS_IN_PARALLEL = is_in_parallel

    if not IS_IN_PARALLEL:

        # Define log format
        log_formatter = logging.Formatter(
            '%(asctime)s %(levelname)s:\t%(message)s')

        # Create logger
        app_log = logging.getLogger('root')

        # Create a rotating log file for regular execution (3 files * 2MB max)
        my_handler = RotatingFileHandler(
            temp_directory + "/lumos.log",
            mode='a',
            maxBytes=2*1024*1024,
            backupCount=2,
            encoding=None,
            delay=0
        )

        my_handler.setFormatter(log_formatter)
        my_handler.setLevel(logging.DEBUG)

        app_log.setLevel(logging.DEBUG)
        app_log.addHandler(my_handler)

    else:
        # Don't log anything, as it is not compatible with multiprocessing
        pass


def p_print(text, end=os.linesep):
    '''
    Parallel print: Handles printing to the console, according to if parallelism is being used or not.

            Parameters:
                    text (string): The text to be printed.
                    end (string): What the separating character at the end of the print should be.
    '''
    if not IS_IN_PARALLEL:
        print(text, end=end)


def debug(text):
    '''
    Stores the message as a DEBUG log in the log file (according to if parallelism is being used or not).

            Parameters:
                    text (string): The message to be stored.
    '''
    if not IS_IN_PARALLEL:
        logging.getLogger('root').debug(text)


def info(text):
    '''
    Stores the message as an INFO log in the log file (according to if parallelism is being used or not).

            Parameters:
                    text (string): The message to be stored.
    '''
    if not IS_IN_PARALLEL:
        logging.getLogger('root').info(text)


def warning(text):
    '''
    Stores the message as a WARNING log in the log file (according to if parallelism is being used or not).

            Parameters:
                    text (string): The message to be stored.
    '''
    if not IS_IN_PARALLEL:
        logging.getLogger('root').warning(text)


def error(text):
    '''
    Stores the message as an ERROR log in the log file (according to if parallelism is being used or not).

            Parameters:
                    text (string): The message to be stored.
    '''
    if not IS_IN_PARALLEL:
        logging.getLogger('root').error(text)


def critical(text):
    '''
    Stores the message as a CRITICAL log in the log file (according to if parallelism is being used or not).

            Parameters:
                    text (string): The message to be stored.
    '''
    if not IS_IN_PARALLEL:
        logging.getLogger('root').critical(text)
