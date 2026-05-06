from functools import partial, update_wrapper

try:
    from strands import tool
except Exception:  # pragma: no cover - allows running without strands installed
    def tool(fn=None, **_kwargs):  # type: ignore[misc]
        if fn is None:
            return lambda f: f
        return fn


def make_tool(func, *bound_args, **bound_kwargs):
    """
    Create a tool from a function with pre-bound arguments.

    This utility wraps a function with pre-filled arguments and keyword arguments,
    then registers it as a tool. It preserves the original function's metadata
    (name, docstring, annotations, etc.) so the tool appears as the original
    function to external observers.

    Args:
        func: The function to wrap and register as a tool.
        *bound_args: Positional arguments to pre-bind to the function.
        **bound_kwargs: Keyword arguments to pre-bind to the function.

    Returns:
        A tool instance created from the wrapped function with pre-bound arguments.

    Example:
        def fetch_user_profile(actor_id, user_id):
            return get_profile(actor_id, user_id)

        # Create a tool with actor_id pre-bound to 'admin'
        admin_profile_tool = make_tool(fetch_user_profile, 'admin')

        # The tool can now be called with just the remaining parameters
        # admin_profile_tool(user_id='user_123')
    """
    partial_func = partial(func, *bound_args, **bound_kwargs)

    def wrapper(*args, **kwargs):
        return partial_func(*args, **kwargs)

    update_wrapper(wrapper, func)  # preserve name, docstring, etc.
    return tool(wrapper)
