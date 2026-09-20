# Archpilot

A Python terminal companion for planning an Arch Linux installation from the live environment. Powered by the official `openai-codex` SDK.

**Milestone 1: hardware discovery → conversation → reviewable draft.** There is no partitioning, formatting, package installation or reboot executor. Plans are intent documents, not executable installation recipes.

## Start from the Arch live ISO

Connect to the internet, then paste:

```sh
curl -fsSL https://github.com/codella/archpilot/releases/download/v0.1.0/install.sh | bash
```

Archpilot installs, opens, and guides you through sign-in if needed. No separate login or chat commands are required. This release is a planner; it does not format disks or install Arch Linux.

## Try it locally

Python 3.11+ is required. From this checkout:

```sh
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/archpilot demo
```

The demo uses fictional hardware and local commands, without credentials or API calls. You can also run it without installing dependencies: `python -m archpilot demo`.

```text
/disk /dev/nvme0n1
/set desktop kde
/set encryption yes
/set hostname archbox
/set timezone Europe/Copenhagen
/plan
/save plan.json
/quit
```

The fixture intentionally includes an existing NTFS partition so the proposed erase is visible, plus an excluded live USB.

## Installation and authentication in the Arch live environment

First establish networking and correct system time, following the [Arch installation guide](https://wiki.archlinux.org/title/Installation_guide). Have this checkout available in the live environment. If Python's venv/pip support is missing, provision it in your live image before running the setup commands above. For the generated bootstrap and release instructions, see below. No custom ISO is provided.

The pinned Python SDK installs its matching Codex runtime automatically. **No Node.js or separate global Codex install is needed.** The assistant calls that runtime through the SDK.

```sh
.venv/bin/archpilot
```

Archpilot checks your session and offers ChatGPT sign-in or a hidden API-key prompt if needed. Once signed in, it opens the conversation automatically. Open the displayed verification URL on a phone or another computer and enter the code. Device-code login is beta and may require enabling it in your ChatGPT security settings or workspace permissions. On later launches, run the same `archpilot` command; an existing session is reused.

Use the same OS user and environment for login and chat. The SDK uses Codex's normal credential store. On the live ISO, keep this state in the live environment; don't copy it into the target installation. Sign out with `archpilot logout` (or use the `.venv/bin/` prefix).

An API key is an alternative, billed through your API account:

```sh
.venv/bin/archpilot login --api-key
```

The key is entered through a hidden terminal prompt, not in the conversation or command arguments. Do not supply passwords or encryption passphrases to the chat. See [official authentication guidance](https://learn.chatgpt.com/docs/auth) and [SDK documentation](https://learn.chatgpt.com/docs/codex-sdk).

## Live conversation

```text
arch> I want KDE and an encrypted root filesystem for a development laptop.
arch> Use Europe/Copenhagen and call it archbox.
arch> /disks
arch> /disk /dev/nvme0n1
arch> /plan
```

The model can discuss choices and update four validated preferences: desktop, encryption, hostname and timezone. It cannot choose the disk through its response schema. Disk selection always uses `/disk` with an exact path. `/set` also works in live mode without an API call.

`archpilot inventory` prints local discovery JSON without starting Codex. `archpilot --model MODEL` overrides the configured model. Discovery uses fixed `lsblk` and `lspci` argument lists, never model-generated shell text. Missing probes are reported. Model prompts contain hardware inventory and preferences; disk serials are removed from prompts, but retained in local review/export.

## Scope and limitations

- First profile: x86_64, UEFI, whole-disk installation intent. Dual boot and partition preservation are future work.
- Mounted devices (including nested mapped devices), read-only devices and USB/removable disks are excluded from target selection. This intentionally excludes USB installation targets too.
- Discovery is a snapshot. A future executor must rediscover and compare disk identity immediately before any write and obtain explicit erase authorization.
- Plans always remain `draft` and `executable: false`. Partition sizes, bootloader, packages, users, locale and driver selection remain future implementation work. An empty pending-preferences list does not make a draft installable.
- Codex threads request a read-only sandbox and deny all escalation approvals. They receive planning-only instructions. Runtime capabilities and host Codex configuration still matter; this is a development prototype for a disposable VM, not a hardened root agent.
- No automatic retry of model calls, cross-process chat resumption, installation execution or recovery engine yet. `/save` preserves the draft, not an executable checkpoint.
- Draft export refuses existing files and symlinks. Export contains disk identifiers; keep it local.

## Development

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m archpilot --help
```

Modules:

- `inventory.py`: fixed read-only probes and disk exclusions.
- `planner.py`: preference validation, draft construction and exclusive export.
- `agent.py`: Codex thread and schema-constrained responses.
- `cli.py`: terminal conversation, local commands and SDK authentication.

The SDK version is pinned in `pyproject.toml`; it pins its own runtime dependency. Offline tests cover disk exclusions, malformed model output and export behavior. Authenticated model calls and booting an actual Arch ISO require separate integration testing.

## Bootstrap from the Arch ISO

From the Arch live shell, connect to the internet and paste this one command:

```sh
curl -fsSL https://github.com/codella/archpilot/releases/download/v0.1.0/install.sh | bash
```

Or download with wget and run after the download succeeds:

```sh
wget -O /tmp/archpilot-install.sh https://github.com/codella/archpilot/releases/download/v0.1.0/install.sh && bash /tmp/archpilot-install.sh
```

These URLs require a published public GitHub release; local builds do not publish it. The script installs Archpilot and immediately opens it. If needed, Archpilot guides you through sign-in, then starts the planning conversation. Interactive input uses the terminal, not the download pipe. This does not initiate installation of Arch Linux.

To install without launching, append `-s -- --no-start` after `bash`. Without an interactive terminal, the installer prints a command to launch later.

The root defaults are `/opt/archpilot/releases/` and `/usr/local/bin/archpilot`. For regular users the defaults are `~/.local/share/archpilot/releases/` (respecting `XDG_DATA_HOME`) and `~/.local/bin/archpilot`; the script prints absolute commands so it also works before updating PATH. Python 3.11+ is required. Missing Python/venv prerequisites are provisioned with `pacman -Syu` **only when running as root inside `/run/archiso`**. This updates the live environment and requires sufficient RAM/overlay space. Elsewhere, install prerequisites yourself.

Every install creates a fresh virtual environment and checks the application launcher before switching the command symlink. Failed downloads, checksum mismatches and failed dependency installation leave an existing launcher unchanged. Old releases are retained. The application wheel checksum is embedded in the installer; dependencies are fetched from the configured Python package index. The bootstrap is not an offline or completely reproducible dependency bundle. Downloading and executing the script trusts the GitHub repository and release publisher.

## Build and publish a release

```sh
.venv/bin/python scripts/build_release.py \
  --base-url https://github.com/codella/archpilot/releases/download/v0.1.0
```

Produces `dist/v0.1.0/install.sh`, the wheel, and `SHA256SUMS`. The wheel checksum is embedded in `install.sh`. Do not edit or replace the wheel afterward without regenerating the installer.

The GitHub Actions release workflow runs tests, verifies the tag matches `pyproject.toml`, builds artifacts and publishes a release when you push a `v*` tag. It derives the repository URL automatically. Once this source is committed to the GitHub repository:

```sh
git tag v0.1.0
git push origin v0.1.0
```

Use new version tags for subsequent releases. Test the bootstrap in a disposable Arch VM before treating it as production-ready. Local tests mock system installation commands; they do not upgrade the host or install packages as root.

## Test in a VM before publishing

Use a disposable **x86_64 VM with UEFI firmware**, a suggested 4 GiB RAM and a new 40 GiB virtual disk. Download the official Arch ISO from https://archlinux.org/download/ and attach it as the boot CD. Use NAT networking. The current prototype does not install a bootable OS; this tests bootstrap, login, discovery and planning.

### Set up Virtual Machine Manager on an Arch Linux host

Run these commands on your **host**, before booting the VM:

```sh
sudo pacman -Syu --needed qemu-desktop virt-manager libvirt edk2-ovmf dnsmasq
sudo systemctl enable --now libvirtd.socket
virt-manager
```

Use the QEMU/KVM system connection. Arch documents `libvirtd.socket` for this connection in the [virt-manager guide](https://wiki.archlinux.org/title/Virt-manager).

### Prepare the Archpilot test disc

From the project root on your host, build the release (if you have not already), then create a separate, non-bootable data disc:

```sh
.venv/bin/python scripts/build_release.py \
  --base-url https://github.com/codella/archpilot/releases/download/v0.1.0
.venv/bin/python -m pip install pycdlib
.venv/bin/python scripts/build_vm_iso.py dist/v0.1.0
```

`pycdlib` is only needed to build this test disc, not to run Archpilot. These commands create local artifacts and do not publish anything to GitHub.

### Create and boot the VM

1. In Virtual Machine Manager, create a new VM using **Local install media** and select the [official Arch Linux ISO](https://archlinux.org/download/).
2. Allocate **4096 MiB memory**, **2 CPUs**, and a **new 40 GiB virtual disk**. Use the **default NAT network**.
3. Select **Customize configuration before install**.
4. In the VM overview, select **UEFI firmware without Secure Boot**.
5. Choose **Add Hardware → Storage**, select `dist/archpilot-test.iso`, and set its device type to **CD-ROM**. This is the second CD/DVD drive; keep the official Arch ISO attached as the boot disc.
6. Start the VM and boot the official Arch installation medium.

### Run Archpilot inside the VM

In the VM's Arch live shell, run:

```sh
mkdir -p /run/archpilot-release
mount -o ro /dev/disk/by-label/ARCHPILOT /run/archpilot-release
bash /run/archpilot-release/install.sh --release-dir /run/archpilot-release
```

The local-release path still verifies the wheel checksum and exercises the real virtual-environment install and launcher creation. It skips the GitHub download, so it does not validate the eventual public URL. Internet is still required for Python dependencies and Codex. `demo` uses fictional hardware; `inventory` and `chat` discover the VM hardware.

The bootstrap opens Archpilot automatically. For separate diagnostics afterward, use `archpilot demo` or `archpilot inventory`. In chat, check `/disks`, select the virtual disk's actual path, set preferences, then `/plan`. No disk is formatted. After testing, run `archpilot logout` and power off the VM. Keep only disposable virtual disks attached; no host disk passthrough is needed. On Apple Silicon, this release requires x86_64 emulation rather than an ARM guest.

The default user flow is one command: `archpilot`. The explicit `login`, `status`, `logout`, `chat`, `inventory` and `demo` subcommands remain available for diagnostics and development.
