"""Interactive, deterministic MCP client. No Alexa or LLM connection is implied."""
import asyncio
import json
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    print('AfterPause — MCP reference client (not Alexa)')
    async with streamablehttp_client(
        'http://127.0.0.1:8765/mcp',
        httpx_client_factory=lambda **kw: httpx.AsyncClient(trust_env=False, **kw),
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            hello = await session.initialize()
            print('Connected using MCP', hello.protocolVersion)

            async def call(name, args):
                result = await session.call_tool(name, args)
                if result.isError:
                    raise ValueError(' '.join(c.text for c in result.content if hasattr(c, 'text')))
                return result.structuredContent or json.loads(result.content[0].text)

            while True:
                tasks = (await call('list_tasks', {}))['tasks']
                pending = [t for t in tasks if t['state'] != 'completed']
                print('\nSaved tasks:')
                for i, task in enumerate(pending, 1):
                    print(f"{i}. {task['title']} ({task['state']})")
                choice = input('Task number, [n] new, or [q] quit: ').strip().lower()
                if choice == 'q':
                    return
                if choice == 'n':
                    title = input('Title: ')
                    steps = input('Steps separated with |: ').split('|')
                    try:
                        task = await call('create_task', {'title': title, 'steps': steps})
                    except ValueError as exc:
                        print(exc)
                        continue
                else:
                    try:
                        index = int(choice) - 1
                        if index < 0:
                            raise ValueError()
                        task = pending[index]
                    except (ValueError, IndexError):
                        print('Choose a listed task.')
                        continue
                while True:
                    cp = await call('get_checkpoint', {'task_id': task['id']})
                    current = cp['task']
                    print('\n' + current['title'])
                    print('Completed:', ', '.join(cp['completed_steps']) or 'None yet')
                    print('Next:', cp['next_step'] or 'All steps confirmed')
                    if current['note']:
                        print('Checkpoint:', current['note'])
                    if cp['timer_due']:
                        print('Reminder due. Check the task; nothing was marked complete.')
                    if current['state'] == 'completed':
                        break
                    command = input('[d] explicitly confirm done, [p] pause, [r] resume, [t] reminder, [b] back: ').lower().strip()
                    if command == 'b':
                        break
                    args = {'task_id': current['id'], 'revision': current['revision']}
                    if command == 'd':
                        if input(f"Have you actually completed '{cp['next_step']}'? Type yes: ").strip().lower() != 'yes':
                            continue
                        args['action'] = 'confirm_step'
                    elif command == 'p':
                        args.update(action='pause', note=input('What should you remember when returning? '))
                    elif command == 'r':
                        args['action'] = 'resume'
                    elif command == 't':
                        try:
                            seconds = int(input('Remind after how many seconds? '))
                        except ValueError:
                            print('Use whole seconds.')
                            continue
                        args.update(action='start_timer', seconds=seconds)
                    else:
                        continue
                    try:
                        await call('update_task', args)
                    except ValueError as exc:
                        print('No change confirmed:', exc)
                        # Always reread. Never automatically repeat a physical completion.


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (EOFError, KeyboardInterrupt):
        print('\nSession closed. Saved tasks remain available.')
