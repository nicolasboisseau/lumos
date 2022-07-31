#!/usr/bin/env python
# -*- coding: utf-8 -*-

cellplainting_channels = [
    ["C01 DNA Hoechst 33342", "C01"],
    ["C02 ER Concanavalin A", "C02"],
    ["C03 RNA SYTO 14", "C03"],
    ["C04 AGP Phalloidin and WGA", "C04"],
    ["C05 MITO MitoTracker", "C05"],
    ["C06 Brigtfield depth1", "Z01C06"],
    ["C06 Brigtfield depth2", "Z02C06"],
    ["C06 Brigtfield depth3", "Z03C06"],
]

cellplainting_channels_dict = {
    "C01": "DNA Hoechst 33342",
    "C02": "ER Concanavalin A",
    "C03": "RNA SYTO 14",
    "C04": "AGP Phalloidin and WGA",
    "C05": "MITO MitoTracker Deep Red",
    "Z01C06": "Brightfield depth1",
    "Z02C06": "Brightfield depth2",
    "Z03C06": "Brightfield depth3",
}

# what is the default channel to render for a single channel rendering
default_channel_to_render = cellplainting_channels[0][1]

# what are the channel to render a singleplate rendering
default_per_plate_channel_to_render = [
    "C01",
    "C02",
    "C03",
    "C04",
    "C05",
    "Z01C06",
    "Z02C06",
    "Z03C06",
]

# rescale coefficient factors per channel
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

clipping_threshold_min_value = 1
clipping_threshold_max_value = 12000
normalize_alpha = 0
normalize_beta = 65535
rescale_ratio = 0.1
