import pytest
import cv2
import tempfile
import numpy as np
import os

import lumos.parameters
import lumos.toolbox
import lumos.picasso


def test_cp_pipeline():
    # Act
    fill_value = 65535
    img = np.full((1000, 1000, 1), fill_value, np.uint16)
    source_folder = tempfile.TemporaryDirectory()
    # save the fake images in the temp folder, one for each channel
    cv2.imwrite(
        source_folder.name+"/DestTestCP_A01_T0001F001L01A01Z01C01.tif",
        img,
    )
    cv2.imwrite(
        source_folder.name+"/DestTestCP_A05_T0001F002L01A01Z01C02.tif",
        img,
    )
    cv2.imwrite(
        source_folder.name+"/DestTestCP_B21_T0001F003L01A01Z01C03.tif",
        img,
    )
    cv2.imwrite(
        source_folder.name+"/DestTestCP_I12_T0001F005L01A01Z01C04.tif",
        img,
    )
    cv2.imwrite(
        source_folder.name+"/DestTestCP_P24_T0001F006L01A01Z01C05.tif",
        img,
    )

    output_folder = tempfile.TemporaryDirectory()
    temporary_folder = tempfile.TemporaryDirectory()
    plate_name = "DestTestCP"
    style = "accurate"

    lumos.picasso.picasso_generate_plate_image(
        source_folder.name,
        plate_name,
        output_folder.name,
        temporary_folder.name,
        style,
        scope='plate',
        display_well_details=False,
    )

    # Assert
    output_image_path = (
        output_folder.name
        + "/"
        + plate_name
        + "-picasso-"
        + style
        + ".jpg"
    )

    # Test that there is an output
    assert(os.path.isfile(output_image_path))

    output_image = cv2.imread(output_image_path)

    # Test that the output has the expected shape
    expected_width = int(3000 * 24 * lumos.parameters.rescale_ratio_picasso_plate)
    expected_height = int(2000 * 16 * lumos.parameters.rescale_ratio_picasso_plate)
    assert(output_image.shape == (expected_height, expected_width, 3))

    # Uncomment the following line to save the generated test output:
    # cv2.imwrite(tempfile.gettempdir()+"/DestTestCP_output_" +
    #             style+".tif", output_image)

    return
