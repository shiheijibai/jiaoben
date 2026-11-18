// 自动控制RKDevTool完成RK3568刷机。
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

internal static class RkDevToolControl
{
    // RKDevTool config: D:\Software\tool3568\config.ini, line 32
    // DEFAULT_IMAGE_CONFIG=D:\rk3568\images\config.cfg
    private const string ActiveImagePath = @"D:\rk3568\images";
    private const string BackupImagePath = @"D:\rk3568\images.down-backup";
    private const string RkDevToolPath = @"D:\Software\tool3568\RKDevTool.exe";
    private const string RkDevToolLogDirectory = @"D:\Software\tool3568\Log";
    private const string HdcPath = @"D:\Path\hdc\hdc.exe";
    private const int LoaderTimeoutSeconds = 90;
    private const int FlashTimeoutSeconds = 900;
    private const int FlashMaxAttempts = 3;

    private const uint BM_CLICK = 0x00F5;
    private const uint WM_CLOSE = 0x0010;
    private const uint SMTO_ABORTIFHUNG = 0x0002;

    private delegate bool EnumWindowsProc(IntPtr window, IntPtr parameter);

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc callback, IntPtr parameter);

    [DllImport("user32.dll")]
    private static extern bool EnumChildWindows(
        IntPtr parent, EnumWindowsProc callback, IntPtr parameter);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowTextW(
        IntPtr window, StringBuilder text, int maximumCount);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetClassNameW(
        IntPtr window, StringBuilder className, int maximumCount);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(
        IntPtr window, out uint processId);

    [DllImport("user32.dll")]
    private static extern int GetDlgCtrlID(IntPtr window);

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr window);

    [DllImport("user32.dll")]
    private static extern bool IsWindowEnabled(IntPtr window);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern IntPtr SendMessageTimeoutW(
        IntPtr window,
        uint message,
        UIntPtr wParam,
        IntPtr lParam,
        uint flags,
        uint timeout,
        out UIntPtr result);

    private sealed class WindowInfo
    {
        internal IntPtr Handle;
        internal int ControlId;
        internal string ClassName = string.Empty;
        internal string Text = string.Empty;
        internal bool Visible;
        internal bool Enabled;
    }

    private sealed class CommandResult
    {
        internal int ExitCode;
        internal string Output = string.Empty;
    }

    private static int Main(string[] arguments)
    {
        Console.OutputEncoding = Encoding.UTF8;
        if (arguments.Length < 1 || arguments.Length > 2) {
            Console.Error.WriteLine(
                "用法：rkdevtool-control.exe <镜像目录> [HDC设备编号]");
            return 2;
        }

        ResetControlLog();
        string device = arguments.Length == 2 ? arguments[1] : string.Empty;
        return Flash(Path.GetFullPath(arguments[0]), device);
    }

    private static int Flash(string imagePath, string requestedDevice)
    {
        if (!Directory.Exists(imagePath) ||
            !File.Exists(Path.Combine(imagePath, "config.cfg"))) {
            Console.Error.WriteLine("镜像目录不存在或缺少 config.cfg。");
            return 3;
        }
        if (Directory.Exists(BackupImagePath)) {
            Console.Error.WriteLine(
                "检测到未恢复的备份目录：" + BackupImagePath);
            return 4;
        }
        if (GetToolProcessCount() != 0) {
            Console.Error.WriteLine("RKDevTool 已在运行，请先关闭。");
            return 5;
        }

        string device;
        if (!ResolveDevice(requestedDevice, out device)) {
            return 6;
        }

        bool backupCreated = false;
        bool imageActivated = false;
        bool toolStarted = false;
        int operationStatus = 1;
        int restoreStatus;

        try {
            if (Directory.Exists(ActiveImagePath)) {
                Directory.Move(ActiveImagePath, BackupImagePath);
                backupCreated = true;
            }
            Directory.Move(imagePath, ActiveImagePath);
            imageActivated = true;

            ProcessStartInfo startInfo = new ProcessStartInfo {
                FileName = RkDevToolPath,
                WorkingDirectory = Path.GetDirectoryName(RkDevToolPath),
                UseShellExecute = true
            };
            using (Process process = Process.Start(startInfo)) {
            }
            toolStarted = true;

            uint processId;
            operationStatus = WaitForSingleToolProcess(out processId);
            if (operationStatus == 0) {
                operationStatus = RebootLoader(device);
            }
            if (operationStatus == 0) {
                operationStatus = WaitForLoaderAndClick(processId);
            }
            if (operationStatus == 0) {
                Console.WriteLine("刷机成功，RKDevTool 已自动关闭。");
            }
        } catch (Exception exception) {
            Console.Error.WriteLine("刷机流程失败：" + exception.Message);
            operationStatus = 1;
        } finally {
            try {
                if (toolStarted && GetToolProcessCount() != 0) {
                    CloseToolProcesses();
                }
            } finally {
                restoreStatus = RestoreImages(
                    imagePath, imageActivated, backupCreated);
            }
        }

        return operationStatus != 0 ? operationStatus : restoreStatus;
    }

    private static bool ResolveDevice(string requestedDevice, out string device)
    {
        device = requestedDevice;
        if (!string.IsNullOrWhiteSpace(device)) {
            return true;
        }

        CommandResult result;
        try {
            result = RunCommand(HdcPath, "list targets -v");
        } catch (Exception exception) {
            Console.Error.WriteLine("读取 HDC 设备失败：" + exception.Message);
            return false;
        }
        if (result.ExitCode != 0) {
            Console.Error.WriteLine("读取 HDC 设备失败：" + result.Output.Trim());
            return false;
        }

        List<string> devices = new List<string>();
        foreach (string line in result.Output.Replace("\r", string.Empty).Split('\n')) {
            string[] fields = line.Split(
                new char[] { ' ', '\t' },
                StringSplitOptions.RemoveEmptyEntries);
            if (fields.Length >= 3 &&
                string.Equals(fields[1], "USB", StringComparison.OrdinalIgnoreCase) &&
                string.Equals(fields[2], "Connected", StringComparison.OrdinalIgnoreCase)) {
                devices.Add(fields[0]);
            }
        }

        if (devices.Count == 0) {
            Console.Error.WriteLine("Windows HDC 未发现已连接的 USB 设备。");
            return false;
        }
        if (devices.Count > 1) {
            Console.Error.WriteLine(
                "检测到多个 HDC 设备，请使用 device=<connect-key> 指定：");
            foreach (string item in devices) {
                Console.Error.WriteLine("  " + item);
            }
            return false;
        }

        device = devices[0];
        return true;
    }

    private static int RebootLoader(string device)
    {
        CommandResult result;
        try {
            result = RunCommand(
                HdcPath,
                "-t \"" + device.Replace("\"", "\\\"") +
                "\" shell reboot loader");
        } catch (Exception exception) {
            Console.Error.WriteLine("设备进入 Loader 失败：" + exception.Message);
            return 7;
        }

        if (!string.IsNullOrWhiteSpace(result.Output)) {
            Console.WriteLine(result.Output.Trim());
        }
        if (result.ExitCode != 0 ||
            result.Output.IndexOf("[Fail]", StringComparison.OrdinalIgnoreCase) >= 0 ||
            result.Output.IndexOf("need connect-key", StringComparison.OrdinalIgnoreCase) >= 0) {
            Console.Error.WriteLine("设备进入 Loader 失败。");
            return 7;
        }
        return 0;
    }

    private static CommandResult RunCommand(string fileName, string arguments)
    {
        ProcessStartInfo startInfo = new ProcessStartInfo {
            FileName = fileName,
            Arguments = arguments,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };
        using (Process process = Process.Start(startInfo)) {
            string output = process.StandardOutput.ReadToEnd();
            string error = process.StandardError.ReadToEnd();
            process.WaitForExit();
            return new CommandResult {
                ExitCode = process.ExitCode,
                Output = output + error
            };
        }
    }

    private static int WaitForSingleToolProcess(out uint processId)
    {
        DateTime deadline = DateTime.UtcNow.AddSeconds(10);
        while (DateTime.UtcNow < deadline) {
            Process[] processes = Process.GetProcessesByName("RKDevTool");
            if (processes.Length == 1) {
                processId = unchecked((uint)processes[0].Id);
                processes[0].Dispose();
                return 0;
            }
            foreach (Process process in processes) {
                process.Dispose();
            }
            if (processes.Length > 1) {
                processId = 0;
                Console.Error.WriteLine("检测到多个 RKDevTool 进程。");
                return 8;
            }
            Thread.Sleep(200);
        }

        processId = 0;
        Console.Error.WriteLine("RKDevTool 启动失败。");
        return 8;
    }

    private static int GetToolProcessCount()
    {
        Process[] processes = Process.GetProcessesByName("RKDevTool");
        int count = processes.Length;
        foreach (Process process in processes) {
            process.Dispose();
        }
        return count;
    }

    private static void CloseToolProcesses()
    {
        foreach (Process process in Process.GetProcessesByName("RKDevTool")) {
            try {
                if (!process.CloseMainWindow() || !process.WaitForExit(5000)) {
                    process.Kill();
                    process.WaitForExit(5000);
                }
            } catch (Exception exception) {
                Console.Error.WriteLine(
                    "自动关闭 RKDevTool 失败：" + exception.Message);
            } finally {
                process.Dispose();
            }
        }
    }

    private static int RestoreImages(
        string imagePath, bool imageActivated, bool backupCreated)
    {
        try {
            if (imageActivated) {
                if (Directory.Exists(imagePath) ||
                    !Directory.Exists(ActiveImagePath)) {
                    Console.Error.WriteLine(
                        "无法恢复本次刷机镜像目录，请手动检查 D:\\rk3568。");
                    return 9;
                }
                Directory.Move(ActiveImagePath, imagePath);
            }
            if (backupCreated) {
                if (Directory.Exists(ActiveImagePath) ||
                    !Directory.Exists(BackupImagePath)) {
                    Console.Error.WriteLine(
                        "无法恢复原 images 目录，请手动检查 D:\\rk3568。");
                    return 9;
                }
                Directory.Move(BackupImagePath, ActiveImagePath);
            }
            return 0;
        } catch (Exception exception) {
            Console.Error.WriteLine("恢复镜像目录失败：" + exception.Message);
            return 9;
        }
    }

    private static int WaitForLoaderAndClick(uint processId)
    {
        IntPtr mainWindow = WaitForMainWindow(processId, LoaderTimeoutSeconds);
        if (mainWindow == IntPtr.Zero) {
            Console.Error.WriteLine("未找到 RKDevTool 主窗口。");
            return 10;
        }

        DateTime deadline = DateTime.UtcNow.AddSeconds(LoaderTimeoutSeconds);
        List<WindowInfo> controls = new List<WindowInfo>();
        while (DateTime.UtcNow < deadline) {
            controls = EnumerateControls(mainWindow);
            bool loaderFound = false;
            List<WindowInfo> executeButtons = new List<WindowInfo>();

            foreach (WindowInfo control in controls) {
                string text = control.Text.Replace("&", string.Empty).Trim();
                if (control.ControlId == 1004 &&
                    control.ClassName == "Static" &&
                    text.IndexOf("LOADER", StringComparison.OrdinalIgnoreCase) >= 0 &&
                    text.IndexOf("设备", StringComparison.Ordinal) >= 0) {
                    loaderFound = true;
                }
                if (control.Visible && control.Enabled &&
                    control.ControlId == 1006 &&
                    control.ClassName == "Button" &&
                    (text == "执行" ||
                     text.StartsWith("执行(", StringComparison.Ordinal))) {
                    executeButtons.Add(control);
                }
            }

            if (loaderFound) {
                WriteLog(mainWindow, controls, "Loader detected");
                if (executeButtons.Count != 1) {
                    Console.Error.WriteLine(
                        "可用的执行按钮数量不是 1：" + executeButtons.Count);
                    return 12;
                }

                return ClickExecuteWithRetry(
                    mainWindow, processId, executeButtons[0].Handle);
            }
            Thread.Sleep(300);
        }

        WriteLog(mainWindow, controls, "Loader timeout");
        Console.Error.WriteLine("等待 Loader 状态超时。");
        return 11;
    }

    private static int ClickExecuteWithRetry(
        IntPtr mainWindow, uint processId, IntPtr executeButton)
    {
        string flashLogPath = Path.Combine(
            RkDevToolLogDirectory,
            "Log" + DateTime.Now.ToString("yyyy-MM-dd") + ".txt");

        for (int attempt = 1; attempt <= FlashMaxAttempts; attempt++) {
            DateTime buttonDeadline = DateTime.UtcNow.AddSeconds(10);
            while (!IsWindowEnabled(executeButton) &&
                   DateTime.UtcNow < buttonDeadline) {
                Thread.Sleep(200);
            }
            if (!IsWindowEnabled(executeButton)) {
                Console.Error.WriteLine("执行按钮未恢复为可用状态。");
                return 13;
            }

            long initialLogLength = File.Exists(flashLogPath)
                ? new FileInfo(flashLogPath).Length
                : 0;
            UIntPtr result;
            IntPtr sent = SendMessageTimeoutW(
                executeButton,
                BM_CLICK,
                UIntPtr.Zero,
                IntPtr.Zero,
                SMTO_ABORTIFHUNG,
                3000,
                out result);
            if (sent == IntPtr.Zero) {
                Console.Error.WriteLine("点击执行失败。");
                return 13;
            }

            Console.WriteLine(
                "已识别 Loader，开始刷机（" + attempt + "/" +
                FlashMaxAttempts + "）。");
            int status = WaitForFlashAndClose(
                mainWindow, processId, flashLogPath, initialLogLength);
            if (status != 16) {
                return status;
            }
            if (attempt < FlashMaxAttempts) {
                Console.Error.WriteLine("刷机失败，重新点击执行。");
                Thread.Sleep(1000);
            }
        }

        Console.Error.WriteLine("刷机连续失败 3 次，停止重试并继续后续流程。");
        return 16;
    }

    private static int WaitForFlashAndClose(
        IntPtr mainWindow,
        uint processId,
        string flashLogPath,
        long initialLogLength)
    {
        DateTime deadline = DateTime.UtcNow.AddSeconds(FlashTimeoutSeconds);
        while (DateTime.UtcNow < deadline) {
            string appendedLog = ReadLogFrom(flashLogPath, initialLogLength);
            int success = appendedLog.LastIndexOf(
                "RunProc is ending, ret=1", StringComparison.Ordinal);
            int failure = appendedLog.LastIndexOf(
                "RunProc is ending, ret=0", StringComparison.Ordinal);

            if (failure > success) {
                return 16;
            }
            if (success >= 0) {
                Thread.Sleep(1000);
                UIntPtr result;
                IntPtr sent = SendMessageTimeoutW(
                    mainWindow,
                    WM_CLOSE,
                    UIntPtr.Zero,
                    IntPtr.Zero,
                    SMTO_ABORTIFHUNG,
                    3000,
                    out result);
                if (sent == IntPtr.Zero) {
                    Console.Error.WriteLine("刷机成功，但自动关闭失败。");
                    return 18;
                }

                try {
                    using (Process process = Process.GetProcessById((int)processId)) {
                        if (!process.WaitForExit(10000)) {
                            Console.Error.WriteLine(
                                "已发送关闭命令，但 RKDevTool 仍在运行。");
                            return 18;
                        }
                    }
                } catch (ArgumentException) {
                }
                return 0;
            }
            Thread.Sleep(500);
        }

        Console.Error.WriteLine("等待刷机结果超时，RKDevTool 将保持打开。");
        return 17;
    }

    private static string ReadLogFrom(string path, long offset)
    {
        try {
            if (!File.Exists(path)) {
                return string.Empty;
            }
            using (FileStream stream = new FileStream(
                path,
                FileMode.Open,
                FileAccess.Read,
                FileShare.ReadWrite | FileShare.Delete)) {
                if (stream.Length <= offset) {
                    return string.Empty;
                }
                stream.Position = offset;
                using (StreamReader reader = new StreamReader(
                    stream, Encoding.Unicode, true)) {
                    return reader.ReadToEnd();
                }
            }
        } catch (IOException) {
            return string.Empty;
        }
    }

    private static IntPtr WaitForMainWindow(uint processId, int timeoutSeconds)
    {
        DateTime deadline = DateTime.UtcNow.AddSeconds(timeoutSeconds);
        while (DateTime.UtcNow < deadline) {
            IntPtr selected = IntPtr.Zero;
            EnumWindows(delegate(IntPtr window, IntPtr parameter) {
                uint windowProcessId;
                GetWindowThreadProcessId(window, out windowProcessId);
                if (windowProcessId != processId || !IsWindowVisible(window)) {
                    return true;
                }

                string title = GetText(window);
                if (title.IndexOf("瑞芯微开发工具", StringComparison.Ordinal) >= 0 ||
                    title.IndexOf("RKDevTool", StringComparison.OrdinalIgnoreCase) >= 0) {
                    selected = window;
                    return false;
                }
                return true;
            }, IntPtr.Zero);

            if (selected != IntPtr.Zero) {
                return selected;
            }
            Thread.Sleep(200);
        }
        return IntPtr.Zero;
    }

    private static List<WindowInfo> EnumerateControls(IntPtr mainWindow)
    {
        List<WindowInfo> controls = new List<WindowInfo>();
        EnumChildWindows(mainWindow, delegate(IntPtr window, IntPtr parameter) {
            controls.Add(new WindowInfo {
                Handle = window,
                ControlId = GetDlgCtrlID(window),
                ClassName = GetClassName(window),
                Text = GetText(window),
                Visible = IsWindowVisible(window),
                Enabled = IsWindowEnabled(window)
            });
            return true;
        }, IntPtr.Zero);
        return controls;
    }

    private static string GetText(IntPtr window)
    {
        StringBuilder text = new StringBuilder(2048);
        GetWindowTextW(window, text, text.Capacity);
        return text.ToString();
    }

    private static string GetClassName(IntPtr window)
    {
        StringBuilder className = new StringBuilder(256);
        GetClassNameW(window, className, className.Capacity);
        return className.ToString();
    }

    private static void WriteLog(
        IntPtr mainWindow, List<WindowInfo> controls, string reason)
    {
        try {
            StringBuilder log = new StringBuilder();
            log.AppendLine(DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));
            log.AppendLine("Reason=" + reason);
            log.AppendLine("MainHandle=0x" + mainWindow.ToInt64().ToString("X"));
            log.AppendLine("Handle\tId\tVisible\tEnabled\tClass\tText");
            foreach (WindowInfo control in controls) {
                log.Append("0x").Append(control.Handle.ToInt64().ToString("X"));
                log.Append('\t').Append(control.ControlId);
                log.Append('\t').Append(control.Visible ? "1" : "0");
                log.Append('\t').Append(control.Enabled ? "1" : "0");
                log.Append('\t').Append(control.ClassName.Replace('\t', ' '));
                log.Append('\t').Append(
                    control.Text.Replace('\t', ' ')
                        .Replace('\r', ' ').Replace('\n', ' '));
                log.AppendLine();
            }
            File.AppendAllText(GetControlLogPath(), log.ToString(), new UTF8Encoding(true));
        } catch (Exception) {
        }
    }

    private static void ResetControlLog()
    {
        try {
            File.WriteAllText(
                GetControlLogPath(), string.Empty, new UTF8Encoding(true));
        } catch (Exception) {
        }
    }

    private static string GetControlLogPath()
    {
        return Path.Combine(
            AppDomain.CurrentDomain.BaseDirectory,
            "rkdevtool-controls.log");
    }
}
