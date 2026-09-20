import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from archpilot.agent import parse_reply
from archpilot.inventory import demo_inventory, normalize_disks, discover
from archpilot.planner import build_plan, save_plan, select_disk, validate_preferences

PREFS = {'desktop': 'kde', 'encryption': True, 'hostname': 'archbox', 'timezone': 'UTC'}


class PlannerTests(unittest.TestCase):
    def test_usb_and_unknown_disk_rejected(self):
        for path in ['/dev/sda', '/dev/missing', '/dev/nvme0n1; reboot']:
            with self.assertRaises(ValueError):
                select_disk(demo_inventory(), path)

    def test_nested_active_descendant_excludes_entire_disk(self):
        disk = {'name': 'sda', 'type': 'disk', 'size': 100_000_000_000,
                'children': [{'name': 'sda1', 'children': [{'name': 'cryptroot', 'mountpoints': ['/']}]}]}
        normalized = normalize_disks({'blockdevices': [disk]})
        self.assertIn('Mounted', normalized[0]['blocked_reasons'][0])
        with self.assertRaises(ValueError):
            select_disk({'disks': normalized}, '/dev/sda')

    def test_snapshot_revalidated_before_plan(self):
        inventory = demo_inventory()
        target = select_disk(inventory, '/dev/nvme0n1')
        inventory['disks'][0]['blocked_reasons'].append('Now mounted')
        with self.assertRaises(ValueError):
            build_plan(inventory, PREFS, target)

    def test_plan_never_infers_disk_or_execution_authority(self):
        plan = build_plan(demo_inventory(), PREFS, None)
        self.assertIsNone(plan['target'])
        self.assertFalse(plan['executable'])
        self.assertTrue(plan['pending'])
        plan = build_plan(demo_inventory(), PREFS, '/dev/nvme0n1')
        self.assertIn('all existing', plan['disk_effect'])
        self.assertEqual(plan['target']['serial'], 'DEMO-001')
        self.assertFalse(plan['executable'])

    def test_bad_model_results_fail_validation(self):
        for key, value in [('hostname', 'foo; reboot'), ('encryption', 'yes'), ('timezone', '../etc/passwd'), ('desktop', 'imaginary')]:
            with self.assertRaises(ValueError):
                validate_preferences({**PREFS, key: value})
        with self.assertRaises(ValueError):
            parse_reply(json.dumps({'message': 'ok', 'preferences': {**PREFS, 'target': '/dev/sda'}}))
        self.assertEqual(parse_reply(json.dumps({'message': 'ok', 'preferences': PREFS}))[1], PREFS)

    def test_export_does_not_overwrite_or_follow_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'plan.json'
            save_plan({'status': 'draft'}, path)
            with self.assertRaises(FileExistsError):
                save_plan({}, path)
            link = Path(directory) / 'link.json'
            link.symlink_to(path)
            with self.assertRaises(FileExistsError):
                save_plan({}, link)
            self.assertEqual(json.loads(path.read_text()), {'status': 'draft'})

    @patch('archpilot.inventory.probe', return_value=('', 'probe unavailable'))
    def test_missing_probes_leave_no_selectable_disks(self, _probe):
        inventory = discover()
        self.assertEqual(inventory['disks'], [])
        self.assertTrue(inventory['warnings'])


if __name__ == '__main__':
    unittest.main()
