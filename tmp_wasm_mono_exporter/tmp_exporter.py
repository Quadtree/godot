import argparse
import os
import shutil
import subprocess
import json

parser = argparse.ArgumentParser()
parser.add_argument("project_root")
parser.add_argument('--build', type=int, default=1)
parser.add_argument('--deploy')
parser.add_argument('--stage-first', action="store_true")
parser.add_argument('--debug-template', type=int, default=-1, help="If 0, use the release template. If 1, use the debug template. Currently because we always use the debug C#, the release template will not work.")
args = parser.parse_args()

TMP_ROOT_DIR = '/tmp'
tmp_env_var = os.getenv('TEMP')
if tmp_env_var is not None: TMP_ROOT_DIR = tmp_env_var

TMP_DIR = TMP_ROOT_DIR + '/tmp_exporter_dir'
TMP_DIR_2 = TMP_ROOT_DIR + '/tmp_exporter_dir_2'
FAKE_TEMPLATE_DIR = os.path.join(os.path.realpath(os.path.dirname(__file__)), 'fake_template').replace('\\', '/')
GODOT_ROOT = os.path.join(os.path.realpath(os.path.dirname(__file__)), '..').replace('\\', '/')
PROJECT_ROOT = os.path.realpath(args.project_root).replace('\\', '/')

if args.stage_first:
    has_csproj = False
    has_sln = False

    STAGE_DIR = TMP_ROOT_DIR + '/tmp_stage_dir'
    os.makedirs(STAGE_DIR, exist_ok=True)
    for ff in os.scandir(PROJECT_ROOT):
        if ff.name == '.godot' or ff.name == 'export_presets.cfg': continue

        if ff.name.lower().endswith('.csproj'): has_csproj = True
        if ff.name.lower().endswith('.sln'): has_sln = True

        stage_loc = os.path.join(STAGE_DIR, ff.name)

        if '.csproj' in ff.name or '.sln' in ff.name:
            print(f'Staging {ff} to {stage_loc} via copy', flush=True)
            shutil.copy(ff, stage_loc)
        else:
            print(f'Staging {ff} to {stage_loc} via symlink', flush=True)
            os.symlink(ff, stage_loc)

    if not has_csproj or not has_sln: raise Exception("One or more project files (.sln and .csproj) are missing. Open the project in the Godot editor, go to Project -> Tools -> C# -> Create C# solution")

    shutil.copy('/usr/local/etc/export_presets.cfg', os.path.join(STAGE_DIR, 'export_presets.cfg'))

    PROJECT_ROOT = STAGE_DIR


if args.debug_template == -1:
    if not args.deploy:
        debug_template = 1
    else:
        debug_template = 0

BUILD_NAME = 'template_debug' if debug_template else 'template_release'

for fn in os.scandir(PROJECT_ROOT):
    if os.path.isfile(fn) and fn.name.endswith(".godot"):
        with open(fn) as f:
            for line in f:
                if line.startswith("config/name"):
                    PROJECT_NAME = json.loads(line.split('=')[-1])
                    break

if not PROJECT_NAME: raise Exception()

print(f'{TMP_DIR=} {TMP_DIR_2=} {FAKE_TEMPLATE_DIR=} {GODOT_ROOT=} {PROJECT_ROOT=} {PROJECT_NAME=} {debug_template=}')

if args.build == 1:
    shutil.rmtree(TMP_DIR, ignore_errors=True)

def copy_file_with_substitutions(ffn:str):
    ffn = ffn.replace('\\', '/')

    ffn_stub = ffn.replace(FAKE_TEMPLATE_DIR.replace('\\', '/'), '')

    ffn_out = TMP_DIR + ffn_stub

    print(f'{ffn=} {ffn_stub=} {ffn_out=}')

    os.makedirs(os.path.dirname(ffn_out), exist_ok=True)

    if ffn.endswith('.png'):
        shutil.copy(ffn, ffn_out)
    else:
        with open(ffn, 'r') as f_in:
            with open(ffn_out, 'w') as f_out:
                for line in f_in:
                    line = line.replace('$GODOT_ROOT', GODOT_ROOT)
                    line = line.replace('$PROJECT_ROOT', PROJECT_ROOT)
                    line = line.replace('$PROJECT_NAME', PROJECT_NAME)
                    line = line.replace('$BUILD_NAME', BUILD_NAME)

                    f_out.write(f'{line}')

def copy_files_with_substitutions(dd:str):
    for f in os.scandir(dd):
        ffn = os.path.join(dd, f)

        print(f'{ffn=}')

        if os.path.isdir(ffn):
            copy_files_with_substitutions(ffn)
        else:
            copy_file_with_substitutions(ffn)

copy_files_with_substitutions(FAKE_TEMPLATE_DIR)

os.makedirs(f'{TMP_DIR}/wwwroot/_framework', exist_ok=True)
shutil.copy('platform/web/js/libs/audio.worklet.js', f'{TMP_DIR}/wwwroot/_framework/godot.audio.worklet.js')
shutil.copy('platform/web/js/libs/audio.position.worklet.js', f'{TMP_DIR}/wwwroot/_framework/godot.audio.position.worklet.js')

if args.build == 1:
    with open(f'{PROJECT_ROOT}/_DummyClassToPreventUnexpectedTrimming.cs', 'w') as f: f.write('public class _DummyClassToPreventUnexpectedTrimming {}\n')

    subprocess.run([f'{GODOT_ROOT}/bin/godot.linuxbsd.editor.x86_64.mono', '--headless', '--export-pack', f'Web', f'{TMP_DIR}/wwwroot/index.pck'], cwd=PROJECT_ROOT, check=True)
    print('BUILD SOLUTIONS', flush=True)
    subprocess.run([f'{GODOT_ROOT}/bin/godot.linuxbsd.editor.x86_64.mono', '--headless', '--build-solutions', '--quit'], cwd=PROJECT_ROOT, check=True)

subprocess.run(['ls', '-la', f'{PROJECT_ROOT}/.godot/mono/temp/bin/Debug'], check=True)
subprocess.run(['cat', f'{TMP_DIR}/web.csproj'])

if not args.deploy:
    subprocess.run(['dotnet', 'run', '--project', f'{TMP_DIR}/web.csproj'], check=True)
else:
    print(f'DELETE {TMP_DIR_2}')
    shutil.rmtree(TMP_DIR_2, ignore_errors=True)

    os.makedirs(TMP_DIR_2)

    subprocess.run(['dotnet', 'publish', '-o', TMP_DIR_2, f'{TMP_DIR}/web.csproj'], check=True)

    print(f'COPY {TMP_DIR_2}/wwwroot TO {args.deploy}')
    shutil.copytree(f'{TMP_DIR_2}/wwwroot', args.deploy, dirs_exist_ok=True)
