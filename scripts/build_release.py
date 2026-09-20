#!/usr/bin/env python3
"""Build a wheel and checksum-pinned HTTPS bootstrap. Never publishes anything."""
import argparse
import hashlib
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent


def render_installer(version, base_url, wheel_name, digest):
    template = (ROOT / 'scripts/install.sh.in').read_text()
    for key, value in {'VERSION': version, 'RELEASE_BASE': base_url.rstrip('/'),
                       'WHEEL': wheel_name, 'WHEEL_SHA256': digest}.items():
        template = template.replace('@' + key + '@', shlex.quote(value))
    return template


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='', help='HTTPS release directory; omit to require --base-url at install time')
    args = parser.parse_args()
    if args.base_url:
        url = urlsplit(args.base_url)
        if url.scheme != 'https' or not url.netloc or url.query or url.fragment or url.username:
            parser.error('--base-url must be an HTTPS directory URL without credentials, query or fragment')
    version = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['version']
    output = ROOT / 'dist' / f'v{version}'
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--wheel-dir', str(output), str(ROOT)], check=True)
    wheel_name = f'archpilot-{version}-py3-none-any.whl'
    wheel = output / wheel_name
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    installer = output / 'install.sh'
    installer.write_text(render_installer(version, args.base_url, wheel_name, digest))
    installer.chmod(0o755)
    (output / 'SHA256SUMS').write_text(f'{digest}  {wheel_name}\n')
    print(f'\nRelease ready in {output}: wheel, install.sh, SHA256SUMS')
    if not args.base_url:
        print('No host configured. Supply --base-url to the installer, or rebuild with --base-url before publishing.')


if __name__ == '__main__':
    main()
