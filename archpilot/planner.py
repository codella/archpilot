"""Validated intent and deterministic review artifact; never an execution recipe."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

FIELDS = ('desktop', 'encryption', 'hostname', 'timezone')
DESKTOPS = ('kde', 'gnome', 'hyprland', 'none')


def validate_preferences(value):
    if not isinstance(value, dict) or set(value) != set(FIELDS):
        raise ValueError('Preferences must contain exactly desktop, encryption, hostname and timezone.')
    if value['desktop'] not in (*DESKTOPS, None):
        raise ValueError('Desktop must be kde, gnome, hyprland or none.')
    if value['encryption'] is not None and type(value['encryption']) is not bool:
        raise ValueError('Encryption must be true or false.')
    hostname = value['hostname']
    if hostname is not None and (not isinstance(hostname, str) or not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', hostname)):
        raise ValueError('Use a hostname of 1–63 lowercase letters, numbers or hyphens; no leading/trailing hyphen.')
    tz = value['timezone']
    if tz is not None:
        try:
            if not isinstance(tz, str):
                raise ValueError('Timezone must be text.')
            ZoneInfo(tz)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError('Use an installed IANA timezone such as Europe/Copenhagen.') from exc
    return dict(value)


def select_disk(inventory, path):
    matches = [d for d in inventory['disks'] if d['path'] == path]
    if len(matches) != 1:
        raise ValueError('Select an exact disk path from /disks.')
    disk = matches[0]
    if disk['blocked_reasons']:
        raise ValueError('; '.join(disk['blocked_reasons']))
    if disk['size_bytes'] < 32 * 1024**3:
        raise ValueError('This prototype requires a disk of at least 32 GiB.')
    return path


def build_plan(inventory, preferences, target):
    preferences = validate_preferences(preferences)
    disk = None
    if target:
        select_disk(inventory, target)
        disk = next(d for d in inventory['disks'] if d['path'] == target)
    pending = [f'Choose {key}.' for key, value in preferences.items() if value is None]
    if disk is None:
        pending.append('Select a target with /disk /dev/… (never inferred by the model).')
    if inventory['boot_mode'] != 'uefi':
        pending.append('This first planning profile supports UEFI only.')
    if inventory['architecture'] != 'x86_64':
        pending.append('This first planning profile supports x86_64 only.')
    return {
        'schema_version': 1, 'status': 'draft', 'executable': False,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'inventory_source': inventory['source'], 'target': disk, 'preferences': preferences,
        'disk_effect': 'Proposed whole-disk erase; all existing partitions and data would be removed.' if disk else 'No disk selected.',
        'outline': [
            'Recheck live environment, network, time and disk identity.',
            'Review and separately authorize a whole-disk layout; dual boot is not supported here.',
            'Prepare an EFI system partition and Linux root filesystem; finalize sizes before execution.',
            'Configure root encryption if requested; collect secrets outside the conversation.',
            'Install base system, boot support, networking and chosen desktop.',
            'Configure users, locale, keyboard, timezone and hostname; verify boot before rebooting.',
        ],
        'pending': pending,
        'limitations': ['Planning milestone only: there is no installation executor.',
                        'Partition sizes, bootloader, drivers, packages, users and locale still need a concrete implementation plan.',
                        'Device inventory is a snapshot, not authorization to erase a disk.'],
    }


def save_plan(plan, path):
    """Exclusive creation avoids overwriting files or following an existing symlink."""
    with Path(path).open('x', encoding='utf-8') as output:
        output.write(json.dumps(plan, indent=2) + '\n')
