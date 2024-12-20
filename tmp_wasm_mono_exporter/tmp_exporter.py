import argparse
import os
import shutil
import subprocess
import json

parser = argparse.ArgumentParser()
parser.add_argument("project_root")
parser.add_argument('--build', type=int, default=1)
parser.add_argument('--deploy')
args = parser.parse_args()

TMP_DIR = 'C:/tmp/tmp_exporter_dir'
FAKE_TEMPLATE_DIR = os.path.join(os.path.realpath(os.path.dirname(__file__)), 'fake_template').replace('\\', '/')
GODOT_ROOT = os.path.join(os.path.realpath(os.path.dirname(__file__)), '..').replace('\\', '/')
PROJECT_ROOT = os.path.realpath(args.project_root).replace('\\', '/')

for fn in os.scandir(PROJECT_ROOT):
    if os.path.isfile(fn) and fn.name.endswith(".godot"):
        with open(fn) as f:
            for line in f:
                if line.startswith("config/name"):
                    PROJECT_NAME = json.loads(line.split('=')[-1])
                    break

if not PROJECT_NAME: raise Exception()

print(f'{TMP_DIR=} {FAKE_TEMPLATE_DIR=} {GODOT_ROOT=} {PROJECT_ROOT=} {PROJECT_NAME=}')

if args.build == 1:
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)

def copy_file_with_substitutions(ffn:str):
    ffn = ffn.replace('\\', '/')

    ffn_stub = ffn.replace(FAKE_TEMPLATE_DIR.replace('\\', '/'), '')

    ffn_out = TMP_DIR + ffn_stub

    print(f'{ffn=} {ffn_stub=} {ffn_out=}')

    if ffn.endswith('.png'):
        shutil.copy(ffn, ffn_out)
    else:
        with open(ffn, 'r') as f_in:
            os.makedirs(os.path.dirname(ffn_out), exist_ok=True)
            with open(ffn_out, 'w') as f_out:
                for line in f_in:
                    line = line.replace('$GODOT_ROOT', GODOT_ROOT)
                    line = line.replace('$PROJECT_ROOT', PROJECT_ROOT)
                    line = line.replace('$PROJECT_NAME', PROJECT_NAME)

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

if args.build == 1:
    subprocess.run([f'{GODOT_ROOT}/bin/godot.windows.editor.x86_64.mono.exe', '--export-pack', f'Web', f'{TMP_DIR}/wwwroot/index.pck'], cwd=PROJECT_ROOT, check=True)
    subprocess.run([f'{GODOT_ROOT}/bin/godot.windows.editor.x86_64.mono.exe', '--build-solutions', '--quit'], cwd=PROJECT_ROOT, check=True)

if not args.deploy:
    subprocess.run(['dotnet', 'run', '--project', f'{TMP_DIR}/web.csproj'], check=True)
else:
    subprocess.run(['dotnet', 'build', f'{TMP_DIR}/web.csproj'], check=True)
    shutil.copytree(f'{TMP_DIR}/wwwroot', args.deploy, dirs_exist_ok=True)
    shutil.copytree(f'{TMP_DIR}/bin/Debug/net9.0/wwwroot/_framework', f'{args.deploy}/_framework', dirs_exist_ok=True)

    #subprocess.run(['dotnet', 'publish', '-o', args.deploy, f'{TMP_DIR}/web.csproj'], check=True)