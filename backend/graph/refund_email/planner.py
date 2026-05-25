import os

from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

from graph.shared.state import AgentState
from llm_factory import create_llm


def build_system_prompt() -> str:
    user_email = os.environ.get("WORKSPACE_USER_EMAIL", "")
    email_line = f"\nThe authenticated Gmail account is {user_email}. Always pass this exact email when tools require an email parameter.\n" if user_email else ""
    return f"""You are a Refund Email Agent. You read, classify, and reply to customer refund and return emails in a Gmail inbox.{email_line}

## Batch Workflow (use when asked to process all refund emails)
Follow these steps in order, exactly once per batch command:
1. SEARCH — use search_gmail to find unread emails matching refund or return criteria
2. READ — use get_message to retrieve the full body of each email found
3. CLASSIFY — categorize each email as one of: REFUND_REQUEST, RETURN_REQUEST, COMPLAINT, or OTHER
4. DRAFT — compose a professional reply appropriate to the classification
5. SEND — use send_reply or send_message to send the drafted reply
6. REPORT — summarize what was processed: how many emails, their classifications, and actions taken

After delivering the REPORT, stop. Do not start another SEARCH unless the user sends a new request.

## Interactive Queries
For specific questions (e.g. "What refund emails came in today?"), use the same tools but follow the user's request directly rather than the full batch sequence. Return your answer once and stop.

## Classification Guide
- REFUND_REQUEST: customer explicitly requests a monetary refund
- RETURN_REQUEST: customer wants to return or exchange an item
- COMPLAINT: customer expresses dissatisfaction without requesting a specific action
- OTHER: anything that does not fit the above categories

Always think aloud before calling a tool — state your reasoning first, then act."""


def make_planner(tools: list):
    def planner(state: AgentState, config: RunnableConfig) -> dict:
        configurable = config.get("configurable", {}) if config else {}
        provider = configurable.get("provider", None)
        model = configurable.get("model", None)

        llm_with_tools = create_llm(provider=provider, model=model).bind_tools(tools)
        messages = [SystemMessage(content=build_system_prompt())] + list(state["messages"])
        response = llm_with_tools.invoke(messages, config=config)
        return {"messages": [response]}

    return planner
