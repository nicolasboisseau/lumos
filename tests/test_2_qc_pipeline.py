import pytest
import cv2
import tempfile
import numpy as np
import os

import lumos.parameters
import lumos.toolbox
import lumos.generator


# Arrange
@pytest.fixture
def fake_placeholder():
    placeholder_img = np.full(
        shape=(int(1000), int(1000), 1),
        fill_value=lumos.parameters.placeholder_background_intensity,
        dtype=np.uint8
    )
    placeholder_img = lumos.toolbox.draw_markers(
        placeholder_img, lumos.parameters.placeholder_markers_intensity)

    return placeholder_img


def test_qc_pipeline(fake_placeholder):
    # Act
    fill_value = 65535
    img = np.full((1000, 1000, 1), fill_value, np.uint16)
    source_folder = tempfile.TemporaryDirectory()
    # save the fake images in the temp folder, one for each channel
    cv2.imwrite(
        source_folder.name+"/DestTestQC_A01_T0001F001L01A01Z01C01.tif",
        img,
    )
    cv2.imwrite(
        source_folder.name+"/DestTestQC_A05_T0001F002L01A01Z01C02.tif",
        img,
    )
    cv2.imwrite(
        source_folder.name+"/DestTestQC_B21_T0001F003L01A01Z01C03.tif",
        img,
    )
    cv2.imwrite(
        source_folder.name+"/DestTestQC_I12_T0001F005L01A01Z01C04.tif",
        img,
    )
    cv2.imwrite(
        source_folder.name+"/DestTestQC_P24_T0001F006L01A01Z01C05.tif",
        img,
    )

    output_folder = tempfile.TemporaryDirectory()
    temporary_folder = tempfile.TemporaryDirectory()
    plate_name = "DestTestQC"

    lumos.generator.render_single_plate_plateview(
        source_folder.name,
        plate_name,
        lumos.parameters.default_channels_to_render,
        output_folder.name,
        temporary_folder.name,
        False,
    )

    # Assert
    for channel_to_test in lumos.parameters.default_channels_to_render:

        output_channel_image_path = (
            output_folder.name
            + "/"
            + plate_name
            + "-"
            + channel_to_test
            + "-"
            + str(lumos.parameters.channel_coefficients[channel_to_test])
            + ".jpg"
        )

        # Test that there is an output for the channel
        assert(os.path.isfile(output_channel_image_path))

        output_channel_image = cv2.imread(output_channel_image_path)

        # Test that the output has the expected shape
        expected_width = int(3000 * 24 * lumos.parameters.rescale_ratio)
        expected_height = int(2000 * 16 * lumos.parameters.rescale_ratio)
        assert(output_channel_image.shape == (expected_height, expected_width, 3))

        # Test that the output has around the expected intensity (with margin because of well labels)
        expected_mean = (2303 * np.mean(fake_placeholder) +
                         (np.mean(img)/256)) / 2304
        assert(abs(expected_mean - np.mean(output_channel_image)) <= 0.5)

        # Uncomment the following line to save the generated test outputs:
        # cv2.imwrite(tempfile.gettempdir()+"/DestTestQC_output_"
        #             + channel_to_test+".tif", output_channel_image)

    return
