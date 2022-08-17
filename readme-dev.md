## Developing the Lumos package

### Local installation

During development, the command ```$ python setup.py develop``` can be used to install the package locally and therefore test the `lumos` command. After development, the command ```$ python setup.py develop --uninstall``` can be used to reverse the operation.

*Note: this is compatible with 'hot-reload', i.e. the `lumos` command will always use the latest version of the source files.*

### Testing

To test your current version of Lumos, install the package (e.g. locally with the command above) and run ```$ pytest -v``` in the root folder of the program.
When creating tests, if print statements are included inside of them for debugging purposes, use ```$ pytest -s``` instead to print them to the console.

### Generating the HTML documentation

The HTML documentation that is provided alongside the source code is generated using the `pdoc3` package.

This package uses the XML documentation present in the source files to generate a static HTML website.

Once the XML documentation is well completed, use the command `$ pdoc3 --html ./lumos` to generate the HTML documentation of the sub-modules contained in the `./lumos` subfolder, i.e. the back-end modules (*for some reason, running this command for the root folder of the codebase `.` gives an error, so only the documentation for the back-end modules can be generated*).

*Note: if some HTML documentation has already been recently generated, use the `--force` flag to overwrite it.*

Once the HTML files have been successfully generated, they can be placed inside of the `./docs` folder.