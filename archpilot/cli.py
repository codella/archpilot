import argparse
import json
import sys
from contextlib import ExitStack

from .inventory import demo_inventory, discover
from .planner import FIELDS, build_plan, save_plan, select_disk, validate_preferences

HELP = '''Commands:
  /disks                      Show disk identities and exclusions
  /disk /dev/nvme0n1           Select a proposed whole-disk target
  /set desktop kde            kde | gnome | hyprland | none
  /set encryption yes         yes | no
  /set hostname archbox
  /set timezone Europe/Copenhagen
  /plan                       Review current draft
  /save plan.json              Save draft (refuses to overwrite)
  /help   /quit
In live mode, type naturally to discuss and update your preferences.
Demo mode uses fixture hardware and explicit /set commands; it makes no AI calls.'''


def clean(value):
    # Strip terminal controls from hardware strings, model text and errors.
    return ''.join(c for c in str(value) if c in '\n\t' or (c.isprintable() and c != '\x1b'))


def say(value=''):
    print(clean(value), flush=True)


def show_disks(inventory):
    for disk in inventory['disks']:
        say(f"\n{disk['path']}  {disk['size_bytes'] / 1024**3:.1f} GiB  {disk['model']}  serial={disk['serial']}")
        for part in disk['partitions']:
            say(f"  {part['path']}  {part['filesystem'] or 'unknown filesystem'}")
        say('  ' + ('EXCLUDED: ' + '; '.join(disk['blocked_reasons']) if disk['blocked_reasons'] else 'Available for a draft whole-disk plan'))
    if not inventory['disks']:
        say('No disks discovered; disk selection unavailable.')


def show_plan(plan):
    say('\nINSTALLATION DRAFT — planning only')
    disk = plan['target']
    if disk:
        say(f"Target: {disk['path']} | {disk['model']} | {disk['size_bytes'] / 1024**3:.1f} GiB | serial={disk['serial']}")
    say(plan['disk_effect'])
    for key, value in plan['preferences'].items():
        say(f'  {key}: {value if value is not None else "undecided"}')
    for index, step in enumerate(plan['outline'], 1):
        say(f'{index}. {step}')
    for question in plan['pending']:
        say('Pending: ' + question)
    say('No disks have been modified. This draft cannot be executed.')


def auth(action, api_key=False):
    from .agent import new_client
    from getpass import getpass
    with new_client() as client:
        if action == 'login':
            if api_key:
                client.login_api_key(getpass('OpenAI API key (hidden): '))
            else:
                login = client.login_chatgpt_device_code()
                say(f'Open on your phone or computer: {login.verification_url}\nCode: {login.user_code}')
                try:
                    result = login.wait()
                except KeyboardInterrupt:
                    login.cancel()
                    raise
                if not result.success:
                    raise RuntimeError('Login failed. Check device-code access in ChatGPT security settings.')
            say('Signed in. Run archpilot chat.')
        elif action == 'logout':
            client.logout()
            say('Signed out.')
        else:
            say('Signed in.' if client.account().account is not None else 'Not signed in. Run archpilot login.')


def chat(demo=False, model=None):
    inventory = demo_inventory() if demo else discover()
    preferences = dict.fromkeys(FIELDS)
    target = None
    say('\nARCHPILOT  /  ' + ('OFFLINE DEMO' if demo else 'INSTALLATION PLANNER'))
    say('A little guidance before you earn the right to say “I use Arch.”')
    say('Milestone 1: discovery and planning. No installation executor.')
    say(f"Boot: {inventory['boot_mode']} | Architecture: {inventory['architecture']}")
    if not inventory['arch_live']:
        say('Arch live environment not detected; exploration is still available.')
    for warning in inventory['warnings']:
        say('Inventory note: ' + warning)
    show_disks(inventory)
    say('\n' + HELP)
    with ExitStack() as stack:
        agent = None
        while True:
            try:
                line = input('\narch> ').strip()
            except EOFError:
                break
            if not line:
                continue
            try:
                command, _, value = line.partition(' ')
                value = value.strip()
                if command == '/quit':
                    break
                elif command == '/help':
                    say(HELP)
                elif command == '/disks':
                    show_disks(inventory)
                elif command == '/disk':
                    target = select_disk(inventory, value)
                    say(f'Proposed target: {target}. A whole-disk install would erase all its data. Selection is not authorization.')
                elif command == '/set':
                    key, _, setting = value.partition(' ')
                    if key not in FIELDS or not setting:
                        raise ValueError('Use /set FIELD VALUE. See /help.')
                    if key == 'encryption':
                        if setting not in ('yes', 'no'):
                            raise ValueError('Use /set encryption yes or no.')
                        setting = setting == 'yes'
                    preferences = validate_preferences({**preferences, key: setting})
                    say('Preference updated.')
                elif command in ('/plan', '/save'):
                    plan = build_plan(inventory, preferences, target)
                    if command == '/plan':
                        show_plan(plan)
                    else:
                        if not value:
                            raise ValueError('Use /save plan.json.')
                        save_plan(plan, value)
                        say('Saved draft to ' + value)
                elif line.startswith('/'):
                    say('Unknown command. Use /help.')
                elif demo:
                    say('Offline demo: use /set to choose preferences, /disk to select, then /plan. Live chat uses Codex.')
                else:
                    if agent is None:
                        from .agent import PlannerAgent, new_client
                        client = stack.enter_context(new_client())
                        if client.account().account is None:
                            raise RuntimeError('Not signed in. Run archpilot login first.')
                        agent = PlannerAgent(client, inventory, model)
                    say('Thinking…')
                    message, updated = agent.reply(line, preferences)
                    preferences = updated
                    say(message)
            except (ValueError, OSError, RuntimeError) as exc:
                say(f'Could not complete that request: {exc}')


def main(argv=None):
    parser = argparse.ArgumentParser(description='An Arch Linux installation planner. No disk modification commands.')
    parser.add_argument('command', nargs='?', default='chat', choices=['chat', 'demo', 'inventory', 'login', 'status', 'logout'])
    parser.add_argument('--model', help='Override the configured Codex model')
    parser.add_argument('--api-key', action='store_true', help='Use a hidden API-key prompt with login')
    args = parser.parse_args(argv)
    if args.api_key and args.command != 'login':
        parser.error('--api-key applies only to login')
    try:
        if args.command in ('login', 'status', 'logout'):
            auth(args.command, args.api_key)
        elif args.command == 'inventory':
            print(json.dumps(discover(), indent=2))
        else:
            chat(args.command == 'demo', args.model)
        return 0
    except KeyboardInterrupt:
        say('\nStopped.')
        return 130
    except ImportError:
        say('Install the SDK with: python -m pip install -e .')
        return 1
    except Exception as exc:
        say(f'Error ({type(exc).__name__}): {exc}')
        say('For connection/authentication issues, check networking and run archpilot status or login.')
        return 1
