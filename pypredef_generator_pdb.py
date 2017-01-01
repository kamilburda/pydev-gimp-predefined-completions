# -*- coding: utf-8 -*-

"""
This module is responsible for generating predefined completions for the GIMP
procedural database (PDB).
"""

from __future__ import absolute_import, print_function, division, unicode_literals

import inspect

import ast

import gimp
import gimpcolor
import gimpenums

import pypredef_generator

#===============================================================================


class PdbType(object):
  
  def __init__(self, type_id, type_, base_type=None):
    self._type_id = type_id
    self._type_ = type_
    self._base_type = base_type
  
  @property
  def type_id(self):
    return self._type_id
  
  @property
  def type_(self):
    return self._type_
  
  @property
  def base_type(self):
    return self._base_type
  
  def get_name(self, include_base_type=False):
    if include_base_type and self._base_type is not None:
      return "{0}({1})".format(get_type_name(self._type_), get_type_name(self._base_type))
    else:
      return get_type_name(self._type_)
  
  @classmethod
  def get_by_id(cls, pdb_type_id):
    return _PDB_TYPES_MAP[pdb_type_id]


def get_type_name(type_):
  type_module = inspect.getmodule(type_)
  
  if type_module and hasattr(type_module, "__name__") and type_module.__name__ != "__builtin__":
    return ".".join([type_module.__name__, type_.__name__])
  else:
    return type_.__name__


_PDB_TYPE_ITEMS = [
  (gimpenums.PDB_INT32, int),
  (gimpenums.PDB_INT16, int),
  (gimpenums.PDB_INT8, int),
  (gimpenums.PDB_FLOAT, float),
  (gimpenums.PDB_STRING, bytes),
  (gimpenums.PDB_COLOR, gimpcolor.RGB),
  
  (gimpenums.PDB_INT32ARRAY, tuple, int),
  (gimpenums.PDB_INT16ARRAY, tuple, int),
  (gimpenums.PDB_INT8ARRAY, tuple, int),
  (gimpenums.PDB_FLOATARRAY, tuple, float),
  (gimpenums.PDB_STRINGARRAY, tuple, bytes),
  (gimpenums.PDB_COLORARRAY, tuple, gimpcolor.RGB),
  
  (gimpenums.PDB_IMAGE, gimp.Image),
  (gimpenums.PDB_ITEM, gimp.Item),
  (gimpenums.PDB_DRAWABLE, gimp.Drawable),
  (gimpenums.PDB_LAYER, gimp.Layer),
  (gimpenums.PDB_CHANNEL, gimp.Channel),
  (gimpenums.PDB_SELECTION, gimp.Channel),
  (gimpenums.PDB_VECTORS, gimp.Vectors),
  
  (gimpenums.PDB_PARASITE, gimp.Parasite),
  (gimpenums.PDB_DISPLAY, gimp.Display),
]

_PDB_TYPES_MAP = {type_item[0]: PdbType(*type_item) for type_item in _PDB_TYPE_ITEMS}

#===============================================================================


def generate_predefined_completions_for_gimp_pdb():
  node_pdb = pypredef_generator.get_ast_node_for_root_module(gimp.pdb)
  pypredef_generator.insert_ast_docstring(node_pdb, gimp.pdb)
  
  for pdb_member_name in dir(gimp.pdb):
    pdb_member = getattr(gimp.pdb, pdb_member_name, None)
    
    if _is_member_pdb_function(pdb_member):
      _insert_ast_node_for_pdb_function(pdb_member_name, pdb_member, node_pdb)
    else:
      pypredef_generator.insert_ast_node(pdb_member_name, gimp.pdb, node_pdb)
  
  pypredef_generator.write_pypredef_file("gimp.pdb", node_pdb)


def _insert_ast_node_for_pdb_function(pdb_function_name, pdb_function, node_pdb):
  node_pdb_function = _get_ast_node_for_pdb_function(pdb_function)
  node_pdb.body.append(node_pdb_function)
  pypredef_generator.insert_ast_docstring(node_pdb_function, pdb_function)


