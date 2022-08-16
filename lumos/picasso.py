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
from . import parameters


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
        new_folder = temp_path + "/tmpgen-" + plate_name + "picasso"
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


def get_images_full_path(selected_channels, plate_input_path):
    '''
    Finds all the paths to all the channels' images from the input folder

            Parameters:
                    selected_channels (string list): A list of all the channels IDs to be loaded.
                    plate_input_path (Path): The path to the folder where the input images are stored.

            Returns:
                    Path list: A list of all the paths to all images of each channels
    '''

    # Get the files from the plate folder, for the targeted channel
    images_full_path_list = []
    for channel in selected_channels:
        current_channel_images_full_path_list = list(
            Path(plate_input_path).glob("*" + channel + ".tif")
        )
        images_full_path_list.extend(current_channel_images_full_path_list)

    # Check that we get expected images for a 384 well image
    try:
        assert len(images_full_path_list) == 2304 * 5
    except AssertionError:
        print(
            "The plate does not have the exact image count: expected " +
            str(2304 * 5) + ", got "
            + str(len(images_full_path_list)),
        )

    return images_full_path_list


def build_robustized_plate_dataframe(images_full_path_list):
    '''
    Scans the input list of Paths to map it to the expected plate structure.
    Missing images or wells must be taken into account in the final render.

            Parameters:
                    images_full_path_list (Path list): A list of all the paths to all the images to be included in the render.

            Returns:
                    Pandas DataFrame:
                            A database of all the image paths to each channel, of each site, of each well.
                            Its columns are: ["well", "site", "channel", "filename", "fullpath"].
    '''

    # Get the filenames list
    images_full_path_list.sort()
    images_filename_list = [str(x.name) for x in images_full_path_list]

    # Get the well list
    image_well_list = [x.split("_")[1].split("_T")[0]
                       for x in images_filename_list]

    # Get the siteid list (sitesid from 1 to 6)
    image_site_list = [
        x.split("_T0001F")[1].split("L")[0] for x in images_filename_list
    ]
    image_site_list_int = [int(x) for x in image_site_list]

    # Get the channel id list (channel id from 1 to 5)
    image_channel_list = [x.split(".ti")[0][-2:] for x in images_filename_list]
    image_channel_list_int = [int(x) for x in image_channel_list]

    # Zip all in a data structure
    image_data_zip = zip(
        image_well_list,
        image_site_list_int,
        image_channel_list_int,
        images_filename_list,
        images_full_path_list,
    )

    # Convert the zip into dataframe
    data_df = pd.DataFrame(
        list(image_data_zip),
        columns=["well", "site", "channel", "filename", "fullpath"],
    )

    # Get the theoretical well list for 384 well plate
    well_theoretical_list = [
        l + str(r).zfill(2) for l in "ABCDEFGHIJKLMNOP" for r in range(1, 25)
    ]
    well_channel_theoretical_list = [
        [w, s, c] for w in well_theoretical_list for s in range(1, 7) for c in range(1, 6)
    ]

    # Create the theoretical well dataframe
    theoretical_data_df = pd.DataFrame(
        well_channel_theoretical_list, columns=["well", "site", "channel"]
    )

    # Join the real wells with the theoretical ones
    theoretical_data_df_joined = theoretical_data_df.merge(
        data_df,
        left_on=["well", "site", "channel"],
        right_on=["well", "site", "channel"],
        how="left",
    )

    # Log if there is a delta between theory and actual plate wells
    delta = set(well_theoretical_list) - set(image_well_list)
    logger.info("Well Delta " + str(delta))

    return theoretical_data_df_joined


