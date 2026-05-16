from langchain_core.messages import HumanMessage, ToolMessage


def test_memory_update_returns_written_key_and_value(monkeypatch):
    from graph.memory_update import memory_update

    class _Conn:
        def cursor(self, *args, **kwargs):
            class _Cursor:
                def execute(self, *args, **kwargs):
                    return None

            return _Cursor()

        def commit(self):
            return None

        def close(self):
            return None

    monkeypatch.setattr("graph.memory_update.get_connection", lambda: _Conn())

    state = {
        "customer_id": 1,
        "messages": [
            HumanMessage(content="Refund order 7890"),
            ToolMessage(
                content='{"order_id": 7890, "status": "refund_requested"}',
                tool_call_id="call_1",
                name="refund",
            ),
        ],
    }

    result = memory_update(state)

    assert result["key"] == "last_interaction_summary"
    assert isinstance(result["value"], str)
    assert "Refund order 7890" in result["value"]
    assert "refund" in result["value"]
