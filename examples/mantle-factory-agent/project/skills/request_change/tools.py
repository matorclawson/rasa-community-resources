"""Verdict card: built by code from the gate record and sent straight to the dialogue."""
from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

MARK = {'ACCEPT': '🟢', 'REJECT': '🔴', 'NOT_READY': '🟡'}
HEADLINE = {
    'ACCEPT': 'ACCEPT: the locked tests passed',
    'REJECT': 'REJECT: a locked test failed',
    'NOT_READY': 'NOT_READY: no verdict was obtained',
}
BAR = {'ACCEPT': '▰▰▰▰▰▰▰▰▰▰', 'REJECT': '▰▰▰▰▰▱▱▱▱▱', 'NOT_READY': '▱▱▱▱▱▱▱▱▱▱'}


def card_text(request, verdict, failing_test, fingerprint, mode, builder_calls, seconds, reason):
    verdict = verdict if verdict in MARK else 'NOT_READY'
    lines = [
        f'{MARK[verdict]}  {HEADLINE[verdict]}',
        '━━━━━━━━━━━━━━',
        f'Request   {request}',
    ]
    if mode == 'LIVE':
        lines.append(f'Builder   LIVE, gpt-6-astra · {builder_calls} tool calls · {seconds} s')
    else:
        lines.append('Builder   SCRIPTED · supplied attempt · 0 model calls')
    lines.append(f'Gate      {BAR[verdict]}')
    if verdict == 'REJECT':
        lines.append(f'Failed    {failing_test or "unknown"}')
    if verdict == 'NOT_READY' and reason:
        lines.append(f'Reason    {reason}')
    if fingerprint:
        lines.append(f'Attempt   {fingerprint[:12]}…')
    lines.append('Status    judged only · nothing released or deployed')
    return '\n'.join(lines)


@tool(description='Show the verdict card for a finished factory check. Call once, right after run_factory returns, with its values.')
async def show_verdict_card(request: str, verdict: str, failing_test: str = '', fingerprint: str = '',
                            mode: str = 'SCRIPTED', builder_calls: int = 0, seconds: float = 0.0,
                            reason: str = '', context: ToolContext = None) -> ToolResult:
    await context.send(card_text(request, verdict, failing_test, fingerprint, mode, builder_calls, seconds, reason))
    return ToolResult(llm_response={'card': 'shown'})
