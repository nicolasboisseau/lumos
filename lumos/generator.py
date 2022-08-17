#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Main functions to generate platemaps with lumos.
'''

import os
import sys
import math
import multiprocessing
import platform
import shutil


import cv2
from tqdm import tqdm
import numpy as np

from . import toolbox
from . import logger
from .config import get_config


def generate_plate_image_for_channel(
    plate_input_path,
    plate_name,
    channel_to_render,
    channel_label,
    temp_folder,
    output_format,
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
                    output_format (string): The format/extension of the generated output images.
                    keep_temp_files (bool): [dev] Whether or not the temporary files should be kept between runs.

            Returns:
                    8-bit cv2 image
    '''

    # Define a temp folder for the run
    temp_folder = temp_folder + "/lumos-tmpgen-" + \
        plate_name + '-' + channel_to_render

    # Remove temp dir if existing
    if not keep_temp_files:
        logger.debug("Purge temporary folder before plate generation")
        shutil.rmtree(temp_folder, ignore_errors=True)
    # Create the temporary directory structure to work on images
    try:
        os.mkdir(temp_folder)
        os.mkdir(temp_folder + "/wells")
    except FileExistsError:
        pass

    # Build a Table of the available images of the plate for the selected channel
    image_df = toolbox.build_input_images_df(
        plate_input_path,
        [channel_to_render],
    )

    logger.info(
        "Start plate image generation for channel: "
        + str(channel_to_render)
        + " - "
        + str(channel_label)
    )

    # Get the site images and store them locally
    logger.info("Copying sources images in temp folder..")

    copy_progressbar = tqdm(
        image_df.iterrows(),
        total=len(image_df),
        desc="Download images to temp",
        unit="images",
        colour="blue" if platform.system() == 'Windows' else "#006464",
        leave=True,
        disable=logger.PARALLELISM or not logger.ENABLED,
        # ascii=True, # Use this if Windows gives encoding errors when printing to the console
    )
    for _, current_image in copy_progressbar:

        # Do not copy if temp file already exists, or if source file doesn't exists
        if not os.path.isfile(temp_folder + "/" + str(current_image["filename"])):
            try:
                shutil.copyfile(
                    current_image["fullpath"],
                    temp_folder + "/" + str(current_image["filename"]),
                )
            except TypeError:
                # This is thrown when the source file does not exist, or when copyfile() fails
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

    logger.info("Generating well images and storing them in temp dir..")

    # Get the list of all the wells in the plate
    well_list = sorted(image_df["well"].unique())

    # Generate one image per well by concatenation of image sites
    well_progressbar = tqdm(
        well_list,
        unit="wells",
        colour="magenta" if platform.system() == 'Windows' else "#6464a0",
        leave=True,
        disable=logger.PARALLELISM or not logger.ENABLED,
    )
    for current_well in well_progressbar:
        well_progressbar.set_description(f"Processing well {current_well}")

        # Get the images for each of the well's sites
        current_wells_df = image_df.loc[image_df["well"]
                                        == current_well]

        # Load the sites into an image list (if image cannot be opened, e.g. if it is missing or corrupted, replace with a placeholder image)
        image_list = []
        for current_site in range(1, image_df["site"].max()+1):
            try:
                # Load image
                img = toolbox.load_site_image(
                    current_site, current_wells_df, temp_folder)
                # Check that the image loaded successfully
                assert (img is not None) and (img.shape != (0, 0))
                # Resize the image first to reduce computations
                img = cv2.resize(
                    src=img,
                    dsize=None,
                    fx=get_config()['rescale_ratio_qc'],
                    fy=get_config()['rescale_ratio_qc'],
                    interpolation=cv2.INTER_CUBIC,
                )
                # Convert to 8 bit
                img = img / 256
                img = img.astype("uint8")
                # Normalize the intensity of each channel by a specific coefficient
                # Create a mask to check when value will overflow
                intensity_coef = get_config(
                )['channel_info'][channel_to_render]['qc_coef']
                mask = (img > (255 / intensity_coef)
                        ) if intensity_coef != 0 else False
                # Clip the result to be in [0;255] if overflow
                img = np.where(mask, 255, img * intensity_coef)

            except:
                logger.warning("Missing or corrupted file in well " +
                               current_well + " (site " + str(current_site) + ")")

                # Create placeholder image if an error occurs
                height = int(get_config()['image_dimensions'].split(
                    'x', maxsplit=1)[0])
                width = int(get_config()['image_dimensions'].rsplit(
                    'x', maxsplit=1)[-1])
                img = np.full(
                    shape=(int(height*get_config()['rescale_ratio_qc']),
                           int(width*get_config()['rescale_ratio_qc']), 1),
                    fill_value=get_config()[
                        'placeholder_background_intensity'],
                    dtype=np.uint8
                )
                img = toolbox.draw_markers(
                    img, get_config()['placeholder_markers_intensity'])

            image_list.append(img)

        # Concatenate the site images horizontally and vertically
        nb_site_row = int(get_config()['site_grid'].split('x', maxsplit=1)[0])
        nb_site_col = int(
            get_config()['site_grid'].rsplit('x', maxsplit=1)[-1])

        well_image = toolbox.concatenate_images_in_grid(
            image_list, nb_site_row, nb_site_col)

        # Add well id on image
        text = current_well + " " + channel_label
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(
            well_image,
            text,
            (math.ceil(25*get_config()['rescale_ratio_qc']),
             math.ceil(125*get_config()['rescale_ratio_qc'])),
            font,
            4*get_config()['rescale_ratio_qc'],
            (192, 192, 192),
            math.ceil(8*get_config()['rescale_ratio_qc']),
            cv2.INTER_AREA,
        )

        # Add well marks on borders
        image_shape = well_image.shape
        cv2.rectangle(
            well_image,
            (0, 0),
            (image_shape[1], image_shape[0]),
            color=(192, 192, 192),
            thickness=1,
        )

        # Save the image in the temp folder
        cv2.imwrite(
            temp_folder + f"/wells/well-{current_well}.{output_format}",
            well_image,
        )

    logger.info("Generating well images and storing them in temp dir..Done")

    # Load all well images and store images in memory into a list
    logger.p_print("Combining well images into final channel image..")
    logger.info("Loading well images from temp dir..")

    well_images = []
    for current_well in list(well_list):
        well_image = toolbox.load_well_image(
            current_well,
            temp_folder + "/wells",
            output_format,
        )
        well_images.append(well_image)

    logger.info("Loading well images from temp dir..Done")

    # Concatenate the well images horizontally and vertically
    logger.info("Concatenating well images into a plate..")

    # Concatenate all the well images into one plate image
    nb_well_row = int(get_config()['well_grid'].split('x', maxsplit=1)[0])
    nb_well_col = int(get_config()['well_grid'].rsplit('x', maxsplit=1)[-1])

    plate_image = toolbox.concatenate_images_in_grid(
        well_images, nb_well_row, nb_well_col)

    logger.info("Concatenating well images into a plate..Done")

    # Purge temp files
    if not keep_temp_files:
        logger.debug("Purge temporary folder after generation")
        shutil.rmtree(temp_folder, ignore_errors=True)

    return plate_image


