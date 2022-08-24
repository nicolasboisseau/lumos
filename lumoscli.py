'''
Lumos command line interface module
'''

import os
import sys
import tempfile
from pathlib import Path
from pkg_resources import resource_string

import click
from art import text2art

from lumos.config import (
    get_config,
    load_config_string,
    load_config_file
)
from lumos import logger
from lumos.generator import (
    render_single_channel_plateview,
    render_single_plate_plateview,
    render_single_run_plateview,
    render_single_plate_plateview_parallelism,
)
from lumos.picasso import picasso_generate_plate_image


# Find the OS temporary directory location
default_temp_directory = tempfile.gettempdir()

# Define general constant parameters
output_file_format_list = ['jpg', 'jpeg', 'png']


# Setup command group
@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    '-cf',
    "--config-file",
    type=click.Path(exists=True),
    help="Specify a custom configuration file to be used by Lumos.",
)
@click.option(
    '-gcf',
    "--generate-config-file",
    type=click.Path(),
    help='''Create a template for a Lumos configuration file that can
            then be customized.''',
)
def cli(ctx, config_file, generate_config_file):
    '''
    \b

    Welcome to Lumos, a plate image visualization tool!

    Please choose an operation mode (i.e. command) from the list below
    and type 'lumos <mode> --help' to get started.

    Alternatively, to use a custom configuration file, type 'lumos -cf <path_to_config> <mode> --help'.

    \b
    '''
    # Print lumos header
    header_ascii_art = text2art("Lumos", font="big")
    click.echo(header_ascii_art)

    if generate_config_file is not None:
        # If the given path is a folder create a new file, otherwise overwrite the existing file
        if os.path.isdir(generate_config_file):
            generate_config_file = generate_config_file + '/lumos_config.yaml'
        # Copy content of default config file
        with open(generate_config_file, 'wb') as f:
            default_config_bytes = resource_string(
                __name__, 'lumos/default_lumos_config.yaml')
            f.write(default_config_bytes)
        click.echo(
            "The template for the configuration file has been created in "+generate_config_file)
        sys.exit(0)

    if config_file is not None:
        # Load the specified config file
        load_config_file(config_file)
    else:
        # Load the default config bundled with lumos
        default_config_string = resource_string(
            __name__, 'lumos/default_lumos_config.yaml').decode('utf-8')
        load_config_string(default_config_string)

    if ctx.invoked_subcommand is None:
        click.secho("Type 'lumos --help' to get started!", fg='bright_blue')


# -----------------------------  QUALITY CONTROL  ----------------------------- #


