#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Main parameters for lumos operation.
'''

cellpainting_channels_info = [
    # Channel number, Channel name, EX wavelength, RGB equivalence
    ["C01", "C01 DNA Hoechst 33342", 450, [0, 70, 255]],            # ~blue
    ["C02", "C02 ER Concanavalin A", 510, [0, 255, 0]],             # ~green
    ["C03", "C03 RNA SYTO 14", 570, [225, 255, 0]],                 # ~yellow
    ["C04", "C04 AGP Phalloidin and WGA", 630, [255, 79, 0]],       # ~orange
    ["C05", "C05 MITO MitoTracker Deep Red", 660, [255, 0, 0]],     # ~red
    ["Z01C06", "C06 Brightfield depth1", None, None],
    ["Z02C06", "C06 Brightfield depth2", None, None],
    ["Z03C06", "C06 Brightfield depth3", None, None],
]
'''
Matrix of information for each of the channels.
    Columns: [Channel number, Channel name, EX wavelength, RGB equivalence]
'''

cellpainting_channels_dict = {
    "C01": "DNA Hoechst 33342",
    "C02": "ER Concanavalin A",
    "C03": "RNA SYTO 14",
    "C04": "AGP Phalloidin and WGA",
    "C05": "MITO MitoTracker Deep Red",
    "Z01C06": "Brightfield depth1",
    "Z02C06": "Brightfield depth2",
    "Z03C06": "Brightfield depth3",
}
'''
Dictionary of the channel names and their respective labels.
'''

# What are the default channels to render for a plate/run
default_channels_to_render = ["C01", "C02", "C03", "C04", "C05"]
'''
List of the default channels to render in a run or single plate rendering.
'''

# Intensity normalizing coefficient factors per channel
channel_coefficients = {
    "C01": 16,
    "C02": 8,
    "C03": 8,
    "C04": 8,
    "C05": 8,
    "Z01C06": 8,
    "Z02C06": 8,
    "Z03C06": 8,
}
'''
Intensity multiplier coefficients for each of the channels (those are arbitrary and used to make interest points easier to see).
'''

platemap_columns = {
    # Equivalence from what is required to the specific platemap column names
    'well_column_name': "well_position",
    'id_column_name': "jump-identifier",
}
'''
Dictionary of the columns to be parsed from the platemap database.
'''

output_file_format_list = ['jpg', 'jpeg', 'png']

rescale_ratio = 0.1

placeholder_background_intensity = 64
placeholder_markers_intensity = 0

# clipping_threshold_min_value = 1
# clipping_threshold_max_value = 12000
# normalize_alpha = 0
# normalize_beta = 65535


#  --------  PARAMETERS ONLY FOR CELL-PAINTING (PICASSO)  --------

rescale_ratio_picasso_wells = 1
rescale_ratio_picasso_plate = 0.25

# List of merge rendering styles for picasso
fingerprint_style_dict = {
    'classic': [[], [], []],
    # ^ This is empty because the classic style relies on another merging method
    'random': [[], [], []],
    'blueish': [[6, 5, 6, 6, 6], [2, 3, 4, 1, 0], [0, 2, 1]],
    'blueish2': [[4, 6, 5, 5, 7], [3, 2, 0, 4, 1], [0, 1, 2]],
    'reddish': [[7, 7, 4, 4, 1], [2, 1, 3, 4, 0], [1, 0, 2]],
    'reddish2': [[7, 3, 6, 8, 5], [1, 2, 3, 0, 4], [1, 0, 2]],
    'blueredgreen': [[3, 8, 4, 4, 8], [0, 3, 4, 2, 1], [2, 0, 1]],
    'blueredgreen2': [[3, 4, 4, 5, 6], [2, 3, 4, 1, 0], [2, 1, 0]],
    'blueredgreen3': [[8, 4, 6, 5, 8], [1, 3, 4, 2, 0], [0, 1, 2]],
    'purple': [[2, 6, 6, 7, 2], [3, 1, 2, 4, 0], [0, 1, 2]],
    'purple2': [[1, 7, 8, 6, 8], [2, 4, 0, 3, 1], [0, 1, 2]],
    'cthulhu': [[3, 2, 3, 5, 7], [0, 3, 2, 1, 4], [1, 0, 2]],
    'meduse': [[8, 8, 3, 7, 8], [0, 3, 4, 1, 2], [2, 0, 1]],
    'alien': [[3, 6, 4, 3, 3], [1, 3, 2, 4, 0], [1, 0, 2]],
}
'''
Dictionary of the styles that can be used for "merge cell painting", and their associated coefficients.
'''

classic_style_parameters = {
    # Tweaked by eye (on DMSO-only plate)
    'intensity': [10, 5, 1.8, 5, 7],
    'contrast': [1, 1, 0.7, 1, 2.5],

    # Equal greyscale (on DMSO-only plate)
    # 'intensity': [10, 7, 2.2, 5, 7.5],
    # 'contrast': [1, 0.5, 0, 0.9, 2],

    # Lumos v0.0.3
    # 'intensity': [11, 9, 2, 4, 12],
    # 'contrast': [0, 0, 0.5, 1, 1.85],
}
'''
Dictionary of the coefficients used for "classic" cell painting
(using an approximation of the actual colors of the channels emitted wavelengths)
'''

# Other styles not integrated
#     'darkgreenblue': [[3,6,2,2,8],[2,1,3,0,4],[2,0,1]],
#     'fingerprint1': [[6,2,3,3,2],[3,1,0,4,2],[0,1,2]],
#     'fingerprint3': [[7,7,6,4,3],[0,2,1,3,4],[1,0,2]],
#     'fingerprint2': [[2,6,6,1,5],[4,3,1,2,0],[2,0,1]],
#     'fingerprint6': [[8,7,4,4,7],[1,3,2,4,0],[0,1,2]],
#     'fingerprint8': [[2,1,4,6,5],[0,3,2,4,1],[0,2,1]],
