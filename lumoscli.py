"""Lumos command line interface module"""

import tempfile
from pathlib import Path
import os
import fnmatch
import logging

import click
from art import text2art
from lumos import parameters
from lumos.generator import (
    render_single_channel_plateview,
    render_single_plate_plateview,
    render_single_run_plateview,
)



# print lumos header
header_ascii_art = text2art("Lumos", font="big")
print(header_ascii_art)

# initialize a temp dir location
default_temp_directory = tempfile.gettempdir()

# activate log in temporary directory
logging.basicConfig(
    filename=default_temp_directory +"lumos.log",
    level=logging.DEBUG,
    format="%(asctime)s %(message)s"
)

# collect parameters
cellpaintingchannels = [x[1] for x in parameters.cellplainting_channels]

@click.command()
@click.option(
    "--scope",
    type=click.Choice(["run", "plate", "channel"], case_sensitive=False),
    help="If you want to generate a plateview from a single channel, plate or whole run",
)
@click.option(
    "--channel",
    type=click.Choice(cellpaintingchannels, case_sensitive=True),
    help="For single channel render only",
)
@click.option(
    "--source-path",
    type=click.Path(exists=True),
    help="Folder of your run or single plate",
)
@click.option(
    "--output-path",
    type=click.Path(exists=True),
    help="Folder where images will be output",
)
@click.option(
    "--temp-path",
    type=click.Path(exists=True),
    help="Temporary working folder path. Default will be: "
    + str(default_temp_directory),
    default=default_temp_directory,
)
def start(scope, channel, source_path, output_path, temp_path):
    """Lumos CLI - Cell painting plate image generator
    """

    # annpunce startup
    logging.info("Started")

    # Check conditions to process run, plate or single channel
    if not scope:
        click.echo("Please define a scope")
        return

    if scope == "run":

        if channel:
            click.echo(
                "--channel argument must not be used for run generation. please remove it"
            )
            return

        # get run name
        run_name = Path(source_path)

        # get plates and their path, only if files in it
        click.echo("Scan to detect plate folders..")

        run_folder_list = Path(source_path).glob("**")

        # create a dict with plate name as key and plate folder path as value
        # only folders with tif images are eligible
        folder_list = {
            x.name: x
            for x in run_folder_list
            if (x.is_dir() and len(fnmatch.filter(os.listdir(x), "*.tif")))
        }

        click.echo(
            "Lumos will process "
            + str(len(folder_list))
            + " Folders from run:"
            + str(run_name)
        )
        click.echo("PLates: " + str(list(folder_list.keys())))

        # generate
        # render all the plates of the run
        render_single_run_plateview(
            source_path,
            folder_list,
            parameters.default_per_plate_channel_to_render,
            parameters.cellplainting_channels_dict,
            output_path,
            temp_path,
        )

    elif scope == "plate":

        if channel:
            click.echo(
                "--channel argument must not be used for plate generation. please remove it"
            )
            return

        # get platename
        plate_name = Path(source_path).name
        click.echo(
            "Process plate: "
            + plate_name
            + " and render channels: "
            + str(parameters.default_per_plate_channel_to_render),
        )

        # render all the channels of the plate
        render_single_plate_plateview(
            source_path,
            plate_name,
            parameters.default_per_plate_channel_to_render,
            parameters.cellplainting_channels_dict,
            output_path,
            temp_path,
        )

    elif scope == "channel":

        if not channel:
            click.echo("Missing channel, please define a channel")
            return
        if not source_path:
            click.echo("Missing source plate path, please define a path")
        else:

            # get platename
            plate_name = Path(source_path).name
            click.echo(
                "Process plate:"
                + plate_name
                + " channel:"
                + channel
                + " "
                + str(parameters.cellplainting_channels_dict[channel]),
            )

            # render the channel for the plate
            render_single_channel_plateview(
                source_path,
                plate_name,
                channel,
                parameters.cellplainting_channels_dict[channel],
                output_path,
                temp_path,
            )

    # annpunce stop
    logging.info("Stop")


if __name__ == "__main__":
    start()
