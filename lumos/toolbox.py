#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Extra helper functions for lumos
"""
import cv2
import pandas as pd
import os
import logging


def load_site_image(site, current_wells_df, source_folder):
    """load a site image, for a specific channel
    Args:
    site: the id of the site (between 1 and 6)
    current_wells_df: the dataframe containing image metadata
    source_folder: the path where the images are stored
    Return:
    a cv2 image
    """

    for id, current_site in current_wells_df.iterrows():
        # process field 1
        if current_site["site"] == site:
            if not os.path.isfile(source_folder + "/" + str(current_site["filename"])):
                logging.info("warning,: path does not exist")
            site_img = cv2.imread(
                source_folder + "/" + str(current_site["filename"]), -1
            )

    try:
        site_img.shape
    except:
        logging.info("Load Error")
        return

    return site_img


def load_well_image(well, source_folder):
    """load a wellimage, for a specific channel
    Well images are temporary images made by lumos for a specific channel
    Args:
    well: the id of the well (e.g. A23)
    source_folder: the path where the images are stored

    Return:
    a cv2 image
    """
    well_image_path = source_folder + "/well-" + str(well) + ".png"
    if not os.path.isfile(well_image_path):
        logging.info("warning,: path does not exist")
    well_img = cv2.imread(well_image_path)

    try:
        well_img.shape
    except:
        logging.info("Load Error")

    return well_img
