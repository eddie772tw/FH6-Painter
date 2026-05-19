using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Web.Script.Serialization;

internal static class Fh6PainterLauncher
{
    private static int Main(string[] args)
    {
        try
        {
            var root = AppDomain.CurrentDomain.BaseDirectory;
            var originalPainter = Path.Combine(root, "forza-painter.exe");
            var importer = Path.Combine(root, "tools", "Fh6ImportLayerTable.exe");

            if (args.Length == 0)
            {
                Console.Error.WriteLine("Drop PNG/JPG files here to generate JSON, or drop JSON files here to import into FH6.");
                Console.Error.WriteLine("FH6 JSON import requires the vinyl editor to be open with a fresh ungrouped template.");
                return 2;
            }

            var exitCode = 0;
            foreach (var path in args)
            {
                var layerCount = AskLayerCount(path);
                if (IsJson(path))
                {
                    if (!File.Exists(importer))
                        throw new FileNotFoundException("FH6 importer not found", importer);
                    Console.WriteLine("Using FH6 target template: " + layerCount + " layers");
                    exitCode = Run(importer, Quote(path) + " --layers=" + layerCount.ToString(CultureInfo.InvariantCulture));
                }
                else
                {
                    if (!File.Exists(originalPainter))
                        throw new FileNotFoundException("Original forza-painter.exe not found", originalPainter);
                    UpdateProfilesForLayerCount(root, layerCount);
                    exitCode = Run(originalPainter, Quote(path));
                }

                if (exitCode != 0)
                    return exitCode;
            }

            return exitCode;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("ERROR: " + ex.Message);
            Console.WriteLine("Press Enter to close...");
            Console.ReadLine();
            return 1;
        }
    }

    private static bool IsJson(string path)
    {
        return string.Equals(Path.GetExtension(path), ".json", StringComparison.OrdinalIgnoreCase);
    }

    private static int AskLayerCount(string path)
    {
        var detected = IsJson(path) ? PickTemplateLayerCount(path) : 2000;
        Console.WriteLine();
        Console.WriteLine("File: " + Path.GetFileName(path));
        if (IsJson(path))
            Console.WriteLine("Detected JSON recommendation: " + detected + " layers");
        Console.WriteLine("FH6 limits: front/rear bumper 1000, left/right/top up to 3000.");
        Console.Write("How many layers? [default " + detected + ", allowed 500-3000]: ");
        var input = Console.ReadLine();
        if (string.IsNullOrWhiteSpace(input))
            return detected;

        int value;
        if (!int.TryParse(input.Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out value))
            return detected;
        if (value < 500) value = 500;
        if (value > 3000) value = 3000;
        return value;
    }

    private static int PickTemplateLayerCount(string jsonPath)
    {
        var importableShapes = CountImportableShapes(jsonPath);
        if (importableShapes <= 1500) return 1500;
        if (importableShapes <= 2000) return 2000;
        return 3000;
    }

    private static int CountImportableShapes(string jsonPath)
    {
        var serializer = new JavaScriptSerializer();
        serializer.MaxJsonLength = int.MaxValue;
        var root = serializer.Deserialize<Dictionary<string, object>>(File.ReadAllText(jsonPath));
        var rawShapes = (ArrayList)root["shapes"];
        var count = 0;
        foreach (Dictionary<string, object> raw in rawShapes)
        {
            if (IsForzaPainterCanvasHeader(raw))
                continue;
            count++;
        }
        return count;
    }

    private static void UpdateProfilesForLayerCount(string root, int layerCount)
    {
        var settingsDir = Path.Combine(root, "settings");
        if (!Directory.Exists(settingsDir))
            return;

        var saveAt = BuildSaveAt(layerCount);
        foreach (var file in Directory.GetFiles(settingsDir, "*.ini"))
        {
            var text = File.ReadAllText(file);
            text = ReplaceSetting(text, "saveAt", saveAt);
            text = ReplaceSetting(text, "stopAt", layerCount.ToString(CultureInfo.InvariantCulture));
            File.WriteAllText(file, text);
        }
        Console.WriteLine("Updated generator profiles: stopAt=" + layerCount + ", saveAt=" + saveAt);
    }

    private static string BuildSaveAt(int layerCount)
    {
        var values = new List<int>();
        for (var n = 500; n < layerCount; n += 500)
            values.Add(n);
        if (!values.Contains(layerCount))
            values.Add(layerCount);
        return string.Join(",", values);
    }

    private static string ReplaceSetting(string text, string key, string value)
    {
        var lines = text.Replace("\r\n", "\n").Split('\n');
        var replaced = false;
        for (var i = 0; i < lines.Length; i++)
        {
            if (lines[i].StartsWith(key + " =", StringComparison.OrdinalIgnoreCase))
            {
                lines[i] = key + " = " + value;
                replaced = true;
            }
        }
        if (!replaced)
        {
            if (lines.Length > 0 && lines[lines.Length - 1].Length == 0)
                lines[lines.Length - 1] = key + " = " + value;
            else
                Array.Resize(ref lines, lines.Length + 1);
            lines[lines.Length - 1] = key + " = " + value;
        }
        return string.Join(Environment.NewLine, lines);
    }

    private static bool IsForzaPainterCanvasHeader(Dictionary<string, object> raw)
    {
        if (!raw.ContainsKey("type") || !raw.ContainsKey("data") || !raw.ContainsKey("color"))
            return false;
        if (Convert.ToInt32(raw["type"], CultureInfo.InvariantCulture) != 1)
            return false;

        var data = (ArrayList)raw["data"];
        var color = (ArrayList)raw["color"];
        return data.Count >= 4
            && Math.Abs(Convert.ToDouble(data[0], CultureInfo.InvariantCulture)) < 0.0001
            && Math.Abs(Convert.ToDouble(data[1], CultureInfo.InvariantCulture)) < 0.0001
            && color.Count >= 4
            && Convert.ToInt32(color[3], CultureInfo.InvariantCulture) == 0;
    }

    private static int Run(string exe, string arguments)
    {
        Console.WriteLine(Path.GetFileName(exe) + " " + arguments);
        var psi = new ProcessStartInfo
        {
            FileName = exe,
            Arguments = arguments,
            UseShellExecute = false,
            WorkingDirectory = Path.GetDirectoryName(exe) ?? Environment.CurrentDirectory
        };
        using (var process = Process.Start(psi))
        {
            process.WaitForExit();
            return process.ExitCode;
        }
    }

    private static string Quote(string value)
    {
        return "\"" + value.Replace("\"", "\\\"") + "\"";
    }
}
