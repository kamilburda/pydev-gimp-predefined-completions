PyDev Predefined Completions Generator for GIMP
===============================================

This simple Python script generates
[predefined completions](http://www.pydev.org/manual_101_interpreter.html)
for [PyDev](http://www.pydev.org/) for GIMP and GTK modules to improve
development of GIMP plug-ins written in Python.

Development of GIMP plug-ins in Python is provided by several Python modules
compiled as `.pyd` files. However, PyDev has trouble parsing such files,
resulting in missing code completion and "Undefined variable from import" error
messages. While PyDev also provides "Forced Builtins" feature, it apparently
does not work for GIMP modules (and GTK modules, at least on Windows).

This script therefore attempts to solve this problem by generating predefined
completions for GIMP and GTK Python modules.

Additionally, this script generates predefined completions for all plug-ins and
procedures installed in GIMP (stored in the so called procedural database, or
PDB in short).


Requirements
------------

* This script is written as a GIMP plug-in and therefore requires GIMP, version
2.8 or later.
* [astor](https://github.com/berkerpeksag/astor) library - not version 0.5, but
  preferably the latest revision from the repository.


Installation
------------

1. Install the script by copying all files to the
   `[user directory]/.gimp-<version>/plug-ins` directory.
2. Download the [astor](https://github.com/berkerpeksag/astor) library and
   install it in `[user directory]/.gimp-<version>/plug-ins` directory.


Running the Generator
---------------------

To run the generator, open GIMP and choose
`Filters -> Python-Fu -> Generate Predefined Completions for PyDev`.

Alternatively, you may run the plug-in from the Python-Fu console: Open GIMP,
choose `Filters -> Python-Fu -> Console` and enter
`pdb.generate_predefined_completions_for_pydev(True, True)`.


Installing Predefined Completions in PyDev
------------------------------------------

Once the generator finishes running, the predefined completions are located in
the `pypredefs` subdirectory of the directory where this plug-in is installed.

To add the predefined completions to PyDev, refer to
[PyDev documentation](http://www.pydev.org/manual_101_interpreter.html). Simply
add the entire `pypredefs` directory to the list of directories with predefined
completions for the Python interpreter used by GIMP.
