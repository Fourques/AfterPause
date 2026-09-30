"""End-to-end MCP check against a separately running local server."""
import asyncio
import json
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    url = 'http://127.0.0.1:8765'
    async with streamablehttp_client(url + '/mcp', httpx_client_factory=lambda **kw: httpx.AsyncClient(trust_env=False, **kw)) as (read, write, _):
        async with ClientSession(read, write) as session:
            hello = await session.initialize()
            assert hello.protocolVersion == '2025-11-25', hello.protocolVersion
            available = await session.list_tools()
            assert {t.name for t in available.tools} == {'create_task', 'list_tasks', 'get_checkpoint', 'update_task'}

            async def call(name, args):
                result = await session.call_tool(name, args)
                assert not result.isError, result
                return result.structuredContent or json.loads(result.content[0].text)

            task = await call('create_task', {'title': 'MCP integration check', 'steps': ['First', 'Second']})
            key = task['id']
            await call('update_task', {'task_id': key, 'revision': 0, 'action': 'confirm_step'})
            duplicate = await session.call_tool('update_task', {'task_id': key, 'revision': 0, 'action': 'confirm_step'})
            assert duplicate.isError
            await call('update_task', {'task_id': key, 'revision': 1, 'action': 'pause', 'note': 'Second item remains'})
            cp = await call('get_checkpoint', {'task_id': key})
            assert cp['next_step'] == 'Second' and cp['task']['state'] == 'paused'
            async with httpx.AsyncClient(trust_env=False) as client:
                ui_state = (await client.get(url + '/api/tasks')).json()
                matching = next(c for c in ui_state['tasks'] if c['task']['id'] == key)
                assert matching['task']['note'] == 'Second item remains'
                for endpoint in ['/api/tasks', '/mcp']:
                    blocked = await client.post(url + endpoint, headers={'Origin': 'https://untrusted.example'}, json={})
                    assert blocked.status_code == 403
            await call('update_task', {'task_id': key, 'revision': 2, 'action': 'resume'})
            final = await call('update_task', {'task_id': key, 'revision': 3, 'action': 'confirm_step'})
            assert final['state'] == 'completed'
            print('PASS: protocol 2025-11-25; four tools; durable shared state; stale update rejected; origin blocked; resume/completion')


if __name__ == '__main__':
    asyncio.run(main())
