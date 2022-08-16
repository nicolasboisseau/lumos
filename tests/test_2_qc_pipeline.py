'''
Test 2
'''

import os
import tempfile
import pytest
import cv2
import numpy as np

from click.testing import CliRunner

import lumos.parameters
import lumos.toolbox
import lumos.generator
from lumoscli import cli


# ARRANGE

@pytest.fixture
def fake_placeholder():
    '''
    Simulate a placeholder image that Lumos generates when a site image is missing.
    '''
    placeholder_img = np.full(
        shape=(int(1000*lumos.parameters.rescale_ratio),
               int(1000*lumos.parameters.rescale_ratio), 1),
        fill_value=lumos.parameters.placeholder_background_intensity,
        dtype=np.uint8
    )
    placeholder_img = lumos.toolbox.draw_markers(
        placeholder_img, lumos.parameters.placeholder_markers_intensity)

    return placeholder_img


def test_qc_pipeline(fake_placeholder):
    '''
    Test that the Cell-Painting operation mode of Lumos can return a valid image,
    and that this image as a mean close to what we can expect.
    '''

    with tempfile.TemporaryDirectory() as sourcedir, tempfile.TemporaryDirectory() as outputdir:

        # ACT

        plate_name = "DestTestQC"
        output_format = 'png'
        fill_value = 65535
        img = np.full((1000, 1000, 1), fill_value, np.uint16)

        try:
            os.mkdir(sourcedir+'/'+plate_name)
        except FileExistsError:
            pass
        # save the fake images in the temp folder, one for each channel
        cv2.imwrite(
            f"{sourcedir}/{plate_name}/{plate_name}_A01_T0001F001L01A01Z01C01.tif",
            img,
        )
        cv2.imwrite(
            f"{sourcedir}/{plate_name}/{plate_name}_A05_T0001F002L01A01Z01C02.tif",
            img,
        )
        cv2.imwrite(
            f"{sourcedir}/{plate_name}/{plate_name}_B21_T0001F003L01A01Z01C03.tif",
            img,
        )
        cv2.imwrite(
            f"{sourcedir}/{plate_name}/{plate_name}_I12_T0001F005L01A01Z01C04.tif",
            img,
        )
        cv2.imwrite(
            f"{sourcedir}/{plate_name}/{plate_name}_P24_T0001F006L01A01Z01C05.tif",
            img,
        )

        # Run Lumos from CLI
        runner = CliRunner()
        result = runner.invoke(cli, ['qc', '--scope', 'plate', '--source-path', sourcedir+'/'+plate_name, '--output-path',
                                     outputdir, '--output-format', output_format])

        # ASSERT

        # Assert that Lumos terminated without errors
        assert result.exit_code == 0

        for channel_to_test in lumos.parameters.default_channels_to_render:

            # Assert that there is an output for the channel
            output_channel_image_path = (
                f"{outputdir}/{plate_name}-{channel_to_test}-{lumos.parameters.channel_coefficients[channel_to_test]}.{output_format}"
            )
            assert os.path.isfile(output_channel_image_path)

            # Assert that the output can be opened
            try:
                output_channel_image = cv2.imread(output_channel_image_path)
            except:
                assert False

            # Uncomment the following line to save the generated test outputs:
            # cv2.imwrite(tempfile.gettempdir()+"/DestTestQC_output_"
            #             + channel_to_test+".tif", output_channel_image)

            # Assert that the output has the expected shape
            expected_width = int(3000 * 24 * lumos.parameters.rescale_ratio)
            expected_height = int(2000 * 16 * lumos.parameters.rescale_ratio)
            assert output_channel_image.shape == (
                expected_height, expected_width, 3)

            # Assert that the output has around the expected intensity (with margin because of well labels)
            expected_mean = (
                2303 * np.mean(fake_placeholder)
                + 1 * (np.mean(img)/256)
            ) / 2304

            test_image_mean = np.mean(output_channel_image)

            diff = test_image_mean - expected_mean

            print("---", channel_to_test, "---")
            print("Expected mean=", expected_mean)
            print("Test image mean=", test_image_mean)
            print("Diff=", diff)

            # Only allow the test mean to be in a range of
            # 5 unit of intensity around the expected mean
            # (~4% tolerance)
            # This is because the well markers and borders
            # are not accounted for by the test
            assert abs(diff) <= 5
