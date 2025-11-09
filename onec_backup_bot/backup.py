from __future__ import annotations

import hashlib
import subprocess
import datetime as dt
import os
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import zipfile



class BackupService:
    def __init__(self, *, onec_exe: str, base_path: str, uc: str, up: str,
                 backup_dir: str, file_prefix: str,
                 logger, db):
        self.onec_exe = onec_exe
        self.base_path = base_path
        self.uc = uc or None
        self.up = up or None
        self.backup_dir = Path(backup_dir)
        self.file_prefix = file_prefix
        self.logger = logger
        self.db = db
        

        self._lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="backup")
        self.dump_timeout_sec = getattr(self, 'dump_timeout_sec', 7200)

        # Ensure main backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _onec_dump(self, dt_path: Path) -> subprocess.CompletedProcess:
        out_log = self.backup_dir / "dump_out.log"
        exe_path = Path(self.onec_exe)
        if not exe_path.exists():
            self.logger.error(f"1C executable not found: {exe_path}")
            raise FileNotFoundError(f"1C executable not found: {exe_path}")
        base_dir = Path(self.base_path)
        if not base_dir.exists():
            self.logger.error(f"1C base path not found: {base_dir}")
            raise FileNotFoundError(f"1C base path not found: {base_dir}")

        args = [
            str(exe_path),
            "DESIGNER",
            "/F", str(base_dir),
            "/DumpIB", str(dt_path),
            "/Out", str(out_log),
            "/DisableStartupDialogs",
        ]
        if self.uc:
            args += ["/N", self.uc]
        if self.up:
            args += ["/P", self.up]
        display_args = list(args)
        try:
            if "/P" in display_args:
                idx = display_args.index("/P")
                if idx + 1 < len(display_args):
                    display_args[idx + 1] = "***"
        except Exception:
            pass
        self.logger.info(f"Running 1C dump: {' '.join(display_args)}")
        return subprocess.run(args, capture_output=True, text=True, timeout=self.dump_timeout_sec)

    def _compute_fingerprint(self) -> str:
        base = Path(self.base_path)
        h = hashlib.sha256()
        if base.exists() and base.is_dir():
            for root, dirs, files in os.walk(base):
                files.sort()
                for name in files:
                    p = Path(root) / name
                    try:
                        st = p.stat()
                        rel = str(p.relative_to(base)).lower().encode("utf-8", errors="ignore")
                        h.update(rel)
                        h.update(int(st.st_size).to_bytes(8, 'little', signed=False))
                        h.update(int(st.st_mtime_ns).to_bytes(8, 'little', signed=False))
                    except Exception:
                        continue
        return h.hexdigest()

    def make_backup(self) -> Optional[Path]:
        if not self._lock.acquire(blocking=False):
            self.logger.warning("Backup already in progress; skipping new request")
            try:
                self.db.insert_backup(ts=dt.datetime.now(), path=None, status="SKIP",
                                      size_bytes=None, duration_sec=None, rc=None, stderr="In-progress",
                                      fingerprint=None)
            except Exception:
                pass
            return None
        try:
            start = dt.datetime.now()
            try:
                current_fp = self._compute_fingerprint()
            except Exception as e:
                current_fp = None
                self.logger.warning(f"Fingerprint error: {e}")
            try:
                last_fp = self.db.last_fingerprint()
            except Exception:
                last_fp = None
            if current_fp and last_fp and current_fp == last_fp:
                self.logger.info("No changes detected in 1C base. Skipping backup.")
                try:
                    self.db.insert_backup(ts=start, path=None, status="SKIP",
                                          size_bytes=None, duration_sec=0.0, rc=0, stderr=None, fingerprint=current_fp)
                except Exception as e:
                    self.logger.warning(f"DB insert failed (SKIP): {e}")
                
                return None

            # Create date-based subfolder (YYYY-MM-DD)
            date_folder = start.strftime("%Y-%m-%d")
            backup_folder = self.backup_dir / date_folder
            backup_folder.mkdir(parents=True, exist_ok=True)
            
            ts = start.strftime("%Y-%m-%d_%H-%M-%S")
            dt_file = backup_folder / f"{self.file_prefix}{ts}.dt"

            try:
                res = self._onec_dump(dt_file)
                duration = (dt.datetime.now() - start).total_seconds()
                stderr = (res.stderr or "").strip()
                size_bytes = dt_file.stat().st_size if dt_file.exists() else None

                if res.returncode == 0 and dt_file.exists():
                    final_path = dt_file
                    if hasattr(self, 'compress') and (self.compress or '').lower() == 'zip':
                        zip_path = dt_file.with_suffix('.zip')
                        self.logger.info(f"Compressing to ZIP: {zip_path} (level={getattr(self, 'compress_level', 6)})")
                        try:
                            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=getattr(self, 'compress_level', 6)) as zf:
                                zf.write(dt_file, arcname=dt_file.name)
                            if getattr(self, 'delete_dt_after_compress', False):
                                dt_file.unlink(missing_ok=True)
                            final_path = zip_path
                            size_bytes = final_path.stat().st_size
                        except Exception as e:
                            self.logger.warning(f"Compression failed, keeping .dt: {e}")

                    self.logger.info(f"OK: backup created {final_path} ({size_bytes} bytes) in {duration:.1f}s")
                    try:
                        self.db.insert_backup(ts=start, path=str(final_path), status="OK",
                                              size_bytes=size_bytes, duration_sec=duration, rc=res.returncode, stderr=stderr,
                                              fingerprint=current_fp)
                    except Exception as e:
                        self.logger.warning(f"DB insert failed: {e}")
                    
                    return final_path
                else:
                    self.logger.error(f"ERR: 1C returned {res.returncode}. stderr={stderr}")
                    try:
                        self.db.insert_backup(ts=start, path=str(dt_file), status="ERR",
                                              size_bytes=size_bytes, duration_sec=duration, rc=res.returncode, stderr=stderr,
                                              fingerprint=current_fp)
                    except Exception as e:
                        self.logger.warning(f"DB insert failed: {e}")
                    
                    return None
            except Exception as e:
                self.logger.exception("Exception during backup: %s", e)
                try:
                    self.db.insert_backup(ts=start, path=str(dt_file), status="EXC",
                                          size_bytes=None, duration_sec=None, rc=None, stderr=str(e),
                                          fingerprint=current_fp)
                except Exception:
                    pass
                
                return None
        finally:
            self._lock.release()

