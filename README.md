# AfterPause

A local checkpoint companion for interrupted, everyday multi-step tasks. The web
interface and MCP tools use one SQLite record. A timer is a reminder to check,
never evidence that a physical action happened.

## Demonstration

[Watch or download the 85-second demo](docs/afterpause-demo.mp4).
The video combines actual local browser capture with recorded MCP client results.
It is not an Alexa device session. Reproduce the protocol checks by running
`.venv/bin/python demo_evidence.py` while the server is running; results are
written into the ignored `.task` directory. A captured synthetic run is included
in `docs/mcp-demo-evidence.json`.

## Run

Python 3.12 is tested. From this directory:

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python server.py
```

Open http://127.0.0.1:8765. The Streamable HTTP MCP endpoint is
http://127.0.0.1:8765/mcp. Configure that URL in a compatible MCP client.
The official Python SDK is used; live testing negotiated protocol 2025-11-25.

Tools: `list_tasks`, `create_task`, `get_checkpoint`, `update_task`.
Run `.venv/bin/python demo_client.py` in a second terminal for an interactive
reference client using the actual MCP transport. It can resume browser-created
tasks; it is not an Alexa connection or an LLM-powered simulation.
See `judging-guide.txt` for a short demonstration sequence and remaining entry gaps.
Clients must read the latest revision before writing, and must get the user's
explicit confirmation before marking a physical step complete. A stale revision
fails rather than silently advancing another step. Pausing does not stop a timer.

## Verify

```sh
.venv/bin/python -m unittest -v test_core.py
# With the server running; creates a clearly named synthetic test task:
.venv/bin/python test_transport.py
```

The six unit tests cover persisted recovery, stale write rejection, timer
semantics, task isolation, completion boundaries and invalid-input rollback.
The transport check uses the actual SDK client over HTTP and verifies tool
discovery, shared UI state, protocol negotiation and cross-origin rejection.

Browser scenario: load packing example → confirm first step → pause with a note
→ reload → verify next step and note → resume → confirm remaining steps.

## Boundaries

- Local single-user prototype. Do not expose it through a tunnel or public bind.
  It does not implement remote identity, OAuth or multi-user access control.
- No microphones, paid model API, cloud resource or physical appliance controls.
- No actual Alexa device integration, certification or voice recognition has
  been verified. The MCP transport works with the tested SDK client.
- Reminder status is displayed while the page is open; there is no background
  push notification or audible alarm. Not for safety-critical reminders.
- Notes and task titles are untrusted content, rendered as text. MCP clients
  should not interpret them as permission to execute unrelated actions.
- Data is stored in `local.sqlite` (excluded from version control). For an
  isolated test instance set `AFTERPAUSE_DB` to a different file before starting.

## Competition status

Prepared as a potential Alexa+ entry for the Amazon Developer Hackathon:
https://amazonappdev2026.devpost.com/rules

Source repository: https://github.com/Fourques/AfterPause

Not registered or submitted. Entrant eligibility, final entry approval,
demonstration video and payout details remain pending.
No prize or income is claimed.

## Source release

The original project code is available under the MIT license in `LICENSE`.
Dependencies retain their own licenses. Run `python package_release.py` to build
`../afterpause-source.zip`; its explicit file list excludes local task data,
virtual environments and caches. SHA256.json records each included file's hash.
