// 临时提高风扇转速并恢复自动控制。
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Principal;
using System.Text;
using System.Threading;
using LibreHardwareMonitor.Hardware;

internal static class Program
{
    private const int DefaultBoostSeconds = 10;

    private static int Main(string[] args)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        AppDomain.CurrentDomain.AssemblyResolve += ResolveDependency;

        if (!IsAdministrator())
        {
            return RelaunchAsAdministrator(args);
        }

        string mode = args.Length == 0 ? "boost" : args[0].ToLowerInvariant();
        if (mode == "auto")
        {
            return FanController.RequestRestore();
        }

        if (mode != "boost")
        {
            Console.Error.WriteLine("错误：仅支持 boost 或 auto。");
            return 2;
        }

        int seconds = DefaultBoostSeconds;
        if (args.Length > 1 && (!int.TryParse(args[1], out seconds) || seconds <= 0))
        {
            Console.Error.WriteLine("错误：持续时间必须是正整数秒数。");
            return 2;
        }

        return FanController.Boost(seconds);
    }

    // 依赖 DLL 在编译时以 FanControl.<文件名> 嵌入 EXE，运行时从自身资源读取并加载。
    private static Assembly ResolveDependency(object sender, ResolveEventArgs args)
    {
        string name = new AssemblyName(args.Name).Name + ".dll";
        using (Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("FanControl." + name))
        {
            if (stream == null)
            {
                return null;
            }
            byte[] assembly = new byte[stream.Length];
            stream.Read(assembly, 0, assembly.Length);
            return Assembly.Load(assembly);
        }
    }

    private static bool IsAdministrator()
    {
        WindowsIdentity identity = WindowsIdentity.GetCurrent();
        WindowsPrincipal principal = new WindowsPrincipal(identity);
        return principal.IsInRole(WindowsBuiltInRole.Administrator);
    }

    private static int RelaunchAsAdministrator(string[] args)
    {
        try
        {
            ProcessStartInfo startInfo = new ProcessStartInfo
            {
                FileName = Assembly.GetExecutingAssembly().Location,
                Arguments = string.Join(" ", args.Select(QuoteArgument).ToArray()),
                UseShellExecute = true,
                Verb = "runas"
            };
            using (Process process = Process.Start(startInfo))
            {
                process.WaitForExit();
                return process.ExitCode;
            }
        }
        catch (Exception exception)
        {
            Console.Error.WriteLine("错误：无法取得风扇控制权限：" + exception.Message);
            return 1;
        }
    }

    private static string QuoteArgument(string argument)
    {
        return "\"" + argument.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
    }
}

internal static class FanController
{
    private const string BoostMutexName = "JiaobenFanControlBoost";
    private const string RestoreRequestName = "JiaobenFanControlRestoreRequest";
    private const string RestoreDoneName = "JiaobenFanControlRestoreDone";

    public static int Boost(int seconds)
    {
        Computer computer = null;
        List<IControl> controls = null;
        Mutex boostMutex = null;
        EventWaitHandle restoreRequest = null;
        EventWaitHandle restoreDone = null;
        ConsoleCancelEventHandler cancelHandler = null;
        bool ownsMutex = false;
        int status = 0;
        try
        {
            boostMutex = new Mutex(false, BoostMutexName);
            try
            {
                ownsMutex = boostMutex.WaitOne(0);
            }
            catch (AbandonedMutexException)
            {
                ownsMutex = true;
            }
            if (!ownsMutex)
            {
                Console.Error.WriteLine("错误：风扇最高速流程已经在运行。");
                return 1;
            }

            restoreRequest = new EventWaitHandle(false, EventResetMode.AutoReset, RestoreRequestName);
            restoreDone = new EventWaitHandle(false, EventResetMode.ManualReset, RestoreDoneName);
            restoreDone.Reset();
            computer = OpenComputer();
            controls = FindConnectedFanControls(computer);
            if (controls.Count != 2)
            {
                Console.Error.WriteLine("错误：没有识别到两个已连接的主板风扇。");
                status = 1;
            }
            else
            {
                foreach (IControl control in controls)
                {
                    control.SetSoftware(100);
                }

                cancelHandler = delegate(object sender, ConsoleCancelEventArgs eventArgs)
                {
                    eventArgs.Cancel = true;
                    restoreRequest.Set();
                };
                Console.CancelKeyPress += cancelHandler;
                Console.WriteLine("风扇已调到最高转速，将在 " + seconds + " 秒后恢复自动调速。");
                restoreRequest.WaitOne(TimeSpan.FromSeconds(seconds));
            }
        }
        catch (Exception exception)
        {
            Console.Error.WriteLine("错误：风扇控制失败：" + exception.Message);
            status = 1;
        }
        finally
        {
            if (cancelHandler != null)
            {
                Console.CancelKeyPress -= cancelHandler;
            }
            if (!RestoreControls(controls))
            {
                Console.Error.WriteLine("错误：恢复风扇自动调速失败。");
                status = 1;
            }
            if (computer != null)
            {
                computer.Close();
            }
            if (restoreDone != null)
            {
                restoreDone.Set();
                restoreDone.Dispose();
            }
            if (restoreRequest != null)
            {
                restoreRequest.Dispose();
            }
            if (ownsMutex)
            {
                boostMutex.ReleaseMutex();
            }
            if (boostMutex != null)
            {
                boostMutex.Dispose();
            }
        }
        return status;
    }

