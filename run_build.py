#!/usr/bin/env python3

import argparse
import subprocess
import os
import json
import random
import datetime
import re
import platform
import multiprocessing
import version
import shutil
from typing import Union

if not os.getenv('MSYSTEM'):
    NICE_LOCATION = "C:/cygwin64/bin/nice.exe"
    PYTHON_LOCATION = "C:/Users/quadtree/AppData/Local/Programs/Python/Python313/python.exe"
    SCONS_LOCATION = "C:/Users/quadtree/AppData/Local/Programs/Python/Python313/Scripts/scons.exe"
else:
    print('Running in MSYS2 mode')
    NICE_LOCATION = "nice"
    PYTHON_LOCATION = "python"
    SCONS_LOCATION = "C:/msys64/mingw64/bin/scons.exe"

if '-WSL2-' in platform.platform():
    print('run_build.py was called in WSL mode')
    NICE_LOCATION = subprocess.run(['wslpath', NICE_LOCATION], capture_output=True, check=True).stdout.decode('utf8').strip()

if 'CYGWIN_NT-' in platform.platform():
    print('run_build.py was called in Cygwin mode')
    NICE_LOCATION = subprocess.run(['cygpath', NICE_LOCATION], capture_output=True, check=True).stdout.decode('utf8').strip()

print(f'{NICE_LOCATION=} {PYTHON_LOCATION=} {SCONS_LOCATION=}')

parser = argparse.ArgumentParser()
parser.add_argument('--rebuild-mono-glue', '-r', action="store_true")
parser.add_argument('--no-change-version', action="store_true")
parser.add_argument('--run', action="store_true")
parser.add_argument('--debug-symbols', action="store_true")
parser.add_argument('--templates', action="store_true")
parser.add_argument('--install-templates', action="store_true")
parser.add_argument('--no-main-build', action="store_true")
parser.add_argument('--disable-lto', action="store_true")
parser.add_argument('--clean', action="store_true")
parser.add_argument('--wasm', action="store_true")
parser.add_argument('--verbose', action="store_true")
args = parser.parse_args()

#lto_enabled = not args.disable_lto
lto_enabled = False

def to_yes_no(val:bool):
    if val:
        return 'yes'
    else:
        return 'no'

def run_clean():
    cmd_args = [NICE_LOCATION, PYTHON_LOCATION, SCONS_LOCATION, '--clean']

    if args.wasm:
        cmd_args += ['platform=web']

    print(f'{cmd_args=}')
    subprocess.run(cmd_args, check=True)

def run_build(use_mono_glue:bool = False, debug_symbols:bool = False, target:Union[str, None] = None, tools:bool = False, arch:Union[str, None] = None, lto:bool = True):
    platform = "windows"
    threads = True
    module_mono_enabled = True
    module_regex_enabled = True

    if args.wasm:
        platform = "web"
        lto = False
        threads = False
        module_mono_enabled = True
        module_regex_enabled = True

    cli_args = [PYTHON_LOCATION, SCONS_LOCATION, 'lto=' + ('full' if lto else 'none'),
        f'platform={platform}',
        f'tools={to_yes_no(tools)}',
        f'module_mono_enabled={to_yes_no(module_mono_enabled)}',
        f'module_regex_enabled={to_yes_no(module_regex_enabled)}',
        f'verbose={to_yes_no(args.verbose)}',
        f'threads={to_yes_no(threads)}'
    ]

    if os.getenv('MSYSTEM') == 'MINGW64': cli_args += ['use_mingw=yes']

    if debug_symbols:
        cli_args += ['debug_symbols=yes', 'seperate_debug_symbols=yes']
    elif target is None:
        cli_args += ['production=yes']

    cli_args += [f'mono_glue={"yes" if use_mono_glue else "no"}']
    if arch is not None: cli_args += [f'arch={arch}']

    if target is not None: cli_args += [f'target={target}']

    print(f'{cli_args=}')

    subprocess.run(cli_args, check=True)

def build_mono_glue():
    subprocess.run([NICE_LOCATION, "bin/godot.windows.editor.x86_64.mono.exe", '--generate-mono-glue', 'modules/mono/glue'], check=True)

def build_mono_assemblies():
    subprocess.run([NICE_LOCATION, PYTHON_LOCATION, 'modules/mono/build_scripts/build_assemblies.py', '--godot-output-dir=bin', '--push-nupkgs-local', "C:/Users/quadtree/Documents/SDK/Generic/godot_nuget"])

def change_version_py():
    with open('version.py') as f:
        old_lines = list(f)

    with open('version.py', 'w') as f:
        for line in old_lines:
            if 'status = ' in line:
                f.write(f'''status = {json.dumps(f"c{str(re.sub(r'[^0-9]', '', datetime.datetime.now().isoformat(timespec='seconds')))}")}\n''')
            else:
                f.write(line)

if args.clean:
    run_clean()

if not args.no_main_build:
    if not args.wasm:
        try:
            os.remove("bin/godot.windows.editor.x86_64.mono.exe")
        except FileNotFoundError: pass

    if args.rebuild_mono_glue:
        if not args.no_change_version: change_version_py()
        run_build(
            use_mono_glue=False,
            debug_symbols=args.debug_symbols,
            tools=True,
            lto=lto_enabled
        )
        build_mono_glue()
        build_mono_assemblies()

    run_build(
        use_mono_glue=True,
        debug_symbols=args.debug_symbols,
        tools=True,
        lto=lto_enabled
    )

if args.templates:
    #run_build(True, False, "template_debug", False, arch="x86_32")
    #run_build(True, False, "template_release", False, arch="x86_32")
    run_build(use_mono_glue=True, target="template_debug", lto=lto_enabled)
    run_build(use_mono_glue=True, target="template_release", lto=lto_enabled)

if args.install_templates:
    initial_dirname = f'{os.getenv("HOMEDRIVE")}{os.getenv("HOMEPATH")}/AppData/Roaming/Godot/export_templates/{version.major}.{version.minor}.{version.patch}.stable.mono'

    template_install_target = initial_dirname
    print(f'{template_install_target=}')

    if not os.path.exists(template_install_target):
        os.mkdir(template_install_target)

    TO_COPY = [
        ('debug', '64'),
        ('release', '64'),
    ]

    for (build_type, bits) in TO_COPY:
        source_file = f'bin/godot.windows.template_{build_type}.x86_{bits}.mono.exe'
        dest_file = os.path.join(template_install_target, f'windows_{build_type}_x86_{bits}.exe')

        print(f'{source_file=} {dest_file=}')

        shutil.copy(source_file, dest_file)


if args.run:
    subprocess.Popen(['bin/godot.windows.editor.x86_64.mono.exe']).wait()
