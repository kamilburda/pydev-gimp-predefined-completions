# -*- coding: utf-8 -*-

"""
This module is responsible for generating predefined completions for the GIMP
procedural database (PDB).
"""

from __future__ import absolute_import, print_function, division, unicode_literals

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
      return (
        "{0}({1})".format(
          pypredef_generator.get_full_type_name(self._type_),
          pypredef_generator.get_full_type_name(self._base_type)))
    else:
      return pypredef_generator.get_full_type_name(self._type_)
  
  @classmethod
  def get_by_id(cls, pdb_type_id):
    return _PDB_TYPES_MAP[pdb_type_id]


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
    self.name = pythonize_string(self._orig_name)
  
  @property
  def pdb_type_id(self):
    return self._pdb_type_id
  
  @property
  def orig_name(self):
    return self._orig_name


def pythonize_string(str_):
  return str_.replace("-", "_")


def unpythonize_string(str_):
  return str_.replace("_", "-")


def get_pdb_params(pdb_function_params):
  return [PdbParam(*pdb_param_info) for pdb_param_info in pdb_function_params]


def get_pdb_params_with_fixed_run_mode(pdb_function_params):
  """
  Return PDB function parameters and a boolean indicating whether `run_mode`
  parameter is in the parameter list.
  
  If `run_mode` is in the parameter list, it is moved to the end of the list.
  """
  
  pdb_params = get_pdb_params(pdb_function_params)
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


_DEFAULT_RUN_MODE_NAME = "gimpenums.RUN_NONINTERACTIVE"

#===============================================================================


class MultiStringRegexPattern(object):
  
  def __init__(self, matches_and_replacements, get_regex_for_matches_func):
    self._matches_and_replacements = matches_and_replacements
    self._get_regex_for_matches_func = get_regex_for_matches_func
    
    self._pattern = None
  
  def get_pattern(self):
    if self._pattern is None:
      self._pattern = re.compile(
        self._get_regex_for_matches_func(self._get_matches_regex_component()), flags=re.UNICODE)
    
    return self._pattern
  
  def _get_matches_regex_component(self):
    return (
      r"("
      + r"|".join(
          re.escape(match_string) for match_string in self._matches_and_replacements)
      + r")")
  
  def sub(self, replacement, str_):
    return self.get_pattern().sub(replacement, str_)


def split_param_description(param_description, regex):
  match = re.search(regex, param_description)
  if match is not None:
    return match.groups()
  else:
    return None


#===============================================================================


def generate_predefined_completions_for_gimp_pdb():
  pdb_node = pypredef_generator.get_ast_node_for_module(gimp.pdb)
  
  for pdb_member_name in dir(gimp.pdb):
    pdb_member = getattr(gimp.pdb, pdb_member_name, None)
    
    if _is_member_pdb_function(pdb_member):
      if _is_member_generated_temporary_pdb_function(pdb_member_name):
        continue
      else:
        _insert_ast_node_for_pdb_function(pdb_member_name, pdb_member, pdb_node)
    else:
      pypredef_generator.insert_ast_node(pdb_member_name, gimp.pdb, pdb_node)
  
  pypredef_generator.insert_ast_docstring(pdb_node, gimp.pdb)
  
  pypredef_generator.write_pypredef_file("gimp.pdb", pdb_node)


def _is_member_pdb_function(member):
  return type(member).__name__ == "PDBFunction"


def _is_member_generated_temporary_pdb_function(member_name):
  return member_name.startswith("temp_procedure_")


def _insert_ast_node_for_pdb_function(pdb_function_name, pdb_function, pdb_node):
  pdb_function_node = _get_ast_node_for_pdb_function(pdb_function)
  pdb_node.body.append(pdb_function_node)
  pypredef_generator.insert_ast_docstring(pdb_function_node, pdb_function)


