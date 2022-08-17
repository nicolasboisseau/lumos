# :microscope: Lumos

Lumos is a script to generate full-plate images from separate well pictures obtained from the cellpainting assay, as well as to generate cell-painted images.

*Note: Your images must be accessible from your file system.*

```
      _                               
     | |                              
     | |    _   _ _ __ ___   ___  ___ 
     | |   | | | | '_ ` _ \ / _ \/ __|
     | |___| |_| | | | | | | (_) \__ \
     |______\__,_|_| |_| |_|\___/|___/ 
```

In this document, you will find information related to:
 * [The installation of the package](#installation)
 * [How to use the program, i.e. the Command-line interface](#command-line-interface-cli)

</br>

To find instructions for developers or maintainers of the package, please refer to [this other documentation](./readme-dev.md).

</br>

## Installation

### Prerequisites

You need to have Python 3.8 installed on a Windows or Linux machine.

### Install Lumos

Choose one of the following 2 options:

#### - Install Lumos from the source files

- Download the source files, either by downloading the ZIP file or cloning the repository.

- Extract/copy them in a 'lumos' folder somewhere on your machine.

- Start a PowerShell terminal in the 'lumos' folder.

- Create a Python VirtualEnv: ```$ python -m venv venv```
    
- Activate the VirtualEnv: ```$ ./venv/Scripts/activate```

- Install the dependencies using PIP: ```$ pip install -r .\requirements.txt```
  
- Install Lumos: ```$ python setup.py install```

#### - Install Lumos from the `wheel` package file

- Get the `wheel` package file from the 'Releases' section on GitHub (it should end with `.whl`).

- Download the release that you are interested in and put it inside of a 'lumos' folder on your machine.

- Start a PowerShell terminal in the 'lumos' folder.

- Create a Python VirtualEnv: ```$ python -m venv venv```
    
- Activate the VirtualEnv: ```$ ./venv/Scripts/activate```

- Install Lumos and its dependencies using PIP: ```$ pip install <name_of_the_package_file>.whl```

### Run Lumos

- Make sure your VirtualEnv is activated.

- Type in the console ```lumos``` to launch the program, or ```lumos --help``` for instructions on how to use it.

</br>

## Command-line Interface (CLI)

The Lumos program is entirely controlled from the terminal. Once installed, you will be able to start the program with the ```lumos``` command, followed by an operation mode, and some arguments.

To see the most up-to-date documentation on the CLI, always run the ```$ lumos --help``` command, and ```$ lumos <arg> --help``` for more detailed documentation on a specific command/argument.

However, we will provide in this document a more detailed and comprehensive explanation of how to use the CLI of Lumos.

### Working with configuration files

In order for Lumos to understand your folder structure and plate configuration, you need to explicitly specify them in a configuration file.

To get started, run `$ lumos --generate-config-file .` in your terminal. This will create a template of a configuration file that will be able to edit with your specific requirements.

Open the newly created file with a text editor and make sure to edit the following entries so that they match how your images are organized:
- `path_from_run_folder_to_plates`
- `path_from_plate_folder_to_images`
- `input_file_naming_scheme`
- `well_grid`
- `site_grid`
- `image_dimensions`
  
Then also make sure that you update the following items with the correct ID of your channels (i.e. how they appear in your file names):
- the keys/sub-entries of `channel_info`
- `default_channels_to_render`
- `brightfield_channels`
- `cp_channels_to_use`

You should also tweak the other parameters to make sure that the output of Lumos suits your needs.

Once your configuration file has been updated, you can tell Lumos to use it by adding the `--config-file` argument right after the `lumos` keyword when you invoke the program as follows:

```
$ lumos -cf <path_to_config_file> ...
```

where we have used the `-cf` argument alias of `--config-file` in order to make the command shorter.

### Operation modes

Lumos has two modes of operation:
 * [Quality Control (`qc`)](#quality-control)
 * [Cell Painting (`cp`)](#cell-painting)

To choose which mode the Lumos program should use, specify its identifier as follows:
 - Use `$ lumos qc ...` to use the Quality Control mode.
 - Use `$ lumos cp ...` to use the Cell Painting mode.

If you are using a configuration file, always specify the operation mode after it:
```
$ lumos -cf <path_to_config_file> qc ...
$ lumos -cf <path_to_config_file> cp ...
```

Here is a brief description of each mode:

> #### Quality Control:
> 
> This mode will assemble all separate pictures of a plate's sites for a specific channel into one single greyscale image. This can be done for a single channel, every channel of a plate, or even several plates in a row.
> 
> This is used to quickly visualize any imperfections or problems that a plate might have exhibited during the experiment.

> #### Cell Painting:
> 
> This mode will combine all separate pictures of a plate's sites, for all channels, into a single color image. The algorithm used for merging the independent channels together can be chosen, and a "classic" style is included to try to reflect the emission wavelengths associated with each channel.
> 
> This can also be used to some extent for quality control, but is mainly intended for the production of resources/assets for communications about the project.

### Arguments

Each operation mode needs arguments to function correctly. Some of them are **required** (such as where the source images can be found), and some are **optional** (such as if any Brightfield channels should be rendered).

Operation mode arguments are always specified after the operation mode as follows:
```
$ lumos qc [arguments]
$ lumos cp [arguments]
$ lumos -cf <path_to_config_file> qc [arguments]
$ lumos -cf <path_to_config_file> cp [arguments]
```

To specify an argument in your command, write its name (or alias) followed by its value: `--argument-name <value>`.

Please find bellow the table of all arguments that can be used in Lumos:

| Operation mode | Required | Argument name | Alias | Expected value | Description |
|---|---|---|---|---|---|
| Both | **Yes** | `--scope` | `-s` | One of [channel, plate, run] if in `qc`, or one of [plate, wells, sites] if in `cp` | The scope indicates to the program what should be rendered and outputted. |
| Both | **Yes** | `--source-path` | `-sp` | A valid path | The path to the source site images. |
| Both | **Yes** | `--output-path` | `-op` | A valid path | The path where the output images should be stored. |
| Both | No | `--temp-path` | `-tp` | A valid path | The path where temporary files should be stored during the operation of the program. If omitted, the default is the system's temp directory. |
| Both | No | `--output-format` | `-f` | One of [jpg, jpeg, png] | The file format that the output images should have. If omitted, the default is 'jpg'. |
| qc | **Yes**, if scope is 'channel' | `--channel` | `-c` | One of the channels' ID | When the scope is 'channel' in `qc` mode, this argument is required to choose which channel should be rendered. |
| qc | No (but can't be used when scope is 'channel') | `--brightfield` | `-b` | One of the brightfield channel IDs or 'all' | Chooses which additional brightfield channels to render. If omitted, none will be rendered by default. |
| qc | No | `--parallelism` | `-p` | An integer number | Chooses on how many CPU cores to split the load of the program. If omitted, this will be 1. If present, less information will be printed to the console during the operation of the program. |
| cp | No | `--style` | *n/a* | One of the available styles' name | Chooses which rendering style to use when generating a cell-painted image. If omitted, the default is the 'classic' style. |
| cp | No (but can't be used when scope is 'plate') | `--single-well` | `-w` | A valid well name | If present, renders only the image of the specified well. |
| cp | No (but can't be used when scope is 'sites') | `--platemap-path` | `-pp` | A valid path to a platemap | If present, the identifier of the compound in each well will be displayed. |

</br>

Some examples of complete commands (using both argument names and aliases) could therefore be:

```
$ lumos qc --scope plate --source-path ./plate1 --output-path ./output
$ lumos qc -s plate -sp ./plate1 -op ./output

