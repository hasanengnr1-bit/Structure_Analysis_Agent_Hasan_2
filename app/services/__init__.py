try:
    from .graph_gen import get_graph
except ModuleNotFoundError:
    get_graph = None
