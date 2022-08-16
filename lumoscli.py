'''
Lumos command line interface module
'''

import os
import tempfile
import fnmatch
from pathlib import Path

import click
from art import text2art

from lumos import parameters
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
cellpainting_channels_list = [x[0]
                              for x in parameters.cellpainting_channels_info]
fingerprint_style_list = list(parameters.fingerprint_style_dict.keys())


# setup command group
@click.group()
def cli():
    '''
    Welcome to Lumos, a plate image visualization tool!

    \b
    Please choose an operation mode (i.e. command) from the list below
    and type 'lumos <mode> --help' to get started.
    '''
    # print lumos header
    header_ascii_art = text2art("Lumos", font="big")
    click.echo(header_ascii_art)


# -----------------------------  QUALITY CONTROL  ----------------------------- #


# setup QC mode
@cli.command(
    name="qc",
    help="Quality Control mode",
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
    help="For single channel render only. Choose which single channel to render.",
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
    help="Path to the temporary working folder.",
)
@click.option(
    '-f',
    "--output-format",
    type=click.Choice(parameters.output_file_format_list,
                      case_sensitive=False),
    default=parameters.output_file_format_list[0],
    show_default=True,
    help="File format of the generated images.",
)
@click.option(
    '-b',
    "--brightfield",
    type=click.Choice(["none", "1", "2", "3", "all"], case_sensitive=False),
    default="none",
    show_default=True,
    help="Choose which brightfield channel to include in the render.",
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
    help="(dev only) Choose if temporary files should be kept instead of copying again the source files.",
    hidden=True,
    # Note: This option is hidden from the --help menu as it is only for debugging purposes.
)
def quality_control(scope, channel, source_path, output_path, temp_path, output_format, brightfield, parallelism, keep_temp_files):
    '''
    Quality Control operation mode - CLI entry
    '''

    is_in_parallel = (parallelism != 1)

    # create logger
    logger.setup(temp_path, is_in_parallel)

    # announce startup to logger
    logger.info("Started - Quality Control")

    # decode arguments
    if is_in_parallel:
        if parallelism < 1:
            click.secho(
                "CLI ERROR: '--paralellism' argument cannot be less than 1. Please remove it or change its value.", fg='bright_red', bold=True)
            return
        click.secho(
            "CLI WARNING: When using parallelism, pressing [CTRL+C] does not terminate the program. To halt the execution of the program before it finishes, you have to close your terminal.", fg='bright_yellow')
        click.secho(
            "CLI INFO: When using parallelism, less progress information will be printed in the terminal.", fg='bright_magenta')
        click.echo()

    if keep_temp_files:
        click.secho("CLI Development Note: Keeping previously downloaded temporary files (remove '--keep-temp-files' to regenerate them every time)", fg='bright_blue')
        logger.info(
            "Argument '--keep-temp-files' used from CLI: keeping previously downloaded temporary files")

    # decode scope
    if scope == "channel":

        if not channel:
            click.secho(
                "CLI ERROR: Missing channel. Please define a channel using '--channel' <channel_name>.", fg='bright_red', bold=True)
            return

        if is_in_parallel:
            click.secho(
                "CLI WARNING: The '--parallelism' argument has no effect on performance when scope is 'channel'. Consider removing it.", fg='bright_yellow')
        if brightfield != "none":
            click.secho("CLI WARNING: The '--brightfield' argument has no effect when scope is 'channel' and should not be specified. Consider removing it.", fg='bright_yellow')
        click.echo()

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
            + str(parameters.cellpainting_channels_dict[channel]),
        )

        # render the channel for the plate
        render_single_channel_plateview(
            source_path,
            plate_name,
            channel,
            parameters.cellpainting_channels_dict[channel],
            output_path,
            temp_path,
            output_format,
            keep_temp_files,
        )

    else:

        if channel:
            click.secho(
                "CLI ERROR: '--channel' argument must not be used for run/plate scope. Please remove it.", fg='bright_red', bold=True)
            return

        channels_to_render = parameters.default_channels_to_render.copy()
        if brightfield == "1":
            channels_to_render.append("Z01C06")
            click.secho(
                "CLI Note: Generating render ONLY for brightfield channel Z01C06.", fg='bright_blue')
        elif brightfield == "2":
            channels_to_render.append("Z02C06")
            click.secho(
                "CLI Note: Generating render ONLY for brightfield channel Z02C06.", fg='bright_blue')
        elif brightfield == "3":
            channels_to_render.append("Z03C06")
            click.secho(
                "CLI Note: Generating render ONLY for brightfield channel Z03C06.", fg='bright_blue')
        elif brightfield == "all":
            channels_to_render.append("Z01C06")
            channels_to_render.append("Z02C06")
            channels_to_render.append("Z03C06")
            click.secho(
                "CLI Note: Generating renders for ALL brightfield channels.", fg='bright_blue')
        else:
            click.secho(
                "CLI Note: Generating render for NONE of the brightfield channels.", fg='bright_blue')
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
                output_format,
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
                    output_format,
                    keep_temp_files,
                )
            else:
                render_single_plate_plateview_parallelism(
                    source_path,
                    plate_name,
                    channels_to_render,
                    output_path,
                    temp_path,
                    output_format,
                    parallelism,
                    keep_temp_files,
                )

    # announce stop to logger
    logger.info("Stopped - Quality Control")

    return


