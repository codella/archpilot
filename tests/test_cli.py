import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from archpilot.cli import main
from archpilot.inventory import demo_inventory


class StartupTests(unittest.TestCase):
    def run_startup(self, signed_in, answers, success=True):
        client = MagicMock()
        client.__enter__.return_value = client
        client.account.return_value.account = object() if signed_in else None
        client.login_chatgpt_device_code.return_value.wait.return_value.success = success
        with patch('archpilot.cli.discover', return_value=demo_inventory()), \
             patch('archpilot.agent.new_client', return_value=client), \
             patch('archpilot.agent.PlannerAgent') as agent, \
             patch('builtins.input', side_effect=answers), \
             patch('archpilot.cli.say'):
            result = main([])
        return result, client, agent

    def test_existing_session_opens_assistant(self):
        result, client, agent = self.run_startup(True, ['/quit'])
        self.assertEqual(result, 0)
        client.login_chatgpt_device_code.assert_not_called()
        agent.assert_called_once()

    def test_first_launch_logs_in_then_opens_assistant(self):
        result, client, agent = self.run_startup(False, ['', '/quit'])
        self.assertEqual(result, 0)
        client.login_chatgpt_device_code.assert_called_once()
        agent.assert_called_once()

    def test_failed_login_does_not_open_assistant(self):
        result, client, agent = self.run_startup(False, [''], success=False)
        self.assertEqual(result, 1)
        agent.assert_not_called()

    def test_quit_before_login(self):
        result, client, agent = self.run_startup(False, ['q'])
        self.assertEqual(result, 0)
        client.login_chatgpt_device_code.assert_not_called()
        agent.assert_not_called()

    def test_api_key_option(self):
        with patch('getpass.getpass', return_value='test-key'):
            result, client, agent = self.run_startup(False, ['a', '/quit'])
        self.assertEqual(result, 0)
        client.login_api_key.assert_called_once_with('test-key')
        agent.assert_called_once()

    def test_cancel_device_login(self):
        result, client, agent = self.run_startup(False, [KeyboardInterrupt()])
        self.assertEqual(result, 130)
        agent.assert_not_called()
