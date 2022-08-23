'''
Pipeline test 3
'''

import os
import tempfile
import pytest
import cv2
import yaml
import numpy as np

from click.testing import CliRunner

import lumos.toolbox
import lumos.generator
import lumos.config
from lumoscli import cli


config_relative_path = '../../lumos/default_lumos_config.yaml'

package_directory = os.path.dirname(os.path.abspath(__file__))
config_absolute_path = os.path.join(package_directory, config_relative_path)
with open(config_absolute_path, 'r', encoding="utf-8") as file:
    config = yaml.safe_load(file)


def test_cp_plate_pipeline():
    '''
    Test that the Cell-Painting operation mode of Lumos can return a valid image.
    '''

    with tempfile.TemporaryDirectory() as sourcedir, tempfile.TemporaryDirectory() as outputdir:

        # ACT

        plate_name = "DestTestCP"
        output_format = 'jpg'
        style = "classic"
        fill_value = 65535
        height = int(config['image_dimensions'].split('x', maxsplit=1)[0])
        width = int(config['image_dimensions'].rsplit('x', maxsplit=1)[-1])
        img = np.full((height, width, 1), fill_value, np.uint16)

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
                                     outputdir, '--output-format', output_format, '--style', style, '--disable-logs'])

        # ASSERT

        # Assert that Lumos terminated without errors
        print(result.output)
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
            assert False, f"Exception occurred when loading output image: {exc}"

        # Assert that the output has the expected shape
        src_img_height = int(
            config['image_dimensions'].split('x', maxsplit=1)[0])
        src_img_width = int(
            config['image_dimensions'].rsplit('x', maxsplit=1)[-1])
        site_grid_row = int(config['site_grid'].split('x', maxsplit=1)[0])
        site_grid_col = int(config['site_grid'].rsplit('x', maxsplit=1)[-1])
        well_grid_row = int(config['well_grid'].split('x', maxsplit=1)[0])
        well_grid_col = int(config['well_grid'].rsplit('x', maxsplit=1)[-1])

        expected_height = int(
            src_img_height * config['rescale_ratio_cp_plate'] * site_grid_row * well_grid_row)
        expected_width = int(
            src_img_width * config['rescale_ratio_cp_plate'] * site_grid_col * well_grid_col)

        assert output_image.shape == (
            expected_height, expected_width, 3)

        # Uncomment the following line to save the generated test output:
        # cv2.imwrite(tempfile.gettempdir()+f"/{plate_name}_output_"+style+".png", output_image)