def _get_ast_node_for_pdb_function(pdb_function):
  return ast.FunctionDef(
    name=pdb_function.proc_name,
    args=_get_ast_arguments_for_pdb_function(pdb_function),
    body=[
      _get_ast_docstring_for_pdb_function(
        pdb_function,
        additional_docstring_processing_callbacks=[
          _pythonize_true_false_names,
          _PdbFunctionNamePythonizer.pythonize,
          _PdbParamNamePythonizer(get_pdb_params(pdb_function.params)).pythonize_docstring]),
      _get_ast_return_value_types_for_pdb_function(pdb_function)],
    decorator_list=[])


def _get_ast_arguments_for_pdb_function(pdb_function):
  args = []
  defaults = []
  
  pdb_params, has_run_mode_param = get_pdb_params_with_fixed_run_mode(pdb_function.params)
  
  if has_run_mode_param:
    defaults.append(ast.Name(id=_DEFAULT_RUN_MODE_NAME))
  
  for pdb_param in pdb_params:
    args.append(pdb_param.name)
  
  return ast.arguments(args=args, vararg=None, kwarg=None, defaults=defaults)


def _get_ast_return_value_types_for_pdb_function(pdb_function):
  if len(pdb_function.return_vals) > 1:
    return_value_types_node = ast.Tuple(
      elts=[ast.Name(id=PdbType.get_by_id(return_vals_info[0]).get_name())
            for return_vals_info in pdb_function.return_vals])
  elif len(pdb_function.return_vals) == 1:
    return_value_types_node = ast.Name(
      id=PdbType.get_by_id(pdb_function.return_vals[0][0]).get_name())
  else:
    return_value_types_node = ast.Name(id="None")
  
  return ast.Return(value=return_value_types_node)


def _get_ast_docstring_for_pdb_function(
      pdb_function, additional_docstring_processing_callbacks=None):
  
  docstring = ""
  
  if pdb_function.proc_blurb:
    docstring += pdb_function.proc_blurb
  
  if pdb_function.proc_help and pdb_function.proc_help != pdb_function.proc_blurb:
    docstring += "\n\n"
    docstring += pdb_function.proc_help
  
  docstring += _get_pdb_docstring_for_params(
    get_pdb_params_with_fixed_run_mode(pdb_function.params)[0], "Parameters:",
    additional_param_processing_callbacks=[
      _PdbParamIntToBoolConverter.convert,
      _GimpenumsNamePythonizer.pythonize,
      _PdbParamNamePythonizer(get_pdb_params(pdb_function.params)).pythonize_param])
  
  docstring += _get_pdb_docstring_for_params(
    get_pdb_params(pdb_function.return_vals), "Returns:",
    additional_param_processing_callbacks=[_GimpenumsNamePythonizer.pythonize])
  
  if additional_docstring_processing_callbacks:
    for process_docstring in additional_docstring_processing_callbacks:
      docstring = process_docstring(docstring)
  
  docstring = "\n" + docstring.strip() + "\n"
  
  docstring = docstring.encode(pypredef_generator.TEXT_FILE_ENCODING)
  
  return ast.Expr(value=ast.Str(s=docstring))


def _get_pdb_docstring_for_params(
      pdb_params, docstring_heading, additional_param_processing_callbacks=None):
  
  params_docstring = ""
  if additional_param_processing_callbacks is None:
    additional_param_processing_callbacks = []
  
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


class _PdbParamIntToBoolConverter(object):
  
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


