#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Extra helper functions for lumos.
'''
import cv2
import os
from . import logger


def load_site_image(site, current_wells_df, source_folder):
    '''
    Loads a site image, for a specific channel.

            Parameters:
                    site (int): The id of the site (between 1 and 6).
                    current_wells_df (DataFrame): The dataframe containing image metadata.
                    source_folder (Path): The path to the folder where the images are stored.

            Returns:
                    16-bit cv2 image
    '''

    for _, current_site in current_wells_df.iterrows():
        # process field 1
        if current_site["site"] == site:
            if not os.path.isfile(source_folder + "/" + str(current_site["filename"])):
                logger.debug("Path to site image does not exist")
            site_img = cv2.imread(
                source_folder + "/" + str(current_site["filename"]), -1
            )

    try:
        site_img.shape
    except:
        logger.warning("Failed to load site image")
        return

    return site_img


def load_well_image(well, source_folder):
    '''
    Loads a well image, for a specific channel.
    Well images are temporary images made by lumos for a specific channel.
    They should be found inside of the working temporary directory.

            Parameters:
                    well (string): The id of the well (e.g. D23).
                    source_folder (Path): The path to the folder where the images are stored.

            Returns:
                    16-bit cv2 image
    '''

    well_image_path = source_folder + "/well-" + str(well) + ".png"
    if not os.path.isfile(well_image_path):
        logger.debug("Path to well image does not exist")
    well_img = cv2.imread(well_image_path)

    try:
        well_img.shape
    except:
        logger.warning("Failed to load well image")

    return well_img


def draw_markers(image, color):
    '''
    Draws standard markers on an image. This includes highlighted corners and an "empty" symbol in the middle of the image.

            Parameters:
                    image (cv2 image|np.array): The input image onto which the markers will be drawn.
                    color (int|int tuple): The intensity/color value that the markers will have.

            Returns:
                    modified image
    '''

    length = int(min(image.shape[0], image.shape[1]) / 10)
    thickness = int(min(image.shape[0], image.shape[1]) / 20)

    startCorner1 = (0, 0)
    startCorner2 = (image.shape[0], 0)
    startCorner3 = (0, image.shape[1])
    startCorner4 = image.shape[:2]

    # draw corner 1
    image = cv2.line(image, startCorner1, (int(
        startCorner1[0] + length), startCorner1[1]), color, thickness)
    image = cv2.line(image, startCorner1, (startCorner1[0], int(
        startCorner1[1] + length)), color, thickness)
    # draw corner 2
    image = cv2.line(image, startCorner2, (int(
        startCorner2[0] - length), startCorner2[1]), color, thickness)
    image = cv2.line(image, startCorner2, (startCorner2[0], int(
        startCorner2[1] + length)), color, thickness)
    # draw corner 3
    image = cv2.line(image, startCorner3, (int(
        startCorner3[0] + length), startCorner3[1]), color, thickness)
    image = cv2.line(image, startCorner3, (startCorner3[0], int(
        startCorner3[1] - length)), color, thickness)
    # draw corner 3
    image = cv2.line(image, startCorner4, (int(
        startCorner4[0] - length), startCorner4[1]), color, thickness)
    image = cv2.line(image, startCorner4, (startCorner4[0], int(
        startCorner4[1] - length)), color, thickness)

    # draw circle
    radius = int(min(image.shape[0], image.shape[1]) / 5)
    center = (int(image.shape[0]/2), int(image.shape[1]/2))
    image = cv2.circle(image, center, radius, color, thickness)

    # draw cross-line
    startCrossLine = (center[0]-radius, center[1]+radius)
    endCrossLine = (center[0]+radius, center[1]-radius)
    image = cv2.line(image, startCrossLine, endCrossLine, color, thickness)

    # # draw character (cv2 does not support unicode characters)
    # text = "Ø"
    # image = cv2.putText(
    #     img = image,
    #     text = text,
    #     org = (int(image.shape[0]/4), int(image.shape[1]*3/4)),
    #     fontFace = cv2.FONT_HERSHEY_SIMPLEX,
    #     fontScale = image.shape[0]/50,
    #     color = color,
    #     thickness = thickness,
    # )

    return image