# -----------------------------  CELL PAINTING  ----------------------------- #


# define cellpainter command
@cli.command(
    name="cp",
    help="Cell Painting mode",
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
    type=click.Choice(["plate", "wells", "sites"], case_sensitive=False),
    required=True,
    help="If you want to generate a cellpainted image for a whole plate, or each individual well.",
)
@click.option(
    '-w',
    "--single-well",
    type=click.STRING,
    help="If scope is 'wells', this allows you to generate the image for only one well.",
)
@click.option(
    '-sp',
    "--source-path",
    type=click.Path(exists=True),
    required=True,
    help="Folder of your plate images.",
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
    help="Path to the temporary working folder.",
)
@click.option(
    '-pp',
    "--platemap-path",
    type=click.Path(exists=True),
    help=f'''Path to the platemap file of your plate.
    This allows the identifier of each compound to be displayed on the well images.
    
    To change which columns are being parsed, you can edit 'lumos.parameters.platemap_columns'.
    The current configuration is {parameters.platemap_columns}''',
)
@click.option(
    '-f',
    "--output-format",
    type=click.Choice(parameters.output_file_format_list,
                      case_sensitive=False),
    default=parameters.output_file_format_list[0],
    show_default=True,
    help="File format of the generated images.",
)
def cell_painting(style, scope, single_well, source_path, output_path, temp_path, platemap_path, output_format):
    '''
    Cell Painting operation mode - CLI entry
    '''

    # create logger
    logger.setup(temp_path, False)

    # announce startup to logger
    logger.info("Started - Cell Painting")

    # get platename
    plate_name = Path(source_path).name

    if platemap_path is not None and scope == 'sites':
        click.secho("CLI WARNING: The '--platemap-path' argument has no effect when scope is 'sites' and should not be specified. Consider removing it.", fg='bright_yellow')
        click.echo()

    if not single_well:
        click.echo(
            "Process wells of plate: "
            + plate_name
            + " and multiplex cell painting channels C01,C02,C03,C04,C05"
        )
    elif scope != 'plate':
        single_well = single_well.upper()
        click.echo(
            "Process well "
            + single_well
            + " of plate: "
            + plate_name
            + " and multiplex cell painting channels C01,C02,C03,C04,C05"
        )
    else:
        logger.error(
            "'-w/--single-well' argument used while in scope 'plate'.")
        click.secho(
            "CLI ERROR: Used '-w/--single-well' argument while using scope 'plate'. Those two arguments are incompatible.",
            fg='bright_red', bold=True
        )
        return

    # multiplex the channels of the plate (not brightfield) into a single RGB image
    picasso_generate_plate_image(
        source_path,
        plate_name,
        output_path,
        temp_path,
        platemap_path,
        output_format,
        style,
        scope,
        single_well,
        True,
    )

    # announce stop to logger
    logger.info("Stopped - Cell Painting")

    return


if __name__ == "__main__":
    # use Click
    cli()
