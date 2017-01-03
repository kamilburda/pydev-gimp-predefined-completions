# -*- coding: utf-8 -*-

"""
This module is responsible for generating predefined completions for the GIMP
procedural database (PDB).
"""

from __future__ import absolute_import, print_function, division, unicode_literals

import inspect
import re

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


class PdbParam(object):
  
  def __init__(self, pdb_type_id, name, description=None):
    self._pdb_type_id = pdb_type_id
    self._orig_name = name.decode(pypredef_generator.TEXT_FILE_ENCODING)
    
    self.description = (
      description.decode(pypredef_generator.TEXT_FILE_ENCODING) if description is not None else "")
    self.pdb_type = PdbType.get_by_id(pdb_type_id)
    self.name = self._get_param_name(self._orig_name)
  
  @property
  def pdb_type_id(self):
    return self._pdb_type_id
  
  @property
  def orig_name(self):
    return self._orig_name
  
  @classmethod
  def _get_param_name(cls, orig_name):
    return orig_name.replace("-", "_")


def get_pdb_params(pdb_function_params):
  """
  Return PDB function parameters and a boolean indicating whether `run_mode`
  parameter is in the parameter list.
  
  If `run_mode` in the parameter list, it is guaranteed to be at the end of the
  parameter list.
  """
  
  pdb_params = [PdbParam(*pdb_param_info) for pdb_param_info in pdb_function_params]
  has_run_mode_param = _move_run_mode_param_to_end(pdb_params)
  
  return pdb_params, has_run_mode_param


def _move_run_mode_param_to_end(pdb_params):
  run_mode_param_index = _get_run_mode_param_index(pdb_params)
  has_run_mode_param = run_mode_param_index is not None
  
  if has_run_mode_param:
    run_mode_param = pdb_params.pop(run_mode_param_index)
    pdb_params.append(run_mode_param)
  
  return has_run_mode_param


def _get_run_mode_param_index(pdb_params):
  for pdb_param_index, pdb_param in enumerate(pdb_params):
    if pdb_param.name == "run_mode":
      return pdb_param_index
  
  return None


#===============================================================================


def generate_predefined_completions_for_gimp_pdb():
  node_pdb = pypredef_generator.get_ast_node_for_root_module(gimp.pdb)
  pypredef_generator.insert_ast_docstring(node_pdb, gimp.pdb)
  
  for pdb_member_name in dir(gimp.pdb):
    pdb_member = getattr(gimp.pdb, pdb_member_name, None)
    
    if _is_member_pdb_function(pdb_member):
      if _is_member_generated_temporary_pdb_function(pdb_member_name):
        continue
      else:
        _insert_ast_node_for_pdb_function(pdb_member_name, pdb_member, node_pdb)
    else:
      pypredef_generator.insert_ast_node(pdb_member_name, gimp.pdb, node_pdb)
  
  pypredef_generator.write_pypredef_file("gimp.pdb", node_pdb)


def _is_member_pdb_function(member):
  return type(member).__name__ == "PDBFunction"


def _is_member_generated_temporary_pdb_function(member_name):
  return member_name.startswith("temp_procedure_")


def _insert_ast_node_for_pdb_function(pdb_function_name, pdb_function, node_pdb):
  node_pdb_function = _get_ast_node_for_pdb_function(pdb_function)
  node_pdb.body.append(node_pdb_function)
  pypredef_generator.insert_ast_docstring(node_pdb_function, pdb_function)


def _get_ast_node_for_pdb_function(pdb_function):
  return ast.FunctionDef(
    name=pdb_function.proc_name,
    args=_get_ast_arguments_for_pdb_function(pdb_function),
    body=[
      _get_ast_docstring_for_pdb_function(
        pdb_function,
        additional_docstring_processing_callbacks=[_pythonize_true_false_names]),
      _get_ast_return_value_types_for_pdb_function(pdb_function)],
    decorator_list=[])


def _get_ast_arguments_for_pdb_function(pdb_function):
  args = []
  defaults = []
  
  pdb_params, has_run_mode_param = get_pdb_params(pdb_function.params)
  
  if has_run_mode_param:
    defaults.append(ast.Name(id="gimpenums.RUN_NONINTERACTIVE"))
  
  for pdb_param in pdb_params:
    args.append(pdb_param.name)
  
  return ast.arguments(args=args, vararg=None, kwarg=None, defaults=defaults)


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


def _get_ast_docstring_for_pdb_function(
      pdb_function, additional_docstring_processing_callbacks=None):
  
  docstring = ""
  
  if pdb_function.proc_blurb:
    docstring += pdb_function.proc_blurb
  
  if pdb_function.proc_help and pdb_function.proc_help != pdb_function.proc_blurb:
    docstring += "\n\n"
    docstring += pdb_function.proc_help
  
  docstring += _get_pdb_docstring_for_params(
    pdb_function.params, "Parameters:",
    additional_param_processing_callbacks=[
      PdbParamIntToBoolConverter.convert,
      GimpenumsNamesPythonizer.pythonize])
  docstring += _get_pdb_docstring_for_params(
    pdb_function.return_vals, "Returns:",
    additional_param_processing_callbacks=[GimpenumsNamesPythonizer.pythonize])
  
  if additional_docstring_processing_callbacks:
    for process_docstring in additional_docstring_processing_callbacks:
      docstring = process_docstring(docstring)
  
  docstring = "\n" + docstring.strip() + "\n"
  
  docstring = docstring.encode(pypredef_generator.TEXT_FILE_ENCODING)
  
  return ast.Expr(value=ast.Str(s=docstring))


