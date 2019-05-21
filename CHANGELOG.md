2.0
===

* Provided compatibility with GIMP 2.10.
* The output directory is now adjustable and defaults to `[path to GIMP user config]/pypredefs`.
* Removed options to toggle generating completions from GIMP + GTK modules and the GIMP PDB. All modules are now considered when generating predefined completions.
* Renamed and reorganized files.


1.3
===

* Updated script to work with `astor` library version 0.6 and later.
* The plug-in file is now readily executable.


1.2
===

Changes related to the generation of .pypredef files:

* `self` parameter is now included in methods.
* Removed methods and attributes in subclasses identical to those in parent classes to reduce file size.
* Types of class attributes or parent classes in a different module now use the full name (including the external module name) and such modules are imported in the corresponding .pypredef file.
* Removed class docstrings from GTK and `_gimpui` modules to reduce file size.
* Sorted classes to correspond with their method resolution order (MRO), starting with the topmost class (last in the MRO).
* Moved all module-level variables to the end of the module for improved readability.
* Moved all class attributes to the beginning of the class for improved readability.
* Fixed wrong class names if their `__name__` attribute is different from the name yielded by `dir()` (the latter is now used to name the class).
* Added `__name__` class attribute if different from the name yielded by `dir()`.

Changes related to the generation of documentation of PDB procedures:

* Replaced relevant integer parameters with booleans.
* Replaced `"TRUE"` and `"FALSE"` constants with `"True"` and `"False"`, respectively.
* Added description of return values.
* "Pythonized" references to enumerated values and PDB procedures, e.g. `gimpenums.NORMAL_MODE` and `pdb.file_png_save` instead of `NORMAL-MODE` and `file-png-save`, respectively.
* Auto-generated temporary procedures (such as progress bar callbacks) are no longer included.


1.1
===

* Added parameters to optionally disable generating completions modules and GIMP PDB procedures, respectively.
* `Generate Predefined Completions for PyDev` menu item now has a simple GUI.
* Added description of parameters to GIMP PDB procedures.
* Added support for Unicode.
* Introspected module objects are now generated as import statements.


1.0
===

* Initial release.
