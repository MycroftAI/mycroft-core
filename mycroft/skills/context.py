from functools import wraps

"""
    Helper decorators for handling context from skills.
"""


def adds_context(context, words=''):
    """
        Adds context to context manager.
    """
    def context_add_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            ret = func(*args, **kwargs)
            args[0].set_context(context)
            return ret
        return func_wrapper
    return context_add_decorator


def removes_context(context):
    """
        Removes context from the context manager.
    """
    def context_removes_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            ret = func(*args, **kwargs)
            args[0].remove_context(context)
            return ret
        return func_wrapper
    return context_removes_decorator