$ lumos qc --scope channel --channel C01 --source-path ./plate2 --output-path ./output --temp-path ./temp
$ lumos qc --s channel --c C01 -sp ./plate2 -op ./output -tp ./temp

$ lumos cp --scope plate --source-path ./plate3 --output-path ./output
$ lumos cp --s plate -sp ./plate3 -op ./output

$ lumos cp --scope wells --source-path ./plate4 --output-path ./output --single-well B23 --platemap-path ./platemap_plate4.txt
$ lumos cp --s wells -sp ./plate4 -op ./output -w B23 -pp ./platemap_plate4.txt
```

And similarly, using a custom configuration file, we could get:

```
$ lumos --config-file ./lumos_config.yaml qc --scope plate --source-path ./plate1 --output-path ./output
$ lumos -cf ./lumos_config.yaml qc -s plate -sp ./plate1 -op ./output

$ lumos --config-file ./lumos_config.yaml qc --scope channel --channel C01 --source-path ./plate2 --output-path ./output --temp-path ./temp
$ lumos -cf ./lumos_config.yaml qc --s channel --c C01 -sp ./plate2 -op ./output -tp ./temp

$ lumos --config-file ./lumos_config.yaml cp --scope plate --source-path ./plate3 --output-path ./output
$ lumos -cf ./lumos_config.yaml cp --s plate -sp ./plate3 -op ./output

$ lumos --config-file ./lumos_config.yaml cp --scope wells --source-path ./plate4 --output-path ./output --single-well B23 --platemap-path ./platemap_plate4.txt
$ lumos -cf ./lumos_config.yaml cp --s wells -sp ./plate4 -op ./output -w B23 -pp ./platemap_plate4.txt
```