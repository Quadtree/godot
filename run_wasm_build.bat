cd ..
cd emsdk
"%USERPROFILE%/AppData/Local/Programs/Python/Python313/python.exe" emsdk.py activate 3.1.56
call emsdk_env.bat
cd ..
cd godot
"%USERPROFILE%/AppData/Local/Programs/Python/Python313/python.exe" ../godot_build_scripts/run_build.py --rebuild-mono-glue --wasm --templates
