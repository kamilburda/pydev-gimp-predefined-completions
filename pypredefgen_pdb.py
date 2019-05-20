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

import pypredefgen


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
        b"{0}({1})".format(
          pypredefgen.get_full_type_name(self._type_),
          pypredefgen.get_full_type_name(self._base_type)))
    else:
      return pypredefgen.get_full_type_name(self._type_)
  
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
    self._orig_name = name
    
    self.description = description if description is not None else b""
    self.pdb_type = PdbType.get_by_id(pdb_type_id)
    self.name = pythonize_string(self._orig_name)
  
  @property
  def pdb_type_id(self):
    return self._pdb_type_id
  
  @property
  def orig_name(self):
    return self._orig_name


def pythonize_string(str_):
  return str_.replace(b"-", b"_")


def unpythonize_string(str_):
  return str_.replace(b"_", b"-")


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
    if pdb_param.name == b"run_mode":
      return pdb_param_index
  
  return None


_DEFAULT_RUN_MODE_NAME = b"gimpenums.RUN_NONINTERACTIVE"

#===============================================================================


class MultiStringRegexPattern(object):
  
  def __init__(self, matches_and_replacements, get_regex_for_matches_func):
    self._matches_and_replacements = matches_and_replacements
    self._get_regex_for_matches_func = get_regex_for_matches_func
    
    self._pattern = None
  
  def get_pattern(self):
    if self._pattern is None:
      self._pattern = re.compile(
        self._get_regex_for_matches_func(self._get_matches_regex_component()))
    
    return self._pattern
  
  def _get_matches_regex_component(self):
    return (
      br"("
      + br"|".join(
          re.escape(match_string) for match_string in self._matches_and_replacements)
      + br")")
  
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
  pdb_element = pypredefgen.Element(
    gimp.pdb, b"pdb", gimp.pdb, pypredefgen.get_ast_node_for_module(gimp.pdb))
  
  for child_member_name in dir(gimp.pdb):
    child_element = pypredefgen.Element(
      getattr(pdb_element.object, child_member_name, None),
      child_member_name, pdb_element.module)
    
    if _is_element_pdb_function(child_element):
      if _is_element_generated_temporary_pdb_function(child_element):
        continue
      else:
        _insert_ast_node_for_pdb_function(child_element, pdb_element)
    else:
      pypredefgen.insert_ast_node(child_member_name, pdb_element, module=gimp)
  
  pypredefgen.insert_ast_docstring(pdb_element)
  
  pypredefgen.write_pypredef_file(pdb_element, filename="gimp.pdb")


def _is_element_pdb_function(element):
  return element.object.__class__.__name__ == b"PDBFunction"


def _is_element_generated_temporary_pdb_function(element):
  return element.name_from_dir.startswith(b"temp_procedure_")


def _insert_ast_node_for_pdb_function(pdb_function_element, pdb_element):
  pdb_function_node = _get_ast_node_for_pdb_function(pdb_function_element.object)
  pdb_element.node.body.append(pdb_function_node)
  pypredefgen.insert_ast_docstring(pdb_function_element)


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
          _PdbParamNamePythonizer(
            get_pdb_params(pdb_function.params)).pythonize_docstring]),
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
    return_value_types_node = ast.Name(id=b"None")
  
  return ast.Return(value=return_value_types_node)


def _get_ast_docstring_for_pdb_function(
      pdb_function, additional_docstring_processing_callbacks=None):
  
  docstring = b""
  
  if pdb_function.proc_blurb:
    docstring += pdb_function.proc_blurb
  
  if pdb_function.proc_help and pdb_function.proc_help != pdb_function.proc_blurb:
    docstring += b"\n\n"
    docstring += pdb_function.proc_help
  
  docstring += _get_pdb_docstring_for_params(
    get_pdb_params_with_fixed_run_mode(pdb_function.params)[0], b"Parameters:",
    additional_param_processing_callbacks=[
      _PdbParamIntToBoolConverter.convert,
      _GimpenumsNamePythonizer.pythonize,
      _PdbParamNamePythonizer(get_pdb_params(pdb_function.params)).pythonize_param])
  
  docstring += _get_pdb_docstring_for_params(
    get_pdb_params(pdb_function.return_vals), b"Returns:",
    additional_param_processing_callbacks=[_GimpenumsNamePythonizer.pythonize])
  
  if additional_docstring_processing_callbacks:
    for process_docstring in additional_docstring_processing_callbacks:
      docstring = process_docstring(docstring)
  
  docstring = b"\n" + docstring.strip() + b"\n"
  
  return ast.Expr(value=ast.Str(s=docstring))