    public static int RequestRestore()
    {
        try
        {
            using (EventWaitHandle restoreRequest = EventWaitHandle.OpenExisting(RestoreRequestName))
            using (EventWaitHandle restoreDone = EventWaitHandle.OpenExisting(RestoreDoneName))
            {
                restoreRequest.Set();
                if (!restoreDone.WaitOne(TimeSpan.FromSeconds(15)))
                {
                    Console.Error.WriteLine("错误：等待原风扇控制进程恢复超时。");
                    return 1;
                }
            }
            Console.WriteLine("风扇已恢复主板自动调速。");
            return 0;
        }
        catch (WaitHandleCannotBeOpenedException)
        {
            Console.Error.WriteLine("错误：最高速控制进程已经不存在，无法安全恢复原始风扇参数；请重启 Windows 让 BIOS 重新初始化风扇控制器。");
            return 1;
        }
        catch (Exception exception)
        {
            Console.Error.WriteLine("错误：恢复风扇自动调速失败：" + exception.Message);
            return 1;
        }
    }

    private static Computer OpenComputer()
    {
        Computer computer = new Computer { IsMotherboardEnabled = true };
        computer.Open();
        return computer;
    }

    private static List<IControl> FindConnectedFanControls(Computer computer)
    {
        List<ISensor> fanSensors = FindSensors(computer, SensorType.Fan)
            .Where(sensor => sensor.Value.HasValue && sensor.Value.Value > 0)
            .ToList();
        HashSet<int> connectedIndexes = new HashSet<int>(fanSensors.Select(sensor => sensor.Index));

        return FindFanControls(computer)
            .Where(sensor => connectedIndexes.Contains(sensor.Index))
            .Take(2)
            .Select(sensor => sensor.Control)
            .ToList();
    }

    private static IEnumerable<ISensor> FindFanControls(Computer computer)
    {
        return FindSensors(computer, SensorType.Control)
            .Where(sensor => sensor.Control != null)
            .OrderBy(sensor => sensor.Index);
    }

    private static List<ISensor> FindSensors(Computer computer, SensorType sensorType)
    {
        List<ISensor> sensors = new List<ISensor>();
        foreach (IHardware hardware in computer.Hardware)
        {
            hardware.Update();
            foreach (IHardware subHardware in hardware.SubHardware)
            {
                subHardware.Update();
                if (subHardware.Name.IndexOf("NCT6796D", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    sensors.AddRange(subHardware.Sensors.Where(sensor => sensor.SensorType == sensorType));
                }
            }
        }
        return sensors;
    }

    private static bool RestoreControls(IEnumerable<IControl> controls)
    {
        if (controls == null)
        {
            return true;
        }

        bool succeeded = true;
        foreach (IControl control in controls)
        {
            try
            {
                control.SetDefault();
            }
            catch
            {
                succeeded = false;
            }
        }
        return succeeded;
    }
}