# Setup QC mode
@cli.command(
    name="qc",
    help="Quality Control mode",
)
@click.option(
    '-s',
    "--scope",
    type=click.Choice(["run", "plate", "channel"], case_sensitive=False),
    required=True,
    help="Choose if you want to generate a plateview for a single channel, a plate or a whole run",
)
@click.option(
    '-c',
    "--channel",
    type=click.STRING,
    help="If scope is 'channel', choose which single channel to render.",
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
    type=click.Choice(output_file_format_list,
                      case_sensitive=False),
    help="File format of the generated images. You can choose the default one in the configuration file.",
)
@click.option(
    '-b',
    "--brightfield",
    type=click.STRING,
    help="Choose a brightfield channel to include in the plate/run render. To render all of them, type 'all'.",
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
@click.option(
    "--disable-logs",
    is_flag=True,
    help="(dev only) Disable the logger and some visual elements in the console (e.g. progress bars). Useful when running tests with pytest as the logger gets printed to the console.",
    hidden=True,
    # Note: This option is hidden from the --help menu as it is only for debugging purposes.
)
def quality_control(scope, channel, source_path, output_path, temp_path, output_format, brightfield, parallelism, keep_temp_files, disable_logs):
    '''
    Quality Control operation mode - CLI entry
    '''

    is_in_parallel = (parallelism != 1)

    # create logger
    logger.setup(temp_path, enabled=not disable_logs, parallelism=is_in_parallel)

    # announce startup to logger
    logger.info("Started - Quality Control")

    # decode arguments
    if is_in_parallel:
        if parallelism < 1:
            click.secho(
                "CLI ERROR: '--parallelism' argument cannot be less than 1. Please remove it or change its value.", fg='bright_red', bold=True)
            sys.exit(1)
        click.secho(
            "CLI WARNING: When using parallelism, pressing [CTRL+C] does not terminate the program. To halt the execution of the program before it finishes, you have to close your terminal.", fg='bright_yellow')
        click.secho(
            "CLI INFO: When using parallelism, less progress information will be printed in the terminal.", fg='bright_magenta')
        click.echo()

    if keep_temp_files:
        click.secho("CLI Development Note: Keeping previously downloaded temporary files (remove '--keep-temp-files' to regenerate them every time)", fg='bright_blue')
        logger.info(
            "Argument '--keep-temp-files' used from CLI: keeping previously downloaded temporary files")

    if output_format is None:
        output_format = get_config()['default_output_format']

    # decode scope
    if scope == "channel":

        if not channel:
            click.secho(
                "CLI ERROR: Missing channel. Please define a channel using '--channel' <channel_name>.", fg='bright_red', bold=True)
            sys.exit(1)

        if channel not in list(get_config()['channel_info'].keys()):
            click.secho(
                f"CLI ERROR: Wrong channel chosen. Please choose one amongst {list(get_config()['channel_info'].keys())}.", fg='bright_red', bold=True)
            sys.exit(1)

        if is_in_parallel:
            click.secho(
                "CLI WARNING: The '--parallelism' argument has no effect on performance when scope is 'channel'. Consider removing it.", fg='bright_yellow')
        if brightfield is not None:
            click.secho("CLI WARNING: The '--brightfield' argument has no effect when scope is 'channel' and should not be specified. Consider removing it.", fg='bright_yellow')
        click.echo()

        # get platename
        plate_name = Path(source_path).name
        click.echo(
            "Process plate: "
            + plate_name,
        )
        # get channel name
        channel_name = get_config()['channel_info'][channel]['name']
        click.echo(
            "Render channel: "
            + channel
            + " - "
            + channel_name,
        )

        # render the channel for the plate
        render_single_channel_plateview(
            source_path,
            plate_name,
            channel,
            channel_name,
            output_path,
            temp_path,
            output_format,
            keep_temp_files,
        )

    else:

        if channel:
            click.secho(
                "CLI ERROR: '--channel' argument must not be used for run/plate scope. Please remove it.", fg='bright_red', bold=True)
            sys.exit(1)

        channels_to_render = get_config()['default_channels_to_render'].copy()
        if brightfield is None:
            click.secho(
                "CLI Note: Generating render for NONE of the brightfield channels.", fg='bright_blue')
        elif brightfield == "all":
            channels_to_render = channels_to_render + \
                get_config()['brightfield_channels']
            click.secho(
                "CLI Note: Generating renders for ALL brightfield channels.", fg='bright_blue')
        elif brightfield not in get_config()['brightfield_channels']:
            click.secho(
                f"CLI ERROR: Wrong brightfield channel chosen. Please choose one amongst {get_config()['brightfield_channels']}.", fg='bright_red', bold=True)
            sys.exit(1)
        else:
            channels_to_render.append(brightfield)
            click.secho(
                f"CLI Note: Generating render ONLY for brightfield channel {brightfield}.",
                fg='bright_blue')

        click.echo(os.linesep)

        # execute image generation according to the scope
        if scope == "run":

            # get run name
            run_name = Path(source_path)

            # get plates and their path, only if files in it
            plate_list = list(Path(source_path).glob(
                f"./{get_config()['path_from_run_folder_to_plates']}/*"))

            # create a dict with plate name as key and plate folder path as value
            # only folders with tif images are eligible
            plate_dict = {
                x.name: x
                for x in plate_list
                if (x.is_dir() and len(list(x.glob(f"./{get_config()['path_from_plate_folder_to_images']}/*.tif*"))))
            }

            if len(plate_dict) == 0:
                click.secho("ERROR: No valid plates found in run folder.",
                            color='bright_red')
                click.secho("       Make sure that your folder structure matches your configuration. "
                            + f"The current configuration is: <run_folder>/{get_config()['path_from_run_folder_to_plates']}"
                            + f"<plate_folders>/{get_config()['path_from_plate_folder_to_images']}<images>",
                            color='bright_red')
                logger.error("No valid plates found in run folder")
                sys.exit(1)

            click.echo(
                "Lumos will process "
                + str(len(plate_dict))
                + " plate folders from run: "
                + str(run_name)
            )
            click.echo("Plates: " + str(list(plate_dict.keys())))
            click.echo(
                "Channels being rendered: "
                + str(channels_to_render)
                + os.linesep
                + os.linesep
            )

            # render all the plates of the run
            render_single_run_plateview(
                plate_dict,
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
                "Process plate '"
                + plate_name
                + "' and render channels: "
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

    # Successfully terminate
    sys.exit(0)


# -----------------------------  CELL PAINTING  ----------------------------- #


# define cellpainter command
@cli.command(
    name="cp",
    help="Cell Painting mode",
)
@click.option(
    '-s',
    "--scope",
    type=click.Choice(["plate", "wells", "sites"], case_sensitive=False),
    required=True,
    help="Choose if you want to generate a cellpainted image for a whole plate, each well, or each individual site.",
)
@click.option(
    '-w',
    "--single-well",
    type=click.STRING,
    help="If scope is 'wells' or 'plate', this allows you to generate the image for only one well.",
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
    help='''Path to the platemap file of your plate.
    This allows the identifier of each compound to be displayed on the well images.
    You can choose which columns to parse in the configuration file.''',
)
@click.option(
    '-f',
    "--output-format",
    type=click.Choice(output_file_format_list,
                      case_sensitive=False),
    help="File format of the generated images. You can choose the default one in the configuration file.",
)
@click.option(
    "--style",
    type=click.STRING,
    default='classic',
    show_default=True,
    help='''Rendering style of the output image.
            You can see and customize the available styles in the configuration file.''',
)
@click.option(
    "--disable-logs",
    is_flag=True,
    help="(dev only) Disable the logger. Useful when running tests with pytest as the logger gets printed to the console.",
    hidden=True,
    # Note: This option is hidden from the --help menu as it is only for debugging purposes.
)
def cell_painting(scope, single_well, source_path, output_path, temp_path, platemap_path, output_format, style, disable_logs):
    '''
    Cell Painting operation mode - CLI entry
    '''

    # create logger
    logger.setup(temp_path, enabled=not disable_logs, parallelism=False)

    # announce startup to logger
    logger.info("Started - Cell Painting")

    # get platename
    plate_name = Path(source_path).name

    if style not in list(get_config()['fingerprint_style_dict'].keys()):
        click.secho(
            f"CLI ERROR: The chosen style does not exist. Please choose one amongst {list(get_config()['fingerprint_style_dict'].keys())}.",
            fg='bright_red', bold=True
        )
        sys.exit(1)

    if output_format is None:
        output_format = get_config()['default_output_format']

    if platemap_path is not None and scope == 'sites':
        click.secho("CLI WARNING: The '--platemap-path' argument has no effect when scope is 'sites' and should not be specified. Consider removing it.", fg='bright_yellow')
        click.echo()

    if not single_well:
        click.echo(
            "Process wells of plate: "
            + plate_name
            + " and multiplex cell painting channels "
            + str(get_config()['cp_channels_to_use'] if style ==
                  'classic' else list(get_config()['channel_info'].keys())[:5])
        )
    elif scope != 'plate':
        click.echo(
            "Process well "
            + single_well
            + " of plate: "
            + plate_name
            + " and multiplex cell painting channels "
            + str(get_config()['cp_channels_to_use'] if style ==
                  'classic' else list(get_config()['channel_info'].keys())[:5])
        )
    else:
        logger.error(
            "'-w/--single-well' argument used while in scope 'plate'.")
        click.secho(
            "CLI ERROR: Used '-w/--single-well' argument while using scope 'plate'. Those two arguments are incompatible.",
            fg='bright_red', bold=True
        )
        sys.exit(1)

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

    # Successfully terminate
    sys.exit(0)


if __name__ == "__main__":
    # use Click
    cli()
