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

1. Locate the directory for plug-ins in your GIMP installation by going to `Edit → Preferences → Folders → Plug-Ins`.
2. Choose one of the listed directories there and copy `pypredefgen_gimp.py` and `pypredefgen_gimp` to that directory.
3. Download the [astor](https://github.com/berkerpeksag/astor) library and place it in the directory for plug-ins.
4. If not available in your Python distribution, install [importlib](https://pypi.org/project/importlib/) and place it in the directory for plug-ins.

On Linux and possibly macOS, you may install the required libraries via `pip` instead:
  
    pip install astor importlib


Running the Generator
---------------------

To run the generator, open GIMP and choose `Filters → Python-Fu → Generate Predefined Completions for PyDev`.

You may adjust the output directory.
By default, the predefined completions are located in the `[path to GIMP user config]/pypredefs` directory.

Alternatively, you may run the generator from the Python-Fu console - open GIMP, choose `Filters -> Python-Fu -> Console` and enter

    pdb.python_fu_generate_predefined_completions_for_pydev(None)


Adding Predefined Completions in PyDev
--------------------------------------

To add the predefined completions to PyDev, go to `Window → Preferences → PyDev → Interpreters → Python Interpreter`, choose the GIMP Python interpreter and add the directory containing the generated completions as per the [instructions](http://www.pydev.org/manual_101_interpreter.html#PyDevInterpreterConfiguration-PredefinedCompletions).


Note for GIMP 2.10 Users on Windows
-----------------------------------

For GIMP 2.10 on Windows up to 2.10.8, predefined completions for the `gimpui` module are not generated due to crashes when accessing certain members of that module. 
This issue does not occur from GIMP 2.10.10 onwards.
