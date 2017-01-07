from types import SimpleNamespace
import time


class AutomationCommands:

    def __init__(self, *args, **kwargs):
        self.last_result = None
        self.nesting_level = 0
        self.prev_nesting_level = 0
        self.set_context(kwargs.pop('context', {}))

    # Use self._ in your commands args / kwargs for parametric arguments.
    def set_context(self, context):
        self._ = SimpleNamespace(**context)
        return self

    def yield_commands(self, *args):
        operation = None
        last_opcode = None
        for key, opcode in enumerate(args):
            if isinstance(opcode, str):
                operation = opcode
                if key == len(args) - 1 or isinstance(args[key + 1], str):
                    yield operation, (), {}
            elif key == 0:
                raise ValueError('method name is not a string: {}'.format(repr(opcode)))
            elif isinstance(opcode, (tuple, list)):
                if key == len(args) - 1 or not isinstance(args[key + 1], dict):
                    yield operation, opcode, {}
            elif isinstance(opcode, dict):
                if isinstance(last_opcode, (tuple, list)):
                    yield operation, last_opcode, opcode
                else:
                    yield operation, (), opcode
            else:
                raise ValueError(
                    'Invalid opcode, should be str (method name), tuple (method args) or dict (method kwagrs)')
            last_opcode = opcode

    def get_method_name(self, operation):
        return '_{}'.format(operation)

    def get_command(self, operation):
        method_name = self.get_method_name(operation)
        if not hasattr(self, method_name):
            raise ValueError('Undefined attribute: {}'.format(method_name))
        method = getattr(self, method_name)
        if not callable(method):
            raise ValueError('Uncallable method: {}'.format(method_name))
        return method

    def exec_command(self, operation, *args, **kwargs):
        self.prev_nesting_level = self.nesting_level
        self.nesting_level += 1
        try:
            start_time = time.process_time()
            result = self.get_command(operation)(*args, **kwargs)
            exec_time = time.process_time() - start_time
        except Exception as e:
            e.exec_time = time.process_time() - start_time
            self.nesting_level -= 1
            raise e
        self.nesting_level -= 1
        return result, exec_time

    def exec(self, *args):
        batch_exec_time = 0
        for operation, args, kwargs in self.yield_commands(*args):
            self.last_result, exec_time = self.exec_command(operation, *args, **kwargs)
            batch_exec_time += exec_time
        return self.last_result

    def yield_class_commands(self, cmd_obj, *attrs):
        for attr_name in attrs:
            attr = getattr(cmd_obj, attr_name)
            if callable(attr):
                yield from attr()
            else:
                yield attr

    def exec_class(self, cmd_obj, *attrs):
        for commands in self.yield_class_commands(cmd_obj, *attrs):
            self.exec(*commands)
        return self
