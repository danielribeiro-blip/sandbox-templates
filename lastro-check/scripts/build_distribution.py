"""Build a client ZIP and wheel from an isolated, allowlisted and scanned stage."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lastro import __version__
from lastro.runtime.distribution import assert_distribution_safe


def stage_source(root: Path, stage: Path) -> None:
    stage.mkdir(parents=True, exist_ok=False)
    for name in ('lastro', 'examples', 'scripts', 'README.md', 'pyproject.toml'):
        source = root / name
        if not source.exists():
            raise FileNotFoundError(source)
        if source.is_symlink() or (source.is_dir() and any(p.is_symlink() for p in source.rglob('*'))):
            raise ValueError('symlink in selected distribution source')
        if source.is_dir():
            shutil.copytree(source, stage / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            shutil.copy2(source, stage / name)
    assert_distribution_safe(stage)


def build(root: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError('release directory already exists')
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / 'source'
        stage_source(root, stage)
        wheels = Path(tmp) / 'wheels'
        # Setuptools runs only against the inspected stage, never the mutable worktree.
        subprocess.run([sys.executable, '-c', 'import setuptools.build_meta,sys; setuptools.build_meta.build_wheel(sys.argv[1])', str(wheels)], cwd=stage, check=True, stdout=subprocess.PIPE)
        wheel = next(wheels.glob('*.whl'))
        inspect = Path(tmp) / 'wheel-inspection'
        with ZipFile(wheel) as z:
            z.extractall(inspect)
        assert_distribution_safe(inspect)
        # Remove build intermediates before a second scan and ZIP creation.
        shutil.rmtree(stage / 'build', ignore_errors=True)
        for metadata in stage.glob('*.egg-info'):
            shutil.rmtree(metadata)
        assert_distribution_safe(stage)
        output.mkdir(parents=True, exist_ok=False)
        archive = output / f'lastro-commercial-v{__version__}.zip'
        with ZipFile(archive, 'x', ZIP_DEFLATED) as z:
            for path in sorted(stage.rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                    z.write(path, f'lastro-commercial-v{__version__}/' + path.relative_to(stage).as_posix())
        shutil.copy2(wheel, output / wheel.name)
        manifest = {'engine_version': __version__, 'artifacts': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())}}
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(ROOT, args.out), indent=2))
