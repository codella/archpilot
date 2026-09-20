"""Read-only probes. No user or model text is ever executed."""
import json
import platform
import subprocess
from pathlib import Path


def probe(argv):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=10, check=True)
        return result.stdout, None
    except (OSError, subprocess.SubprocessError) as exc:
        return '', f'{argv[0]} unavailable ({type(exc).__name__})'


def walk(node):
    yield node
    for child in node.get('children', []):
        yield from walk(child)


def normalize_disks(data):
    disks = []
    for node in data.get('blockdevices', []):
        if node.get('type') != 'disk':
            continue
        members = list(walk(node))
        mounts = [m for n in members for m in (n.get('mountpoints') or []) if m]
        reasons = []
        if mounts:
            reasons.append('Mounted or active descendants: ' + ', '.join(mounts))
        if node.get('ro') in (True, 1, '1'):
            reasons.append('Read-only device')
        if node.get('rm') in (True, 1, '1') or node.get('tran') == 'usb':
            reasons.append('Removable/USB device; excluded in this prototype')
        disks.append({
            'path': node.get('path') or '/dev/' + node['name'],
            'model': (node.get('model') or 'Unknown').strip(),
            'serial': (node.get('serial') or 'Unknown').strip(),
            'size_bytes': int(node.get('size') or 0),
            'partitions': [{'path': n.get('path') or '/dev/' + n['name'],
                            'filesystem': n.get('fstype'), 'size_bytes': int(n.get('size') or 0)}
                           for n in members[1:]],
            'blocked_reasons': reasons,
        })
    return disks


def discover():
    raw, error = probe(['lsblk', '--json', '--bytes', '--paths', '--output',
                        'NAME,PATH,TYPE,SIZE,MODEL,SERIAL,RO,RM,TRAN,FSTYPE,MOUNTPOINTS'])
    warnings = [error] if error else []
    try:
        disks = normalize_disks(json.loads(raw)) if raw else []
    except (ValueError, KeyError, TypeError):
        disks = []
        warnings.append('Could not parse disk inventory; disk selection disabled.')
    gpu, gpu_error = probe(['lspci'])
    if gpu_error:
        warnings.append(gpu_error)
    return {
        'source': 'live', 'architecture': platform.machine(),
        'boot_mode': ('uefi' if Path('/sys/firmware/efi').exists() else 'bios')
                     if platform.system() == 'Linux' else 'unknown',
        'arch_live': Path('/run/archiso').exists(),
        'graphics': [s for s in gpu.splitlines() if any(x in s for x in ('VGA', '3D controller', 'Display controller'))],
        'disks': disks, 'warnings': warnings,
    }


def demo_inventory():
    return {
        'source': 'demo', 'architecture': 'x86_64', 'boot_mode': 'uefi', 'arch_live': True,
        'graphics': ['Demo AMD graphics'], 'warnings': [],
        'disks': [
            {'path': '/dev/nvme0n1', 'model': 'Demo SSD', 'serial': 'DEMO-001',
             'size_bytes': 1_000_000_000_000,
             'partitions': [{'path': '/dev/nvme0n1p1', 'filesystem': 'ntfs', 'size_bytes': 500_000_000_000}],
             'blocked_reasons': []},
            {'path': '/dev/sda', 'model': 'Arch live USB', 'serial': 'DEMO-USB',
             'size_bytes': 32_000_000_000, 'partitions': [],
             'blocked_reasons': ['Removable/USB device; excluded in this prototype']},
        ],
    }