def _get_ast_node_for_pdb_function(pdb_function):
  return ast.FunctionDef(
    name=pdb_function.proc_name,
    args=_get_ast_arguments_for_pdb_function(pdb_function),
    body=[
      _get_ast_docstring_for_pdb_function(pdb_function),
      _get_ast_return_value_types_for_pdb_function(pdb_function)],
    decorator_list=[])


def _get_ast_arguments_for_pdb_function(pdb_function):
  args = []
  defaults = []
  
  pdb_params, has_run_mode_param = _get_pdb_params(pdb_function)
  
  if has_run_mode_param:
    pdb_params = pdb_params[:-1]
  
  for pdb_param_info in pdb_params:
    pdb_param_name = _get_pdb_param_name(pdb_param_info)
    args.append(pdb_param_name)
  
  if has_run_mode_param:
    run_mode_name, run_mode_default_value_name = _get_run_mode_parameter_name_and_default_value()
    args.append(ast.Name(id=run_mode_name))
    defaults.append(ast.Name(id=run_mode_default_value_name))
  
  return ast.arguments(args=args, vararg=None, kwarg=None, defaults=defaults)


def _get_run_mode_parameter_name_and_default_value():
  return "run_mode", "gimpenums.RUN_NONINTERACTIVE"


def _get_ast_docstring_for_pdb_function(pdb_function):
  docstring = "\n"
  docstring += pdb_function.proc_blurb
  docstring += "\n\n"
  
  if pdb_function.proc_help and pdb_function.proc_help != pdb_function.proc_blurb:
    docstring += pdb_function.proc_help + "\n"
  
  docstring += "\n"
  docstring += _get_pdb_docstring_param_info(pdb_function)
  
  docstring = docstring.encode(pypredef_generator.TEXT_FILE_ENCODING)
  
  return ast.Expr(value=ast.Str(s=docstring))


def _get_pdb_docstring_param_info(pdb_function):
  docstring_param_info = ""
  pdb_params = _get_pdb_params(pdb_function)[0]
  
  if pdb_params:
    docstring_param_info += "Parameters:\n"
    
    for pdb_param_info in pdb_params:
      docstring_param_info += _get_pdb_param_docstring(pdb_param_info) + "\n"
  
  return docstring_param_info


def _get_pdb_param_docstring(pdb_param_info):
  return "{0} ({1}): {2}".format(
    _get_pdb_param_name(pdb_param_info),
    PdbType.get_by_id(pdb_param_info[0]).get_name(include_base_type=True),
    _get_pdb_param_description(pdb_param_info))


def _get_ast_return_value_types_for_pdb_function(pdb_function):
  if len(pdb_function.return_vals) > 1:
    node_return_value_types = ast.Tuple(
      elts=[ast.Name(id=PdbType.get_by_id(return_vals_info[0]).get_name())
            for return_vals_info in pdb_function.return_vals])
  elif len(pdb_function.return_vals) == 1:
    node_return_value_types = ast.Name(
      id=PdbType.get_by_id(pdb_function.return_vals[0][0]).get_name())
  else:
    node_return_value_types = ast.Name(id="None")
  
  return ast.Return(value=node_return_value_types)


def _is_member_pdb_function(member):
  return type(member).__name__ == "PDBFunction"


def _get_pdb_params(pdb_function):
  """
  Return PDB function parameters and a boolean indicating whether `run_mode`
  parameter is in the parameter list.
  
  If `run_mode` in the parameter list, it is guaranteed to be at the end of the
  parameter list.
  """
  
  pdb_params = []
  run_mode_param_info = None
  
  for pdb_param_info in pdb_function.params:
    if _get_pdb_param_name(pdb_param_info) == "run_mode":
      run_mode_param_info = pdb_param_info
    else:
      pdb_params.append(pdb_param_info)
  
  if run_mode_param_info is not None:
    pdb_params.append(run_mode_param_info)
  
  has_run_mode_param = run_mode_param_info is not None
  
  return pdb_params, has_run_mode_param


def _get_pdb_param_name(pdb_param_info):
  return pdb_param_info[1].replace("-", "_")


def _get_pdb_param_description(pdb_param_info):
  return pdb_param_info[2] if pdb_param_info[2] is not None else ""
