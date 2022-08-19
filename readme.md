# :microscope: Lumos

Lumos is a script to generate full-plate images from separate well pictures obtained from the cellpainting assay, as well as to generate cell-painted images.

Important notes:
- This version of Lumos fits with images generated with the Yokogawa CV8000 High content analysis system.
- Your images must be accessible from your file system.

</br>

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

To find instructions for developers or maintainers of the project, please refer to [this other documentation](./readme-dev.md).

</br>

## Installation

### Prerequisites

You need to have Python 3.8 installed on a Windows or Linux machine.

### Install Lumos

Choose one of the following 2 options:

#### Install Lumos from the source files

- Download the source files, either by downloading the ZIP file or cloning the repository.

- Extract/copy them in a 'lumos' folder somewhere on your machine.

- Start a PowerShell terminal in the 'lumos' folder.

- Create a Python VirtualEnv: ```$ python -m venv venv```
    
- Activate the VirtualEnv: ```$ ./venv/Script/activate.ps1```

- Install the dependencies using PIP: ```$ pip install -r .\requirements.txt```
  
- Install Lumos: ```$ python setup.py install```

#### Install Lumos from the `wheel` package file

- Get the `wheel` package file from the 'Releases' section on GitHub (it should end with `.whl`).

- Download the release that you are interested in and put it inside of a 'lumos' folder on your machine.

- Start a PowerShell terminal in the 'lumos' folder.

- Create a Python VirtualEnv: ```$ python -m venv venv```
    
- Activate the VirtualEnv: ```$ ./venv/Script/activate.ps1```

- Install Lumos and its dependencies using PIP: ```$ pip install <name_of_the_package_file>.whl```

### Run Lumos

- Make sure your VirtualEnv is activated.

- Type in the console ```lumos``` to launch the program, or ```lumos --help``` for instructions on how to use it.

</br>

## Command-line Interface (CLI)

The Lumos program is entirely controlled from the terminal. Once installed, you will be able to start the program with the ```lumos``` command, followed by an operation mode, and some arguments.

To see the most up-to-date documentation on the CLI, always run the ```$ lumos --help``` command, and ```$ lumos <arg> --help``` for more detailed documentation on a specific command/argument.

However, we will provide in this document a more detailed and comprehensive explanation of how to use the CLI of Lumos.

### Operation modes

Lumos has currently two modes of operation:
 * [Quality Control (`qc`)](#quality-control)
 * [Cell Painting (`cp`)](#cell-painting)

To choose which mode the Lumos program should use, specify its identifier after the `lumos` keyword as follows:
 - Use `$ lumos qc <args>` to use the Quality Control mode.
 - Use `$ lumos cp <args>` to use the Cell Painting mode.

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

Please find bellow the table of all arguments that can be used in Lumos:

| Operation mode | Argument name   | Alias | Required                 | Expected value                                                               | Description                                                                                                                                                                                  |
|----------------|-----------------|-------|--------------------------|------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Both           | `--scope`       | `-s`  | Yes                      | One of [channel, plate, run] if in `qc`, or one of [plate, wells, sites] if in `cp` | The scope indicates to the program what should be rendered and outputted.                                                                                                                    |
| qc             | `--channel`     | `-c`  | Yes, if scope is channel | One of the channels' name (run `$ lumos qc --help` for full list)            | When the scope is "channel" in QC mode, this argument is required in order to indicate which channel should be rendered.                                                                   |
| Both           | `--source-path` | `-sp` | Yes                      | A valid path                                                                 | The path to the source site images.                                                                                                                                                          |
| Both           | `--output-path` | `-op` | Yes                      | A valid path                                                                 | The path where the output images should be stored.                                                                                                                                           |
| Both           | `--temp-path`   | `-tp` | No                       | A valid path, if present                                                     | The path where temporary files should be stored during the operation of the program. If omitted, the default is the system's temp directory.                                                 |
| Both           | `--output-format` | `-f` | No                      | One of [jpg, jpeg, png], if present                                          | The file format that the output images should have. If omitted, the default is 'jpg'.                                                 |
| qc             | `--brightfield` | `-b`  | No                       | One of [none, 1, 2, 3, all], if present                                      | When scope is "plate" or "run", chooses which brightfield channels to render. If omitted, none will be rendered by default.                                                                                  |
| qc             | `--parallelism` | `-p`  | No                       | An integer number, if present                                                | Chooses on how many CPU cores to split the load of the program. If omitted, this will be 1. If present, less information will be printed to the console during the operation of the program. |
| cp             | `--style`       |  *n/a*  | No                       | One of the available styles' name (run `$ lumos cp --help` for full list)    | Chooses which rendering style to use when generating a cell-painted image. If omitted, the default is the 'classic' style.                                                                   |
| cp  | `--single-well` | `-w`  | No (but can't be used when scope is 'plate')  | A valid well name  | If present, renders only the image of the specified well |
| cp  | `--platemap-path` | `-pp`  | No (but can't be used when scope is 'sites')  | A valid path to a platemap  | If present, displays the identifier of the compound in each well |
