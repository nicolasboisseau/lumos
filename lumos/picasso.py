#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Main functions to generate cell-painted platemaps with Lumos Picasso.
'''

import math
import os
from pathlib import Path
import pandas as pd
from shutil import copyfile
import shutil
from . import toolbox
from . import parameters
import cv2
from tqdm import tqdm
from . import logger
import numpy as np
import random


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

    # load images from path list + resize + convert to 8bit
    np_image_channels_array = []
    for current_image in img_channels_fullpath:
        # load image
        img16 = cv2.imread(str(current_image), -1)
        try:
            assert(not img16.shape == (0, 0))
        except:
            # create blank file
            img16 = np.full(shape=(1000, 1000, 1),
                            fill_value=0, dtype=np.uint16)
            logger.warning("Missing or corrupted image " + str(current_image))

        # resize image
        img16 = cv2.resize(
            src=img16,
            dsize=None,
            fx=rescale_ratio,
            fy=rescale_ratio,
            interpolation=cv2.INTER_CUBIC,
        )

        # convert image to 8bit
        img8 = (img16 / 256).astype("uint8")
        np_image_channels_array.append(img8)

    # Perform merging, according to the style
    if style == 'accurate':
        # initialize RGB channels
        red_channel = np.zeros(np_image_channels_array[0].shape)
        green_channel = np.zeros(np_image_channels_array[0].shape)
        blue_channel = np.zeros(np_image_channels_array[0].shape)

        # # compute the mean of each layer
        # means=[]
        # for idx in range(5):
        #     means.append(np.mean(np_image_channels_array[idx]))

        # # contrast image at the mean of each layer (naive approche)
        # for idx in range(5):
        #     vLambda = np.vectorize(lambda x : ((x**parameters.accurate_style_parameters['contrast_coeffs'][idx])/means[idx]) if parameters.accurate_style_parameters['contrast_coeffs'][idx] != 0 else x)
        #     np_image_channels_array[idx] = vLambda(np_image_channels_array[idx])

        # # perform thresholding at the mean of each layer
        # for idx in range(5):
        #     # thresholder = lambda x : x if x > (means[idx] * parameters.accurate_style_parameters['threshold_coeffs'][idx])  else 0
        #     # vThreshold = np.vectorize(thresholder)
        #     # np_image_channels_array[idx] = vThreshold(np_image_channels_array[idx])

        # get the current style's contrast coefficients
        contrast_coef = parameters.accurate_style_parameters['contrast']
        # add contrast to each layer according to coefficients
        for idx in range(5):
            contrast = contrast_coef[idx]
            f = float(131 * (contrast + 127)) / (127 * (131 - contrast))
            alpha_c = f
            gamma_c = 127*(1-f)
            np_image_channels_array[idx] = cv2.addWeighted(
                np_image_channels_array[idx], alpha_c, np_image_channels_array[idx], 0, gamma_c)

        # get the current style's intensity coefficients
        intensity_coef = parameters.accurate_style_parameters['intensity']
        # multiply the intensity of the channels using input coefs
        np_image_array_adjusted = []
        for idx in range(5):  # TODO: adapt for less than 5 selected channels
            np_image_array_adjusted.append(
                np_image_channels_array[idx] * intensity_coef[idx])
        np_image_channels_array = np_image_array_adjusted

        # combine the images according to their RGB coefficients
        for idx in range(5):
            red_channel = red_channel + \
                (np_image_channels_array[idx] / 255 *
                 parameters.cellplainting_channels_info[idx][3][0])
            green_channel = green_channel + \
                (np_image_channels_array[idx] / 255 *
                 parameters.cellplainting_channels_info[idx][3][1])
            blue_channel = blue_channel + \
                (np_image_channels_array[idx] / 255 *
                 parameters.cellplainting_channels_info[idx][3][2])

        # merge the Blue, Green and Red channels to form the final image
        merged_img = cv2.merge(
            (blue_channel, green_channel, red_channel)
        )

    else:

        # get the current style's intensity coefficients
        intensity_coef = parameters.fingerprint_style_dict[style][0]

        # get other parameters
        channel_order = parameters.fingerprint_style_dict[style][1]
        target_rgb = parameters.fingerprint_style_dict[style][2]

        # randomly initiate coefficients if they are missing
        if len(intensity_coef) == 0 and len(channel_order) == 0 and len(target_rgb) == 0:
            # parameters for each channel
            intensity_coef = [random.randint(
                1, max_multiply_coef) for x in range(5)]
            channel_order = [0, 1, 2, 3, 4]
            random.shuffle(channel_order)
            target_rgb = [0, 1, 2]
            random.shuffle(target_rgb)

        # multiply the intensity of the channels using input coefs
        np_image_array_adjusted = []
        # TODO: adapt for less than 5 selected channels?
        for index, current_coef_mult in enumerate(intensity_coef):
            np_image_array_adjusted.append(
                np_image_channels_array[index] * current_coef_mult)
        np_image_channels_array = np_image_array_adjusted

        # merge 2 extra channels each on 1 rgb channel
        np_image_channels_array[target_rgb[0]] = (
            np_image_channels_array[target_rgb[0]] +
            np_image_channels_array[channel_order[3]]
        )
        np_image_channels_array[target_rgb[1]] = (
            np_image_channels_array[target_rgb[1]] +
            np_image_channels_array[channel_order[4]]
        )

        merged_img = cv2.merge(
            (
                np_image_channels_array[channel_order[0]],
                np_image_channels_array[channel_order[1]],
                np_image_channels_array[channel_order[2]],
            )
        )

    # add fingerprint id on image
    if display_fingerprint:
        text = str(intensity_coef) + str(channel_order) + str(
            target_rgb) if style != 'accurate' else str(parameters.accurate_style_parameters)
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
    data_df, temp_folder, style, display_well_details, scope
):
    '''
    Generates a colorized image from all 5 channels of a well, for all wells, and saves it in the temporary directory.

            Parameters:
                    data_df (Pandas DataFrame): Dataframe containing the paths to each channel, of each site, of each well.
                    temp_folder_path (Path): The path to the folder where temporary data can be stored.
                    style (string): The name of the style being used to generate the colorized image.
                    style (string): The name of rendering style.
                    display_well_details (bool): Whether or not the name of the well should be printed on its generated image.
                    scope (string): 'plate' or 'wells' (this will have an impact on the resizing of the well/site images).

            Returns:
                    True (in case of success)
    '''

    if scope == 'wells':
        rescale_ratio = parameters.rescale_ratio_picasso_wells
    if scope == 'plate':
        rescale_ratio = parameters.rescale_ratio_picasso_plate

    # get the well list
    well_list = list(set(data_df["well"]))
    well_list.sort()

    # multiplex all well/site channels into 1 well/site 8bit color image
    wellprogressbar = tqdm(list(well_list), unit="wells", leave=False)
    for current_well in wellprogressbar:
        current_well_sites_multiplexed_image_list = []
        for current_site in range(1, 7):

            # get the image path list for the channels of the site, in the correct order
            current_sites_df = data_df[
                ((data_df["well"] == current_well) &
                 (data_df["site"] == current_site))
            ]
            current_sites_df_ordered = current_sites_df.sort_values(
                by="channel", ascending=True
            )

            channel_images_path = current_sites_df_ordered["fullpath"].to_list()

            # proceed to the generation using shaker 4 function with a first predefined fingerprint
            multiplexed_image = colorizer(
                img_channels_fullpath=channel_images_path,
                rescale_ratio=rescale_ratio,
                max_multiply_coef=8,
                style=style,
            )

            # collect image in memory
            current_well_sites_multiplexed_image_list.append(multiplexed_image)

        # save well image
        sites_row1 = cv2.hconcat(
            [
                current_well_sites_multiplexed_image_list[0],
                current_well_sites_multiplexed_image_list[1],
                current_well_sites_multiplexed_image_list[2],
            ]
        )
        sites_row2 = cv2.hconcat(
            [
                current_well_sites_multiplexed_image_list[3],
                current_well_sites_multiplexed_image_list[4],
                current_well_sites_multiplexed_image_list[5],
            ]
        )
        all_sites_image = cv2.vconcat([sites_row1, sites_row2])

        # add fingerprint id on image
        if display_well_details:
            text = str(current_well)
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(
                img=all_sites_image,
                text=text,
                org=(math.ceil(80*rescale_ratio), math.ceil(80*rescale_ratio)),
                fontFace=font,
                fontScale=2.2*rescale_ratio,
                thickness=math.ceil(3*rescale_ratio),
                color=(192, 192, 192),
                lineType=cv2.INTER_AREA,
            )
        if scope == 'plate':
            # add well marks on borders
            image_shape = all_sites_image.shape
            cv2.rectangle(
                all_sites_image,
                (0, 0),
                (image_shape[1], image_shape[0]),
                (192, 192, 192),
                math.ceil(8*rescale_ratio),
            )

        cv2.imwrite(
            temp_folder + "/wells/well-" + str(current_well) + ".png",
            all_sites_image,
        )

    return


def concatenate_well_images(well_list, temp_folder_path):
    '''
    Loads all temporary well images from the temporary directory and concatenates them into one image of the whole plate.

            Parameters:
                    well_list (string list): A list of all the well IDs (e.g. ['A01', 'A02', 'A03', ...]).
                    temp_folder_path (Path): The path to the folder where temporary data can be stored.

            Returns:
                    8-bit cv2 image: The concatenated image of all the wells
    '''

    # load all well images and store images in memory into a list
    print("Load well images in memory..")
    logger.info("Load well images in memory..")

    image_well_data = []
    for current_well in list(well_list):
        well_image = toolbox.load_well_image(
            current_well,
            temp_folder_path + "/wells",
        )
        image_well_data.append(well_image)

    # concatenate all the well images into horizontal stripes (1 per row)
    logger.info("Concatenate images into a plate..")

    image_row_data = []
    for current_plate_row in range(1, 17):

        # concatenate horizontally and vertically
        well_start_id = ((current_plate_row - 1) * 24) + 0
        well_end_id = current_plate_row * 24
        sites_row = cv2.hconcat(image_well_data[well_start_id:well_end_id])
        image_row_data.append(sites_row)

    # concatenate all the stripes into 1 image
    plate_image = cv2.vconcat(image_row_data)
    return plate_image


def get_images_full_path(channel_string_ids, plate_input_path):
    '''
    Finds all the paths to all the channels' images from the input folder

            Parameters:
                    channel_string_ids (string list): A list of all the channels IDs to be loaded.
                    plate_input_path (Path): The path to the folder where the input images are stored.

            Returns:
                    Path list: A list of all the paths to all images of each channels
    '''

    # get the files from the plate folder, for the targeted channel
    images_full_path_list = []
    for current_channel in channel_string_ids:
        current_channel_images_full_path_list = list(
            Path(plate_input_path).glob("*" + current_channel + ".tif")
        )
        images_full_path_list = images_full_path_list + \
            current_channel_images_full_path_list

    # check that we get expected images for a 384 well image
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

    # get the filenames list
    images_full_path_list.sort()
    images_filename_list = [str(x.name) for x in images_full_path_list]

    # get the well list
    image_well_list = [x.split("_")[1].split("_T")[0]
                       for x in images_filename_list]

    # get the siteid list (sitesid from 1 to 6)
    image_site_list = [
        x.split("_T0001F")[1].split("L")[0] for x in images_filename_list
    ]
    image_site_list_int = [int(x) for x in image_site_list]

    # get the channel id list (channel id from 1 to 5)
    image_channel_list = [x.split(".ti")[0][-2:] for x in images_filename_list]
    image_channel_list_int = [int(x) for x in image_channel_list]

    # zip all in a data structure
    image_data_zip = zip(
        image_well_list,
        image_site_list_int,
        image_channel_list_int,
        images_filename_list,
        images_full_path_list,
    )

    # convert the zip into dataframe
    data_df = pd.DataFrame(
        list(image_data_zip),
        columns=["well", "site", "channel", "filename", "fullpath"],
    )

    # get the theoretical well list for 384 well plate
    well_theoretical_list = [
        l + str(r).zfill(2) for l in "ABCDEFGHIJKLMNOP" for r in range(1, 25)
    ]
    well_channel_theoretical_list = [
        [x, r, c] for x in well_theoretical_list for r in range(1, 7) for c in range(1, 6)
    ]

    # create the theoretical well dataframe
    theoretical_data_df = pd.DataFrame(
        well_channel_theoretical_list, columns=["well", "site", "channel"]
    )

    # join the real wells with the theoric ones
    theoretical_data_df_joined = theoretical_data_df.merge(
        data_df,
        left_on=["well", "site", "channel"],
        right_on=["well", "site", "channel"],
        how="left",
    )

    # log if there is a delta between theory and actual plate wells
    delta = set(well_theoretical_list) - set(image_well_list)
    logger.info("Well Delta " + str(delta))

    return theoretical_data_df_joined


def copy_well_images_to_output_folder(temp_folder, output_path, well_list, plate_name, style):
    '''
    Copies all temporary well images into the output folder.
    Used for when the scope of the operation is 'well' and we want only the well images to be outputed.

            Parameters:
                    temp_folder (Path): The path to the temporary working directory where the well images are currently stored in.
                    output_path (Path): The path to the folder where the images should be copied to.
                    well_list (string list): A list of all the well IDs (e.g. ['A01', 'A02', 'A03', ...]).
                    plate_name (string): The name of the current plate (used to generate the output files' names).
                    style (string): The name of the style used for rendering (used to generate the output files' names).

            Returns:
                    8 bit cv2 image
    '''

    print("Putting well images into output folder..")

    for current_well in list(well_list):
        copyfile(
            temp_folder + "/wells/well-"+current_well+".png",
            output_path+'/'+plate_name+"-"+current_well+"-"+style+".png"
        )

    return


def picasso_generate_plate_image(
    source_path,
    plate_name,
    output_path,
    temp_folder_path,
    style,
    scope,
    display_well_details,
):
    '''
    Generates cell-painted colorized images of individual wells or of a whole plate.

            Parameters:
                    source_path (Path): The folder where the input images of the plate are stored.
                    plate_name (string): The name of the plate being rendered.
                    output_path (Path): The path to the folder where the output images should be stored.
                    temp_folder_path (Path): The path to the folder where temporary data can be stored.
                    style (string): The name of the rendering style.
                    scope (string):
                            Either 'wells' or 'plate'. Defines if we should generate individual well images,
                            or concatenate them into a single plate image.
                    display_well_details (bool): Whether or not the name of the well should be written on the generated images.

            Returns:
                    8 bit cv2 image(s):
                            If the scope is 'wells', then all colorized well images are outputed to the output folder.
                            If the scope is 'wells', then the well images are concatenated into one image of the whole
                            plate before being outputed to the output folder.
    '''

    # define a temp folder for the run
    temp_folder_path = temp_folder_path + "/tmpgen-" + plate_name + "picasso"

    # remove temp dir if existing
    shutil.rmtree(temp_folder_path, ignore_errors=True)

    # create the temporary directory structure to work on wells
    try:
        os.mkdir(temp_folder_path)
    except FileExistsError:
        pass
    # also create a subfolder to store well images
    try:
        os.mkdir(temp_folder_path + "/wells")
    except FileExistsError:
        pass

    # read the plate input path
    plate_input_path = Path(source_path)

    # get the list of all paths for each channel image
    images_full_path_list = get_images_full_path(
        # TODO: adapt for less than 5 selected channels?
        channel_string_ids=["C01", "C02", "C03", "C04", "C05"],
        plate_input_path=plate_input_path,
    )

    # build a database of the theorical plate
    # TODO: adapt for less than 5 selected channels?
    data_df = build_robustized_plate_dataframe(images_full_path_list)

    # get the well list
    well_list = list(set(data_df["well"]))
    well_list.sort()

    # generate images inside the temp folder
    generate_multiplexed_well_images(
        data_df=data_df,
        temp_folder=temp_folder_path,
        style=style,
        display_well_details=display_well_details,
        scope=scope,
    )

    if scope == 'plate':
        # concatenate well images into a plate image
        plate_image = concatenate_well_images(well_list, temp_folder_path)

        # save image
        plate_image_path = (
            output_path + "/" + plate_name + "-" +
            "picasso" + "-" + str(style) + ".jpg"
        )
        cv2.imwrite(plate_image_path, plate_image)

        print(" -> Generated image of size:", plate_image.shape)
        print(" -> Saved as ", plate_image_path)

    if scope == 'wells':
        # copy well files in output folder
        copy_well_images_to_output_folder(
            temp_folder_path, output_path, well_list, plate_name, style)

        print(" -> Saved well images in ", output_path)

    # purge temp files
    logger.info("Purge temporary folder")
    shutil.rmtree(temp_folder_path, ignore_errors=True)

    return
