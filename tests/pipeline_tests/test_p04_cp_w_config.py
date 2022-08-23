'''
Pipeline test 4
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


config_relative_path = './testing_config.yaml'

package_directory = os.path.dirname(os.path.abspath(__file__))
config_absolute_path = os.path.join(package_directory, config_relative_path)
with open(config_absolute_path, 'r', encoding="utf-8") as file:
    config = yaml.safe_load(file)


def test_cp_sites_pipeline_with_config():
    '''
    Test that the Cell-Painting operation mode of Lumos can return
    valid site images with a custom configuration file.
    '''

    with tempfile.TemporaryDirectory() as sourcedir, tempfile.TemporaryDirectory() as outputdir:

        # ACT

        plate_name = "DestTestConfigCP"
        images_path = f"{sourcedir}/{plate_name}/Images/"
        output_format = 'jpg'
        style = "classic"
        fill_value = 65535
        height = int(config['image_dimensions'].split('x', maxsplit=1)[0])
        width = int(config['image_dimensions'].rsplit('x', maxsplit=1)[-1])
        img = np.full((height, width, 1), fill_value, np.uint16)

        # Create the plate folder structure
        os.makedirs(images_path, exist_ok=True)

        # Save the fake images in the temp folder, one for each channel
        cv2.imwrite(f"{images_path}/r01c01f01p01-ch1sk1fk1fl1.tif", img)
        cv2.imwrite(f"{images_path}/r08c20f03p01-ch2sk1fk1fl1.tif", img)
        cv2.imwrite(f"{images_path}/r20c32f04p01-ch4sk1fk1fl1.tif", img)
        # Also add a fake image that should not be picked up by the
        cv2.imwrite(f"{images_path}/r15c15f02p01-ch5sk1fk1fl1.tif", img)

        # Run Lumos from CLI
        runner = CliRunner()
        result = runner.invoke(cli, ['-cf', config_absolute_path, 'cp', '--scope', 'sites', '--source-path', sourcedir+'/'+plate_name, '--output-path',
                                     outputdir, '--output-format', output_format, '--style', style, '--disable-logs'])

        # ASSERT

        # Assert that Lumos terminated without errors
        print(result.output)
        assert result.exit_code == 0

        # Test the 4 active test sites + a control
        test_sites = [("r01c01_s1", "color"), ("r08c20_s3", "color"), ("r20c32_s4", "color"),
                      ("r15c15_s2", "black"), ("r16c16_s2", "black"), ]

        for site_to_test, category in test_sites:

            # Assert that there is an output
            output_image_path = (
                f"{outputdir}/sites_{plate_name}_{style}/{site_to_test}.{output_format}"
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

            expected_height = src_img_height
            expected_width = src_img_width

            assert output_image.shape == (
                expected_height, expected_width, 3)

            # Uncomment the following line to save the generated test output:
            # cv2.imwrite(tempfile.gettempdir()+f"/{plate_name}_output_"+site_to_test+".png", output_image)

            output_image = cv2.cvtColor(output_image, cv2.COLOR_BGR2GRAY)
            print(f"{site_to_test} non-zero pixel count:",
                  cv2.countNonZero(output_image))
            if category == "black":
                # Check that the image is completely black
                assert cv2.countNonZero(output_image) == 0
            if category == "color":
                # Check that the image is not black
                assert cv2.countNonZero(
                    output_image) == expected_height * expected_width
