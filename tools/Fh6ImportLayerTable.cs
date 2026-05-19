using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;

internal static class Fh6ImportLayerTable
{
    private const uint PROCESS_VM_READ = 0x0010;
    private const uint PROCESS_VM_WRITE = 0x0020;
    private const uint PROCESS_VM_OPERATION = 0x0008;
    private const uint PROCESS_QUERY_INFORMATION = 0x0400;
    private const uint PROCESS_QUERY_LIMITED_INFORMATION = 0x1000;

    private const uint MEM_COMMIT = 0x1000;
    private const uint MEM_PRIVATE = 0x20000;

    private const uint PAGE_NOACCESS = 0x01;
    private const uint PAGE_READONLY = 0x02;
    private const uint PAGE_READWRITE = 0x04;
    private const uint PAGE_WRITECOPY = 0x08;
    private const uint PAGE_EXECUTE_READ = 0x20;
    private const uint PAGE_EXECUTE_READWRITE = 0x40;
    private const uint PAGE_EXECUTE_WRITECOPY = 0x80;
    private const uint PAGE_GUARD = 0x100;

    private const ulong GroupCountOffset = 0x5A;
    private const ulong GroupTableOffset = 0x78;

    private const ulong LayerPosOffset = 0x18;
    private const ulong LayerScaleOffset = 0x28;
    private const ulong LayerRotationOffset = 0x50;
    private const ulong LayerColorOffset = 0x74;
    private const ulong LayerMaskOffset = 0x78;
    private const ulong LayerShapeIdOffset = 0x7A;

    private const byte ShapeIdOther = 101;
    private const byte ShapeIdEllipse = 102;

    private const int ChunkSize = 4 * 1024 * 1024;

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr OpenProcess(uint access, bool inheritHandle, int processId);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool CloseHandle(IntPtr handle);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool ReadProcessMemory(IntPtr process, IntPtr address, byte[] buffer, UIntPtr size, out UIntPtr read);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool WriteProcessMemory(IntPtr process, IntPtr address, byte[] buffer, UIntPtr size, out UIntPtr written);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern UIntPtr VirtualQueryEx(IntPtr process, IntPtr address, out MEMORY_BASIC_INFORMATION64 buffer, UIntPtr length);

    [StructLayout(LayoutKind.Sequential)]
    private struct MEMORY_BASIC_INFORMATION64
    {
        public ulong BaseAddress;
        public ulong AllocationBase;
        public uint AllocationProtect;
        public uint __alignment1;
        public ulong RegionSize;
        public uint State;
        public uint Protect;
        public uint Type;
        public uint __alignment2;
    }

    private sealed class Region
    {
        public ulong Base;
        public ulong Size;
        public uint Protect;
        public uint Type;
    }

    private sealed class Shape
    {
        public int Type;
        public readonly List<double> Data = new List<double>();
        public readonly List<int> Color = new List<int>();
    }

    private sealed class Options
    {
        public string JsonPath = "";
        public int LayerCount = 3000;
        public bool Reverse;
        public bool DryRun;
        public bool IncludeHeader;
        public bool NoCache;
        public double ScaleDivisor = 63.0;
        public double CoordinateScale = 1.0;
        public int MaxCandidates = 200000;
    }

