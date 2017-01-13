# -*- coding: utf-8 -*-

"""
This module defines functions to generate predefined completions for PyDev by
introspection of module objects.
"""

from __future__ import absolute_import, print_function, division, unicode_literals

import collections
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


class Element(object):
  
  node_element_map = collections.OrderedDict()
  node_element_map_per_module = collections.OrderedDict()
  
  def __init__(self, object_, name_from_dir, module, ast_node=None):
    self._object = object_
    self._name_from_dir = name_from_dir
    self._module = module
    
    if ast_node is not None:
      self.set_node(ast_node)
    else:
      self._node = None
  
  @property
  def object(self):
    return self._object
  
  @property
  def name_from_dir(self):
    return self._name_from_dir
  
  @property
  def module(self):
    return self._module
  
  @property
  def node(self):
    return self._node
  
  def set_node(self, node):
    self._node = node
    
    self.node_element_map[node] = self
    
    if self._module not in self.node_element_map_per_module:
      self.node_element_map_per_module[self._module] = collections.OrderedDict()
    
    self.node_element_map_per_module[self._module][node] = self


#===============================================================================


def generate_predefined_completions(module):
  module_node = get_ast_node_for_module(module)
  module_element = Element(module, None, module, module_node)
  
  insert_ast_nodes(module_element)
  
  insert_ast_docstring(module_element)
  
  process_ast_nodes(module_element)
  
  write_pypredef_file(module_element)


def write_pypredef_file(module_element, filename=None):
  if filename is None:
    filename = module_element.object.__name__
  
  pypredef_file_path = _get_pypredef_file_path(filename)
  with io.open(pypredef_file_path, "w", encoding=TEXT_FILE_ENCODING) as pypredef_file:
    pypredef_file.write(astor.to_source(module_element.node).decode(TEXT_FILE_ENCODING))


def _get_pypredef_file_path(module_name):
  return os.path.join(PYPREDEF_FILES_DIR, module_name + ".pypredef")


#===============================================================================


def insert_ast_nodes(element):
  for child_member_name in dir(element.object):
    insert_ast_node(child_member_name, element)


def insert_ast_node(child_member_name, element, module=None):
  if module is None:
    module = element.module
  
  child_element = Element(
    getattr(element.object, child_member_name, None), child_member_name, module)
  
  if inspect.ismodule(child_element.object):
    child_element.set_node(get_ast_node_for_import(child_element))
    element.node.body.insert(0, child_element.node)
  elif (inspect.isclass(child_element.object)
        and _can_inspect_class_element(child_element)):
    child_element.set_node(
      get_ast_node_for_class(child_element, module_root=element.module))
    
    element.node.body.append(child_element.node)
    insert_ast_docstring(child_element)
    
    external_module_names = _get_external_module_names_for_base_classes(
      child_element.object)
    for module_name in reversed(external_module_names):
      element.node.body.insert(0, get_ast_node_for_import_by_module_name(module_name))
  elif inspect.isroutine(child_element.object):
    if not inspect.isclass(element.object):
      child_element.set_node(get_ast_node_for_function(child_element))
    else:
      child_element.set_node(get_ast_node_for_method(child_element))
    
    element.node.body.append(child_element.node)
    insert_ast_docstring(child_element)
  else:
    child_element.set_node(get_ast_node_for_assignment_of_type_to_name(child_element))
    element.node.body.append(child_element.node)


def _can_inspect_class_element(class_element):
  return class_element.name_from_dir != "__class__"


def get_ast_node_for_module(module):
  return ast.Module(body=[])


def get_ast_node_for_import(module_element):
  return ast.Import(
    names=[ast.alias(
      name=get_relative_module_name(
        module_element.object, module_root=module_element.module),
      asname=None)])


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


