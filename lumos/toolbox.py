#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Extra helper functions for lumos.
'''

import os
import sys
from pathlib import Path

import cv2
import pandas as pd

from . import logger
from .config import get_config


def build_input_images_df(plate_input_path, selected_channels):
    '''
    Scans the input plate folder to build a table of all the available images for the selected channels.
    It handles nested files that match the folder structure specified by the user in the configuration.

            Parameters:
                    plate_input_path (Path): A path to a plate folder.
                    selected_channels (string list): A list of all the channels IDs to be included in the DF.

            Returns:
                    Pandas DataFrame:
                            A database of the paths to the images of each channel, for each site of each well.
                            Its columns are: ["well", "site", "channel", "filename", "fullpath"].
    '''

    # Get the path to the images of the plate folder, for the targeted channels
    # (this is just a rough selection, and it will be refined later)
    images_full_path_list = []
    for current_channel in selected_channels:

        current_channel_images = list(
            Path(plate_input_path).glob(
                f"./{get_config()['path_from_plate_folder_to_images']}/*{current_channel}*.tif*")
        )

        if len(current_channel_images) == 0:
            logger.err_print(f"ERROR: No images found for channel '{current_channel}' of this plate.",
                             color='bright_red')
            logger.err_print("       Make sure that you have configured the channel IDs to be the same as they appear in your file names.",
                             color='bright_red')
            logger.err_print("       Also make sure you that your folder structure matches your path-to-images configuration. "
                             + f"The current configuration is: <plate_folder>/{get_config()['path_from_plate_folder_to_images']}<images>",
                             color='bright_red')
            logger.error("No files found when building dataframe")
            sys.exit(1)

        if len(current_channel_images) >= 50000:
            logger.err_print("ERROR: Too many images found for this plate's channel. Make sure that you have chosen a valid plate.",
                             color='bright_red')
            logger.error("Too many files found when building dataframe")
            sys.exit(1)

        images_full_path_list.extend(current_channel_images)

    # Get the filenames list
    images_full_path_list.sort()
    images_filename_list = [str(x.name) for x in images_full_path_list]

    # Get the grid patterns from config
    nb_site_row = int(get_config()['site_grid'].split('x', maxsplit=1)[0])
    nb_site_col = int(get_config()['site_grid'].rsplit('x', maxsplit=1)[-1])
    nb_site = nb_site_row * nb_site_col

    nb_well_row = int(get_config()['well_grid'].split('x', maxsplit=1)[0])
    nb_well_col = int(get_config()['well_grid'].rsplit('x', maxsplit=1)[-1])
    nb_well = nb_well_row * nb_well_col

    if get_config()['input_file_naming_scheme'] == 'letter_wells':
        # Extract the metadata of the images from their name
        try:
            # Extract the available wells list
            image_well_list = [x.split('_')[-2]
                               for x in images_filename_list]
            # Extract the available sites list
            image_site_list = [
                int(x.split('_')[-1].split('F')[1].split('L')[0])
                for x in images_filename_list
            ]
            # Extract the channel list
            image_channel_list = [x.split(".tif")[0][-6:]
                                  for x in images_filename_list]
        except IndexError:
            logger.err_print("ERROR: File names do not follow the chosen INPUT_FILE_NAMING_SCHEME '" +
                             get_config()['input_file_naming_scheme']+"'",
                             color='bright_red')
            logger.error("File names do not follow the chosen INPUT_FILE_NAMING_SCHEME '" +
                         get_config()['input_file_naming_scheme']+"'")
            sys.exit(1)

        # Compute the theoretical reference well list for a standard plate
        reference_well_list = [
            # e.g. "A01"
            l + str(col).zfill(2) for l in "ABCDEFGHIJKLMNOP" for col in range(1, nb_well_col+1)
        ]
        complete_reference_list = [
            # e.g. ["A01", 1, "Z01C01"] .. ["P24", 6, "Z01C01"]
            [w, s, c] for w in reference_well_list for s in range(1, nb_site+1) for c in selected_channels
        ]

    elif get_config()['input_file_naming_scheme'] == 'rows_and_columns':
        # Extract the metadata of the images from their name
        try:
            # Extract the available wells list
            image_well_list = [x.split('-')[0].split('f')[0]
                               for x in images_filename_list]
            # Extract the available sites list
            image_site_list = [
                int(x.split('-')[0].split('f')[1].split("p")[0])
                for x in images_filename_list
            ]
            # Extract the channel list
            image_channel_list = [x.split('-')[1].split('sk')[0]
                                  for x in images_filename_list]

        except IndexError:
            logger.err_print("ERROR: File names do not follow the chosen INPUT_FILE_NAMING_SCHEME '" +
                             get_config()['input_file_naming_scheme']+"'",
                             color='bright_red')
            logger.error("File names do not follow the chosen INPUT_FILE_NAMING_SCHEME '" +
                         get_config()['input_file_naming_scheme']+"'")
            sys.exit(1)

        # Compute the theoretical reference well list for a standard plate
        reference_well_list = [
            # e.g. "r01c01"
            f"r{str(row).zfill(2)}c{str(col).zfill(2)}" for row in range(1, nb_well_row+1) for col in range(1, nb_well_col+1)
        ]
        complete_reference_list = [
            # e.g. ["r01c01", 1, "ch1"] .. ["r16c24", 6, "ch5"]
            [w, s, c] for w in reference_well_list for s in range(1, nb_site+1) for c in selected_channels
        ]

    else:
        logger.err_print("ERROR: Non-valid INPUT_FILE_NAMING_SCHEME '" +
                         get_config()['input_file_naming_scheme']+"'",
                         color='bright_red')
        logger.error("Non-valid INPUT_FILE_NAMING_SCHEME '" +
                     get_config()['input_file_naming_scheme']+"'")
        sys.exit(1)

    # Zip all the data of the channel images together
    image_data_zip = zip(
        image_well_list,
        image_site_list,
        image_channel_list,
        images_filename_list,
        images_full_path_list,
    )
    # Convert the zip into dataframe
    image_data_df = pd.DataFrame(
        list(image_data_zip), columns=["well", "site", "channel", "filename", "fullpath"]
    )

    # Check that we get the expected number of images
    expected_image_nb = nb_well * nb_site * len(selected_channels)
    actual_image_nb = len(image_data_df)

    if actual_image_nb != expected_image_nb:
        logger.p_print(
            "The plate does not have the exact image count: expected "
            + str(expected_image_nb)
            + ", got " + str(actual_image_nb)
        )
        logger.warning(
            "Plate doesn't have the exact image count: expected "
            + str(expected_image_nb)
            + ", got " + str(actual_image_nb)
        )

    # Create the theoretical well dataframe
    reference_data_df = pd.DataFrame(
        complete_reference_list, columns=["well", "site", "channel"]
    )

    # Join the reference table with the real one
    # to highlight differences
    image_data_df_joined = reference_data_df.merge(
        image_data_df,
        left_on=["well", "site", "channel"],
        right_on=["well", "site", "channel"],
        how="left",
    )

    # Remove all images that may have been captured without being in the selected channels
    # (this can happen when a well name is also a channel name, e.g. 'C01')
    current_channels_df = image_data_df_joined[image_data_df_joined['channel'].isin(
        selected_channels)]

    return current_channels_df.copy()


def load_site_image(site, current_wells_df, source_folder):
    '''
    Loads a site image, for a specific channel.

            Parameters:
                    site (int): The ID of the site to be loaded.
                    current_wells_df (DataFrame): The dataframe containing image metadata.
                    source_folder (Path): The path to the folder where the images are stored.

            Returns:
                    16-bit cv2 image
    '''

    for _, current_site in current_wells_df.iterrows():
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
        return None

    return site_img


def load_well_image(well, source_folder, image_format):
    '''
    Loads a well image, for a specific channel.
    Well images are temporary images made by lumos for a specific channel.
    They should be found inside of the working temporary directory.

            Parameters:
                    well (string): The ID of the well to be loaded.
                    source_folder (Path): The path to the folder where the images are stored.

            Returns:
                    16-bit cv2 image
    '''

    well_image_path = source_folder + f"/well-{well}.{image_format}"
    if not os.path.isfile(well_image_path):
        logger.debug("Path to well image does not exist")
    well_img = cv2.imread(well_image_path)

    try:
        well_img.shape
    except:
        logger.warning("Failed to load well image")
        return None

    return well_img


def concatenate_images_in_grid(image_list, nb_rows, nb_columns):
    '''
    Concatenates all the images together in the specified grid pattern.

            Parameters:
                    image_list (Image/Mat list): The images to be concatenated together.
                    nb_rows (int): The number of rows of the grid pattern.
                    nb_columns (int): The number of columns of the grid pattern.

            Returns:
                    8-bit cv2 image
    '''

    rows = [
        # Concatenate the images of each row in a horizontal stripe
        cv2.hconcat(image_list[row*nb_columns:(row+1)*nb_columns])
        for row in range(nb_rows)
    ]
    # Concatenate the rows vertically on top of each other to assemble the grid
    return cv2.vconcat(rows)


def draw_markers(image, color):
    '''
    Draws standard markers on an image. This includes highlighted corners and an "empty" symbol in the middle of the image.

            Parameters:
                    image (cv2 image|np.array): The input image onto which the markers will be drawn.
                    color (int|int tuple): The intensity/color value that the markers will have.

            Returns:
                    modified image
    '''

    # Define the characteristics of the shapes to be drawn
    length = int(min(image.shape[0], image.shape[1]) / 10)
    thickness = int(min(image.shape[0], image.shape[1]) / 20)

    # Find the corners of the image
    start_corner_1 = (0, 0)
    start_corner_2 = (image.shape[0], 0)
    start_corner_3 = (0, image.shape[1])
    start_corner_4 = image.shape[:2]

    # Draw corner 1
    image = cv2.line(image, start_corner_1, (int(
        start_corner_1[0] + length), start_corner_1[1]), color, thickness)
    image = cv2.line(image, start_corner_1, (start_corner_1[0], int(
        start_corner_1[1] + length)), color, thickness)
    # Draw corner 2
    image = cv2.line(image, start_corner_2, (int(
        start_corner_2[0] - length), start_corner_2[1]), color, thickness)
    image = cv2.line(image, start_corner_2, (start_corner_2[0], int(
        start_corner_2[1] + length)), color, thickness)
    # Draw corner 3
    image = cv2.line(image, start_corner_3, (int(
        start_corner_3[0] + length), start_corner_3[1]), color, thickness)
    image = cv2.line(image, start_corner_3, (start_corner_3[0], int(
        start_corner_3[1] - length)), color, thickness)
    # Draw corner 3
    image = cv2.line(image, start_corner_4, (int(
        start_corner_4[0] - length), start_corner_4[1]), color, thickness)
    image = cv2.line(image, start_corner_4, (start_corner_4[0], int(
        start_corner_4[1] - length)), color, thickness)

    # Draw circle
    radius = int(min(image.shape[0], image.shape[1]) / 5)
    center = (int(image.shape[0]/2), int(image.shape[1]/2))
    image = cv2.circle(image, center, radius, color, thickness)

    # Draw cross-line
    start_cross_line = (center[0]-radius, center[1]+radius)
    end_cross_line = (center[0]+radius, center[1]-radius)
    image = cv2.line(image, start_cross_line, end_cross_line, color, thickness)

    return image
