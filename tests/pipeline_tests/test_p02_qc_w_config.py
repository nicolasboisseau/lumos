'''
Pipeline test 2
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


# ARRANGE
config_relative_path = './testing_config.yaml'

package_directory = os.path.dirname(os.path.abspath(__file__))
config_absolute_path = os.path.join(package_directory, config_relative_path)
with open(config_absolute_path, 'r', encoding="utf-8") as file:
    config = yaml.safe_load(file)


@pytest.fixture
def fake_placeholder():
    '''
    Simulate a placeholder image that Lumos generates when a site image is missing.
    '''
    height = int(config['image_dimensions'].split('x', maxsplit=1)[0])
    width = int(config['image_dimensions'].rsplit('x', maxsplit=1)[-1])

    placeholder_img = np.full(
        shape=(int(height*config['rescale_ratio_qc']),
               int(width*config['rescale_ratio_qc']), 1),
        fill_value=config['placeholder_background_intensity'],
        dtype=np.uint8
    )

    placeholder_img = lumos.toolbox.draw_markers(
        placeholder_img, config['placeholder_markers_intensity'])

    return placeholder_img


def test_qc_run_pipeline_with_config(fake_placeholder):
    '''
    Test that the Cell-Painting operation mode of Lumos can return a valid image
    with a custom configuration file, and that this image has a mean close to
    what we expect.
    '''

    with tempfile.TemporaryDirectory() as sourcedir, tempfile.TemporaryDirectory() as outputdir:

        plate_name = "DestTestConfigQC"
        run_name = "test_run1"
        images_path = f"{sourcedir}/{run_name}/plates/{plate_name}/Images/"
        output_format = 'png'
        extra_channel = 'ch8'

        # Create fake run folder
        os.makedirs(images_path, exist_ok=True)

        # save the fake images in the temp folder, one for each channel
        fill_value = 65535
        height = int(config['image_dimensions'].split('x', maxsplit=1)[0])
        width = int(config['image_dimensions'].rsplit('x', maxsplit=1)[-1])
        img = np.full((height, width, 1), fill_value, np.uint16)
        cv2.imwrite(f"{images_path}/r01c01f01p01-ch1sk1fk1fl1.tif", img)
        cv2.imwrite(f"{images_path}/r01c32f04p01-ch2sk1fk1fl1.tif", img)
        cv2.imwrite(f"{images_path}/r20c01f02p01-ch3sk1fk1fl1.tif", img)
        cv2.imwrite(f"{images_path}/r01c32f03p01-ch4sk1fk1fl1.tif", img)
        cv2.imwrite(f"{images_path}/r20c32f04p01-ch5sk1fk1fl1.tif", img)
        cv2.imwrite(f"{images_path}/r08c20f02p01-ch6sk1fk1fl1.tif", img)
        cv2.imwrite(f"{images_path}/r15c05f01p01-ch7sk1fk1fl1.tif", img)
        cv2.imwrite(f"{images_path}/r18c14f03p01-ch8sk1fk1fl1.tif", img)

        # ACT

        # Run Lumos from CLI
        runner = CliRunner()
        result = runner.invoke(cli, ['-cf', config_absolute_path, 'qc', '--scope', 'run', '--source-path', sourcedir+'/'+run_name, '--output-path',
                                     outputdir, '--output-format', output_format, '--brightfield', extra_channel, '--disable-logs'])

        # ASSERT

        # Assert that Lumos terminated without errors
        print(result.output)
        assert result.exit_code == 0

        test_channels = config['default_channels_to_render'] + [extra_channel]
        for channel_to_test in test_channels:

            # Assert that there is an output for the channel
            output_channel_image_path = (
                f"{outputdir}/{plate_name}-{channel_to_test}-"
                + f"{config['channel_info'][channel_to_test]['qc_coef']}"
                + f".{output_format}"
            )

            assert os.path.isfile(output_channel_image_path)

            # Assert that the output can be opened
            try:
                output_channel_image = cv2.imread(output_channel_image_path)
            except:
                assert False

            # Uncomment the following line to save the generated test outputs:
            # cv2.imwrite(tempfile.gettempdir()+f"/{plate_name}_output_"+channel_to_test+".png", output_channel_image)

            # Assert that the output has the expected shape
            src_img_height = int(
                config['image_dimensions'].split('x', maxsplit=1)[0])
            src_img_width = int(
                config['image_dimensions'].rsplit('x', maxsplit=1)[-1])
            site_grid_row = int(config['site_grid'].split('x', maxsplit=1)[0])
            site_grid_col = int(
                config['site_grid'].rsplit('x', maxsplit=1)[-1])
            well_grid_row = int(config['well_grid'].split('x', maxsplit=1)[0])
            well_grid_col = int(
                config['well_grid'].rsplit('x', maxsplit=1)[-1])

            expected_height = int(
                src_img_height * config['rescale_ratio_qc'] * site_grid_row * well_grid_row)
            expected_width = int(
                src_img_width * config['rescale_ratio_qc'] * site_grid_col * well_grid_col)

            assert output_channel_image.shape == (
                expected_height, expected_width, 3)

            # Assert that the output has around the expected intensity (with margin because of well labels)
            image_count = site_grid_row * site_grid_col * well_grid_row * well_grid_col

            expected_mean = (
                (image_count-1) * np.mean(fake_placeholder)
                + 1 * (np.mean(img)/256)
            ) / image_count

            test_image_mean = np.mean(output_channel_image)

            diff = test_image_mean - expected_mean

            print("---", channel_to_test, "---")
            print("Expected mean=", expected_mean)
            print("Test image mean=", test_image_mean)
            print("Diff=", diff)

            # Only allow the test mean to be in a range of
            # 20 unit of intensity around the expected mean
            # (~16% tolerance)
            # This is because the well markers and borders
            # are not accounted for by the test
            assert abs(diff) <= 20