def get_ast_node_for_class(class_element, module_root=None):
  class_node = ast.ClassDef(
    name=class_element.name_from_dir,
    bases=[
      ast.Name(id=get_full_type_name(base_class, module_root))
      for base_class in class_element.object.__bases__],
    body=[],
    decorator_list=[])
  
  class_element.set_node(class_node)
  
  if class_element.name_from_dir != class_element.object.__name__:
    class_element.node.body.insert(
      0, ast.Assign(
        targets=[ast.Name(id="__name__")],
        value=ast.Str(s=bytes(get_full_type_name(class_element.object, module_root)))))
  
  insert_ast_nodes(class_element)
  
  return class_node


def get_full_type_name(type_, module_root=None):
  type_module = inspect.getmodule(type_)
  
  if (type_module and hasattr(type_module, "__name__")
      and type_module.__name__ != "__builtin__"):
    if (module_root is not None
        and _module_names_equal(type_module.__name__, module_root.__name__)):
      return type_.__name__
    else:
      return (
        _get_module_name_without_internal_component(type_module.__name__)
        + "." + type_.__name__)
  else:
    return type_.__name__


def get_full_type_name_from_object(object_, module_root=None):
  if hasattr(object_, "__class__"):
    type_ = object_.__class__
  else:
    type_ = type(object_)
  
  return get_full_type_name(type_, module_root=module_root)


def _get_external_module_names_for_base_classes(subclass):
  external_modules = []
  
  for base_class in subclass.__bases__:
    if (base_class.__module__ != "__builtin__"
        and not _module_names_equal(base_class.__module__, subclass.__module__)):
      external_module_name = _get_module_name_without_internal_component(
        base_class.__module__)
      if external_module_name not in external_modules:
        external_modules.append(external_module_name)
  
  return external_modules


def _module_names_equal(module_name1, module_name2):
  return (
    module_name1 == module_name2
    or (module_name1.startswith("_") and module_name1[1:] == module_name2)
    or (_get_module_name_without_internal_component(module_name1) == module_name2)
    or (module_name2.startswith("_") and module_name1 == module_name2[1:])
    or (module_name1 == _get_module_name_without_internal_component(module_name2)))


def _get_module_name_without_internal_component(module_name):
  module_name_components = module_name.split(".")
  
  if (len(module_name_components) >= 2
      and module_name_components[0] == module_name_components[1].lstrip("_")):
    return ".".join([module_name_components[0]] + module_name_components[2:])
  else:
    return module_name


def get_ast_node_for_function(function_element):
  return ast.FunctionDef(
    name=function_element.name_from_dir,
    args=get_ast_arguments_for_routine(function_element.object),
    body=[ast.Pass()],
    decorator_list=[])


def get_ast_node_for_method(method_element):
  arguments = get_ast_arguments_for_routine(method_element.object)
  if not arguments.args:
    arguments.args.insert(0, ast.Name(id="self"))
  
  return ast.FunctionDef(
    name=method_element.name_from_dir,
    args=arguments,
    body=[ast.Pass()],
    decorator_list=[])


def get_ast_node_for_assignment_of_type_to_name(element):
  if element.object is not None:
    member_type_name = get_full_type_name_from_object(element.object, element.module)
  else:
    member_type_name = "None"
  
  return ast.Assign(
    targets=[ast.Name(id=element.name_from_dir)], value=ast.Name(id=member_type_name))


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


def insert_ast_docstring(element):
  member_dostring = inspect.getdoc(element.object)
  if member_dostring:
    element.node.body.insert(0, ast.Expr(value=ast.Str(s=member_dostring)))


#===============================================================================

module_specific_processing_functions = collections.OrderedDict()


def process_ast_nodes(module_element):
  remove_redundant_members_from_subclasses(module_element)
  sort_classes_by_hierarchy(module_element)
  
  remove_duplicate_imports(module_element)
  
  move_top_level_variables_to_end(module_element)
  move_class_level_variables_before_methods(module_element)
  
  if module_element.module.__name__ in module_specific_processing_functions:
    processing_functions = (
      module_specific_processing_functions[module_element.module.__name__])
    for processing_function in processing_functions:
      processing_function(module_element)
  
  fix_empty_class_bodies(module_element)


#===============================================================================


