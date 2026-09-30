"""Capture real MCP responses for the demo; no physical actions are claimed."""
import asyncio
import json
from pathlib import Path
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    evidence = {'kind': 'synthetic demonstration over real local MCP transport', 'events': []}
    async with streamablehttp_client(
        'http://127.0.0.1:8765/mcp',
        httpx_client_factory=lambda **kw: httpx.AsyncClient(trust_env=False, **kw),
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            hello = await session.initialize()
            evidence['protocol'] = hello.protocolVersion
            evidence['tools'] = [t.name for t in (await session.list_tools()).tools]

            async def call(name, args):
                response = await session.call_tool(name, args)
                texts = [c.text for c in response.content if hasattr(c, 'text')]
                data = response.structuredContent
                if data is None:
                    data = {'text': texts} if response.isError else json.loads(texts[0])
                evidence['events'].append({'tool': name, 'arguments': args, 'isError': response.isError, 'result': data})
                return response, data

            _, task = await call('create_task', {'title': 'Demo: pack a bag', 'steps': ['Choose a bag', 'Pack the charger', 'Check keys']})
            key = task['id']
            await call('update_task', {'task_id': key, 'revision': 0, 'action': 'confirm_step'})
            duplicate, _ = await call('update_task', {'task_id': key, 'revision': 0, 'action': 'confirm_step'})
            assert duplicate.isError
            await call('update_task', {'task_id': key, 'revision': 1, 'action': 'start_timer', 'seconds': 1})
            await call('update_task', {'task_id': key, 'revision': 2, 'action': 'pause', 'note': 'Charger is on the desk.'})
            await asyncio.sleep(1.1)
            _, checkpoint = await call('get_checkpoint', {'task_id': key})
            assert checkpoint['timer_due'] and checkpoint['task']['cursor'] == 1
            assert checkpoint['task']['state'] == 'paused'
            assert checkpoint['next_step'] == 'Pack the charger'
            evidence['checks'] = {'stale_completion_rejected': True, 'timer_expiry_did_not_advance_step': True}
    directory = Path('.task')
    directory.mkdir(exist_ok=True)
    (directory / 'mcp-demo-evidence.json').write_text(json.dumps(evidence, indent=2))
    report = '\n'.join([
        'AFTERPAUSE / REAL MCP CLIENT RESULTS', '',
        f'Negotiated protocol: {evidence["protocol"]}',
        'Transport: Streamable HTTP on localhost',
        'Discovered tools: ' + ', '.join(evidence['tools']), '',
        'Synthetic task: Demo: pack a bag',
        'Completed: Choose a bag',
        'Next: Pack the charger',
        'State: paused',
        'Saved note: Charger is on the desk.', '',
        'PASS: stale completion request rejected',
        'PASS: timer expired without completing a step', '',
        'Captured from actual SDK calls. No Alexa device is connected.',
    ])
    (directory / 'mcp-demo-report.txt').write_text(report)
    print(report)


if __name__ == '__main__':
    asyncio.run(main())
