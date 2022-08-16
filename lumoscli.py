'''
Lumos command line interface module
'''

import tempfile
from pathlib import Path
import os
import fnmatch

import click
from art import text2art

from lumos import parameters
from lumos import toolbox
from lumos import logger
from lumos.generator import (
    render_single_channel_plateview,
    render_single_plate_plateview,
    render_single_run_plateview,
    render_single_plate_plateview_parallelism,
)
from lumos.picasso import picasso_generate_plate_image


# find the OS temporary directory location
default_temp_directory = tempfile.gettempdir()

# collect parameters
cellpainting_channels_list = [x[0] for x in parameters.cellplainting_channels_info]
fingerprint_style_list = [x for x in parameters.fingerprint_style_dict]


# setup command group
@click.group()
def cli():
    # print lumos header
    header_ascii_art = text2art("Lumos", font="big")
    click.echo(header_ascii_art)
    
    pass


# -----------------------------  QUALITY CONTROL  ----------------------------- #


# setup QC mode
@cli.command(
    name="qc",
    help="Quality Control",
)
@click.option(
    '-s',
    "--scope",
    type=click.Choice(["run", "plate", "channel"], case_sensitive=False),
    required=True,
    help="If you want to generate a plateview from a single channel, plate or whole run",
)
@click.option(
    '-c',
    "--channel",
    type=click.Choice(cellpainting_channels_list, case_sensitive=True),
    help="For single channel render only.",
)
@click.option(
    '-sp',
    "--source-path",
    type=click.Path(exists=True),
    required=True,
    help="Folder of your run or single plate.",
)
@click.option(
    '-op',
    "--output-path",
    type=click.Path(exists=True),
    required=True,
    help="Folder where images will be outputted.",
)
@click.option(
    '-tp',
    "--temp-path",
    type=click.Path(exists=True),
    default=default_temp_directory,
    show_default=True,
    help="Path to the temporary working folder",
)
@click.option(
    '-b',
    "--brightfield",
    type=click.Choice(["1", "2", "3", "all"], case_sensitive=False),
    help="Choose which brightfield channels to render, none are rendered by default.",
)
@click.option(
    '-p',
    "--parallelism",
    type=click.INT,
    default=1,
    show_default=True,
    help="Choose the number of CPU cores on which to perform parallel computation of different channels.",
)
@click.option(
    '-k',
    "--keep-temp-files",
    is_flag=True,
    help="(dev) Choose if temporary files should be kept and not overwriten by a new copy of the source files.",
)
def quality_control(scope, channel, source_path, output_path, temp_path, brightfield, parallelism, keep_temp_files):

    is_in_parallel = (parallelism != 1)

    # create logger
    logger.setup(temp_path, is_in_parallel)

    # announce startup
    logger.info("Started - Quality Control")

    # decode arguments
    if is_in_parallel:
        if parallelism < 1:
            click.echo("CLI ERROR: '--paralellism' argument cannot be less than 1. Please remove it or change its value.")
            return
        click.echo("CLI WARNING: When using parallelism, Keyboard Interrupts (CTRL+C) do not terminate the program.")
        click.echo("             To halt the execution of the program before it finishes normally, you have to close your terminal.")
        click.echo()

    if keep_temp_files:
        click.echo("CLI Note: Keeping previously downloaded temporary files (remove CLI argument '-k' or '--keep-temp-files' to regenerate them every time)")
        logger.info("Argument '--keep-temp-files' used from CLI: keeping previously downloaded temporary files")

    if scope != "channel":
        if channel:
            click.echo("CLI ERROR: '--channel' argument must not be used for run/plate generation. Please remove it.")
            return

        channels_to_render = parameters.default_channels_to_render.copy()
        if brightfield == "1":
            channels_to_render.append("Z01C06")
            click.echo("CLI Note: Generating render ONLY for brightfield channel Z01C06.")
        elif brightfield == "2":
            channels_to_render.append("Z02C06")
            click.echo("CLI Note: Generating render ONLY for brightfield channel Z02C06.")
        elif brightfield == "3":
            channels_to_render.append("Z03C06")
            click.echo("CLI Note: Generating render ONLY for brightfield channel Z03C06.")
        elif brightfield == "all":
            channels_to_render.append("Z01C06")
            channels_to_render.append("Z02C06")
            channels_to_render.append("Z03C06")
            click.echo("CLI Note: Generating renders for ALL brightfield channels.")
        else:
            click.echo("CLI Note: Generating NO render for brightfield channels.")
        click.echo(os.linesep)

    # execute image generation according to the scope
    if scope == "run":

        # get run name
        run_name = Path(source_path)

        # get plates and their path, only if files in it
        run_folder_list = Path(source_path).glob("**")

        # create a dict with plate name as key and plate folder path as value
        # only folders with tif images are eligible
        source_folder_dict = {
            x.name: x
            for x in run_folder_list
            if (x.is_dir() and len(fnmatch.filter(os.listdir(x), "*.tif")))
        }

        click.echo(
            "Lumos will process "
            + str(len(source_folder_dict))
            + " plate folders from run: "
            + str(run_name)
        )
        click.echo("Plates: " + str(list(source_folder_dict.keys())))
        click.echo(
            "Channels being rendered: "
            + str(channels_to_render)
            + os.linesep
            + os.linesep
        )

        # render all the plates of the run
        render_single_run_plateview(
            source_folder_dict,
            channels_to_render,
            output_path,
            temp_path,
            parallelism,
            keep_temp_files,
        )

    elif scope == "plate":

        # get platename
        plate_name = Path(source_path).name
        click.echo(
            "Process plate: "
            + plate_name
            + " and render channels: "
            + str(channels_to_render),
        )

        # render all the channels of the plate
        if not is_in_parallel:
            render_single_plate_plateview(
                source_path,
                plate_name,
                channels_to_render,
                output_path,
                temp_path,
                keep_temp_files,
            )
        else:
            render_single_plate_plateview_parallelism(
                source_path,
                plate_name,
                channels_to_render,
                output_path,
                temp_path,
                parallelism,
                keep_temp_files,
            )

    elif scope == "channel":

        if not channel:
            click.echo("Missing channel, please define a channel")
            return

        # get platename
        plate_name = Path(source_path).name
        click.echo(
            "Process plate: "
            + plate_name,
        )
        click.echo(
            "Render channel: "
            + channel
            + " - "
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
            keep_temp_files,
        )

    # announce stop
    logger.info("Stopped - Quality Control")
    
    return


