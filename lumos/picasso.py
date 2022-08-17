#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Main functions to generate cell-painted platemaps with Lumos Picasso.
'''

import sys
import os
import math
import random
import shutil
from pathlib import Path

import cv2
from tqdm import tqdm
import numpy as np
import pandas as pd

from . import logger
from . import toolbox
from .config import get_config


def create_temp_and_output_folders(temp_path, output_path, scope, plate_name, style):
    '''
    Creates a directory structure depending on the scope. This is where the multiplexed well images will be stored.
    If the scope is 'plate', this will be a temporary directory for them to be stored before concatenation.
    If the scope is 'wells' or 'sites', this will be their output folder.

            Parameters:
                    temp_path (Path): The path to the folder where temporary data can be stored.
                    output_path (Path): The path to the folder where the output images should be stored.
                    scope (string): 'plate','wells' or 'sites' (this will have an impact on the resizing of the well/site images).
                    plate_name (string): Name of the current plate.
                    style (string): The name of the style being used to generate the colorized image.

            Returns:
                    Path to the root of the created folder structure.
    '''

    # If the scope is plate, we put the multiplexed well images into a Temp
    # folder before they are concatenated for final output.
    if scope == 'plate':
        # Create a Temp folder
        new_folder = temp_path + "/lumos-tmpgen-" + plate_name + "-picasso"
        # Remove folder if existing
        shutil.rmtree(new_folder, ignore_errors=True)
        # Create the temporary directory structure to work on wells
        try:
            os.mkdir(new_folder)
            os.mkdir(new_folder + "/wells")
        except FileExistsError:
            pass

    # If the scope is wells or sites, we output directly the multiplexed well
    # images in the output folder.
    if scope in ('wells', 'sites'):
        # Create the output folder
        new_folder = output_path + f"/{scope}_{plate_name}_{style}"
        try:
            os.mkdir(new_folder)
        except FileExistsError:
            pass

    return new_folder


def colorizer(
    site_df,
    rescale_ratio,
    style,
    max_multiply_coef=1,
    display_fingerprint=False,
):
    '''
    Merges input images from different channels into one RGB image.

            Parameters:
                    site_df (DataFrame): The table of all the image-info for the current site.
                    rescale_ratio (float): The ratio used to rescale the image before generation.
                    style (string): The name of the style being used to generate the colorized image.
                    max_multiply_coef (int): Max multiplication factor in case of random coefficient generation.
                    display_fingerprint (bool): Whether the coefficients used for generation should be printed on the output image.

            Returns:
                    8-bit cv2 image
    '''

    # Reset the index of each channel entry
    site_df.reset_index(inplace=True)

    # For each channel image of the site:
    # Load images from path list + resize + convert to 8bit
    image_channels_array = []
    for _, current_channel in site_df.iterrows():
        try:
            # Load image
            img = cv2.imread(str(current_channel['fullpath']), -1)
            # Check that the image loaded successfully
            assert img.shape != (0, 0)
            # Resize image according to rescale ratio
            img = cv2.resize(
                src=img,
                dsize=None,
                fx=rescale_ratio,
                fy=rescale_ratio,
                interpolation=cv2.INTER_CUBIC,
            )
            # Convert image to 8bit
            img = (img / 256).astype("uint8")
        except:
            logger.warning("Missing or corrupted image " +
                           str(current_channel['fullpath']))

            # Create blank file if the image can't be loaded
            height = int(get_config()['image_dimensions'].split(
                'x', maxsplit=1)[0])
            width = int(get_config()['image_dimensions'].rsplit(
                'x', maxsplit=1)[-1])
            img = np.full(shape=(height, width, 1),
                          fill_value=0,
                          dtype=np.uint8)
            img = cv2.resize(
                src=img,
                dsize=None,
                fx=rescale_ratio,
                fy=rescale_ratio,
                interpolation=cv2.INTER_CUBIC,
            )

        image_channels_array.append(img)

    # Perform merging, according to the style
    if style == 'classic':

        # Initialize RGB channels to zeros
        site_shape = image_channels_array[0].shape
        red_channel = np.zeros(site_shape)
        green_channel = np.zeros(site_shape)
        blue_channel = np.zeros(site_shape)

        # Add contrast to each layer according to coefficients
        for idx, current_channel in site_df.iterrows():
            contrast_coef = get_config()['channel_info'][current_channel['channel']
                                                         ]['cp_contrast']

            alpha_c = float(131 * (contrast_coef + 127)) / \
                (127 * (131 - contrast_coef))
            gamma_c = 127*(1-alpha_c)

            image_channels_array[idx] = cv2.addWeighted(
                image_channels_array[idx], alpha_c, image_channels_array[idx], 0, gamma_c)

        # Multiply the intensity of the channels by coefs
        for idx, current_channel in site_df.iterrows():
            intensity_coef = get_config()['channel_info'][current_channel['channel']
                                                          ]['cp_intensity']

            # Create a mask to check when value will overflow
            mask = (image_channels_array[idx] > (255 / intensity_coef)
                    ) if intensity_coef != 0 else False

            # Clip the result to be in [0;255] if overflow
            image_channels_array[idx] = np.where(
                mask,
                255,
                image_channels_array[idx] * intensity_coef)

        # Combine the images according to their RGB coefficients
        for idx, current_channel in site_df.iterrows():
            rgb_coef = get_config()[
                'channel_info'][current_channel['channel']]['rgb']
            red_channel = red_channel + \
                (image_channels_array[idx] / 255 * rgb_coef[0])
            green_channel = green_channel + \
                (image_channels_array[idx] / 255 * rgb_coef[1])
            blue_channel = blue_channel + \
                (image_channels_array[idx] / 255 * rgb_coef[2])

        # Merge the Blue, Green and Red channels to form the final image
        merged_img = cv2.merge(
            (blue_channel, green_channel, red_channel)
        )

    else:

        # Get the current style's parameters
        intensity_coef = get_config()['fingerprint_style_dict'][style][0]
        channel_order = get_config()['fingerprint_style_dict'][style][1]
        target_rgb = get_config()['fingerprint_style_dict'][style][2]

        # Randomly initiate coefficients for each channel if they are missing
        if len(intensity_coef) == 0 and len(channel_order) == 0 and len(target_rgb) == 0:
            intensity_coef = [random.randint(
                1, max_multiply_coef) for _ in range(5)]
            channel_order = [0, 1, 2, 3, 4]
            random.shuffle(channel_order)
            target_rgb = [0, 1, 2]
            random.shuffle(target_rgb)

        # Multiply the intensity of the channels using input coefs
        image_array_adjusted = []
        for index, current_coef_mult in enumerate(intensity_coef):
            image_array_adjusted.append(
                image_channels_array[index] * current_coef_mult)
        image_channels_array = image_array_adjusted

        # Merge 2 extra channels each on 1 rgb channel
        image_channels_array[target_rgb[0]] = (
            image_channels_array[target_rgb[0]] +
            image_channels_array[channel_order[3]]
        )
        image_channels_array[target_rgb[1]] = (
            image_channels_array[target_rgb[1]] +
            image_channels_array[channel_order[4]]
        )

        # Merge the 3 BGR channels into one color image
        merged_img = cv2.merge(
            (
                image_channels_array[channel_order[0]],
                image_channels_array[channel_order[1]],
                image_channels_array[channel_order[2]],
            )
        )

    # Add fingerprint id on image
    if display_fingerprint:
        # Build the fingerprint text to display
        if style != 'classic':
            text = str(intensity_coef) + str(channel_order) + str(
                target_rgb)
        else:
            intensities = [x.get('cp_intensity')
                           for x in get_config()['channel_info'].values()]
            contrasts = [x.get('cp_contrast')
                         for x in get_config()['channel_info'].values()]
            filtered_intensities = list(filter(None, intensities))
            filtered_contrasts = list(filter(None, contrasts))
            text = str(filtered_intensities) + ' - ' + str(filtered_contrasts)

        # Add text to image
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(
            merged_img,
            text,
            (math.ceil(10*rescale_ratio), math.ceil(990*rescale_ratio)),
            font,
            0.8*rescale_ratio,
            (192, 192, 192),
            math.ceil(2*rescale_ratio),
            cv2.INTER_AREA,
        )

    return merged_img


def generate_multiplexed_well_images(
    data_df,
    well_list,
    gen_image_output_folder,
    platemap_path,
    output_format,
    style,
    display_well_details,
    plate_name,
    scope
):
    '''
    Generates a colorized image from all 5 channels of a well, for all wells, and saves it in the temporary directory.

            Parameters:
                    data_df (Pandas DataFrame): Dataframe containing the paths to each channel, of each site, of each well.
                    well_list (string list): The list of wells to be generated
                    gen_image_output_folder (Path): The path to the folder where the images generated should be stored.
                    platemap_path (Path): The path to the platemap file of the plate.
                    output_format (string): The format/extension of the generated output images.
                    style (string): The name of the style being used to generate the colorized image.
                    display_well_details (bool): Whether or not the name of the well should be printed on its generated image.
                    plate_name (string): Name of the current plate.
                    scope (string): 'plate','wells' or 'sites' (this will have an impact on the resizing of the well/site images).

            Returns:
                    True (in case of success)
    '''

    # Define the rescale ratio based on the scope
    if scope == 'wells':
        rescale_ratio = get_config()['rescale_ratio_cp_wells']
    elif scope == 'plate':
        rescale_ratio = get_config()['rescale_ratio_cp_plate']
    else:
        rescale_ratio = 1

    # Multiplex all well/site channels into 1 well/site 8bit colored image
    well_progressbar = tqdm(well_list, unit="wells", leave=False, disable=not logger.ENABLED)
    for current_well in well_progressbar:
        # For each well, generate the multiplexed images of its 6 sites
        current_well_sites_multiplexed_image_list = []
        for current_site in range(1, data_df["site"].max()+1):

            # Get the image path list for the channels of the site, in the correct order
            current_site_df = data_df[
                ((data_df["well"] == current_well) &
                 (data_df["site"] == current_site))
            ]

            # Generate the multiplexed image of the current site
            multiplexed_site_image = colorizer(
                site_df=current_site_df.copy(),
                rescale_ratio=rescale_ratio,
                max_multiply_coef=8,
                style=style,
            )

            if scope == 'sites':
                # Return the site image directly
                cv2.imwrite(
                    gen_image_output_folder +
                    f"/{current_well}_s{current_site}.{output_format}",
                    multiplexed_site_image,
                )

            else:
                # Collect images in memory for site image concatenation
                # into one well image
                current_well_sites_multiplexed_image_list.append(
                    multiplexed_site_image)

        if scope in ('plate', 'wells'):

            # Concatenate the site images into one well image
            nb_site_row = int(
                get_config()['site_grid'].split('x', maxsplit=1)[0])
            nb_site_col = int(
                get_config()['site_grid'].rsplit('x', maxsplit=1)[-1])

            current_well_image = toolbox.concatenate_images_in_grid(
                current_well_sites_multiplexed_image_list,
                nb_site_row,
                nb_site_col,
            )

            # Add fingerprint on image
            if display_well_details:

                # Compose well label
                text = current_well
                if platemap_path is not None:
                    # If the platemap is provided, extract all required columns
                    pm_well_column = get_config(
                    )['platemap_columns']['well_column_name']
                    pm_id_column = get_config(
                    )['platemap_columns']['id_column_name']

                    platemap_df = pd.read_csv(platemap_path,
                                              sep='\t',
                                              header=0,
                                              usecols=[pm_well_column, pm_id_column])

                    # Select the row of the current well (if there is one)
                    current_platemap_row = platemap_df.loc[platemap_df[pm_well_column]
                                                           == current_well]

                    # If there is indeed a row, add the JCP to the well label
                    if len(current_platemap_row.index) != 0:
                        current_compound = current_platemap_row.iloc[0][pm_id_column]
                        text = current_well + " - " + current_compound

                # Add the label to the well image
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(
                    img=current_well_image,
                    text=text,
                    org=(math.ceil(80*rescale_ratio),
                         math.ceil(80*rescale_ratio)),
                    fontFace=font,
                    fontScale=2.2*rescale_ratio,
                    thickness=math.ceil(3*rescale_ratio),
                    color=(192, 192, 192),
                    lineType=cv2.INTER_AREA,
                )

            # Output the well images in the pre-defined temp/output folder
            # depending on the scope
            if scope == 'plate':
                # Add well borders
                image_shape = current_well_image.shape
                cv2.rectangle(
                    current_well_image,
                    (0, 0),
                    (image_shape[1], image_shape[0]),
                    (192, 192, 192),
                    math.ceil(8*rescale_ratio),
                )
                # Return the image
                cv2.imwrite(
                    gen_image_output_folder +
                    f"/wells/well-{current_well}.{output_format}",
                    current_well_image,
                )
            elif scope == 'wells':
                # Return the image
                cv2.imwrite(
                    gen_image_output_folder +
                    f"/{plate_name}_{current_well}_{style}.{output_format}",
                    current_well_image,
                )


def concatenate_well_images(well_list, temp_folder_path, output_format):
    '''
    Loads all temporary well images from the temporary directory and concatenates them into one image of the whole plate.

            Parameters:
                    well_list (string list): A list of all the well IDs (e.g. ['A01', 'A02', 'A03', ...]).
                    temp_folder_path (Path): The path to the folder where temporary data can be stored.

            Returns:
                    8-bit cv2 image: The concatenated image of all the wells
    '''

    # Load all well images and store images in memory into a list
    print("Load well images in memory..")
    logger.info("Load well images in memory..")

    well_images = []
    for current_well in well_list:
        well_image = toolbox.load_well_image(
            current_well,
            temp_folder_path + "/wells",
            image_format=output_format,
        )
        well_images.append(well_image)

    # Concatenate all the well images into horizontal stripes (1 per row)
    logger.info("Concatenate images into a plate..")

    # Concatenate all the well images into one plate image
    nb_well_row = int(get_config()['well_grid'].split('x', maxsplit=1)[0])
    nb_well_col = int(get_config()['well_grid'].rsplit('x', maxsplit=1)[-1])

    plate_image = toolbox.concatenate_images_in_grid(
        well_images, nb_well_row, nb_well_col)

    return plate_image


def picasso_generate_plate_image(
    source_path,
    plate_name,
    output_path,
    temp_folder_path,
    platemap_path,
    output_format,
    style,
    scope,
    single_well,
    display_well_details,
):
    '''
    Generates cell-painted colorized images of individual wells or of a whole plate.

            Parameters:
                    source_path (Path): The folder where the input images of the plate are stored.
                    plate_name (string): The name of the plate being rendered.
                    output_path (Path): The path to the folder where the output images should be stored.
                    temp_folder_path (Path): The path to the folder where temporary data can be stored.
                    platemap_path (Path): The path to the platemap file of the plate.
                    output_format (string): The format/extension of the generated output images.
                    style (string): The name of the rendering style.
                    scope (string):
                            Either 'wells' or 'plate'. Defines if we should generate individual well images,
                            or concatenate them into a single plate image.
                    single_well (string): If not None, name of a unique well to render the image for.
                    display_well_details (bool): Whether or not the name of the well should be written on the generated images.

            Returns:
                    8 bit cv2 image(s):
                            If the scope is 'wells', then all colorized well images are outputted to the output folder.
                            If the scope is 'plate', then the well images are concatenated into one image of the whole
                            plate before being outputted to the output folder.
    '''

    created_folder = create_temp_and_output_folders(
        temp_folder_path, output_path, scope, plate_name, style)

    channels_to_include = get_config()['cp_channels_to_use'] \
        if style == 'classic' else list(get_config()['channel_info'].keys())[:5]

    # Build a Table of the available images of the plate
    data_df = toolbox.build_input_images_df(
        source_path, channels_to_include)

    # Get the list of wells to be rendered
    well_list = sorted(data_df["well"].unique())

    # Handle the single-well request
    if single_well and single_well not in well_list:
        logger.error("Single-well parameter not a valid well")
        logger.err_print(f"ERROR: {single_well} is not a valid well.",
                         color='bright_red')
        sys.exit(1)
    elif single_well:
        # Override the list of wells to be rendered
        # with the single well
        well_list = [single_well]

    # Generate the Cell-painted well images
    generate_multiplexed_well_images(
        data_df=data_df,
        well_list=well_list,
        gen_image_output_folder=created_folder,
        platemap_path=platemap_path,
        output_format=output_format,
        style=style,
        display_well_details=display_well_details,
        plate_name=plate_name,
        scope=scope,
    )

    if scope in ('sites', 'wells'):
        print(f" -> Saved {scope} images in {output_path}")

    elif scope == 'plate':
        # Concatenate well images into a plate image
        plate_image = concatenate_well_images(
            well_list, created_folder, output_format)

        # Save the concatenated image in the output folder
        plate_image_path = (
            output_path + f"/{plate_name}-picasso-{style}.{output_format}"
        )
        cv2.imwrite(plate_image_path, plate_image)

        print(" -> Generated image of size:", plate_image.shape)
        print(" -> Saved as ", plate_image_path)

        # Purge the temp files (only for plate)
        logger.info("Purge temporary folder")
        shutil.rmtree(created_folder, ignore_errors=True)
