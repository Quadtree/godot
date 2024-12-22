# Mono WASM
This branch provides highly experimental support for running C# on Godot 4 web exports. It does this by compiling Godot to LLVM bitcode, and then statically linking it to the `dotnet.js` WASM version of .NET.

This version is very hacky. A final version would have to be cleaned up and made to work with Godot's usual export system. This version also breaks non-Mono WASM builds, and that would have to be fixed before it could be merged.

While it does work, there are a few caveats:
- Exporting is currently done via the `tmp_wasm_mono_exporter/tmp_exporter.py` script rather than through the proper in-editor export mechanism
- For the linking to work, the version of Emscripten that is used to compile Godot and the version of Emscripten that .NET Core uses have to be the same. .NET Core 9 uses Emscripten `3.1.56`. This means that to get this to work, we have to relax the rule where `4.4` requires Emscripten `3.1.62`. I _think_ that this rule is only needed for GDExtensions, and at the moment GDExtensions do not work with Mono WASM anyway, so we can probably safely relax this rule specifically for the Mono WASM builds. The other problem this raises is that if Godot is going to support multiple versions of .NET Core, we will have to ship multiple versions of the compiled Godot bitcode, since again Emscripten does not guarantee any cross-version ABI stability.
- AOT compilation doesn't work, because AOT is dependent on code trimming, which causes issues
- This is not a threaded build, but it seems to be possible to create threads in .NET anyway. This seems to have unpredictable results.

### Code Issues
There are some very odd code issues. For example, assume that `thing` is of type `Thing` that is a Godot Node:

```C#
// throws InvalidCastException
var duplicate = (Thing)thing.Duplicate();

// works
var tmp = thing.Duplicate();
var tmp2 = $"{tmp}";
var duplicate = (Thing)tmp;
```

Even though the "tmp2" line is in theory a no-op, it casues this to work. This is not the case on desktop. However, honestly, there were quirks like this back in Godot 3 so I'm not sure this is a showstopper.

## Use
- Check out this branch somewhere. Currently, the path to the Godot source tree must not have any spaces in it. This is a temporary problem due to how the temporary export script works
- Make sure you have .NET SDK 9.0 installed, and `wasm-tools` installed by running `dotnet workload install wasm-tools`
- Build the desktop version of Godot, .NET edition using the normal .NET build process
- If you are _not_ on Windows, alter the `tmp_wasm_mono_exporter/tmp_exporter.py` `godot.windows.editor.x86_64.mono.exe` lines to the name of the desktop executable on your platform
- Build the WASM version of Godot, making sure that `module_mono_enabled=yes` and you are building using Emscripten `3.1.56`
- Open your Godot project in the editor. Ensure that it has a Web export configuration, named "Web"
- Run the `tmp_wasm_mono_exporter/tmp_exporter.py` script with a single argument pointing at your Godot project
- If there are no errors, visit the app by going to http://localhost:8080/

## Further Development
With more work, some of the problems with this approach could be fixed, but some are pretty hard limits:
- The Emscripten versioning issue is going to be pretty hard to fix. `wasm-tools` does a lot of magical stuff behind the secnes, so it'd be hard to replicate with our own code, and it'd be hard to maintain, too. Most Emscripten ABI breaks between versions that I've seen aren't that large, and there might be other workarounds, too. It's worth noting that this is going to be a problem with a lot of approaches to getting .NET to work on web, since actually recompiling .NET to work with our Emscripten version will be tricky.
- Switching over to using Godot's standard exporting setup should be pretty easy.
- I suspect that the AOT issue can be fixed, but I don't know how hard it will be.
