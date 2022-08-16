'''
Test 3
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


def test_cp_pipeline():
    '''
    Test that the Cell-Painting operation mode of Lumos can return a valid image.
    '''

    with tempfile.TemporaryDirectory() as sourcedir, tempfile.TemporaryDirectory() as outputdir:

        # ACT

        plate_name = "DestTestQC"
        output_format = 'jpg'
        style = "classic"
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
        result = runner.invoke(cli, ['cp', '--scope', 'plate', '--source-path', sourcedir+'/'+plate_name, '--output-path',
                                     outputdir, '--output-format', output_format, '--style', style])

        # ASSERT

        # Assert that Lumos terminated without errors
        assert result.exit_code == 0

        # Assert that there is an output
        output_image_path = (
            f"{outputdir}/{plate_name}-picasso-{style}.{output_format}"
        )
        assert os.path.isfile(output_image_path)

        # Assert that the output can be opened
        try:
            output_image = cv2.imread(output_image_path)
        except Exception as exc:
            assert False, f"Exception occured when loading output image: {exc}"

        # Assert that the output has the expected shape
        expected_width = int(
            3000 * 24 * lumos.parameters.rescale_ratio_picasso_plate)
        expected_height = int(
            2000 * 16 * lumos.parameters.rescale_ratio_picasso_plate)
        assert output_image.shape == (expected_height, expected_width, 3)

        # Uncomment the following line to save the generated test output:
        # cv2.imwrite(tempfile.gettempdir()+"/DestTestCP_output_" +
        #             style+".tif", output_image)
