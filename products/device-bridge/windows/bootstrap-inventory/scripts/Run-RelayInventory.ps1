#requires -Version 5.1
<#
Runs the fixed no-argument diagnostic after bundle file-integrity validation.
Creates only a new private local evidence directory and its three files.
The manifest/verifier are unauthenticated bundle members: file equality is not
authorship, safe launch or loaded-image proof. A killed collector has no claimed
successful native cleanup. No service, key, root, installation or elevation.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PrivateCaptureDirectory,
    [ValidateRange(1, 120)][int]$TimeoutSeconds = 30,
    [string]$PythonExecutable = 'python.exe'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-LocalPlainPath([string]$Candidate) {
    $full = [IO.Path]::GetFullPath($Candidate)
    if ($full -notmatch '^[A-Za-z]:\\' -or $full.StartsWith('\\')) { throw 'Local path required' }
    if ([IO.DriveInfo]::new([IO.Path]::GetPathRoot($full)).DriveType -ne [IO.DriveType]::Fixed) { throw 'Fixed local drive required' }
    $node = $full
    while ($node) {
        if ([IO.File]::Exists($node) -or [IO.Directory]::Exists($node)) {
            if (([IO.File]::GetAttributes($node) -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse path refused' }
        }
        $parent = [IO.Directory]::GetParent($node)
        if ($null -eq $parent) { break }
        $node = $parent.FullName
    }
    return $full
}

function Write-NewPrivateFile([string]$Name, [byte[]]$Bytes) {
    $stream = [IO.FileStream]::new($Name, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $stream.Write($Bytes, 0, $Bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
}

$lease = $null
$captureValidated = $false
try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or -not [Environment]::Is64BitProcess) { throw 'Unsupported platform' }
    $bundle = Assert-LocalPlainPath ([IO.Directory]::GetParent($PSScriptRoot).FullName)
    $python = Assert-LocalPlainPath ((Get-Command $PythonExecutable -CommandType Application -ErrorAction Stop).Source)
    & $python (Join-Path $bundle 'tools/package_inventory.py') --verify $bundle *> $null
    if ($LASTEXITCODE -ne 0) { throw 'Bundle integrity failed' }
    $destination = Assert-LocalPlainPath $PrivateCaptureDirectory
    if ($destination.Equals($bundle, [StringComparison]::OrdinalIgnoreCase) -or
        $destination.StartsWith($bundle.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Capture outside bundle required' }
    if ([IO.Directory]::Exists($destination) -or [IO.File]::Exists($destination)) { throw 'Existing capture destination refused' }
    $parentDirectory = [IO.Directory]::GetParent($destination)
    if ($null -eq $parentDirectory -or -not $parentDirectory.Exists) { throw 'Existing local parent required' }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $drive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($destination))
    if ($drive.DriveType -ne [IO.DriveType]::Fixed -or $drive.AvailableFreeSpace -lt 2147483648) { throw 'Capacity floor not met' }
    if (-not ('HubRelayPrivateDirectory' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
public static class HubRelayPrivateDirectory {
    [StructLayout(LayoutKind.Sequential)] private struct SecurityAttributes {
        public int Length; public IntPtr Descriptor; public int InheritHandle;
    }
    [StructLayout(LayoutKind.Sequential)] private struct AttributeTag { public uint Attributes; public uint Tag; }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    private static extern IntPtr CreateFileW(string path, uint access, uint share, IntPtr security, uint disposition, uint flags, IntPtr template);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    private static extern bool CreateDirectoryW(string path, ref SecurityAttributes attributes);
    [DllImport("kernel32.dll", SetLastError=true)] private static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll")] private static extern IntPtr LocalFree(IntPtr pointer);
    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool GetFileInformationByHandleEx(IntPtr handle, int kind, out AttributeTag info, uint size);
    [DllImport("advapi32.dll")] private static extern uint GetSecurityInfo(IntPtr handle, int kind, uint information,
        out IntPtr owner, out IntPtr group, out IntPtr dacl, out IntPtr sacl, out IntPtr descriptor);
    [DllImport("advapi32.dll")] private static extern uint GetSecurityDescriptorLength(IntPtr descriptor);
    public sealed class Lease : IDisposable {
        private readonly List<IntPtr> handles = new List<IntPtr>();
        public bool CleanupComplete = true;
        internal void Add(IntPtr handle) { handles.Add(handle); }
        public void Dispose() {
            for (int i=handles.Count-1; i>=0; --i) if (!CloseHandle(handles[i])) CleanupComplete=false;
            handles.Clear();
        }
    }
    private static IntPtr OpenDirectory(string path, Lease lease) {
        // READ_CONTROL | FILE_READ_ATTRIBUTES | SYNCHRONIZE; READ/WRITE sharing,
        // deliberately no FILE_SHARE_DELETE. OPEN_REPARSE_POINT never follows
        // a leaf reparse object. Every parent handle stays retained through write.
        IntPtr handle=CreateFileW(path,0x120080,3,IntPtr.Zero,3,0x02200000,IntPtr.Zero);
        if (handle==IntPtr.Zero || handle==new IntPtr(-1)) throw new InvalidOperationException("Private namespace unavailable");
        lease.Add(handle);
        AttributeTag info;
        if (!GetFileInformationByHandleEx(handle,9,out info,8) || (info.Attributes & 0x410)!=0x10 || info.Tag!=0)
            throw new InvalidOperationException("Private namespace unavailable");
        return handle;
    }
    private static RawSecurityDescriptor ReadDescriptor(IntPtr handle) {
        IntPtr owner,group,dacl,sacl,descriptor;
        if (GetSecurityInfo(handle,1,5,out owner,out group,out dacl,out sacl,out descriptor)!=0 || descriptor==IntPtr.Zero)
            throw new InvalidOperationException("Private namespace unavailable");
        byte[] bytes=null; bool freed=false;
        try {
            uint length=GetSecurityDescriptorLength(descriptor);
            if (length<20 || length>65536) throw new InvalidOperationException("Private namespace unavailable");
            bytes=new byte[(int)length]; Marshal.Copy(descriptor,bytes,0,bytes.Length);
        } finally { freed=LocalFree(descriptor)==IntPtr.Zero; }
        if (!freed) throw new InvalidOperationException("Private namespace unavailable");
        return new RawSecurityDescriptor(bytes,0);
    }
    private static void CheckDescriptor(RawSecurityDescriptor descriptor, HashSet<string> trusted, bool finalParent) {
        if (descriptor.Owner==null || !trusted.Contains(descriptor.Owner.Value) || descriptor.DiscretionaryAcl==null
            || (descriptor.ControlFlags & ControlFlags.DiscretionaryAclPresent)==0)
            throw new InvalidOperationException("Private namespace unavailable");
        foreach (GenericAce entry in descriptor.DiscretionaryAcl) {
            CommonAce ace=entry as CommonAce;
            if (ace==null || ace.IsCallback || (ace.AceQualifier!=AceQualifier.AccessAllowed && ace.AceQualifier!=AceQualifier.AccessDenied))
                throw new InvalidOperationException("Private namespace unavailable");
            if (ace.AceQualifier==AceQualifier.AccessDenied || trusted.Contains(ace.SecurityIdentifier.Value)) continue;
            bool applies=(ace.AceFlags & AceFlags.InheritOnly)==0;
            bool inheritedByNewDirectory=finalParent && (ace.AceFlags & AceFlags.ContainerInherit)!=0;
            // DENY entries never subtract ALLOW grants. Allow add-subdirectory
            // alone: presquatting the final requested name makes creation fail.
            if ((applies || inheritedByNewDirectory) && (unchecked((uint)ace.AccessMask) & 0x500D0152U)!=0)
                throw new InvalidOperationException("Private namespace unavailable");
        }
    }
    public static Lease Create(string destination, string userSid) {
        Lease lease=new Lease();
        try {
            SecurityIdentifier user=new SecurityIdentifier(userSid);
            HashSet<string> trusted=new HashSet<string>(StringComparer.Ordinal) { userSid,"S-1-5-18","S-1-5-32-544",
                "S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464" };
            List<string> chain=new List<string>();
            DirectoryInfo directory=Directory.GetParent(destination);
            while (directory!=null) { chain.Add(directory.FullName); directory=directory.Parent; }
            chain.Reverse();
            for (int i=0;i<chain.Count;++i) CheckDescriptor(ReadDescriptor(OpenDirectory(chain[i],lease)),trusted,i==chain.Count-1);
            DirectorySecurity security=new DirectorySecurity();
            security.SetOwner(user); security.SetAccessRuleProtection(true,false);
            foreach (SecurityIdentifier principal in new SecurityIdentifier[] { user,new SecurityIdentifier("S-1-5-18") })
                security.AddAccessRule(new FileSystemAccessRule(principal,FileSystemRights.FullControl,
                    InheritanceFlags.ContainerInherit|InheritanceFlags.ObjectInherit,PropagationFlags.None,AccessControlType.Allow));
            byte[] bytes=security.GetSecurityDescriptorBinaryForm(); IntPtr native=Marshal.AllocHGlobal(bytes.Length);
            try {
                Marshal.Copy(bytes,0,native,bytes.Length);
                SecurityAttributes attributes=new SecurityAttributes {Length=Marshal.SizeOf(typeof(SecurityAttributes)),Descriptor=native,InheritHandle=0};
                if (!CreateDirectoryW(destination,ref attributes)) throw new InvalidOperationException("Private namespace unavailable");
            } finally { Marshal.FreeHGlobal(native); }
            HashSet<string> privatePrincipals=new HashSet<string>(StringComparer.Ordinal) {userSid,"S-1-5-18"};
            CheckDescriptor(ReadDescriptor(OpenDirectory(destination,lease)),privatePrincipals,true);
            return lease;
        } catch { lease.Dispose(); throw; }
    }
}
'@
    }
    # Security is supplied atomically to CreateDirectoryW. No pathname Set-Acl
    # window exists; retained namespace handles deny delete sharing until done.
    $lease = [HubRelayPrivateDirectory]::Create($destination, $identity.Value)
    if (-not ('HubRelayCapture' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
public sealed class HubRelayCaptureResult {
    public int ExitCode = -1;
    public bool Complete;
}
public static class HubRelayCapture {
    private static int Pump(Stream source, Stream target, long limit) {
        byte[] buffer = new byte[8192]; long count = 0;
        try {
            for (;;) {
                int read = source.Read(buffer, 0, buffer.Length);
                if (read == 0) { target.Flush(); return 0; }
                int retained = (int)Math.Min((long)read, limit - count);
                if (retained > 0) { target.Write(buffer, 0, retained); count += retained; }
                if (retained != read) { target.Flush(); return 1; }
            }
        } catch { return 2; }
    }
    public static HubRelayCaptureResult Run(string executable, string output, string errors, int timeout) {
        HubRelayCaptureResult result = new HubRelayCaptureResult();
        using (FileStream stdout = new FileStream(output, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        using (FileStream stderr = new FileStream(errors, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        using (Process child = new Process()) {
            child.StartInfo = new ProcessStartInfo(executable) {
                Arguments = "", UseShellExecute = false, CreateNoWindow = true,
                RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true,
                WorkingDirectory = Path.GetDirectoryName(executable)
            };
            if (!child.Start()) return result;
            child.StandardInput.Close();
            Task<int> outTask = Task.Run(() => Pump(child.StandardOutput.BaseStream, stdout, 32L * 1024 * 1024));
            Task<int> errTask = Task.Run(() => Pump(child.StandardError.BaseStream, stderr, 64L * 1024));
            Stopwatch clock = Stopwatch.StartNew(); bool interrupted = false;
            while (!child.WaitForExit(20)) {
                if (clock.ElapsedMilliseconds >= timeout * 1000L || (outTask.IsCompleted && outTask.Result != 0)
                    || (errTask.IsCompleted && errTask.Result != 0)) { interrupted = true; break; }
            }
            if (interrupted) {
                try { child.Kill(); } catch { }
                // This is a transfer guard, not proof of safe collector cleanup.
                try { child.WaitForExit(2000); } catch { }
                try { child.StandardOutput.BaseStream.Close(); } catch { }
                try { child.StandardError.BaseStream.Close(); } catch { }
            }
            bool drained = Task.WaitAll(new Task[] {outTask, errTask}, 2000);
            if (!drained) {
                try { child.StandardOutput.BaseStream.Close(); } catch { }
                try { child.StandardError.BaseStream.Close(); } catch { }
                Task.WaitAll(new Task[] {outTask, errTask}, 2000);
            }
            if (child.HasExited) result.ExitCode = child.ExitCode;
            result.Complete = !interrupted && drained && outTask.Result == 0 && errTask.Result == 0 && child.HasExited;
            stdout.Flush(true); stderr.Flush(true);
        }
        return result;
    }
}
'@
    }
    $receiptPath = Join-Path $destination 'receipt.json'
    $stderrPath = Join-Path $destination 'stderr.bin'
    $capturePath = Join-Path $destination 'capture.json'
    $result = [HubRelayCapture]::Run((Join-Path $bundle 'hub-relay-bootstrap-inventory.exe'), $receiptPath, $stderrPath, $TimeoutSeconds)
    $length = ([IO.FileInfo]::new($receiptPath)).Length
    $digest = (Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $record = [ordered]@{ schema = 'hub_relay.capture.v0.1'; exit_code = $result.ExitCode;
        capture_complete = [bool]$result.Complete; byte_length = $length; sha256 = $digest; authority = 'none' }
    Write-NewPrivateFile $capturePath ([Text.UTF8Encoding]::new($false).GetBytes(($record | ConvertTo-Json -Compress)))
    & $python (Join-Path $bundle 'tools/verify_inventory.py') --receipt $receiptPath --capture-record $capturePath *> $null
    if ($LASTEXITCODE -ne 0) { throw 'Capture validation failed' }
    $captureValidated = $true
} catch {
    $captureValidated = $false
} finally {
    if ($null -ne $lease) { $lease.Dispose(); if (-not $lease.CleanupComplete) { $captureValidated = $false } }
}
if ($captureValidated) {
    Write-Output 'Private complete diagnostic capture validated; no authority established; activation blocked.'
    exit 0
} else {
    Write-Output 'Diagnostic capture incomplete or invalid; private evidence retained where created; native cleanup not certified; activation blocked.'
    exit 1
}