    private static int Main(string[] args)
    {
        try
        {
            var options = ParseArgs(args);
            if (options == null)
                return 2;

            var allShapes = LoadShapes(options.JsonPath);
            if (allShapes.Count == 0)
                throw new InvalidOperationException("No shapes found in JSON.");

            var canvas = FindCanvas(allShapes);
            var shapes = BuildImportShapeList(allShapes, options.IncludeHeader);
            if (shapes.Count == 0)
                throw new InvalidOperationException("No importable shapes found after metadata/header filtering.");

            var process = FindForzaProcess();
            Console.WriteLine("PID=" + process.Id + " JSON shapes=" + shapes.Count + " template layers=" + options.LayerCount);
            Console.WriteLine(string.Format(CultureInfo.InvariantCulture,
                "canvas={0:0.###}x{1:0.###} scaleDiv={2:0.###} coordScale={3:0.###} order={4} dryRun={5}",
                canvas.Item1, canvas.Item2, options.ScaleDivisor, options.CoordinateScale,
                options.Reverse ? "reverse" : "table", options.DryRun));

            var handle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION, false, process.Id);
            if (handle == IntPtr.Zero)
                throw new InvalidOperationException("OpenProcess failed. Win32=" + Marshal.GetLastWin32Error());

            try
            {
                var cachePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "fh6-layer-table.cache");
                var layerPointers = options.NoCache ? null : TryLoadCachedLayerPointers(handle, cachePath, process.Id, options.LayerCount);
                if (layerPointers == null)
                {
                    layerPointers = LocateLayerPointers(handle, options.LayerCount, options.MaxCandidates);
                    SaveCachedLayerPointers(cachePath, process.Id, options.LayerCount, layerPointers);
                }
                Console.WriteLine("LiveryGroup found. Valid layer pointers=" + layerPointers.Count);

                var n = Math.Min(shapes.Count, layerPointers.Count);
                if (options.DryRun)
                {
                    PrintPreview(layerPointers, shapes, canvas, options, Math.Min(n, 12));
                    Console.WriteLine("Dry run only; no writes performed.");
                    return 0;
                }

                var written = 0;
                for (var i = 0; i < n; i++)
                {
                    var shapeIndex = options.Reverse ? n - 1 - i : i;
                    var layerIndex = i;
                    var layerPtr = layerPointers[layerIndex];
                    if (ScoreLayer(handle, layerPtr) < 5)
                        continue;

                    WriteShape(handle, layerPtr, shapes[shapeIndex], canvas, options);
                    written++;
                    if (written <= 12 || written % 100 == 0)
                        Console.WriteLine("written " + written + "/" + n + " -> layerPtr=0x" + layerPtr.ToString("X", CultureInfo.InvariantCulture));
                }

                Console.WriteLine("DONE written=" + written + "/" + n);
                if (shapes.Count > layerPointers.Count)
                    Console.WriteLine("WARNING: JSON has more shapes than template layers. Remaining shapes were skipped.");
            }
            finally
            {
                CloseHandle(handle);
            }

            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("ERROR: " + ex.Message);
            return 1;
        }
    }

    private static Options ParseArgs(string[] args)
    {
        if (args.Length < 1)
        {
            Console.Error.WriteLine("Usage: Fh6ImportLayerTable.exe <json> [--layers=3000] [--dry-run] [--reverse] [--include-header] [--scale-div=63] [--coord-scale=1]");
            return null;
        }

        var o = new Options();
        o.JsonPath = args[0];
        for (var i = 1; i < args.Length; i++)
        {
            var arg = args[i];
            if (arg == "--dry-run") o.DryRun = true;
            else if (arg == "--reverse") o.Reverse = true;
            else if (arg == "--include-header") o.IncludeHeader = true;
            else if (arg == "--no-cache") o.NoCache = true;
            else if (arg.StartsWith("--layers=", StringComparison.OrdinalIgnoreCase)) o.LayerCount = int.Parse(arg.Substring(9), CultureInfo.InvariantCulture);
            else if (arg.StartsWith("--scale-div=", StringComparison.OrdinalIgnoreCase)) o.ScaleDivisor = double.Parse(arg.Substring(12), CultureInfo.InvariantCulture);
            else if (arg.StartsWith("--coord-scale=", StringComparison.OrdinalIgnoreCase)) o.CoordinateScale = double.Parse(arg.Substring(14), CultureInfo.InvariantCulture);
            else if (arg.StartsWith("--max-candidates=", StringComparison.OrdinalIgnoreCase)) o.MaxCandidates = int.Parse(arg.Substring(17), CultureInfo.InvariantCulture);
            else throw new ArgumentException("Unknown argument: " + arg);
        }
        return o;
    }

    private static Process FindForzaProcess()
    {
        var processes = Process.GetProcessesByName("forzahorizon6");
        if (processes.Length == 0)
            throw new InvalidOperationException("forzahorizon6.exe is not running.");
        return processes[0];
    }

    private static Tuple<double, double> FindCanvas(List<Shape> shapes)
    {
        foreach (var s in shapes)
        {
            if (IsHeaderShape(s))
                return Tuple.Create(s.Data[2], s.Data[3]);
        }
        if (shapes[0].Data.Count >= 4)
            return Tuple.Create(shapes[0].Data[2], shapes[0].Data[3]);
        throw new InvalidOperationException("Could not determine canvas size.");
    }

    private static bool IsHeaderShape(Shape s)
    {
        return s.Type == 1
            && s.Data.Count >= 4
            && Math.Abs(s.Data[0]) < 0.0001
            && Math.Abs(s.Data[1]) < 0.0001
            && s.Color.Count >= 4
            && s.Color[3] == 0;
    }

    private static List<Shape> BuildImportShapeList(List<Shape> allShapes, bool includeHeader)
    {
        var shapes = new List<Shape>();
        foreach (var s in allShapes)
        {
            if (!includeHeader && IsHeaderShape(s))
                continue;
            if (s.Data.Count >= 4)
                shapes.Add(s);
        }
        return shapes;
    }

    private static List<Shape> LoadShapes(string path)
    {
        var serializer = new JavaScriptSerializer();
        serializer.MaxJsonLength = int.MaxValue;
        var root = serializer.Deserialize<Dictionary<string, object>>(File.ReadAllText(path));
        var rawShapes = (ArrayList)root["shapes"];
        var shapes = new List<Shape>(rawShapes.Count);
        foreach (Dictionary<string, object> raw in rawShapes)
        {
            var shape = new Shape();
            if (raw.ContainsKey("type"))
                shape.Type = Convert.ToInt32(raw["type"], CultureInfo.InvariantCulture);
            foreach (var value in (ArrayList)raw["data"])
                shape.Data.Add(Convert.ToDouble(value, CultureInfo.InvariantCulture));
            if (raw.ContainsKey("color"))
                foreach (var value in (ArrayList)raw["color"])
                    shape.Color.Add(Convert.ToInt32(value, CultureInfo.InvariantCulture));
            shapes.Add(shape);
        }
        return shapes;
    }

    private static List<ulong> LocateLayerPointers(IntPtr handle, int layerCount, int maxCandidates)
    {
        var regions = EnumerateRegions(handle);
        regions.Sort(delegate(Region a, Region b) { return b.Size.CompareTo(a.Size); });
        Console.WriteLine("Scanning writable private regions=" + regions.Count);

        var patternLo = (byte)(layerCount & 0xFF);
        var patternHi = (byte)((layerCount >> 8) & 0xFF);
        var perfect = new List<Tuple<ulong, ulong>>();
        var candidates = 0;
        var totalBytes = 0UL;
        foreach (var region in regions)
            totalBytes += region.Size;
        var scannedBytes = 0UL;
        var lastProgress = DateTime.UtcNow;

        for (var rIndex = 0; rIndex < regions.Count; rIndex++)
        {
            var region = regions[rIndex];
            var offset = 0UL;
            while (offset < region.Size)
            {
                var toRead = (int)Math.Min((ulong)ChunkSize, region.Size - offset);
                var chunkBase = region.Base + offset;
                var data = TryRead(handle, chunkBase, toRead);
                if (data != null && data.Length >= 2)
                {
                    for (var pos = 0; pos < data.Length - 1; pos++)
                    {
                        if (data[pos] != patternLo || data[pos + 1] != patternHi)
                            continue;
                        candidates++;
                        if (candidates > maxCandidates)
                            return PickBestPerfect(handle, perfect, layerCount);

                        var countAddr = chunkBase + (ulong)pos;
                        if (countAddr < GroupCountOffset)
                            continue;
                        var groupAddr = countAddr - GroupCountOffset;
                        var tableAddr = ReadU64(handle, groupAddr + GroupTableOffset);
                        if (!IsUserPtr(tableAddr))
                            continue;

                        if (FirstSampleIsPerfect(handle, tableAddr, layerCount))
                            perfect.Add(Tuple.Create(groupAddr, tableAddr));
                    }
                }
                scannedBytes += (ulong)toRead;
                var now = DateTime.UtcNow;
                if ((now - lastProgress).TotalSeconds >= 2.0 || perfect.Count > 0)
                {
                    var pct = totalBytes == 0 ? 0.0 : scannedBytes * 100.0 / totalBytes;
                    Console.WriteLine(string.Format(CultureInfo.InvariantCulture,
                        "scan {0:0.0}% regions {1}/{2} candidates={3} perfect={4}",
                        pct, rIndex + 1, regions.Count, candidates, perfect.Count));
                    lastProgress = now;
                }
                offset += (ulong)toRead;
            }
        }

        return PickBestPerfect(handle, perfect, layerCount);
    }

    private static List<ulong> TryLoadCachedLayerPointers(IntPtr handle, string cachePath, int pid, int layerCount)
    {
        if (!File.Exists(cachePath))
        {
            Console.WriteLine("No layer cache yet; full scan needed once for this FH6/editor session.");
            return null;
        }

        try
        {
            var lines = File.ReadAllLines(cachePath);
            if (lines.Length < 2)
            {
                Console.WriteLine("Layer cache is incomplete; full scan needed.");
                return null;
            }
            var header = lines[0].Split('|');
            if (header.Length != 2)
            {
                Console.WriteLine("Layer cache header is invalid; full scan needed.");
                return null;
            }
            if (int.Parse(header[0], CultureInfo.InvariantCulture) != pid)
            {
                Console.WriteLine("Layer cache is from another FH6 process; full scan needed.");
                return null;
            }
            if (int.Parse(header[1], CultureInfo.InvariantCulture) != layerCount)
            {
                Console.WriteLine("Layer cache is for a different layer count; full scan needed.");
                return null;
            }

            var pointers = new List<ulong>(layerCount);
            for (var i = 1; i < lines.Length && pointers.Count < layerCount; i++)
                pointers.Add(ulong.Parse(lines[i], NumberStyles.HexNumber, CultureInfo.InvariantCulture));
            if (pointers.Count != layerCount)
            {
                Console.WriteLine("Layer cache pointer count does not match; full scan needed.");
                return null;
            }

            var valid = 0;
            foreach (var pointer in pointers)
                if (ScoreLayer(handle, pointer) >= 5)
                    valid++;

            if (valid < layerCount * 95 / 100)
            {
                Console.WriteLine("Layer cache no longer matches the active vinyl group (" + valid + "/" + layerCount + " valid); full scan needed.");
                return null;
            }

            Console.WriteLine("Using cached layer pointers valid=" + valid + "/" + layerCount);
            return pointers;
        }
        catch
        {
            Console.WriteLine("Layer cache could not be read; full scan needed.");
            return null;
        }
    }

    private static void SaveCachedLayerPointers(string cachePath, int pid, int layerCount, List<ulong> pointers)
    {
        using (var writer = new StreamWriter(cachePath, false))
        {
            writer.WriteLine(pid.ToString(CultureInfo.InvariantCulture) + "|" + layerCount.ToString(CultureInfo.InvariantCulture));
            foreach (var pointer in pointers)
                writer.WriteLine(pointer.ToString("X", CultureInfo.InvariantCulture));
        }
    }

    private static List<ulong> PickBestPerfect(IntPtr handle, List<Tuple<ulong, ulong>> perfect, int layerCount)
    {
        if (perfect.Count == 0)
            throw new InvalidOperationException("No confident LiveryGroup match. Open FH6 vinyl editor with a fresh ungrouped " + layerCount + "-sphere template.");

        var bestTable = 0UL;
        var bestValid = -1;
        foreach (var candidate in perfect)
        {
            var valid = CountValidLayers(handle, candidate.Item2, layerCount);
            Console.WriteLine("candidate group=0x" + candidate.Item1.ToString("X", CultureInfo.InvariantCulture)
                + " table=0x" + candidate.Item2.ToString("X", CultureInfo.InvariantCulture)
                + " valid=" + valid + "/" + layerCount);
            if (valid > bestValid)
            {
                bestValid = valid;
                bestTable = candidate.Item2;
            }
        }

        if (bestValid < layerCount * 95 / 100)
            throw new InvalidOperationException("Best LiveryGroup candidate only validated " + bestValid + "/" + layerCount + " layers; refusing unsafe write.");

        var pointers = new List<ulong>(layerCount);
        for (var i = 0; i < layerCount; i++)
            pointers.Add(ReadU64(handle, bestTable + (ulong)i * 8));
        return pointers;
    }

    private static bool FirstSampleIsPerfect(IntPtr handle, ulong tableAddr, int layerCount)
    {
        var sample = Math.Min(layerCount, 16);
        for (var i = 0; i < sample; i++)
        {
            var ptr = ReadU64(handle, tableAddr + (ulong)i * 8);
            if (ScoreLayer(handle, ptr) < 5)
                return false;
        }
        return true;
    }

    private static int CountValidLayers(IntPtr handle, ulong tableAddr, int layerCount)
    {
        var valid = 0;
        for (var i = 0; i < layerCount; i++)
        {
            var ptr = ReadU64(handle, tableAddr + (ulong)i * 8);
            if (ScoreLayer(handle, ptr) >= 5)
                valid++;
        }
        return valid;
    }

    private static int ScoreLayer(IntPtr handle, ulong layerPtr)
    {
        if (!IsUserPtr(layerPtr))
            return 0;
        var score = 0;
        var pos = Read2Floats(handle, layerPtr + LayerPosOffset);
        if (pos != null && IsFiniteInRange(pos.Item1, -8192f, 8192f) && IsFiniteInRange(pos.Item2, -8192f, 8192f))
            score++;
        var scale = Read2Floats(handle, layerPtr + LayerScaleOffset);
        if (scale != null && IsFiniteInRange(Math.Abs(scale.Item1), 0.00001f, 64f) && IsFiniteInRange(Math.Abs(scale.Item2), 0.00001f, 64f))
            score++;
        var color = TryRead(handle, layerPtr + LayerColorOffset, 4);
        if (color != null && color.Length == 4)
            score++;
        var shape = TryRead(handle, layerPtr + LayerShapeIdOffset, 1);
        if (shape != null && shape.Length == 1 && (shape[0] == ShapeIdOther || shape[0] == ShapeIdEllipse))
            score++;
        var mask = TryRead(handle, layerPtr + LayerMaskOffset, 1);
        if (mask != null && mask.Length == 1 && (mask[0] == 0 || mask[0] == 1))
            score++;
        return score;
    }

    private static bool IsFiniteInRange(float value, float min, float max)
    {
        return !float.IsNaN(value) && !float.IsInfinity(value) && value >= min && value <= max;
    }

    private static bool IsUserPtr(ulong value)
    {
        return value > 0x000001000000UL && value < 0x800000000000UL;
    }

    private static void WriteShape(IntPtr handle, ulong layerPtr, Shape shape, Tuple<double, double> canvas, Options options)
    {
        var x = (float)((shape.Data[0] - canvas.Item1 / 2.0) * options.CoordinateScale);
        var y = (float)((shape.Data[1] - canvas.Item2 / 2.0) * options.CoordinateScale);
        var sx = (float)(shape.Data[2] / options.ScaleDivisor);
        var sy = (float)(shape.Data[3] / options.ScaleDivisor);
        var angle = shape.Data.Count >= 5 ? (float)(shape.Data[4] % 360.0) : 0f;

        WriteBytes(handle, layerPtr + LayerPosOffset, PackFloat2(x, -y));
        WriteBytes(handle, layerPtr + LayerScaleOffset, PackFloat2(sx, sy));
        WriteBytes(handle, layerPtr + LayerRotationOffset, BitConverter.GetBytes((360f - angle) % 360f));
        WriteBytes(handle, layerPtr + LayerColorOffset, PackColor(shape));
        WriteBytes(handle, layerPtr + LayerShapeIdOffset, new[] { ShapeIdEllipse });
        WriteBytes(handle, layerPtr + LayerMaskOffset, new byte[] { 0 });
    }

    private static void PrintPreview(List<ulong> layerPointers, List<Shape> shapes, Tuple<double, double> canvas, Options options, int count)
    {
        for (var i = 0; i < count; i++)
        {
            var shapeIndex = options.Reverse ? Math.Min(shapes.Count, layerPointers.Count) - 1 - i : i;
            var shape = shapes[shapeIndex];
            var x = (shape.Data[0] - canvas.Item1 / 2.0) * options.CoordinateScale;
            var y = (shape.Data[1] - canvas.Item2 / 2.0) * options.CoordinateScale;
            var sx = shape.Data[2] / options.ScaleDivisor;
            var sy = shape.Data[3] / options.ScaleDivisor;
            Console.WriteLine(string.Format(CultureInfo.InvariantCulture,
                "#{0} shapeIndex={1} ptr=0x{2:X} x={3:0.###} y(write)={4:0.###} sx={5:0.###} sy={6:0.###}",
                i + 1, shapeIndex, layerPointers[i], x, -y, sx, sy));
        }
    }

    private static byte[] PackColor(Shape shape)
    {
        var r = shape.Color.Count > 0 ? shape.Color[0] : 255;
        var g = shape.Color.Count > 1 ? shape.Color[1] : 255;
        var b = shape.Color.Count > 2 ? shape.Color[2] : 255;
        return new[] { ClampByte(r), ClampByte(g), ClampByte(b), (byte)255 };
    }

    private static byte ClampByte(int value)
    {
        if (value < 0) return 0;
        if (value > 255) return 255;
        return (byte)value;
    }

    private static byte[] PackFloat2(float a, float b)
    {
        var bytes = new byte[8];
        Buffer.BlockCopy(BitConverter.GetBytes(a), 0, bytes, 0, 4);
        Buffer.BlockCopy(BitConverter.GetBytes(b), 0, bytes, 4, 4);
        return bytes;
    }

    private static void WriteBytes(IntPtr handle, ulong address, byte[] bytes)
    {
        UIntPtr written;
        if (!WriteProcessMemory(handle, new IntPtr(unchecked((long)address)), bytes, new UIntPtr((uint)bytes.Length), out written)
            || written.ToUInt64() != (ulong)bytes.Length)
            throw new InvalidOperationException("Write failed at 0x" + address.ToString("X", CultureInfo.InvariantCulture));
    }

    private static ulong ReadU64(IntPtr handle, ulong address)
    {
        var bytes = TryRead(handle, address, 8);
        if (bytes == null || bytes.Length != 8)
            return 0;
        return BitConverter.ToUInt64(bytes, 0);
    }

    private static Tuple<float, float> Read2Floats(IntPtr handle, ulong address)
    {
        var bytes = TryRead(handle, address, 8);
        if (bytes == null || bytes.Length != 8)
            return null;
        return Tuple.Create(BitConverter.ToSingle(bytes, 0), BitConverter.ToSingle(bytes, 4));
    }

    private static byte[] TryRead(IntPtr handle, ulong address, int size)
    {
        var buffer = new byte[size];
        UIntPtr read;
        if (!ReadProcessMemory(handle, new IntPtr(unchecked((long)address)), buffer, new UIntPtr((uint)size), out read) || read.ToUInt64() == 0)
            return null;
        if (read.ToUInt64() == (ulong)size)
            return buffer;
        var partial = new byte[read.ToUInt64()];
        Buffer.BlockCopy(buffer, 0, partial, 0, partial.Length);
        return partial;
    }

    private static List<Region> EnumerateRegions(IntPtr handle)
    {
        var regions = new List<Region>();
        var address = 0UL;
        var mbiSize = (uint)Marshal.SizeOf(typeof(MEMORY_BASIC_INFORMATION64));
        while (address < 0x7FFFFFFFFFFFUL)
        {
            MEMORY_BASIC_INFORMATION64 mbi;
            var result = VirtualQueryEx(handle, new IntPtr(unchecked((long)address)), out mbi, new UIntPtr(mbiSize));
            if (result == UIntPtr.Zero)
                break;

            if (mbi.State == MEM_COMMIT && mbi.Type == MEM_PRIVATE && IsReadable(mbi.Protect) && IsWritable(mbi.Protect))
            {
                regions.Add(new Region { Base = mbi.BaseAddress, Size = mbi.RegionSize, Protect = mbi.Protect, Type = mbi.Type });
            }

            var next = mbi.BaseAddress + mbi.RegionSize;
            if (next <= address)
                break;
            address = next;
        }
        return regions;
    }

    private static bool IsReadable(uint protect)
    {
        if ((protect & PAGE_GUARD) != 0 || (protect & PAGE_NOACCESS) != 0)
            return false;
        return (protect & (PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY)) != 0;
    }

    private static bool IsWritable(uint protect)
    {
        if ((protect & PAGE_GUARD) != 0 || (protect & PAGE_NOACCESS) != 0)
            return false;
        return (protect & (PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY)) != 0;
    }
}
