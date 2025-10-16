from functools import wraps
import inspect

def wrap_node(node_fn, name):
    if inspect.iscoroutinefunction(node_fn):
        @wraps(node_fn)
        async def async_wrapper(state):
            print(f"⚙️ Executing node: {name}")
            new_state = await node_fn(state)
            print(f"➡️ Next route: {new_state.get('route', 'END')}\n")
            return new_state
        return async_wrapper
    else:
        @wraps(node_fn)
        def sync_wrapper(state):
            print(f"⚙️ Executing node: {name}")
            new_state = node_fn(state)
            print(f"➡️ Next route: {new_state.get('route', 'END')}\n")
            return new_state
        return sync_wrapper
