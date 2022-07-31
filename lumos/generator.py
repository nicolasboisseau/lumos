#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Main functions to generate platemaps with lumos

"""

import os
from pathlib import Path, PureWindowsPath
import pandas as pd
from shutil import copyfile
import shutil
from . import toolbox
from . import parameters
import cv2
from tqdm import tqdm
import logging
import numpy as np


def generate_plate_image(
    plate_input_path_string,
    plate_name,
    channel_to_render,
    channel_label,
    temp_folder,
):
    """Generate an image of a cellpainting plate for a specific channel
    Args:
    plate_images_folder_path : The folder where the images of the plate are stored
    plate_name: name of the plate
    channel_to_render: the cellpainting channel to render
    channel_label: The text describing the channel type
    temp_folder_path: The folder where temporary data can be stored
    Return: 8 bit cv2 image
    """

    # define a temp folder for the run
    temp_folder = temp_folder + "/tmpgen-" + plate_name + channel_to_render

    # remove temp dir if existing
    shutil.rmtree(temp_folder, ignore_errors=True)

    # create the temporary directory structure to work on images
    try:
        os.mkdir(temp_folder)
        os.mkdir(temp_folder + "/wells")

    except FileExistsError:
        pass

    # read the plate input path
    plate_input_path = Path(PureWindowsPath(plate_input_path_string))

    # get the files from the plate folder, for the targeted channel
    images_full_path_list = list(
        Path(plate_input_path).glob("*" + channel_to_render + ".tif")
    )

    # check that we get 2304 images for a 384 well image
    try:
        assert len(images_full_path_list) == 2304
    except AssertionError:
        print(
            "The plate does not have the exact image count expected",
            len(images_full_path_list),
        )

    logging.info(
        "Start plate image generation for channel:"
        + str(channel_to_render)
        + " "
        + str(channel_label)
    )

    # get the filenames list
    images_full_path_list.sort()
    images_filename_list = [str(x.name) for x in images_full_path_list]

    # get the well list
    image_well_list = [x.split("_")[1].split("_T")[0] for x in images_filename_list]

    # get the siteid list (sitesid from 1 to 6)
    image_site_list = [
        x.split("_T0001F")[1].split("L")[0] for x in images_filename_list
    ]
    image_site_list_int = [int(x) for x in image_site_list]

    # zip all in a data structure
    image_data_zip = zip(
        image_well_list,
        image_site_list_int,
        images_filename_list,
        images_full_path_list,
    )

    # convert the zip into dataframe
    data_df = pd.DataFrame(
        list(image_data_zip), columns=["well", "site", "filename", "fullpath"]
    )

    # get the theoretical well list for 384 well plate
    well_theoretical_list = [
        l + str(r).zfill(2) for l in "ABCDEFGHIJKLMNOP" for r in range(1, 25)
    ]
    well_site_theoretical_list = [
        [x, r] for x in well_theoretical_list for r in range(1, 7)
    ]

    # create the theoretical well dataframe
    theoretical_data_df = pd.DataFrame(
        well_site_theoretical_list, columns=["well", "site"]
    )

    # join the real wells with the theoric ones
    theoretical_data_df_joined = theoretical_data_df.merge(
        data_df,
        left_on=["well", "site"],
        right_on=["well", "site"],
        how="left",
    )

    # log if there is a delta between theory and actual plate wells
    delta = set(well_theoretical_list) - set(image_well_list)
    logging.info("Well Delta " + str(delta))

    # promote theoretical over actual
    data_df = theoretical_data_df_joined

    # get the site images and store them locally
    logging.info("Copy sources images in temp folder..")

    for index, current_image in tqdm(
        data_df.iterrows(),
        desc="Download images to temp",
        unit="images",
        colour="#006464",
        leave=True,
    ):
        # do not copy if file exists
        if not os.path.isfile(temp_folder + "/" + str(current_image["filename"])):
            try:
                copyfile(
                    current_image["fullpath"],
                    temp_folder + "/" + str(current_image["filename"]),
                )
            except TypeError:
                logging.warning(
                    "TypeError:"
                    + str(current_image["fullpath"])
                    + str(temp_folder)
                    + "/"
                    + str(current_image["filename"])
                )

    # get the well set
    well_list = list(set(data_df["well"]))
    well_list.sort()

    logging.info("Generate Well images")

    # generate one image per well by concatenation of image sites
    wellprogressbar = tqdm(list(well_list), unit="wells", leave=False)
    for current_well in wellprogressbar:

        wellprogressbar.set_description("Processing well %s" % current_well)
        # get the 6 images metadate of the well
        current_wells_df = data_df[data_df["well"] == current_well]

        # load 6 wells into an image list
        image_list = []
        for current_site in range(1, 7):
            img = toolbox.load_site_image(current_site, current_wells_df, temp_folder)
            try:
                img.shape
            except:
                # create blank file
                img = np.full((1000, 1000, 1), 32768, np.uint16)
                logging.warning("Missing file in well" + current_well)

            image_list.append(img)

        # clip and rescale each image individualy
        rescaled_image_list = []
        for img in image_list:
            img_norm = img * parameters.channel_coefficients[channel_to_render]
            rescaled_image_list.append(img_norm)

        # concatenate horizontally and vertically
        sites_row1 = cv2.hconcat(
            [rescaled_image_list[0], rescaled_image_list[1], rescaled_image_list[2]]
        )
        sites_row2 = cv2.hconcat(
            [rescaled_image_list[3], rescaled_image_list[4], rescaled_image_list[5]]
        )
        all_sites_image = cv2.vconcat([sites_row1, sites_row2])
        all_sites_image_norm = all_sites_image

        # convert to 8 bit
        # comment the following line to generate interesting images
        all_sites_image = all_sites_image_norm / 256
        all_sites_image = all_sites_image.astype("uint8")

        # add well id on image
        text = current_well + " " + channel_label
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(
            all_sites_image,
            text,
            (25, 125),
            font,
            4,
            (192, 192, 192),
            8,
            cv2.INTER_AREA,
        )

        # add well marks on borders
        image_shape = all_sites_image.shape
        cv2.rectangle(
            all_sites_image,
            (0, 0),
            (image_shape[1], image_shape[0]),
            (192, 192, 192),
            8,
        )
        # resize
        all_sites_image_resized = cv2.resize(
            src=all_sites_image,
            dsize=None,
            fx=parameters.rescale_ratio,
            fy=parameters.rescale_ratio,
            interpolation=cv2.INTER_CUBIC,
        )
        # save
        cv2.imwrite(
            temp_folder + "/wells/well-" + str(current_well) + ".png",
            all_sites_image_resized,
        )

    # load all well images and store images in memory into a list
    print("Load well images in memory..")
    logging.info("Generate Well images")

    image_well_data = []
    for current_well in list(well_list):
        well_image = toolbox.load_well_image(
            current_well,
            temp_folder + "/wells",
        )
        image_well_data.append(well_image)

    # concatenate all the well images into horizontal stripes (1 per row)
    logging.info("Concatenate images into a plate..")

    image_row_data = []
    for current_plate_row in range(1, 17):

        # concatenate horizontally and vertically
        well_start_id = ((current_plate_row - 1) * 24) + 0
        well_end_id = current_plate_row * 24
        sites_row = cv2.hconcat(image_well_data[well_start_id:well_end_id])
        image_row_data.append(sites_row)

    # concatenate all the stripes into 1 image
    plate_image = cv2.vconcat(image_row_data)

    # purge temp files
    logging.info("Purge temporary folder")

    shutil.rmtree(temp_folder, ignore_errors=True)

    return plate_image


def render_single_channel_plateview(
    source_path, plate_name, channel, channel_label, output_path, temp_folder
):
    """Render 1 image for a specific plate channel
    args:
    source_path: the source folder containing plate images
    plate_name: name of the plate
    channel: the code of the channel to render (e.g. C02)
    channel_label: the text detail of the channel
    output_path: the folder where to save the image
    temp_folder: temporary work folder
    returns: true in case of success
    """

    # generate cv2 image for the channel
    plate_image = generate_plate_image(
        source_path,
        plate_name,
        channel,
        channel_label,
        temp_folder,
    )
    # save image
    plate_image_path = (
        output_path
        + "/"
        + plate_name
        + "-"
        + str(channel)
        + "-"
        + str(parameters.channel_coefficients[channel])
        + ".jpg"
    )
    print("Generated image of size:", plate_image.shape)
    print("Saved as ", plate_image_path)

    cv2.imwrite(plate_image_path, plate_image)

    return


def render_single_plate_plateview(
    source_path,
    plate_name,
    channel_list,
    channel_details_dict,
    output_path,
    temp_folder,
):
    """Render images (1 per channel) for a specific plate
    args:
    source_path: the source folder containing plate images
    plate_name: name of the plate
    channel_list: The list of channels to render
    channel_details_dict: channel details stored in a dict
    output_path: the folder where to save the images
    temp_folder: temporary work folder
    returns: true in case of success
    """
    for current_channel in tqdm(
        channel_list,
        desc="Render plate channels",
        unit="channel plateview",
        colour="green",
        bar_format=None,
    ):
        print("Generate", current_channel, channel_details_dict[current_channel])

        render_single_channel_plateview(
            source_path,
            plate_name,
            current_channel,
            channel_details_dict[current_channel],
            output_path,
            temp_folder,
        )

    return


def render_single_run_plateview(
    source_path,
    folder_list,
    channel_list,
    channel_details_dict,
    output_path,
    temp_folder,
):
    """Render images for all plates of a run
    args:
    source_path: the source folder containing plate images
    folder_list: name of the plates and their respective path inside a dict
    channel_list: The list of channels to render for each plate
    channel_details_dict: channel details stored in a dict
    output_path: the folder where to save the images
    temp_folder: temporary work folder
    returns: true in case of success
    """

    for current_plate in folder_list.keys():
        print("Render", current_plate)

        # render all the channels of the plate
        render_single_plate_plateview(
            folder_list[current_plate],
            current_plate,
            parameters.default_per_plate_channel_to_render,
            parameters.cellplainting_channels_dict,
            output_path,
            temp_folder,
        )

    return
