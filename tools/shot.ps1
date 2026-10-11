param(
    [Parameter(Mandatory=$true)][int]$TargetPid,
    [string]$Out = "shot.png"
)

$ProgressPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Drawing

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinApi2 {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int c);
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
"@

[void][WinApi2]::SetProcessDPIAware()
$p = Get-Process -Id $TargetPid -ErrorAction Stop
$h = $p.MainWindowHandle
if ($h -eq [IntPtr]::Zero) { Write-Error "no main window for pid $TargetPid"; exit 1 }

[void][WinApi2]::ShowWindow($h, 5)
[void][WinApi2]::SetForegroundWindow($h)
Start-Sleep -Milliseconds 800

$r = New-Object WinApi2+RECT
[void][WinApi2]::GetWindowRect($h, [ref]$r)
$w = $r.Right - $r.Left
$ht = $r.Bottom - $r.Top
if ($w -le 0 -or $ht -le 0) { Write-Error "bad rect $w x $ht"; exit 1 }

$bmp = New-Object System.Drawing.Bitmap $w, $ht
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.Left, $r.Top, 0, 0, (New-Object System.Drawing.Size($w, $ht)))
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
Write-Output "saved $Out ($w x $ht)"
