// GdeFs: read-only WinFsp filesystem exposing ONE virtual file,
// model.gguf, whose bytes are served from the GDE extent store
// (extents.bin + manifest.json written by ingest_gguf.py).
//
// Every Read callback is counted (reads, bytes) and snapshots are
// appended to gde_stats.log next to the store, so an inference run can
// prove that its tensor bytes traversed the GDE retrieval layer.
//
// Build (no SDK needed; uses the in-box .NET Framework compiler):
//   csc /target:exe /out:GdeFs.exe /reference:winfsp-msil.dll GdeFs.cs
// Run:
//   GdeFs.exe <store_dir> <mountpoint e.g. G:>
using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;

using Fsp;
using VolumeInfo = Fsp.Interop.VolumeInfo;
using FileInfo = Fsp.Interop.FileInfo;

namespace GdeFsApp
{
    class GdeFs : FileSystemBase
    {
        private readonly string ExtentsPath;
        private readonly string StatsPath;
        private readonly long FileSize;
        private readonly UInt64 FileTime;  // stable across all queries
        private readonly FileStream Stream;
        private readonly object IoLock = new object();
        private long Reads;
        private long Bytes;

        public GdeFs(string storeDir)
        {
            ExtentsPath = Path.Combine(storeDir, "extents.bin");
            StatsPath = Path.Combine(storeDir, "gde_stats.log");
            FileSize = new System.IO.FileInfo(ExtentsPath).Length;
            FileTime = (UInt64)DateTime.Now.ToFileTimeUtc();
            Stream = new FileStream(ExtentsPath, FileMode.Open, FileAccess.Read,
                FileShare.Read, 1 << 20, FileOptions.RandomAccess);
        }

        private FileInfo InfoFor(string name)
        {
            FileInfo info = default(FileInfo);
            // Stable timestamps: returning DateTime.Now on every query
            // makes the file look perpetually modified and the cache
            // manager invalidates in-flight readahead on revalidation.
            info.CreationTime = info.LastAccessTime = info.LastWriteTime = info.ChangeTime = FileTime;
            if (name == "\\")
            {
                info.FileAttributes = (UInt32)FileAttributes.Directory;
                info.FileSize = 0;
                info.AllocationSize = 0;
                info.IndexNumber = 1;
            }
            else
            {
                info.FileAttributes = (UInt32)FileAttributes.ReadOnly | (UInt32)FileAttributes.Archive;
                info.FileSize = (UInt64)FileSize;
                info.AllocationSize = (UInt64)((FileSize + 4095) & ~4095L);
                // Unique, stable file identity: sharing IndexNumber 0 with
                // the root directory confuses the Windows cache manager.
                info.IndexNumber = 2;
            }
            info.HardLinks = 1;
            return info;
        }

        private static Byte[] DefaultSecurity()
        {
            var sd = new System.Security.AccessControl.RawSecurityDescriptor(
                "O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;WD)");
            var bytes = new Byte[sd.BinaryLength];
            sd.GetBinaryForm(bytes, 0);
            return bytes;
        }

        // Host configuration belongs in Init (called before the FSD is
        // created); setting these in Mounted is too late and they are
        // ignored. Aligned with the official memfs-dotnet sample.
        public override Int32 Init(Object hostObj)
        {
            FileSystemHost host = (FileSystemHost)hostObj;
            host.SectorSize = 512;
            host.SectorsPerAllocationUnit = 1;
            host.VolumeCreationTime = (UInt64)DateTime.Now.ToFileTimeUtc();
            host.VolumeSerialNumber = 0x47444531; /* "GDE1" */
            host.CaseSensitiveSearch = false;
            host.CasePreservedNames = true;
            host.UnicodeOnDisk = true;
            host.PersistentAcls = true;
            host.ReparsePoints = true;
            host.ReparsePointsAccessCheck = false;
            host.NamedStreams = true;
            host.PostCleanupWhenModifiedOnly = true;
            host.PostDispositionWhenNecessaryOnly = true;
            host.PassQueryDirectoryFileName = true;
            host.ExtendedAttributes = true;
            host.WslFeatures = true;
            host.RejectIrpPriorToTransact0 = true;
            host.SupportsPosixUnlinkRename = true;
            host.FileInfoTimeout = 1000;
            return STATUS_SUCCESS;
        }

        public override Int32 GetVolumeInfo(out VolumeInfo volumeInfo)
        {
            volumeInfo = default(VolumeInfo);
            volumeInfo.TotalSize = (UInt64)((FileSize + 4095) & ~4095L);
            volumeInfo.FreeSize = 0;
            volumeInfo.SetVolumeLabel("GDE");
            return STATUS_SUCCESS;
        }

        public override Int32 GetSecurityByName(
            String fileName, out UInt32 fileAttributes, ref Byte[] securityDescriptor)
        {
            if (securityDescriptor != null) securityDescriptor = DefaultSecurity();
            if (fileName == "\\") { fileAttributes = (UInt32)FileAttributes.Directory; return STATUS_SUCCESS; }
            if (String.Equals(fileName, "\\model.gguf", StringComparison.OrdinalIgnoreCase))
            { fileAttributes = (UInt32)FileAttributes.ReadOnly; return STATUS_SUCCESS; }
            fileAttributes = 0;
            return STATUS_OBJECT_NAME_NOT_FOUND;
        }

