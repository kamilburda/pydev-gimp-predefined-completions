# -*- coding: utf-8 -*-

"""
This module defines functions to generate predefined completions for PyDev by
introspection of module objects.
"""

from __future__ import absolute_import, print_function, division, unicode_literals

import inspect
import io
import os

import ast

import astor

#===============================================================================

PLUGIN_DIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
MODULES_FILE_PATH = os.path.join(PLUGIN_DIR, "modules.txt")
PYPREDEF_FILES_DIRNAME = "pypredefs"
PYPREDEF_FILES_DIR = os.path.join(PLUGIN_DIR, PYPREDEF_FILES_DIRNAME)

TEXT_FILE_ENCODING = "utf-8"

#===============================================================================


def generate_predefined_completions(module):
  module_node = get_ast_node_for_root_module(module)
  insert_ast_docstring(module, module_node)
  
  insert_ast_nodes(module, module_node)
  
  process_ast_nodes(module, module_node)
  
  write_pypredef_file(module.__name__, module_node)


def write_pypredef_file(module_name, module_node):
  pypredef_file_path = _get_pypredef_file_path(module_name)
  with io.open(pypredef_file_path, "w", encoding=TEXT_FILE_ENCODING) as pypredef_file:
    pypredef_file.write(astor.to_source(module_node).decode(TEXT_FILE_ENCODING))


def _get_pypredef_file_path(module_name):
  return os.path.join(PYPREDEF_FILES_DIR, module_name + ".pypredef")


#===============================================================================


def insert_ast_nodes(member, member_node):
  for child_member_name in dir(member):
    insert_ast_node(child_member_name, member, member_node)


def insert_ast_node(child_member_name, member, member_node):
  child_member = getattr(member, child_member_name, None)
  
  if inspect.ismodule(child_member):
    child_member_node = get_ast_node_for_module(child_member, member)
    member_node.body.insert(0, child_member_node)
  elif inspect.isclass(child_member) and _can_inspect_class_member(child_member_name):
    child_member_node = get_ast_node_for_class(
      child_member, module=member if isinstance(member_node, ast.Module) else None)
    member_node.body.append(child_member_node)
    insert_ast_docstring(child_member, child_member_node)
  elif inspect.isroutine(child_member):
    if not inspect.isclass(member):
      child_member_node = get_ast_node_for_function(child_member)
    else:
      child_member_node = get_ast_node_for_method(child_member)
    
    member_node.body.append(child_member_node)
    insert_ast_docstring(child_member, child_member_node)
  else:
    child_member_node = get_ast_node_for_member(child_member, child_member_name)
    member_node.body.append(child_member_node)


def _can_inspect_class_member(class_member_name):
  return class_member_name != "__class__"


def get_ast_node_for_root_module(root_module):
  return ast.Module(body=[])


def get_ast_node_for_module(module, module_root):
  return ast.Import(
    names=[ast.alias(name=get_relative_module_name(module, module_root), asname=None)])


def get_relative_module_name(module, module_root):
  module_path_components = module.__name__.split(".")
  module_root_path_components = module_root.__name__.split(".")
  
  for root_path_component in module_root_path_components:
    if len(module_path_components) > 1 and root_path_component == module_path_components[0]:
      del module_path_components[0]
    else:
      break
  
  return ".".join(module_path_components)


def get_ast_node_for_class(class_, module=None):
  class_node = ast.ClassDef(
    name=class_.__name__,
    bases=[
      ast.Name(id=get_full_class_name(base_class, module)) for base_class in class_.__bases__],
    body=[],
    decorator_list=[])
  
  insert_ast_nodes(class_, class_node)
  
  return class_node


def get_full_class_name(class_, module=None):
  if (hasattr(class_, "__module__") and module is not None
      and module.__name__ != class_.__module__
      and class_.__module__ != "__builtin__"):
    return (
      _get_module_name_without_internal_components(class_.__module__)
      + "." + class_.__name__)
  else:
    return class_.__name__


def _get_module_name_without_internal_components(module_name):
  return ".".join(
    module_name_component for module_name_component in module_name.split(".")
    if not module_name_component.startswith("_"))


def get_ast_node_for_function(routine):
  return ast.FunctionDef(
    name=routine.__name__,
    args=get_ast_arguments_for_routine(routine),
    body=[ast.Pass()],
    decorator_list=[])


def get_ast_node_for_method(method):
  arguments = get_ast_arguments_for_routine(method)
  if not arguments.args:
    arguments.args.insert(0, ast.Name(id="self"))
  
  return ast.FunctionDef(
    name=method.__name__,
    args=arguments,
    body=[ast.Pass()],
    decorator_list=[])


def get_ast_node_for_member(member, member_name=None):
  """
  Return AST node describing `<member name> = <member type>` assignment.
  
  If `member` has no `__class__` attribute, assign None.
  
  If `member_name` is not None, it is used as a member name instead of the name
  inferred from `member.` This is useful is `member` has no `__name__`
  attribute.
  """
  
  member_name = member_name if member_name is not None else member.__name__
  
  if member is not None and hasattr(member, "__class__"):
    member_type_name = member.__class__.__name__
  else:
    member_type_name = "None"
  
  return ast.Assign(targets=[ast.Name(id=member_name)], value=ast.Name(id=member_type_name))


def get_ast_arguments_for_routine(routine):
  arguments = ast.arguments(args=[], vararg=None, kwarg=None, defaults=[])
  try:
    argspec = inspect.getargspec(routine)
  except TypeError:
    # Can't get argspec because it's a built-in routine.
    pass
  else:
    if argspec.args:
      arguments.args = [ast.Name(id=arg_name) for arg_name in argspec.args]
    arguments.vararg = argspec.varargs
    arguments.kwarg = argspec.keywords
    if argspec.defaults:
      arguments.defaults = [ast.Name(id=arg_name) for arg_name in argspec.defaults]
  
  return arguments


def insert_ast_docstring(member, member_node):
  member_dostring = inspect.getdoc(member)
  if member_dostring:
    member_node.body.insert(0, ast.Expr(value=ast.Str(s=member_dostring)))
