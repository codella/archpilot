import fcntl
import pty
import termios
import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.build_release import render_installer


class BootstrapTests(unittest.TestCase):
    def run_installer(self, *, corrupt=False, fail_pip=False, existing=False, unrelated=False, local=False, terminal=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fakebin = root / 'fakebin'
            fakebin.mkdir()
            prefix = root / 'install'
            bindir = root / 'bin'
            bindir.mkdir()
            wheel = root / 'archpilot-0.1.0-py3-none-any.whl'
            wheel.write_bytes(b'wheel fixture')
            digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
            installer = root / 'install.sh'
            installer.write_text(render_installer('0.1.0', 'https://example.invalid/v0.1.0', 'archpilot-0.1.0-py3-none-any.whl', '0'*64 if corrupt else digest))
            scripts = {
                'curl': '#!/bin/bash\nwhile (($#)); do if [[ $1 == -o ]]; then cp "$FIXTURE_WHEEL" "$2"; exit; fi; shift; done\nexit 1\n',
                'uname': '#!/bin/bash\n[[ $1 == -s ]] && echo Linux || echo x86_64\n',
                'python3': '''#!/bin/bash
if [[ $1 == -c ]]; then exit 0; fi
[[ $1 == -m && $2 == venv ]] || exit 9
mkdir -p "$3/bin"
printf '#!/bin/bash\\nexit %s\\n' "$PIP_EXIT" > "$3/bin/python"
printf '#!/bin/bash\\nif (($# == 0)); then echo started > "$START_MARKER"; fi\\necho archpilot-fixture\\n' > "$3/bin/archpilot"
chmod +x "$3/bin/"*
''',
            }
            for name, source in scripts.items():
                path = fakebin / name
                path.write_text(source)
                path.chmod(0o755)
            launcher = bindir / 'archpilot'
            if existing:
                old = prefix / 'releases' / 'old' / 'bin' / 'archpilot'
                old.parent.mkdir(parents=True)
                old.write_text('old working command')
                launcher.symlink_to(old)
            if unrelated:
                launcher.write_text('unrelated command')
            env = {**os.environ, 'PATH': str(fakebin) + ':' + os.environ['PATH'],
                   'START_MARKER': str(root / 'started'), 'FIXTURE_WHEEL': str(wheel), 'PIP_EXIT': '1' if fail_pip else '0'}
            args = ['bash', str(installer), '--prefix', str(prefix), '--bin-dir', str(bindir)]
            if local:
                args.extend(['--release-dir', str(root)])
            if terminal:
                master, slave = pty.openpty()
                def attach_terminal():
                    os.setsid()
                    fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
                try:
                    # Feed the installer over a pipe, just like curl | bash.
                    result = subprocess.run(['bash', '-s', '--', *args[2:]],
                                            input=installer.read_text(), env=env, text=True,
                                            capture_output=True, timeout=15,
                                            pass_fds=(slave,), preexec_fn=attach_terminal)
                    self.assertTrue((root / 'started').exists(), result.stderr)
                finally:
                    os.close(master)
                    os.close(slave)
            else:
                result = subprocess.run(args, env=env, text=True, capture_output=True,
                                        timeout=15, start_new_session=True)
            if corrupt or fail_pip or unrelated:
                self.assertNotEqual(result.returncode, 0, result.stdout)
                if existing:
                    self.assertEqual(launcher.read_text(), 'old working command')
                elif unrelated:
                    self.assertEqual(launcher.read_text(), 'unrelated command')
                else:
                    self.assertFalse(launcher.exists())
            else:
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(launcher.is_symlink())
                self.assertTrue(launcher.resolve().is_file())
                self.assertIn('Start Archpilot:', result.stdout)
            releases = list((prefix / 'releases').iterdir())
            self.assertEqual(len(releases), (1 if existing else 0) + (0 if corrupt or fail_pip or unrelated else 1))

    def test_piped_install_opens_assistant_on_terminal(self):
        self.run_installer(terminal=True)

    def test_success(self):
        self.run_installer()

    def test_local_release(self):
        self.run_installer(local=True)

    def test_local_checksum_failure(self):
        self.run_installer(local=True, corrupt=True)

    def test_checksum_failure(self):
        self.run_installer(corrupt=True)

    def test_failed_upgrade_preserves_existing(self):
        self.run_installer(fail_pip=True, existing=True)

    def test_upgrade(self):
        self.run_installer(existing=True)

    def test_unrelated_launcher_preserved(self):
        self.run_installer(unrelated=True)

    def test_missing_host_fails_before_install(self):
        script = render_installer('0.1.0', '', 'a.whl', '0' * 64)
        result = subprocess.run(['bash'], input=script, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('HTTPS URL', result.stderr)
