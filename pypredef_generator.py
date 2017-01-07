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
  module_node = get_ast_node_for_module(module)
  
  insert_ast_nodes(module, module_node)
  
  insert_ast_docstring(module, module_node)
  
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
    child_member_node = get_ast_node_for_import(child_member, member)
    member_node.body.insert(0, child_member_node)
  elif inspect.isclass(child_member) and _can_inspect_class_member(child_member_name):
    child_member_node = get_ast_node_for_class(child_member)
    member_node.body.append(child_member_node)
    insert_ast_docstring(child_member, child_member_node)
    
    external_module_names = _get_external_module_names_for_base_classes(child_member)
    for module_name in reversed(external_module_names):
      member_node.body.insert(0, get_ast_node_for_import_by_module_name(module_name))
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


def get_ast_node_for_module(module):
  return ast.Module(body=[])


def get_ast_node_for_import(module, module_root):
  return ast.Import(
    names=[ast.alias(name=get_relative_module_name(module, module_root), asname=None)])


def get_ast_node_for_import_by_module_name(module_name):
  return ast.Import(names=[ast.alias(name=module_name, asname=None)])


def get_relative_module_name(module, module_root):
  module_path_components = module.__name__.split(".")
  module_root_path_components = module_root.__name__.split(".")
  
  for root_path_component in module_root_path_components:
    if (len(module_path_components) > 1
        and root_path_component == module_path_components[0]):
      del module_path_components[0]
    else:
      break
  
  return ".".join(module_path_components)


def get_ast_node_for_class(class_):
  class_node = ast.ClassDef(
    name=class_.__name__,
    bases=[
      ast.Name(
        id=get_full_type_name(base_class)) for base_class in class_.__bases__],
    body=[],
    decorator_list=[])
  
  insert_ast_nodes(class_, class_node)
  
  return class_node


def get_full_type_name(type_):
  type_module = inspect.getmodule(type_)
  
  if (type_module and hasattr(type_module, "__name__")
      and type_module.__name__ != "__builtin__"):
    return ".".join([type_module.__name__, type_.__name__])
  else:
    return type_.__name__


def _get_external_module_names_for_base_classes(subclass):
  external_modules = []
  
  for base_class in subclass.__bases__:
    if (base_class.__module__ != subclass.__module__
        and base_class.__module__ != "__builtin__"):
      external_module_name = _get_module_name_without_internal_components(
        base_class.__module__)
      if external_module_name not in external_modules:
        external_modules.append(external_module_name)
  
  return external_modules


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
  
  return ast.Assign(
    targets=[ast.Name(id=member_name)], value=ast.Name(id=member_type_name))


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


#===============================================================================


def process_ast_nodes(member, member_node):
  remove_redundant_methods_from_subclasses(member, member_node)
  remove_duplicate_imports(member, member_node)


def remove_redundant_methods_from_subclasses(member, member_node):
  class_nodes = [node for node in member_node.body if isinstance(node, ast.ClassDef)]
  classes = _get_classes_from_member(class_nodes, member)
  
  class_nodes_map = {}
  class_node_names = {node.name: node for node in class_nodes}
  for class_ in classes:
    class_nodes_map[get_full_type_name(class_)] = class_node_names[class_.__name__]
  
  non_member_class_nodes_map = {}
  
  method_nodes_for_classes = {}
  visited_classes = set()
  
  for mro_for_class in (inspect.getmro(class_) for class_ in classes):
    for class_index, class_ in reversed(list(enumerate(mro_for_class))):
      if (get_full_type_name(class_) in class_nodes_map
          and class_ not in visited_classes
          and class_index + 1 < len(mro_for_class)):
        class_node = class_nodes_map[get_full_type_name(class_)]
        method_nodes_for_class = _get_method_nodes_for_class_node(
          class_node, method_nodes_for_classes)
        
        parent_class = mro_for_class[class_index + 1]
        parent_class_node = _get_ast_node_for_non_member_class(
          parent_class, non_member_class_nodes_map)
        method_nodes_for_parent_class = _get_method_nodes_for_class_node(
          parent_class_node, method_nodes_for_classes)
        
        for method_node in list(method_nodes_for_class):
          if _is_same_routine_node_in_nodes(method_node, method_nodes_for_parent_class):
            _remove_ast_node(method_node, class_node, member)
        
        visited_classes.add(class_)


def _get_classes_from_member(class_nodes, member):
  classes = []
  
  for class_node in class_nodes:
    class_ = getattr(member, class_node.name, None)
    if class_ is not None:
      classes.append(class_)
  
  return classes


def _get_ast_node_for_non_member_class(class_, non_member_class_nodes_map):
  class_node = non_member_class_nodes_map.get(get_full_type_name(class_))
  if class_node is None:
    class_node = get_ast_node_for_class(class_)
    non_member_class_nodes_map[get_full_type_name(class_)] = class_node
  
  return class_node


def _get_method_nodes_for_class_node(class_node, method_nodes_for_classes):
  method_nodes_for_class = method_nodes_for_classes.get(class_node.name)
  if method_nodes_for_class is None:
    method_nodes_for_class = _get_method_nodes(class_node)
    method_nodes_for_classes[class_node.name] = method_nodes_for_class
  
  return method_nodes_for_class


def _get_method_nodes(class_node):
  return [node for node in class_node.body if isinstance(node, ast.FunctionDef)]


def _is_same_routine_node_in_nodes(routine_node, routine_nodes):
  """
  Return True if there is a routine node in `routine_nodes` with the same name,
  signature and docstring as `routine_node`.
  """
  
  for node in routine_nodes:
    if routine_node.name == node.name:
      return _routine_nodes_equal(routine_node, node)
  
  return False


def _routine_nodes_equal(routine_node1, routine_node2):
  return (_routine_signatures_equal(routine_node1, routine_node2)
          and _routine_docstrings_equal(routine_node1, routine_node2))


def _routine_signatures_equal(routine_node1, routine_node2):
  return (
    all(
      routine_node1_arg_name.id == routine_node2_arg_name.id
      for routine_node1_arg_name, routine_node2_arg_name
      in zip(routine_node1.args.args, routine_node2.args.args))
    and routine_node1.args.vararg == routine_node2.args.vararg
    and routine_node1.args.kwarg == routine_node2.args.kwarg
    and all(
      routine_node1_default_name.id == routine_node2_default_name.id
      for routine_node1_default_name, routine_node2_default_name
      in zip(routine_node1.args.defaults, routine_node2.args.defaults)))


def _routine_docstrings_equal(routine_node1, routine_node2):
  return ast.get_docstring(routine_node1) == ast.get_docstring(routine_node2)


def _remove_ast_node(node, parent_node, member):
  del parent_node.body[parent_node.body.index(node)]


def remove_duplicate_imports(member, member_node):
  
  class ImportDeduplicator(ast.NodeTransformer):
    
    import_node_names = set()
    
    def visit_Import(self, import_node):
      for alias_index, alias in reversed(list(enumerate(import_node.names))):
        if alias.name not in self.import_node_names:
          self.import_node_names.add(alias.name)
        else:
          del import_node.names[alias_index]
      
      if import_node.names:
        return import_node
      else:
        return None
  
  ImportDeduplicator().visit(member_node)
