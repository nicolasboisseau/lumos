#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Main functions to generate platemaps with lumos.
'''

import math
import multiprocessing
import os
from pathlib import Path
import platform
import pandas as pd
from shutil import copyfile
import shutil
from . import toolbox
from . import logger
from . import parameters
import cv2
from tqdm import tqdm
import numpy as np


def generate_plate_image_for_channel(
    plate_input_path_string,
    plate_name,
    channel_to_render,
    channel_label,
    temp_folder,
    keep_temp_files,
):
    '''
    Generates an image of a cellpainting plate for a specific channel.

            Parameters:
                    plate_images_folder_path (Path): The path to the folder where the images of the plate are stored.
                    plate_name (string): Name of the plate.
                    channel_to_render (string): The cellpainting channel to render.
                    channel_label (string): The label describing the channel type.
                    temp_folder_path (Path): The folder where temporary data can be stored.

            Returns:
                    8-bit cv2 image
    '''

    # define a temp folder for the run
    temp_folder = temp_folder + "/lumos-tmpgen-" + plate_name + channel_to_render

    # remove temp dir if existing
    if not keep_temp_files:
        logger.debug("Purge temporary folder before plate generation")
        shutil.rmtree(temp_folder, ignore_errors=True)

    # create the temporary directory structure to work on images
    try:
        os.mkdir(temp_folder)
        os.mkdir(temp_folder + "/wells")
    except FileExistsError:
        pass

    # read the plate input path
    plate_input_path = Path(plate_input_path_string)

    # get the files from the plate folder, for the targeted channel
    images_full_path_list = list(
        Path(plate_input_path).glob("*" + channel_to_render + ".tif")
    )

    # check that we get 2304 images for a 384 well image
    try:
        assert len(images_full_path_list) == 2304
    except AssertionError:
        logger.p_print(
            "The plate does not have the exact image count: expected 2304, got "
            + str(len(images_full_path_list))
        )
        logger.warning(
            "The plate does not have the exact image count: expected 2304, got "
            + str(len(images_full_path_list))
        )

    logger.info(
        "Start plate image generation for channel: "
        + str(channel_to_render)
        + " - "
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
        l + str(r).zfill(2) for l in "ABCDEFGHIJKLMNOP" for r in range(1, 25)       # e.g. "A01"
    ]
    well_site_theoretical_list = [
        [x, r] for x in well_theoretical_list for r in range(1, 7)                  # e.g. ["A01", 1] .. ["A01", 6]
    ]

    # create the theoretical well dataframe
    theoretical_data_df = pd.DataFrame(
        well_site_theoretical_list, columns=["well", "site"]
    )

    # join the real wells with the theoric ones
    data_df_joined = theoretical_data_df.merge(
        data_df,
        left_on=["well", "site"],
        right_on=["well", "site"],
        how="left",
    )

    # log if there is a delta between theory and actual plate wells
    delta = set(well_theoretical_list) - set(image_well_list)
    logger.debug("Well Delta " + str(delta))

    # get the site images and store them locally
    logger.info("Copying sources images in temp folder..")

    copyprogressbar = tqdm(
        data_df_joined.iterrows(),
        total=len(data_df_joined),
        desc="Download images to temp",
        unit="images",
        colour="blue" if platform.system() == 'Windows' else "#006464",
        leave=True,
        disable=logger._is_in_parallel,
    )
    for _, current_image in copyprogressbar:

        # do not copy if temp file already exists, or if source file doesn't exists
        if not os.path.isfile(temp_folder + "/" + str(current_image["filename"])):
            try:
                copyfile(
                    current_image["fullpath"],
                    temp_folder + "/" + str(current_image["filename"]),
                )
            except TypeError:
                # this is thrown when the source file does not exist, or when copyfile() fails
                logger.warning(
                    "TypeError: from "
                    + str(current_image["fullpath"])
                    + " to "
                    + str(temp_folder)
                    + "/"
                    + str(current_image["filename"])
                )
        else:
            logger.debug(
                "File already exists in temp folder: "
                + temp_folder + "/" + str(current_image["filename"])
            )

    logger.info("Copying sources images in temp folder..Done")

    # get the list of all the wells
    # We first convert to a set to remove redundant wells (duplicate data because each is represented 6 times, one per site)
    well_list = list(set(data_df_joined["well"]))
    well_list.sort()

    logger.info("Generating well images and storing them in temp dir..")

    # generate one image per well by concatenation of image sites
    wellprogressbar = tqdm(
        well_list,
        unit="wells",
        colour="magenta" if platform.system() == 'Windows' else "#6464a0",
        leave=True,
        disable=logger._is_in_parallel,
    )
    for current_well in wellprogressbar:
        wellprogressbar.set_description("Processing well %s" % current_well)

        # get the 6 images metadata of the well
        current_wells_df = data_df_joined.loc[data_df_joined["well"] == current_well]

        # load 6 wells into an image list (if image cannot be opened, e.g. if it is missing or corrupted, replace with a placeholder image)
        image_list = []
        for current_site in range(1, 7):
            img = toolbox.load_site_image(current_site, current_wells_df, temp_folder)
            try:
                # resize the image first to reduce computations
                img = cv2.resize(
                    src=img,
                    dsize=None,
                    fx=parameters.rescale_ratio,
                    fy=parameters.rescale_ratio,
                    interpolation=cv2.INTER_CUBIC,
                )
                # normalize the intensity of each channel by a specific coefficient
                img = img * parameters.channel_coefficients[channel_to_render]
                # convert to 8 bit
                img = img / 256
                img = img.astype("uint8")
            except:
                # create placeholder image when error
                img = np.full(
                    shape=(int(1000*parameters.rescale_ratio), int(1000*parameters.rescale_ratio), 1),
                    fill_value=parameters.placeholder_background_intensity,
                    dtype=np.uint8
                )
                img = toolbox.draw_markers(img, parameters.placeholder_markers_intensity)
                logger.warning("Missing or corrupted file in well " + current_well + " (site " + str(current_site) + ")")

            image_list.append(img)

        # concatenate horizontally and vertically
        sites_row1 = cv2.hconcat(
            [image_list[0], image_list[1], image_list[2]]
        )
        sites_row2 = cv2.hconcat(
            [image_list[3], image_list[4], image_list[5]]
        )
        all_sites_image = cv2.vconcat([sites_row1, sites_row2])

        # add well id on image
        text = current_well + " " + channel_label
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(
            all_sites_image,
            text,
            (math.ceil(25*parameters.rescale_ratio), math.ceil(125*parameters.rescale_ratio)),
            font,
            4*parameters.rescale_ratio,
            (192, 192, 192),
            math.ceil(8*parameters.rescale_ratio),
            cv2.INTER_AREA,
        )

        # add well marks on borders
        image_shape = all_sites_image.shape
        cv2.rectangle(
            all_sites_image,
            (0, 0),
            (image_shape[1], image_shape[0]),
            color=(192, 192, 192),
            thickness=1,
        )

        # save the image in the temp folder
        cv2.imwrite(
            temp_folder + "/wells/well-" + str(current_well) + ".png",
            all_sites_image,
        )

    logger.info("Generating well images and storing them in temp dir..Done")

    # load all well images and store images in memory into a list
    logger.p_print("Combining well images into final channel image..")
    logger.info("Loading well images from temp dir..")

    image_well_data = []
    for current_well in list(well_list):
        well_image = toolbox.load_well_image(
            current_well,
            temp_folder + "/wells",
        )
        image_well_data.append(well_image)

    logger.info("Loading well images from temp dir..Done")

    # concatenate all the well images into horizontal stripes (1 per row)
    logger.info("Concatenating well images into a plate..")

    image_row_data = []
    for current_plate_row in range(1, 17):

        # concatenate horizontally and vertically
        well_start_id = ((current_plate_row - 1) * 24) + 0
        well_end_id = current_plate_row * 24
        sites_row = cv2.hconcat(image_well_data[well_start_id:well_end_id])
        image_row_data.append(sites_row)

    # concatenate all the stripes into 1 image
    plate_image = cv2.vconcat(image_row_data)

    logger.info("Concatenating well images into a plate..Done")

    # purge temp files
    if not keep_temp_files:
        logger.debug("Purge temporary folder after generation")
        shutil.rmtree(temp_folder, ignore_errors=True)

    return plate_image


def render_single_channel_plateview(
    source_path, plate_name, channel_to_render, channel_label, output_path, temp_folder_path, keep_temp_files
):
    '''
    Renders 1 image for a specific channel of a plate.

            Parameters:
                    source_path (Path): The path to the folder where the images of the plate are stored.
                    plate_name (string): Name of the plate.
                    channel_to_render (string): The name of the channel to render.
                    channel_label (string): The label describing the channel type.
                    output_path (Path): The folder where to save the generated image.
                    temp_folder_path (Path): The folder where temporary data can be stored.
                    keep_temp_files (bool): [dev] Whether or not the temporary files should be kept between runs.

            Returns:
                    True (in case of success)
    '''

    # generate cv2 image for the channel
    plate_image = generate_plate_image_for_channel(
        source_path,
        plate_name,
        channel_to_render,
        channel_label,
        temp_folder_path,
        keep_temp_files
    )
    logger.p_print(" -> Generated image of size: " + str(plate_image.shape))

    # save image
    plate_image_path = (
        output_path
        + "/"
        + plate_name
        + "-"
        + str(channel_to_render)
        + "-"
        + str(parameters.channel_coefficients[channel_to_render])
        + ".jpg"
    )
    cv2.imwrite(plate_image_path, plate_image)
    logger.p_print(" -> Saved as " + plate_image_path)

    return


def render_single_plate_plateview(
    source_path,
    plate_name,
    channel_list,
    output_path,
    temp_folder_path,
    keep_temp_files
):
    '''
    Renders 1 image per channel for a specific plate.

            Parameters:
                    source_path (Path): The path to the folder where the images of the plate are stored.
                    plate_name (string): Name of the plate.
                    channel_list (string list): The list of the channels to render.
                    output_path (Path): The folder where to save the generated image.
                    temp_folder_path (Path): The folder where temporary data can be stored.
                    keep_temp_files (bool): [dev] Whether or not the temporary files should be kept between runs.

            Returns:
                    True (in case of success)
    '''

    for current_channel in tqdm(
        channel_list,
        desc="Render plate channels",
        unit="channel",
        colour="green" if platform.system() == 'Windows' else "#00ff00",
    ):
        # get the current channel's label
        channel_label = parameters.cellplainting_channels_dict[current_channel]

        logger.p_print(os.linesep)
        logger.p_print("Generate " + current_channel + " - " + channel_label + os.linesep)

        render_single_channel_plateview(
            source_path,
            plate_name,
            current_channel,
            channel_label,
            output_path,
            temp_folder_path,
            keep_temp_files
        )

    return


def render_single_plate_plateview_parallelism(
    source_path,
    plate_name,
    channel_list,
    output_path,
    temp_folder_path,
    parallelism,
    keep_temp_files
):
    '''
    Renders, in parallel, 1 image per channel for a specific plate.

            Parameters:
                    source_path (Path): The path to the folder where the images of the plate are stored.
                    plate_name (string): Name of the plate.
                    channel_list (string list): The list of the channels to render.
                    output_path (Path): The folder where to save the generated image.
                    temp_folder_path (Path): The folder where temporary data can be stored.
                    parallelism (int): On how many CPU cores should the computation be spread.
                    keep_temp_files (bool): [dev] Whether or not the temporary files should be kept between runs.

            Returns:
                    True (in case of success)
    '''

    n_cores = min(parallelism, multiprocessing.cpu_count())
    pool = multiprocessing.Pool(n_cores)

    try:
        for current_channel in channel_list:
            # get the current channel's label
            channel_label = parameters.cellplainting_channels_dict[current_channel]

            pool.apply_async(render_single_channel_plateview, args=(
                source_path,
                plate_name,
                current_channel,
                channel_label,
                output_path,
                temp_folder_path,
                keep_temp_files
            ))

        pool.close()
        pool.join()

    except KeyboardInterrupt:
        # does not work: this is an issue with the multiprocessing library
        pool.terminate()
        pool.join()

    return


def render_single_run_plateview(
    source_folder_dict,
    channel_list,
    output_path,
    temp_folder_path,
    parallelism,
    keep_temp_files
):
    '''
    Renders images for all plates of a run. Compatible with parallelism.

            Parameters:
                    source_folder_dict (dict): A dictionary of the name of the plates and their respective path.
                    channel_list (string list): The list of the channels to render for all plates.
                    output_path (Path): The folder where to save the generated image.
                    temp_folder_path (Path): The folder where temporary data can be stored.
                    parallelism (int): On how many CPU cores should the computation be spread.
                    keep_temp_files (bool): [dev] Whether or not the temporary files should be kept between runs.

            Returns:
                    True (in case of success)
    '''
    runprogressbar = tqdm(
        source_folder_dict.keys(),
        total=len(source_folder_dict),
        desc="Run progress",
        unit="plates",
        colour='cyan' if platform.system() == 'Windows' else "#0AAFAF",
        leave=True,
    )
    for current_plate in runprogressbar:
        # render all the channels of the plate
        if parallelism == 1:
            render_single_plate_plateview(
                source_folder_dict[current_plate],
                current_plate,
                channel_list,
                output_path,
                temp_folder_path,
                keep_temp_files,
            )
        else:
            render_single_plate_plateview_parallelism(
                source_folder_dict[current_plate],
                current_plate,
                channel_list,
                output_path,
                temp_folder_path,
                parallelism,
                keep_temp_files,
            )

    print(os.linesep + os.linesep + "Run completed!")
    print(str(len(source_folder_dict.keys())), "plate(s) have been processed.", os.linesep)

    return
