from graph.customer_service.graph import graph as _cs_graph, get_async_graph as _cs_get_async_graph


def get_graph(agent_type: str):
    if agent_type == "customer_service":
        return _cs_graph
    raise ValueError(f"Unknown agent_type '{agent_type}'. Must be one of: ['customer_service']")


async def get_async_graph(agent_type: str):
    if agent_type == "customer_service":
        return await _cs_get_async_graph()
    raise ValueError(f"Unknown agent_type '{agent_type}'. Must be one of: ['customer_service']")