def remove_redundant_members_from_subclasses(module_element):
  class_nodes = [
    node for node in module_element.node.body if isinstance(node, ast.ClassDef)]
  class_element_map = _get_class_element_map(class_nodes, module_element)
  
  external_class_nodes_map = {}
  
  member_nodes_for_classes = {}
  visited_classes = set()
  
  for mro_for_class in (
        inspect.getmro(class_in_module) for class_in_module in class_element_map):
    for class_ in reversed(mro_for_class):
      if class_ in class_element_map and class_ not in visited_classes:
        class_node = class_element_map[class_].node
        class_member_nodes = _get_class_member_nodes(
          class_, class_node, member_nodes_for_classes)
        
        for parent_class in class_.__bases__:
          if parent_class in class_element_map:
            parent_class_node = class_element_map[parent_class].node
          else:
            parent_class_node = _get_ast_node_for_external_class(
              parent_class, external_class_nodes_map)
          
          parent_class_member_nodes = _get_class_member_nodes(
            parent_class, parent_class_node, member_nodes_for_classes)
          
          for class_member_node in list(class_member_nodes):
            _remove_redundant_class_member_node(
              class_member_node, class_node, parent_class_member_nodes)
          
        visited_classes.add(class_)


def _get_class_element_map(class_nodes, element):
  node_element_map_for_module = Element.node_element_map_per_module[element.module]
  
  return collections.OrderedDict(
    (node_element_map_for_module[class_node].object,
     node_element_map_for_module[class_node])
    for class_node in class_nodes)


def _get_ast_node_for_external_class(class_, external_class_nodes_map):
  class_node = external_class_nodes_map.get(class_)
  if class_node is None:
    #FIXME: This is not OK, we shouldn't use `__name__` as it can differ from
    # the name from `dir(module)`. We should use the latter instead.
    # If the name from `dir()` is not available, we need to find such name by
    # comparing `id(class_)` with each `dir()` member
    # (or use a {module: member ID} map?).
    class_element = Element(class_, class_.__name__, inspect.getmodule(class_))
    class_node = get_ast_node_for_class(class_element)
    external_class_nodes_map[class_] = class_node
  
  return class_node


def _get_class_member_nodes(class_, class_node, member_nodes_for_classes):
  class_member_nodes = member_nodes_for_classes.get(class_)
  if class_member_nodes is None:
    class_member_nodes = list(class_node.body)
    member_nodes_for_classes[class_] = class_member_nodes
  
  return class_member_nodes


def _remove_redundant_class_member_node(
      class_member_node, class_node, parent_class_member_nodes):
  for node_type, equality_function in [
        (ast.FunctionDef, _routine_nodes_equal), (ast.Assign, _assign_nodes_equal)]:
    if isinstance(class_member_node, node_type):
      _remove_node(
        class_member_node, class_node, parent_class_member_nodes, node_type,
        equality_function)
      break


def _remove_node(
      class_member_node, class_node, parent_class_member_nodes, node_type,
      equality_function):
  member_nodes_of_type = (
    node for node in parent_class_member_nodes if isinstance(node, node_type))
  
  for node in member_nodes_of_type:
    if equality_function(class_member_node, node):
      _remove_ast_node(class_member_node, class_node)
      break


