"""
This module is responsible for generating predefined completions for the GIMP
procedural database (PDB).
"""

import inspect

import ast

import gimp
import gimpcolor
import gimpenums

import pypredef_generator

#===============================================================================

_PDB_TYPES_MAP = {
  gimpenums.PDB_INT32: int,
  gimpenums.PDB_INT16: int,
  gimpenums.PDB_INT8: int,
  gimpenums.PDB_FLOAT: float,
  gimpenums.PDB_STRING: bytes,
  gimpenums.PDB_COLOR: gimpcolor.RGB,
  
  gimpenums.PDB_INT32ARRAY: tuple,
  gimpenums.PDB_INT16ARRAY: tuple,
  gimpenums.PDB_INT8ARRAY: tuple,
  gimpenums.PDB_FLOATARRAY: tuple,
  gimpenums.PDB_STRINGARRAY: tuple,
  gimpenums.PDB_COLORARRAY: tuple,
  
  gimpenums.PDB_IMAGE: gimp.Image,
  gimpenums.PDB_ITEM: gimp.Item,
  gimpenums.PDB_DRAWABLE: gimp.Drawable,
  gimpenums.PDB_LAYER: gimp.Layer,
  gimpenums.PDB_CHANNEL: gimp.Channel,
  gimpenums.PDB_SELECTION: gimp.Channel,
  gimpenums.PDB_VECTORS: gimp.Vectors,
  
  gimpenums.PDB_PARASITE: gimp.Parasite,
  gimpenums.PDB_DISPLAY: gimp.Display,
}

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
    args.append(ast.Name(id="run_mode"))
    #FIXME: Avoid inserting constant string
    defaults.append(ast.Name(id="gimpenums.RUN_NONINTERACTIVE"))
  
  return ast.arguments(args=args, vararg=None, kwarg=None, defaults=defaults)


def _get_ast_docstring_for_pdb_function(pdb_function):
  docstring = "\n" + pdb_function.proc_blurb
  
  if pdb_function.proc_help and pdb_function.proc_help != pdb_function.proc_blurb:
    docstring += "\n\n" + pdb_function.proc_help
  
  docstring += _get_pdb_docstring_type_info(pdb_function)
  
  docstring += "\n"
  
  return ast.Expr(value=ast.Str(s=docstring))


def _get_pdb_docstring_type_info(pdb_function):
  docstring_type_info = ""
  pdb_params = _get_pdb_params(pdb_function)[0]
  
  if pdb_params:
    docstring_type_info += "\n"
    
    for pdb_param_info in pdb_params:
      docstring_type_info += "\n@type {0}: {1}".format(
        _get_pdb_param_name(pdb_param_info), _get_pdb_type_name_by_id(pdb_param_info[0]))
  
  return docstring_type_info


def _get_ast_return_value_types_for_pdb_function(pdb_function):
  if len(pdb_function.return_vals) > 1:
    node_return_value_types = ast.Tuple(
      elts=[ast.Name(id=_get_pdb_type_name_by_id(return_vals_info[0]))
            for return_vals_info in pdb_function.return_vals])
  elif len(pdb_function.return_vals) == 1:
    node_return_value_types = ast.Name(id=_get_pdb_type_name_by_id(pdb_function.return_vals[0][0]))
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


def _get_pdb_type_name_by_id(pdb_type_id):
  pdb_type = _PDB_TYPES_MAP[pdb_type_id]
  
  pdb_type_module = inspect.getmodule(pdb_type)
  
  if (pdb_type_module and hasattr(pdb_type_module, "__name__")
      and pdb_type_module.__name__ != "__builtin__"):
    return ".".join([pdb_type_module.__name__, pdb_type.__name__])
  else:
    return pdb_type.__name__


def _get_pdb_param_name(pdb_param_info):
  return pdb_param_info[1].replace("-", "_")