def colorizer(
    img_channels_fullpath,
    rescale_ratio,
    style,
    max_multiply_coef=1,
    display_fingerprint=False,
):
    '''
    Merges input images from different channels into one RGB image.

            Parameters:
                    img_channels_fullpath (Path list): The list of paths to the channels' images (in proper order [C01,C02,C03,C04,C05]).
                    rescale_ratio (float): The ratio used to rescale the image before generation.
                    style (string): The name of the style being used to generate the colorized image.
                    max_multiply_coef (int): Max multiplication factor in case of random coefficient generation.
                    display_fingerprint (bool): Whether the coefficients used for generation should be printed on the output image.

            Returns:
                    8-bit cv2 image
    '''

    # For each channel image of the site:
    # Load images from path list + resize + convert to 8bit
    np_image_channels_array = []
    for current_image in img_channels_fullpath:
        # Load image
        img16 = cv2.imread(str(current_image), -1)
        try:
            assert img16.shape != (0, 0)
        except:
            # Create blank file if the image can't be loaded
            img16 = np.full(shape=(1000, 1000, 1),
                            fill_value=0, dtype=np.uint16)
            logger.warning("Missing or corrupted image " + str(current_image))

        # Resize image according to rescale ratio
        img16 = cv2.resize(
            src=img16,
            dsize=None,
            fx=rescale_ratio,
            fy=rescale_ratio,
            interpolation=cv2.INTER_CUBIC,
        )

        # Convert image to 8bit
        img8 = (img16 / 256).astype("uint8")
        np_image_channels_array.append(img8)

    # Perform merging, according to the style
    if style == 'classic':
        # Initialize RGB channels to zeros
        red_channel = np.zeros(np_image_channels_array[0].shape)
        green_channel = np.zeros(np_image_channels_array[0].shape)
        blue_channel = np.zeros(np_image_channels_array[0].shape)

        # Get the current style's contrast coefficients
        contrast_coef = parameters.classic_style_parameters['contrast']
        # Add contrast to each layer according to coefficients
        for idx in range(5):
            contrast = contrast_coef[idx]
            alpha_c = float(131 * (contrast + 127)) / (127 * (131 - contrast))
            gamma_c = 127*(1-alpha_c)
            np_image_channels_array[idx] = cv2.addWeighted(
                np_image_channels_array[idx], alpha_c, np_image_channels_array[idx], 0, gamma_c)

        # Get the current style's intensity coefficients
        intensity_coef = parameters.classic_style_parameters['intensity']
        # Multiply the intensity of the channels using input coefs
        for idx, image in enumerate(np_image_channels_array):
            # Create a mask to check when value will overflow
            mask = (image > (255 / intensity_coef[idx])
                    ) if intensity_coef[idx] != 0 else False
            # Clip the result to be in [0;255] if overflow
            np_image_channels_array[idx] = np.where(
                mask,
                255,
                image * intensity_coef[idx])

        # Combine the images according to their RGB coefficients
        for idx, tuned_channel_image in enumerate(np_image_channels_array):
            red_channel = red_channel + \
                (tuned_channel_image / 255 *
                 parameters.cellpainting_channels_info[idx][3][0])
            green_channel = green_channel + \
                (tuned_channel_image / 255 *
                 parameters.cellpainting_channels_info[idx][3][1])
            blue_channel = blue_channel + \
                (tuned_channel_image / 255 *
                 parameters.cellpainting_channels_info[idx][3][2])

        # Merge the Blue, Green and Red channels to form the final image
        merged_img = cv2.merge(
            (blue_channel, green_channel, red_channel)
        )

    else:

        # Get the current style's parameters
        intensity_coef = parameters.fingerprint_style_dict[style][0]
        channel_order = parameters.fingerprint_style_dict[style][1]
        target_rgb = parameters.fingerprint_style_dict[style][2]

        # Randomly initiate coefficients for each channel if they are missing
        if len(intensity_coef) == 0 and len(channel_order) == 0 and len(target_rgb) == 0:
            intensity_coef = [random.randint(
                1, max_multiply_coef) for _ in range(5)]
            channel_order = [0, 1, 2, 3, 4]
            random.shuffle(channel_order)
            target_rgb = [0, 1, 2]
            random.shuffle(target_rgb)

        # Multiply the intensity of the channels using input coefs
        np_image_array_adjusted = []
        # TODO: adapt for less than 5 selected channels?
        for index, current_coef_mult in enumerate(intensity_coef):
            np_image_array_adjusted.append(
                np_image_channels_array[index] * current_coef_mult)
        np_image_channels_array = np_image_array_adjusted

        # Merge 2 extra channels each on 1 rgb channel
        np_image_channels_array[target_rgb[0]] = (
            np_image_channels_array[target_rgb[0]] +
            np_image_channels_array[channel_order[3]]
        )
        np_image_channels_array[target_rgb[1]] = (
            np_image_channels_array[target_rgb[1]] +
            np_image_channels_array[channel_order[4]]
        )

        # Merge the 3 BGR channels into one color image
        merged_img = cv2.merge(
            (
                np_image_channels_array[channel_order[0]],
                np_image_channels_array[channel_order[1]],
                np_image_channels_array[channel_order[2]],
            )
        )

    # Add fingerprint id on image
    if display_fingerprint:
        text = str(intensity_coef) + str(channel_order) + str(
            target_rgb) if style != 'classic' else str(parameters.classic_style_parameters)
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
        rescale_ratio = parameters.rescale_ratio_picasso_wells
    elif scope == 'plate':
        rescale_ratio = parameters.rescale_ratio_picasso_plate
    else:
        rescale_ratio = 1

    # Multiplex all well/site channels into 1 well/site 8bit colored image
    wellprogressbar = tqdm(well_list, unit="wells", leave=False)
    for current_well in wellprogressbar:
        # For each well, generate the multiplexed images of its 6 sites
        current_well_sites_multiplexed_image_list = []
        for current_site in range(1, 7):

            # Get the image path list for the channels of the site, in the correct order
            current_sites_df = data_df[
                ((data_df["well"] == current_well) &
                 (data_df["site"] == current_site))
            ]
            current_sites_df_ordered = current_sites_df.sort_values(
                by="channel", ascending=True
            )
            channel_images_path = \
                current_sites_df_ordered["fullpath"].to_list()

            # Generate the multiplexed image of the current site
            multiplexed_site_image = colorizer(
                img_channels_fullpath=channel_images_path,
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
            sites_row1 = cv2.hconcat(
                current_well_sites_multiplexed_image_list[:3]
            )
            sites_row2 = cv2.hconcat(
                current_well_sites_multiplexed_image_list[3:]
            )
            current_well_image = cv2.vconcat([sites_row1, sites_row2])

            # Add fingerprint on image
            if display_well_details:

                # Compose well label
                text = current_well
                if platemap_path is not None:
                    # If the platemap is provided, extract all required columns
                    pm_well_column = parameters.platemap_columns['well_column_name']
                    pm_id_column = parameters.platemap_columns['id_column_name']

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

    image_well_data = []
    for current_well in well_list:
        well_image = toolbox.load_well_image(
            current_well,
            temp_folder_path + "/wells",
            image_format=output_format,
        )
        image_well_data.append(well_image)

    # Concatenate all the well images into horizontal stripes (1 per row)
    logger.info("Concatenate images into a plate..")

    image_row_data = []
    for current_plate_row in range(1, 17):
        # Concatenate horizontally and vertically
        well_start_id = ((current_plate_row - 1) * 24) + 0
        well_end_id = current_plate_row * 24
        sites_row = cv2.hconcat(image_well_data[well_start_id:well_end_id])
        image_row_data.append(sites_row)

    # Concatenate all the stripes into 1 image
    plate_image = cv2.vconcat(image_row_data)

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
                            If the scope is 'wells', then all colorized well images are outputed to the output folder.
                            If the scope is 'plate', then the well images are concatenated into one image of the whole
                            plate before being outputed to the output folder.
    '''

    created_folder = create_temp_and_output_folders(
        temp_folder_path, output_path, scope, plate_name, style)

    # Get the list of all paths for each channel image
    images_full_path_list = get_images_full_path(
        selected_channels=["C01", "C02", "C03", "C04", "C05"],
        plate_input_path=source_path,
    )

    # Build a database of the theorical plate
    # TODO: adapt for less than 5 selected channels?
    data_df = build_robustized_plate_dataframe(images_full_path_list)

    # Get the list of wells to be rendered
    well_list = sorted(data_df["well"].unique())

    # Handle the single-well request
    if single_well and single_well not in well_list:
        logger.error("Single-well parameter not a valid well")
        print(os.linesep, "ERROR:", single_well,
              "is not a valid well.", os.linesep)
        sys.exit()
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

        # Purge the temp files
        logger.info("Purge temporary folder")
        shutil.rmtree(created_folder, ignore_errors=True)
