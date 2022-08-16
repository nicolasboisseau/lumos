import pytest
import cv2
import tempfile
import numpy as np
import pandas as pd
from pathlib import Path
import os

from lumos.toolbox import load_site_image


# Arrange
@pytest.fixture
def fake_image():
    """ Generate a fake image and save it in temp folder
    """
    img = np.full((1000, 1000, 1), 32768, np.uint16)

    fake_16_bit_image_file = tempfile.NamedTemporaryFile(
        delete=False, suffix='.tif')

    cv2.imwrite(
        fake_16_bit_image_file.name,
        img,
    )

    return fake_16_bit_image_file.name


@pytest.fixture
def fake_dataframe(fake_image):
    """ generate a dataframe with the following columns ["well", "site", "filename", "fullpath"]
    """
    image_path = Path(fake_image)
    dict = [{"well": "A01", "site": 1, "filename": image_path.name,
             "fullpath": image_path.parent}]
    fake_df = pd.DataFrame.from_dict(dict, orient='columns')
    return fake_df


def test_load_image(fake_dataframe, fake_image):
    # Act
    fake_image_path = Path(fake_image)
    site_image = load_site_image(
        1, fake_dataframe, str(fake_image_path.parent))

    # Assert
    assert site_image.shape == (1000, 1000)

    # Clean-up
    os.remove(fake_image_path)
