using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

internal static class Launcher
{
    [STAThread]
    private static int Main(string[] args)
    {
        string executable = Application.ExecutablePath;
        string root = Path.GetDirectoryName(executable);
        string entry = Path.Combine(root, "Jarvis Desktop.pyw");
        string python = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            @"Jarvis\desktop-venv\Scripts\pythonw.exe");
        if (args.Length == 1 && args[0] == "--check")
            return File.Exists(entry) && File.Exists(python) ? 0 : 1;

        try
        {
            if (!File.Exists(entry) || !File.Exists(python))
                throw new FileNotFoundException("Keep Jarvis.exe beside Jarvis Desktop.pyw and install the Desktop environment.");
            var start = new ProcessStartInfo(python, "-B \"" + entry + "\"");
            start.WorkingDirectory = root;
            start.UseShellExecute = false;
            start.EnvironmentVariables["JARVIS_DESKTOP_LAUNCHER"] = executable;
            Process.Start(start);
            return 0;
        }
        catch (Exception error)
        {
            MessageBox.Show(error.Message, "Jarvis Desktop", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