def _get_pdb_docstring_for_params(
      pdb_params, docstring_heading, additional_param_processing_callbacks=None):
  
  params_docstring = b""
  if additional_param_processing_callbacks is None:
    additional_param_processing_callbacks = []
  
  if pdb_params:
    params_docstring += b"\n\n"
    params_docstring += b"{0}\n".format(docstring_heading)
    
    for pdb_param in pdb_params:
      for process_pdb_param in additional_param_processing_callbacks:
        process_pdb_param(pdb_param)
      params_docstring += _get_pdb_param_docstring(pdb_param) + b"\n"
    
    params_docstring = params_docstring.rstrip(b"\n")
  
  return params_docstring


def _get_pdb_param_docstring(pdb_param):
  return b"{0} ({1}): {2}".format(
    pdb_param.name,
    pdb_param.pdb_type.get_name(include_base_type=True),
    pdb_param.description)


#===============================================================================


def _pythonize_true_false_names(docstring):
  return docstring.replace(b"FALSE", b"False").replace(b"TRUE", b"True")


class _PdbParamIntToBoolConverter(object):
  
  _BOOL_PARAM_DESCRIPTION_TRUE_FALSE_REGEX_FORMAT = (
    br"[\.:]? *\(?{0}(  *or  *| *[/,] *){1}\)?"
    br"|[\.:]? *\{{ *{0}( *\({2}\))?, *{1}( *\({3}\))? *\}}")
  
  _PDB_BOOL_PARAM_DESCRIPTION_MATCH_REGEX_COMPONENTS = (
    _BOOL_PARAM_DESCRIPTION_TRUE_FALSE_REGEX_FORMAT.format(
      br"true", br"false", br"1", br"0")
    + br"|"
    + _BOOL_PARAM_DESCRIPTION_TRUE_FALSE_REGEX_FORMAT.format(
        br"false", br"true", br"0", br"1"))
  
  _PDB_BOOL_PARAM_DESCRIPTION_MATCH_REGEX = (
    br"("
    + _PDB_BOOL_PARAM_DESCRIPTION_MATCH_REGEX_COMPONENTS
    + br"|true: .*false: "
    + br"|false: .*true: "
    + br"|\?$"
    + br")")
  
  _PDB_BOOL_PARAM_DESCRIPTION_SUBSTITUTE_REGEX = (
    br"(" + _PDB_BOOL_PARAM_DESCRIPTION_MATCH_REGEX_COMPONENTS + br")$")
  
  @classmethod
  def convert(cls, pdb_param):
    if cls._is_pdb_param_bool(pdb_param):
      pdb_param.pdb_type = PdbType(pdb_param.pdb_type.type_, bool)
      pdb_param.description = re.sub(
        cls._PDB_BOOL_PARAM_DESCRIPTION_SUBSTITUTE_REGEX, b"",
        pdb_param.description, flags=re.IGNORECASE)
  
  @classmethod
  def _is_pdb_param_bool(cls, pdb_param):
    return (
      pdb_param.pdb_type.type_ is int
      and re.search(
        cls._PDB_BOOL_PARAM_DESCRIPTION_MATCH_REGEX,
        pdb_param.description, flags=re.IGNORECASE))


