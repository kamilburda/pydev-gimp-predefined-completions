"""
This module defines functions to generate predefined completions for PyDev by
introspection of module objects.
"""

import inspect
import os

import ast

import astor

#===============================================================================

PLUGIN_DIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
MODULES_FILE_PATH = os.path.join(PLUGIN_DIR, "modules.txt")
PYPREDEF_FILES_DIRNAME = "pypredefs"
PYPREDEF_FILES_DIR = os.path.join(PLUGIN_DIR, PYPREDEF_FILES_DIRNAME)

#===============================================================================


def generate_predefined_completions(module):
  node_module = get_ast_node_for_root_module(module)
  insert_ast_docstring(node_module, module)
  
  insert_ast_nodes(module, node_module)
  
  write_pypredef_file(module.__name__, node_module)


def write_pypredef_file(module_name, node_module):
  with open(_get_pypredef_file_path(module_name), "w") as pypredef_file:
    pypredef_file.write(astor.to_source(node_module))


def _get_pypredef_file_path(module_name):
  return os.path.join(PYPREDEF_FILES_DIR, module_name + ".pypredef")


#===============================================================================


def insert_ast_nodes(member, node_member):
  for child_member_name in dir(member):
    insert_ast_node(child_member_name, member, node_member)


def insert_ast_node(child_member_name, member, node_member):
  child_member = getattr(member, child_member_name, None)
  
  if inspect.ismodule(child_member):
    node_child_member = get_ast_node_for_module(child_member, member)
    node_member.body.insert(0, node_child_member)
  elif inspect.isclass(child_member) and _can_inspect_class_member(child_member_name):
    node_child_member = get_ast_node_for_class(child_member)
    node_member.body.append(node_child_member)
    insert_ast_docstring(node_child_member, child_member)
  elif inspect.isroutine(child_member):
    node_child_member = get_ast_node_for_routine(child_member)
    node_member.body.append(node_child_member)
    insert_ast_docstring(node_child_member, child_member)
  else:
    node_child_member = get_ast_node_for_member(child_member, child_member_name)
    node_member.body.append(node_child_member)


def _can_inspect_class_member(class_member_name):
  return class_member_name != "__class__"


def get_ast_node_for_root_module(root_module):
  return ast.Module(body=[])


def get_ast_node_for_module(module, module_root):
  return ast.Import(
    names=[ast.alias(name=_get_relative_module_name(module, module_root), asname=None)])


def _get_relative_module_name(module, module_root):
  module_path_components = module.__name__.split(".")
  module_root_path_components = module_root.__name__.split(".")
  
  for root_path_component in module_root_path_components:
    if len(module_path_components) > 1 and root_path_component == module_path_components[0]:
      del module_path_components[0]
    else:
      break
  
  return ".".join(module_path_components)


def get_ast_node_for_class(class_):
  node_class = ast.ClassDef(
    name=class_.__name__,
    bases=[
      ast.Name(id=base_class.__name__) for base_class in class_.__bases__],
    body=[],
    decorator_list=[])
  
  insert_ast_nodes(class_, node_class)
  
  return node_class


def get_ast_node_for_routine(routine):
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


def insert_ast_docstring(node_member, member):
  member_dostring = inspect.getdoc(member)
  if member_dostring:
    node_member.body.insert(0, ast.Expr(value=ast.Str(s=member_dostring)))