class _PdbFunctionNamePythonizer(object):
  
  _pdb_function_names_map = {}
  _pdb_function_names_pattern = MultiStringRegexPattern(
    _pdb_function_names_map, lambda matches_regex: r"'\b" + matches_regex + r"\b'")
  
  @classmethod
  def pythonize(cls, docstring):
    def _pythonize_function_name(match):
      return "`{0}`".format(cls._pdb_function_names_map[match.group(1)])
    
    cls._fill_pdb_function_names_map()
    
    return cls._pdb_function_names_pattern.sub(_pythonize_function_name, docstring)
  
  @classmethod
  def _fill_pdb_function_names_map(cls):
    if not cls._pdb_function_names_map:
      for pdb_member_name in dir(gimp.pdb):
        if (_is_member_pdb_function(getattr(gimp.pdb, pdb_member_name, None))
            and not _is_member_generated_temporary_pdb_function(pdb_member_name)):
          unpythonized_member_name = unpythonize_string(pdb_member_name)
          cls._pdb_function_names_map[unpythonized_member_name] = "pdb." + pdb_member_name
    
    return cls._pdb_function_names_map


class _PdbParamNamePythonizer(object):
  
  def __init__(self, pdb_params):
    self._pdb_params = pdb_params
    
    self._pdb_param_names = {
      pdb_param.orig_name: pdb_param.name for pdb_param in pdb_params}
  
    self._pdb_param_names_pattern = MultiStringRegexPattern(
      self._pdb_param_names, lambda matches_regex: r"'\b" + matches_regex + r"\b'")
  
  def pythonize_param(self, pdb_param):
    param_description_parts = split_param_description(
      pdb_param.description, r"^(.*)\((.*?)\)$")
    if not param_description_parts:
      return
    
    pdb_param.description = "".join([
      param_description_parts[0],
      self._pythonize_param_name_in_description(param_description_parts[1])])
  
  def _pythonize_param_name_in_description(self, param_description_part):
    components = re.split(r"( +[<>]=? +)", param_description_part)
    processed_components = []
    
    for component in components:
      if component in self._pdb_param_names:
        processed_components.append(self._pdb_param_names[component])
      else:
        processed_components.append(component)
    
    return "({0})".format("".join(processed_components))
  
  def pythonize_docstring(self, docstring):
    def _pythonize_param_name(match):
      return "`{0}`".format(self._pdb_param_names[match.group(1)])
    
    return self._pdb_param_names_pattern.sub(_pythonize_param_name, docstring)


class _GimpenumsNamePythonizer(object):
  
  _gimpenums_names_map = {}
  
  @classmethod
  def pythonize(cls, pdb_param):
    pdb_param_description_parts = split_param_description(
      pdb_param.description, r"(.*{ *)(.*?)( *})$")
    if not pdb_param_description_parts:
      return
    
    pdb_param.description = "".join([
      pdb_param_description_parts[0],
      cls._pythonize_enum_names(pdb_param_description_parts[1]),
      pdb_param_description_parts[2]])
  
  @classmethod
  def _get_gimpenums_names_map(cls):
    if not cls._gimpenums_names_map:
      python_gimpenums_names = [
        member for member in dir(gimpenums)
        if re.match(r"[A-Z][A-Z0-9_]*$", member) and member not in ["TRUE", "FALSE"]]
      
      for python_enum_name in python_gimpenums_names:
        pdb_enum_name = unpythonize_string(python_enum_name)
        cls._gimpenums_names_map[pdb_enum_name] = gimpenums.__name__ + "." + python_enum_name
    
    return cls._gimpenums_names_map
  
  @classmethod
  def _pythonize_enum_names(cls, enums):
    enum_strings = re.split(r", *", enums)
    processed_enum_strings = []
    
    for enum_string in enum_strings:
      enum_string_components = re.split(r"^([A-Z][A-Z0-9-]+) *(\([0-9]+\))$", enum_string)
      enum_string_components = [component for component in enum_string_components if component]
      
      if len(enum_string_components) == 2:
        enum_name, enum_number_string = enum_string_components
        if enum_name in cls._get_gimpenums_names_map():
          enum_name = cls._get_gimpenums_names_map()[enum_name]
        
        processed_enum_strings.append("{0} {1}".format(enum_name, enum_number_string))
      else:
        processed_enum_strings.append(enum_string)
    
    return ", ".join(processed_enum_strings)