class _PdbFunctionNamePythonizer(object):
  
  _pdb_function_names_map = {}
  _pdb_function_names_pattern = MultiStringRegexPattern(
    _pdb_function_names_map, lambda matches_regex: br"'\b" + matches_regex + br"\b'")
  
  @classmethod
  def pythonize(cls, docstring):
    def _pythonize_function_name(match):
      return b"`{0}`".format(cls._pdb_function_names_map[match.group(1)])
    
    cls._fill_pdb_function_names_map()
    
    return cls._pdb_function_names_pattern.sub(_pythonize_function_name, docstring)
  
  @classmethod
  def _fill_pdb_function_names_map(cls):
    if not cls._pdb_function_names_map:
      for pdb_member_name in dir(gimp.pdb):
        element = pypredefgen.Element(
          getattr(gimp.pdb, pdb_member_name, None), pdb_member_name, gimp.pdb)
        if (_is_element_pdb_function(element)
            and not _is_element_generated_temporary_pdb_function(element)):
          unpythonized_member_name = unpythonize_string(pdb_member_name)
          cls._pdb_function_names_map[unpythonized_member_name] = (
            b"pdb." + pdb_member_name)
    
    return cls._pdb_function_names_map


class _PdbParamNamePythonizer(object):
  
  def __init__(self, pdb_params):
    self._pdb_params = pdb_params
    
    self._pdb_param_names = {
      pdb_param.orig_name: pdb_param.name for pdb_param in pdb_params}
  
    self._pdb_param_names_pattern = MultiStringRegexPattern(
      self._pdb_param_names, lambda matches_regex: br"'\b" + matches_regex + br"\b'")
  
  def pythonize_param(self, pdb_param):
    param_description_parts = split_param_description(
      pdb_param.description, br"^(.*)\((.*?)\)$")
    if not param_description_parts:
      return
    
    pdb_param.description = b"".join([
      param_description_parts[0],
      self._pythonize_param_name_in_description(param_description_parts[1])])
  
  def _pythonize_param_name_in_description(self, param_description_part):
    components = re.split(br"( +[<>]=? +)", param_description_part)
    processed_components = []
    
    for component in components:
      if component in self._pdb_param_names:
        processed_components.append(self._pdb_param_names[component])
      else:
        processed_components.append(component)
    
    return b"({0})".format(b"".join(processed_components))
  
  def pythonize_docstring(self, docstring):
    def _pythonize_param_name(match):
      return b"`{0}`".format(self._pdb_param_names[match.group(1)])
    
    return self._pdb_param_names_pattern.sub(_pythonize_param_name, docstring)


class _GimpenumsNamePythonizer(object):
  
  _gimpenums_names_map = {}
  
  @classmethod
  def pythonize(cls, pdb_param):
    pdb_param_description_parts = split_param_description(
      pdb_param.description, br"(.*{ *)(.*?)( *})$")
    if not pdb_param_description_parts:
      return
    
    pdb_param.description = b"".join([
      pdb_param_description_parts[0],
      cls._pythonize_enum_names(pdb_param_description_parts[1]),
      pdb_param_description_parts[2]])
  
  @classmethod
  def _get_gimpenums_names_map(cls):
    if not cls._gimpenums_names_map:
      python_gimpenums_names = [
        member for member in dir(gimpenums)
        if re.match(br"[A-Z][A-Z0-9_]*$", member) and member not in [b"TRUE", b"FALSE"]]
      
      for python_enum_name in python_gimpenums_names:
        pdb_enum_name = unpythonize_string(python_enum_name)
        cls._gimpenums_names_map[pdb_enum_name] = (
          gimpenums.__name__ + b"." + python_enum_name)
    
    return cls._gimpenums_names_map
  
  @classmethod
  def _pythonize_enum_names(cls, enums):
    enum_strings = re.split(br", *", enums)
    processed_enum_strings = []
    
    for enum_string in enum_strings:
      enum_string_components = re.split(
        br"^([A-Z][A-Z0-9-]+) *(\([0-9]+\))$", enum_string)
      enum_string_components = [
        component for component in enum_string_components if component]
      
      if len(enum_string_components) == 2:
        enum_name, enum_number_string = enum_string_components
        if enum_name in cls._get_gimpenums_names_map():
          enum_name = cls._get_gimpenums_names_map()[enum_name]
        
        processed_enum_strings.append(b"{0} {1}".format(enum_name, enum_number_string))
      else:
        processed_enum_strings.append(enum_string)
    
    return b", ".join(processed_enum_strings)