# -----------------------------  CELL PAINTING  ----------------------------- #


# define cellpainter command
@cli.command(
    name="cp",
    help="Cell Painting",
)
@click.option(
    "--style",
    type=click.Choice(fingerprint_style_list, case_sensitive=False),
    default=fingerprint_style_list[0],
    show_default=True,
    help="Choose the rendering style of the output image.",
)
@click.option(
    '-s',
    "--scope",
    type=click.Choice(["plate", "wells"], case_sensitive=False),
    required=True,
    help="If you want to generate a cellpainted image for a whole plate, or each individual well.",
)
@click.option(
    '-sp',
    "--source-path",
    type=click.Path(exists=True),
    required=True,
    help="Folder of your run or single plate.",
)
@click.option(
    '-op',
    "--output-path",
    type=click.Path(exists=True),
    required=True,
    help="Folder where images will be outputted.",
)
@click.option(
    '-tp',
    "--temp-path",
    type=click.Path(exists=True),
    default=default_temp_directory,
    show_default=True,
    help="Path to the temporary working folder",
)
def cell_painting(scope, source_path, output_path, temp_path, style):

    # create logger
    logger.setup(temp_path, False)

    # announce startup
    logger.info("Started - Cell Painting")

    # get platename
    plate_name = Path(source_path).name

    click.echo(
        "Process wells of plate: "
        + plate_name
        + " and multiplex cell painting channels C01,C02,C03,C04,C05"
    )

    # multiplex the channels of the plate (not brightfield) into a single RGB image
    picasso_generate_plate_image(
        source_path,
        plate_name,
        output_path,
        temp_path,
        style,
        scope,
        True,
    )

    # announce stop
    logger.info("Stopped - Cell Painting")

    return


if __name__ == "__main__":
    # use Click
    cli()
