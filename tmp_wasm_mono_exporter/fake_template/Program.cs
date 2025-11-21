using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.JavaScript;

[assembly: System.Runtime.Versioning.SupportedOSPlatform("browser")]

// this fulfills the need for a "Main" in C#. We never call it
Console.WriteLine("Virtual main called in C#. Normally this should not be needed");

public static unsafe partial class WebGlue
{
    [DllImport("godot.web.$BUILD_NAME.wasm32.nothreads.mono")]
    static extern void wasm_mono_entrypoint(int argc, void* argv);

    [JSExport]
    static unsafe IntPtr GetInitializeFromGameProjectPtr()
    {
        Console.WriteLine("GetInitializeFromGameProjectPtr");

        // the version of .NET on Linux seems to be very buggy
        // - We have to specifically reference a class from the game, or the entire thing will get trimmed
        //   preventing us from loading it at all
        // - Another bug makes GodotPlugins.Game.Main private even though it's defined as public. As a result
        //   we have to obtain it awkwardly via reflection.

        _DummyClassToPreventUnexpectedTrimming dummyClass = null;
        Console.WriteLine($"dummyClass={dummyClass}");

        var asm = typeof(Thing1).Assembly;
        Console.WriteLine($"asm={asm}");
        var clazz = asm.GetType("GodotPlugins.Game.Main");
        Console.WriteLine($"clazz={clazz}");
        var method = clazz.GetMethod("InitializeFromGameProject", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
        Console.WriteLine($"method={method}");

        delegate* unmanaged<IntPtr, IntPtr, IntPtr, int, Godot.NativeInterop.godot_bool> somePtr = (delegate* unmanaged<IntPtr, IntPtr, IntPtr, int, Godot.NativeInterop.godot_bool>)method.MethodHandle.GetFunctionPointer();
        return (IntPtr)somePtr;
    }

    [JSExport]
    static unsafe void CallMain(string[] args)
    {
        Console.WriteLine($"C# args={string.Join(',', args)}");

        byte[] charBuffer = new byte[args.Select(it => it.Length + 1).Sum()];

        fixed (byte* cb = charBuffer)
        {
            List<int> indices = new();
            int curIdx = 0;

            var ptrs = new byte*[args.Length];

            foreach (var it in args)
            {
                indices.Add(curIdx);
                foreach (char c in it)
                {
                    if (curIdx >= charBuffer.Length) throw new Exception();
                    cb[curIdx] = (byte)c;
                    ++curIdx;
                }

                if (curIdx >= charBuffer.Length) throw new Exception();
                cb[curIdx] = (byte)0;
                ++curIdx;

                for (var i = 0; i < indices.Count; ++i)
                {
                    ptrs[i] = cb + indices[i];
                }
            }

            fixed (byte** ptrsPtr = ptrs)
            {
                wasm_mono_entrypoint(args.Length, ptrsPtr);
            }
        }
    }

}