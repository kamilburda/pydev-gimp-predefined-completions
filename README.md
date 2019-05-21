PyDev Predefined Completions Generator for GIMP
===============================================

This Python script generates [predefined completions](http://www.pydev.org/manual_101_interpreter.html) for [PyDev](http://www.pydev.org/) for GIMP and GTK modules to improve development of GIMP plug-ins written in Python.

Development of Python GIMP plug-ins is provided by several Python modules compiled as `.pyd` files.
However, PyDev has trouble parsing such files, resulting in missing code completion and `Undefined variable from import` error messages.

This script therefore mitigates this problem by generating predefined completions for GIMP modules, GTK modules and GIMP procedures/plug-ins (accessible via `gimp.pdb`).


Requirements
------------

* GIMP 2.8 or later
* [astor](https://github.com/berkerpeksag/astor) library - version 0.6 or later


Installation
------------

1. Locate the directory for plug-ins in your GIMP installation. Go to `Edit → Preferences → Folders → Plug-Ins`.
2. Choose one of the listed directories there and copy the contents of the package to that directory.
3. Download the [astor](https://github.com/berkerpeksag/astor) library and place it in the directory for plug-ins. On Linux and possibly macOS, you may install the library via `pip`:
  
    pip install astor


Running the Generator
---------------------

To run the generator, open GIMP and choose `Filters -> Python-Fu -> Generate Predefined Completions for PyDev`.

Alternatively, you may run the plug-in from the Python-Fu console: Open GIMP, choose `Filters -> Python-Fu -> Console` and enter

    pdb.python_fu_generate_predefined_completions_for_pydev(True, True)


Adding Predefined Completions in PyDev
--------------------------------------

Once the generator finishes running, the predefined completions are located in the `pypredefs` subdirectory of the directory containing this script.

To add the predefined completions to PyDev, simply choose the GIMP Python interpreter and add the entire `pypredefs` directory as per the [instructions](http://www.pydev.org/manual_101_interpreter.html#PyDevInterpreterConfiguration-PredefinedCompletions).