def _routine_nodes_equal(routine_node1, routine_node2):
  return (
    routine_node1.name == routine_node2.name
    and _routine_signatures_equal(routine_node1, routine_node2)
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


def _assign_nodes_equal(assign_node1, assign_node2):
  return (
    _assign_targets_equal(assign_node1, assign_node2)
    and _assign_values_equal(assign_node1, assign_node2))


def _assign_targets_equal(assign_node1, assign_node2):
  return (
    len(assign_node1.targets) == 1 and len(assign_node2.targets) == 1
    and assign_node1.targets[0].id == assign_node2.targets[0].id)


def _assign_values_equal(assign_node1, assign_node2):
  element1 = Element.node_element_map[assign_node1]
  element2 = Element.node_element_map[assign_node2]
  
  module_root = element1.module
  
  return (
    get_full_type_name_from_object(element1.object, module_root=module_root)
    == get_full_type_name_from_object(element2.object, module_root=module_root))


def _remove_ast_node(node, parent_node):
  try:
    node_index = parent_node.body.index(node)
  except ValueError:
    # The node may have already been removed. This can happen e.g. if multiple
    # base classes define a member with the same name.
    pass
  else:
    del parent_node.body[node_index]


#===============================================================================


def sort_classes_by_hierarchy(module_element):
  
  class_nodes = [
    node for node in module_element.node.body if isinstance(node, ast.ClassDef)]
  class_element_map = _get_class_element_map(class_nodes, module_element)
  
  class_nodes_and_indices = collections.OrderedDict([
    (node, node_index) for node_index, node in enumerate(module_element.node.body)
    if isinstance(node, ast.ClassDef)])
  class_nodes_new_order = collections.OrderedDict()
  
  for mro_for_class in reversed(list(
        inspect.getmro(class_in_module) for class_in_module in class_element_map)):
    for class_ in mro_for_class:
      if class_ in class_element_map:
        class_node = class_element_map[class_].node
        
        if class_node in class_nodes_new_order:
          _move_ordered_dict_element_to_end(class_nodes_new_order, class_node)
        else:
          class_nodes_new_order[class_node] = None
  
  _reverse_ordered_dict(class_nodes_new_order)
  
  for class_element in class_element_map.values():
    _remove_ast_node(class_element.node, module_element.node)
  
  for orig_class_node, new_class_node in zip(
        class_nodes_and_indices, class_nodes_new_order):
    class_node_new_position = class_nodes_and_indices[orig_class_node]
    module_element.node.body.insert(class_node_new_position, new_class_node)


def _move_ordered_dict_element_to_end(ordered_dict, element_key):
  value = ordered_dict[element_key]
  del ordered_dict[element_key]
  ordered_dict[element_key] = value


def _reverse_ordered_dict(ordered_dict):
  for key, value in reversed(list(ordered_dict.items())):
    del ordered_dict[key]
    ordered_dict[key] = value


#===============================================================================


def remove_duplicate_imports(module_element):
  
  class _ImportDeduplicator(ast.NodeTransformer):
    
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
  
  _ImportDeduplicator().visit(module_element.node)


#===============================================================================


def move_top_level_variables_to_end(module_element):
  variable_nodes_and_indices = [
    (node, node_index) for node_index, node in enumerate(module_element.node.body)
    if isinstance(node, ast.Assign)]
  
  for node, node_index in reversed(variable_nodes_and_indices):
    del module_element.node.body[node_index]
  
  for node, unused_ in variable_nodes_and_indices:
    module_element.node.body.append(node)


#===============================================================================


def move_class_level_variables_before_methods(module_element):
  for class_node in (
        node for node in module_element.node.body if isinstance(node, ast.ClassDef)):
    class_variable_nodes_and_indices = [
      (node, node_index) for node_index, node in enumerate(class_node.body)
      if isinstance(node, ast.Assign)]
    
    for node, node_index in reversed(class_variable_nodes_and_indices):
      del class_node.body[node_index]
    
    first_method_node_index = next(
      (node_index for node_index, node in enumerate(class_node.body)
       if isinstance(node, ast.FunctionDef)),
      max(len(class_node.body), 0))
    
    for node, unused_ in reversed(class_variable_nodes_and_indices):
      class_node.body.insert(first_method_node_index, node)


#===============================================================================


def fix_empty_class_bodies(module_element):
  for class_node in (
        node for node in ast.walk(module_element.node) if isinstance(node, ast.ClassDef)):
    if not class_node.body:
      class_node.body.append(ast.Pass())


#===============================================================================


def remove_class_docstrings(module_element):
  for class_node in (
        node for node in module_element.node.body if isinstance(node, ast.ClassDef)):
    if ast.get_docstring(class_node):
      del class_node.body[0]