def render_single_channel_plateview(
    source_path, plate_name, channel_to_render, channel_label, output_path, temp_folder_path, output_format, keep_temp_files
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
                    output_format (string): The format/extension of the generated output images.
                    keep_temp_files (bool): [dev] Whether or not the temporary files should be kept between runs.

            Returns:
                    True (in case of success)
    '''

    # Generate cv2 image for the channel
    plate_image = generate_plate_image_for_channel(
        source_path,
        plate_name,
        channel_to_render,
        channel_label,
        temp_folder_path,
        output_format,
        keep_temp_files
    )

    if plate_image is None:
        logger.err_print("ERROR: Generated image is empty. This should not happen.",
                         color='bright_red')
        sys.exit(1)

    logger.p_print(" -> Generated image of size: " + str(plate_image.shape))

    # Save image
    plate_image_path = (
        output_path
        + f"/{plate_name}-{channel_to_render}-"
        + f"{get_config()['channel_info'][channel_to_render]['qc_coef']}"
        + f".{output_format}"
    )
    cv2.imwrite(plate_image_path, plate_image)
    logger.p_print(" -> Saved as " + plate_image_path)


def render_single_plate_plateview(
    source_path,
    plate_name,
    channel_list,
    output_path,
    temp_folder_path,
    output_format,
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
                    output_format (string): The format/extension of the generated output images.
                    keep_temp_files (bool): [dev] Whether or not the temporary files should be kept between runs.

            Returns:
                    True (in case of success)
    '''

    for current_channel in tqdm(
        channel_list,
        desc="Render plate channels",
        unit="channel",
        colour="green" if platform.system() == 'Windows' else "#00ff00",
        disable=logger.PARALLELISM or not logger.ENABLED,
    ):
        # Get the current channel's label
        channel_label = get_config()['channel_info'][current_channel]['name']

        logger.p_print(os.linesep)
        logger.p_print("Generate " + current_channel +
                       " - " + channel_label + os.linesep)

        render_single_channel_plateview(
            source_path,
            plate_name,
            current_channel,
            channel_label,
            output_path,
            temp_folder_path,
            output_format,
            keep_temp_files
        )


def render_single_plate_plateview_parallelism(
    source_path,
    plate_name,
    channel_list,
    output_path,
    temp_folder_path,
    output_format,
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
                    output_format (string): The format/extension of the generated output images.
                    parallelism (int): On how many CPU cores should the computation be spread.
                    keep_temp_files (bool): [dev] Whether or not the temporary files should be kept between runs.

            Returns:
                    True (in case of success)
    '''

    n_cores = min(parallelism, multiprocessing.cpu_count())
    pool = multiprocessing.Pool(n_cores)

    try:
        for current_channel in channel_list:
            # Get the current channel's label
            channel_label = get_config(
            )['channel_info'][current_channel]['name']

            pool.apply_async(render_single_channel_plateview, args=(
                source_path,
                plate_name,
                current_channel,
                channel_label,
                output_path,
                temp_folder_path,
                output_format,
                keep_temp_files
            ))

        pool.close()
        pool.join()

    # Try to handle KeyboardInterrupts to stop the program
    except KeyboardInterrupt:
        # Does not work: this is an issue with the multiprocessing library
        pool.terminate()
        pool.join()


def render_single_run_plateview(
    source_folder_dict,
    channel_list,
    output_path,
    temp_folder_path,
    output_format,
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
                    output_format (string): The format/extension of the generated output images.
                    parallelism (int): On how many CPU cores should the computation be spread.
                    keep_temp_files (bool): [dev] Whether or not the temporary files should be kept between runs.

            Returns:
                    True (in case of success)
    '''
    run_progressbar = tqdm(
        source_folder_dict.keys(),
        total=len(source_folder_dict),
        desc="Run progress",
        unit="plates",
        colour='cyan' if platform.system() == 'Windows' else "#0AAFAF",
        leave=True,
        disable=not logger.ENABLED,
    )
    for current_plate in run_progressbar:
        # Render all the channels of the plate
        if parallelism == 1:
            render_single_plate_plateview(
                source_folder_dict[current_plate],
                current_plate,
                channel_list,
                output_path,
                temp_folder_path,
                output_format,
                keep_temp_files,
            )
        else:
            render_single_plate_plateview_parallelism(
                source_folder_dict[current_plate],
                current_plate,
                channel_list,
                output_path,
                temp_folder_path,
                output_format,
                parallelism,
                keep_temp_files,
            )

    print(os.linesep + os.linesep + "Run completed!")
    print(str(len(source_folder_dict.keys())),
          "plate(s) have been processed.", os.linesep)