        public override Int32 Open(
            String fileName, UInt32 createOptions, UInt32 grantedAccess,
            out Object fileNode, out Object fileDesc, out FileInfo fileInfo,
            out String normalizedName)
        {
            fileNode = fileDesc = null;
            normalizedName = fileName;
            if (fileName == "\\" || String.Equals(fileName, "\\model.gguf", StringComparison.OrdinalIgnoreCase))
            {
                fileNode = fileName;
                fileInfo = InfoFor(fileName);
                return STATUS_SUCCESS;
            }
            fileInfo = default(FileInfo);
            return STATUS_OBJECT_NAME_NOT_FOUND;
        }

        public override Int32 Create(
            String fileName, UInt32 createOptions, UInt32 grantedAccess,
            UInt32 fileAttributes, Byte[] securityDescriptor, UInt64 allocationSize,
            out Object fileNode, out Object fileDesc, out FileInfo fileInfo,
            out String normalizedName)
        {
            // Read-only volume: Create is only ever an open of existing objects.
            return Open(fileName, createOptions, grantedAccess,
                out fileNode, out fileDesc, out fileInfo, out normalizedName);
        }

        public override Int32 Read(
            Object fileNode, Object fileDesc, IntPtr buffer, UInt64 offset,
            UInt32 length, out UInt32 bytesTransferred)
        {
            bytesTransferred = 0;
            Interlocked.Increment(ref Reads);
            try { return ReadInner(buffer, offset, length, out bytesTransferred); }
            catch (Exception ex)
            {
                try { File.AppendAllText(StatsPath, "READ EXCEPTION: " + ex + "\n"); } catch { }
                return STATUS_ACCESS_DENIED;
            }
        }

        private Int32 ReadInner(
            IntPtr buffer, UInt64 offset, UInt32 length, out UInt32 bytesTransferred)
        {
            bytesTransferred = 0;
            if ((long)offset >= FileSize) return STATUS_SUCCESS;
            int toRead = (int)Math.Min((long)length, FileSize - (long)offset);
            byte[] data = new byte[toRead];
            int read;
            lock (IoLock)
            {
                Stream.Seek((long)offset, SeekOrigin.Begin);
                read = 0;
                while (read < toRead)
                {
                    int n = Stream.Read(data, read, toRead - read);
                    if (n <= 0) break;
                    read += n;
                }
            }
            if (read > 0)
            {
                Marshal.Copy(data, 0, buffer, read);
                bytesTransferred = (UInt32)read;
                long r = Interlocked.Read(ref Reads);
                Interlocked.Add(ref Bytes, read);
                if (r % 200 == 0) Snapshot();
            }
            return STATUS_SUCCESS;
        }

        private void Snapshot()
        {
            try
            {
                lock (IoLock)
                    File.AppendAllText(StatsPath,
                        String.Format("reads={0} bytes={1}\n",
                            Interlocked.Read(ref Reads), Interlocked.Read(ref Bytes)));
            }
            catch { /* stats must never break reads */ }
        }

        public override Int32 GetFileInfo(
            Object fileNode, Object fileDesc, out FileInfo fileInfo)
        {
            fileInfo = InfoFor((String)fileNode);
            return STATUS_SUCCESS;
        }

        public override Boolean ReadDirectoryEntry(
            Object fileNode, Object fileDesc, String pattern, String marker,
            ref Object context, out String fileName, out FileInfo fileInfo)
        {
            fileName = null;
            fileInfo = default(FileInfo);
            if ((String)fileNode != "\\") return false;
            IEnumerator<String> en = (IEnumerator<String>)context;
            if (en == null)
            {
                context = en = new List<String> { ".", "..", "model.gguf" }.GetEnumerator();
            }
            if (!en.MoveNext()) return false;
            fileName = en.Current;
            fileInfo = InfoFor(fileName == "model.gguf" ? "\\model.gguf" : "\\");
            return true;
        }

        public override void Cleanup(
            Object fileNode, Object fileDesc, String fileName, UInt32 flags) { }

        public override void Close(Object fileNode, Object fileDesc)
        {
            Snapshot();
            Console.WriteLine("[gde] reads={0} bytes={1}",
                Interlocked.Read(ref Reads), Interlocked.Read(ref Bytes));
        }
    }

    class Program
    {
        static int Main(string[] args)
        {
            if (args.Length < 2)
            {
                Console.WriteLine("usage: GdeFs.exe <store_dir> <mountpoint>");
                return 2;
            }
            FileSystemHost host = new FileSystemHost(new GdeFs(args[0]));
            host.FileSystemName = "GDE";
            if (0 > host.Mount(args[1], null, false, 0))
            {
                Console.WriteLine("cannot mount");
                return 1;
            }
            Console.WriteLine("mounted at " + host.MountPoint());
            Console.Out.Flush();
            // Stay alive until killed by the harness.
            Thread.Sleep(Timeout.Infinite);
            return 0;
        }
    }
}
