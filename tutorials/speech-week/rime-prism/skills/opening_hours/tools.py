"""Fixed fictional exercise data; no network or personal data."""
from rasa.mantle.tools.decorator import tool
from rasa.mantle.tools.result import ToolResult


@tool(description="Read the fictional Juniper Library hours for one day.")
async def opening_hours(day: str) -> ToolResult:
    normalized = day.strip().lower()
    if normalized in {"monday", "tuesday", "wednesday", "thursday", "friday"}:
        hours = "09:00 to 18:00"
    elif normalized == "saturday":
        hours = "10:00 to 14:00"
    elif normalized == "sunday":
        hours = "closed"
    else:
        return ToolResult(llm_response={"state": "clarify_day", "accepted": "Monday through Sunday"})
    return ToolResult(llm_response={"state": "available", "day": normalized, "hours": hours,
                                    "fixture": "fictional Juniper Library"})
