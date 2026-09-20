#!/usr/bin/env python3
"""Create a non-bootable release data disc; requires pycdlib (build-time only)."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release_dir', type=Path)
    parser.add_argument('--output', type=Path, default=Path('dist/archpilot-test.iso'))
    args = parser.parse_args()
    import pycdlib
    files = [args.release_dir / 'install.sh', args.release_dir / 'SHA256SUMS']
    wheels = list(args.release_dir.glob('archpilot-*.whl'))
    if len(wheels) != 1:
        parser.error('Release directory must contain exactly one Archpilot wheel.')
    files.extend(wheels)
    if not all(path.is_file() for path in files):
        parser.error('Build the release first; installer or checksums missing.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, vol_ident='ARCHPILOT', rock_ridge='1.09', joliet=3)
    try:
        for index, path in enumerate(files):
            iso.add_file(str(path), iso_path=f'/FILE{index:03}.DAT;1', rr_name=path.name, joliet_path='/' + path.name)
        iso.write(str(args.output))
    finally:
        iso.close()
    print(f'Attach {args.output} as a SECOND CD/DVD drive alongside the Arch boot ISO.')


if __name__ == '__main__':
    main()
