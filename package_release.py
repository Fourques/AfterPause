"""Build a source-only judging bundle. User databases and environments stay local."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parent
FILES = (
    '.gitignore', 'LICENSE', 'README.md', 'requirements.txt', 'core.py',
    'server.py', 'index.html', 'demo_client.py', 'test_core.py',
    'test_transport.py', 'judging-guide.txt', 'package_release.py',
)


def build():
    contents = {name: (ROOT / name).read_bytes() for name in FILES}
    manifest = {name: hashlib.sha256(body).hexdigest() for name, body in contents.items()}
    output = ROOT.parent / 'afterpause-source.zip'
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, body in contents.items():
            archive.writestr('afterpause/' + name, body)
        archive.writestr('afterpause/SHA256.json', json.dumps(manifest, indent=2) + '\n')
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for name, digest in manifest.items():
            assert hashlib.sha256(archive.read('afterpause/' + name)).hexdigest() == digest
    print(f'{output}: {len(contents)} source files plus SHA256.json; {output.stat().st_size} bytes')


if __name__ == '__main__':
    build()
