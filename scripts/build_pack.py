"""Build with the original 18-font resource layout, in an isolated directory."""
import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from verify_pack import ROOT, read_pack, verify

BUILDER_COMMIT = 'b0c05f6f9185ded7d9d50d6df91caf506e7ae792'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--builder', type=Path, required=True,
                        help='Local clone of Pyxzure/pebble-lang-gen at the documented commit')
    args = parser.parse_args()
    builder = args.builder.resolve()
    revision = subprocess.check_output(['git', '-C', str(builder), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != BUILDER_COMMIT:
        parser.error(f'Builder must be at {BUILDER_COMMIT}; see README.md')
    if subprocess.check_output(['git', '-C', str(builder), 'diff', 'HEAD', '--', 'build.py', 'utils'], text=True).strip():
        parser.error('Builder source has local changes; use an unmodified checkout')
    baseline = ROOT / 'pebble-EN-RU-HE.pbl'
    metadata = read_pack(baseline, builder)[0]
    output = ROOT / 'pebble-EN-RU-HE-symbols.pbl'
    with tempfile.TemporaryDirectory(prefix='pebble-fonts-') as temporary:
        work = Path(temporary)
        shutil.copy(builder / 'build.py', work)
        shutil.copytree(builder / 'utils', work / 'utils')
        shutil.copytree(ROOT / 'lang', work / 'lang')
        shutil.copytree(ROOT / 'ttf', work / 'ttf')
        (work / 'translation').mkdir()
        (work / 'translation' / '000').write_bytes(metadata)
        subprocess.run([sys.executable, 'build.py'], cwd=work, check=True)
        built = work / 'build' / 'langpack.pbl'
        verify(built, builder, baseline)
        shutil.copy(built, output)
    print(f'Output: {output}')
    print(f'SHA-256: {hashlib.sha256(output.read_bytes()).hexdigest()}')


if __name__ == '__main__':
    main()
