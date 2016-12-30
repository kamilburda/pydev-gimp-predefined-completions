"""
This module defines a GIMP plug-in to generate predefined completions for PyDev
(Eclipse IDE plug-in) for GIMP modules.
"""

import os

import importlib

import gimpfu

import pypredef_generator
import pypredef_generator_pdb

#===============================================================================


def generate_predefined_completions_for_pydev():
  module_names = _get_module_names(pypredef_generator.MODULES_FILE_PATH)
  
  _make_dirs(pypredef_generator.PYPREDEF_FILES_DIR)
  
  for module_name in module_names:
    module = importlib.import_module(module_name)
    pypredef_generator.generate_predefined_completions(module)
  
  pypredef_generator_pdb.generate_predefined_completions_for_gimp_pdb()


def _get_module_names(modules_file_path):
  if os.path.isfile(modules_file_path):
    with open(modules_file_path, "r") as modules_file:
      return [line.strip() for line in modules_file.readlines()]
  else:
    return []


def _make_dirs(path):
  """
  Recursively create directories from the specified path.
  
  Do not raise exception if the path already exists.
  """
  
  try:
    os.makedirs(path)
  except OSError as exc:
    if exc.errno == os.errno.EEXIST and os.path.isdir(path):
      pass
    elif exc.errno == os.errno.EACCES and os.path.isdir(path):
      # This can happen if `os.makedirs` is called on a root directory
      # in Windows (e.g. `os.makedirs("C:\\")`).
      pass
    else:
      raise

#===============================================================================

gimpfu.register(
  proc_name="generate_predefined_completions_for_pydev",
  blurb=("Generate predefined completions for GIMP modules for PyDev "
         "(Eclipse IDE plug-in)"),
  help=('This plug-in generates separate .pypredef files for each module and '
        'for the GIMP procedural database in the "{0}" subdirectory '
        'of the directory where this plug-in is located.'
        .format(pypredef_generator.PYPREDEF_FILES_DIRNAME)),
  author="khalim19",
  copyright="",
  date="",
  label="Generate Predefined Completions for PyDev",
  imagetypes="",
  params=[],
  results=[],
  function=generate_predefined_completions_for_pydev,
  menu="<Image>/Filters/Languages/Python-Fu")

gimpfu.main()
