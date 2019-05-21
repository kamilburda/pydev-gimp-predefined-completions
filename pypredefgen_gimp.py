#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines a GIMP plug-in to generate predefined completions for PyDev
(Eclipse IDE plug-in) for GIMP modules.
"""

from __future__ import absolute_import, print_function, division, unicode_literals

import inspect
import io
import os
import sys

# Fix Windows installation failing to import modules from subdirectories in the
# `plug-ins` directory.
if os.name == "nt":
  current_module_dirpath = os.path.dirname(inspect.getfile(inspect.currentframe()))
  if current_module_dirpath not in sys.path:
    sys.path.append(current_module_dirpath)

import importlib

import gimp
import gimpfu

from pypredefgen_gimp import pypredefgen
from pypredefgen_gimp import pypredefgen_pdb


PLUGIN_DIRPATH = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
MODULES_FILEPATH = os.path.join(PLUGIN_DIRPATH, "modules.txt")

PYPREDEF_FILES_DIRNAME = "pypredefs"
PYPREDEF_FILES_DIRPATH = os.path.join(gimp.directory, PYPREDEF_FILES_DIRNAME)

MODULES_FOR_WHICH_TO_IGNORE_DOCSTRINGS = [
  "_gimpui",
  "gtk._gtk",
  "gtk.gdk",
  "gobject._gobject",
  "cairo._cairo",
  "pango",
  "pangocairo",
  "atk",
  "glib._glib",
  "gio._gio",
]


def generate_predefined_completions_for_pydev(output_dirpath=PYPREDEF_FILES_DIRPATH):
  if not output_dirpath:
    output_dirpath = PYPREDEF_FILES_DIRPATH
  
  module_names = _get_module_names(MODULES_FILEPATH)
  
  gimp_progress = GimpProgress(_get_num_progress_items(module_names))
  gimp_progress.initialize()
  
  _make_dirs(output_dirpath)
  
  _generate_for_modules(output_dirpath, module_names, gimp_progress)
  
  _generate_for_pdb(output_dirpath, gimp_progress)


def _generate_for_modules(output_dirpath, module_names, gimp_progress):
  pypredefgen.module_specific_processing_functions.update({
    module_name: [pypredefgen.remove_class_docstrings]
    for module_name in MODULES_FOR_WHICH_TO_IGNORE_DOCSTRINGS
  })
  
  for module_name in module_names:
    module = importlib.import_module(module_name)
    pypredefgen.generate_predefined_completions(output_dirpath, module)
    gimp_progress.update()


def _generate_for_pdb(output_dirpath, gimp_progress):
  pypredefgen_pdb.generate_predefined_completions_for_gimp_pdb(output_dirpath)
  gimp_progress.update()


def _get_module_names(modules_file_path):
  if os.path.isfile(modules_file_path):
    with io.open(
           modules_file_path, "r",
           encoding=pypredefgen.TEXT_FILE_ENCODING) as modules_file:
      return [line.strip() for line in modules_file.readlines()]
  else:
    return []


def _make_dirs(path):
  """
  Recursively create directories from the specified path. Do not raise exception
  if the path already exists.
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


class GimpProgress(object):
  
  def __init__(self, num_total_tasks=0):
    self.num_total_tasks = num_total_tasks
    self._num_finished_tasks = 0
  
  @property
  def num_finished_tasks(self):
    return self._num_finished_tasks
  
  def initialize(self, message=None):
    gimp.progress_init(message if message is not None else "")
  
  def update(self, num_tasks=1):
    if self._num_finished_tasks + num_tasks > self.num_total_tasks:
      raise ValueError("number of finished tasks exceeds the number of total tasks")
    
    self._num_finished_tasks += num_tasks
    
    gimp.progress_update(self._num_finished_tasks / self.num_total_tasks)
  

def _get_num_progress_items(module_names):
  return len(module_names) + 1


gimpfu.register(
  proc_name="generate_predefined_completions_for_pydev",
  blurb=("Generate predefined completions for GIMP modules for PyDev "
         "(Eclipse IDE plug-in)"),
  help=('This plug-in generates separate .pypredef files for each module and '
        'for the GIMP procedural database in the "{0}" subdirectory '
        'of the directory where this plug-in is located.'
        .format(PYPREDEF_FILES_DIRNAME)),
  author="khalim19",
  copyright="",
  date="",
  label="Generate Predefined Completions for PyDev",
  imagetypes="",
  params=[
    (gimpfu.PF_STRING, "output_folder", "Output folder", PYPREDEF_FILES_DIRPATH),
  ],
  results=[],
  function=generate_predefined_completions_for_pydev,
  menu="<Image>/Filters/Languages/Python-Fu")


if __name__ == "__main__":
  gimpfu.main()
