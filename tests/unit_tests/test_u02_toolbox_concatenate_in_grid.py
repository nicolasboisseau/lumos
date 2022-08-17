'''
Unit test 2
'''

import numpy as np

from lumos.toolbox import concatenate_images_in_grid


def test_concatenate_images_in_grid():
    '''
    Test that concatenate_images_in_grid() produces a grid of the right shape
    '''

    # Arrange
    height = width = 500
    img = np.full((height, width, 3), 0, np.uint8)

    rows = 7
    columns = 3
    img_list = [img] * rows * columns

    # Act
    output_grid = concatenate_images_in_grid(img_list, rows, columns)

    # Assert
    assert output_grid.shape == (rows * height, columns * width, 3)