def _get_pdb_docstring_for_params(
      pdb_function_params, docstring_heading, additional_param_processing_callbacks=None):
  
  params_docstring = ""
  if additional_param_processing_callbacks is None:
    additional_param_processing_callbacks = []
  
  pdb_params, unused_ = get_pdb_params(pdb_function_params)
  
  if pdb_params:
    params_docstring += "\n\n"
    params_docstring += "{0}\n".format(docstring_heading)
    
    for pdb_param in pdb_params:
      for process_pdb_param in additional_param_processing_callbacks:
        process_pdb_param(pdb_param)
      params_docstring += _get_pdb_param_docstring(pdb_param) + "\n"
    
    params_docstring = params_docstring.rstrip("\n")
  
  return params_docstring


def _get_pdb_param_docstring(pdb_param):
  return "{0} ({1}): {2}".format(
    pdb_param.name,
    pdb_param.pdb_type.get_name(include_base_type=True),
    pdb_param.description)


#===============================================================================


def _pythonize_true_false_names(docstring):
  return docstring.replace("FALSE", "False").replace("TRUE", "True")


class PdbParamIntToBoolConverter(object):
  
  _BOOL_PARAM_DESCRIPTION_TRUE_FALSE_REGEX_FORMAT = (
    r"[\.:]? *\(?{0}(  *or  *| *[/,] *){1}\)?"
    r"|[\.:]? *\{{ *{0}( *\({2}\))?, *{1}( *\({3}\))? *\}}")
  
  _PDB_BOOL_PARAM_DESCRIPTION_MATCH_REGEX_COMPONENTS = (
    _BOOL_PARAM_DESCRIPTION_TRUE_FALSE_REGEX_FORMAT.format(r"true", r"false", r"1", r"0")
    + r"|"
    + _BOOL_PARAM_DESCRIPTION_TRUE_FALSE_REGEX_FORMAT.format(r"false", r"true", r"0", r"1"))
  
  _PDB_BOOL_PARAM_DESCRIPTION_MATCH_REGEX = (
    r"("
    + _PDB_BOOL_PARAM_DESCRIPTION_MATCH_REGEX_COMPONENTS
    + r"|true: .*false: "
    + r"|false: .*true: "
    + r"|\?$"
    + r")")
  
  _PDB_BOOL_PARAM_DESCRIPTION_SUBSTITUTE_REGEX = (
    r"(" + _PDB_BOOL_PARAM_DESCRIPTION_MATCH_REGEX_COMPONENTS + r")$")
  
  @classmethod
  def convert(cls, pdb_param):
    if cls._is_pdb_param_bool(pdb_param):
      pdb_param.pdb_type = PdbType(pdb_param.pdb_type.type_, bool)
      pdb_param.description = re.sub(
        cls._PDB_BOOL_PARAM_DESCRIPTION_SUBSTITUTE_REGEX, "",
        pdb_param.description, flags=re.UNICODE | re.IGNORECASE)
  
  @classmethod
  def _is_pdb_param_bool(cls, pdb_param):
    return (
      pdb_param.pdb_type.type_ is int
      and re.search(
        cls._PDB_BOOL_PARAM_DESCRIPTION_MATCH_REGEX,
        pdb_param.description, flags=re.UNICODE | re.IGNORECASE))


class GimpenumsNamesPythonizer(object):
  
  _gimpenums_names_map = {}
  
  @classmethod
  def pythonize(cls, pdb_param):
    cls._fill_gimpenums_names_map()
    
    pdb_param_description_parts = cls._get_param_description_parts(pdb_param.description)
    if not pdb_param_description_parts:
      return
    
    pdb_param.description = "".join(
      [pdb_param_description_parts[0],
       cls._pythonize_enum_names(pdb_param_description_parts[1]),
       pdb_param_description_parts[2]])
  
  @classmethod
  def _fill_gimpenums_names_map(cls):
    if not cls._gimpenums_names_map:
      python_gimpenums_names = [
        member for member in dir(gimpenums)
        if re.match(r"[A-Z][A-Z0-9_]*$", member) and member not in ["TRUE", "FALSE"]]
      
      for python_enum_name in python_gimpenums_names:
        pdb_enum_name = python_enum_name.replace("_", "-")
        cls._gimpenums_names_map[pdb_enum_name] = gimpenums.__name__ + "." + python_enum_name
  
  @classmethod
  def _pythonize_enum_names(cls, enums):
    enum_strings = re.split(r", *", enums)
    processed_enum_strings = []
    
    for enum_string in enum_strings:
      enum_string_components = re.split(r"^([A-Z][A-Z0-9-]+) *(\([0-9]+\))$", enum_string)
      enum_string_components = [component for component in enum_string_components if component]
      
      if len(enum_string_components) == 2:
        enum_name, enum_number_string = enum_string_components
        if enum_name in cls._gimpenums_names_map:
          enum_name = cls._gimpenums_names_map[enum_name]
        
        processed_enum_strings.append("{0} {1}".format(enum_name, enum_number_string))
      else:
        processed_enum_strings.append(enum_string)
    
    return ", ".join(processed_enum_strings)
  
  @classmethod
  def _get_param_description_parts(cls, param_description):
    match = re.search(r"(.*{ *)(.*?)( *})$", param_description)
    if match:
      return match.groups()
    else:
      return None
