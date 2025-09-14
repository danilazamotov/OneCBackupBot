from __future__ import annotations

import hashlib
import subprocess
import shutil
import datetime as dt
import os
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import zipfile

from .uptime import push_status


class BackupService:
    def __init__(self, *, onec_exe: str, base_path: str, uc: str, up: str,
                 backup_dir: str, file_prefix: str,
                 keep_hourly_days: int, keep_daily_count: int, keep_monthly_count: int,
                 daily_copy_hour: int, monthly_copy_day: int, monthly_copy_hour: int,
                 logger, db, uptime_push_url: str = ""):
        self.onec_exe = onec_exe
        self.base_path = base_path
        self.uc = uc or None
        self.up = up or None
        self.backup_dir = Path(backup_dir)
        self.file_prefix = file_prefix
        self.keep_hourly_days = keep_hourly_days
        self.keep_daily_count = keep_daily_count
        self.keep_monthly_count = keep_monthly_count
        self.daily_copy_hour = daily_copy_hour
        self.monthly_copy_day = monthly_copy_day
        self.monthly_copy_hour = monthly_copy_hour
        self.logger = logger
        self.db = db
        self.uptime_push_url = uptime_push_url

        self._lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="backup")
        self.dump_timeout_sec = getattr(self, 'dump_timeout_sec', 7200)

        hourly = getattr(self, 'hourly_subdir', 'Hourly')
        daily = getattr(self, 'daily_subdir', 'Daily')
        monthly = getattr(self, 'monthly_subdir', 'Monthly')
        (self.backup_dir / hourly).mkdir(parents=True, exist_ok=True)
        (self.backup_dir / daily).mkdir(parents=True, exist_ok=True)
        (self.backup_dir / monthly).mkdir(parents=True, exist_ok=True)

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
                push_status(self.uptime_push_url, "up", "No changes, backup skipped")
                return None

            ts = start.strftime("%Y-%m-%d_%H-%M")
            hourly_dir = self.backup_dir / getattr(self, 'hourly_subdir', 'Hourly')
            dt_file = hourly_dir / f"{self.file_prefix}{ts}.dt"

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
                    push_status(self.uptime_push_url, "up", "Backup OK")
                    return final_path
                else:
                    self.logger.error(f"ERR: 1C returned {res.returncode}. stderr={stderr}")
                    try:
                        self.db.insert_backup(ts=start, path=str(dt_file), status="ERR",
                                              size_bytes=size_bytes, duration_sec=duration, rc=res.returncode, stderr=stderr,
                                              fingerprint=current_fp)
                    except Exception as e:
                        self.logger.warning(f"DB insert failed: {e}")
                    push_status(self.uptime_push_url, "down", "Dump failed")
                    return None
            except Exception as e:
                self.logger.exception("Exception during backup: %s", e)
                try:
                    self.db.insert_backup(ts=start, path=str(dt_file), status="EXC",
                                          size_bytes=None, duration_sec=None, rc=None, stderr=str(e),
                                          fingerprint=current_fp)
                except Exception:
                    pass
                push_status(self.uptime_push_url, "down", "Exception")
                return None
        finally:
            self._lock.release()

    def rotate_backups(self, last_hourly_path: Optional[Path]):
        now = dt.datetime.now()
        hourly_dir = self.backup_dir / getattr(self, 'hourly_subdir', 'Hourly')
        daily_dir = self.backup_dir / getattr(self, 'daily_subdir', 'Daily')
        monthly_dir = self.backup_dir / getattr(self, 'monthly_subdir', 'Monthly')
        yearly_dir = self.backup_dir / getattr(self, 'yearly_subdir', 'Yearly')
        halfyearly_dir = self.backup_dir / getattr(self, 'halfyearly_subdir', 'HalfYearly')

        removed_h = 0
        for name in list(os.listdir(hourly_dir)):
            p = hourly_dir / name
            if p.is_file() and p.suffix.lower() in {'.dt', '.zip'}:
                age_days = (now - dt.datetime.fromtimestamp(p.stat().st_mtime)).days
                if age_days > self.keep_hourly_days:
                    try:
                        p.unlink()
                        removed_h += 1
                    except Exception as e:
                        self.logger.warning(f"Can't remove {p}: {e}")
        if removed_h:
            self.logger.info(f"Hourly rotation: removed {removed_h} old files")

        if last_hourly_path and now.hour == self.daily_copy_hour:
            suffix = Path(last_hourly_path).suffix
            dst = daily_dir / f"{self.file_prefix}{now.strftime('%Y-%m-%d')}{suffix}"
            try:
                shutil.copy2(last_hourly_path, dst)
                self.logger.info(f"Daily copy saved: {dst}")
            except Exception as e:
                self.logger.warning(f"Daily copy failed: {e}")

            files = sorted([p for p in daily_dir.iterdir() if p.is_file() and p.suffix.lower() in {'.dt', '.zip'}], key=lambda p: p.stat().st_mtime, reverse=True)
            for old in files[self.keep_daily_count:]:
                try:
                    old.unlink()
                except Exception as e:
                    self.logger.warning(f"Can't remove daily {old}: {e}")

        if last_hourly_path and now.day == self.monthly_copy_day and now.hour == self.monthly_copy_hour:
            suffix = Path(last_hourly_path).suffix
            dst = monthly_dir / f"{self.file_prefix}{now.strftime('%Y-%m')}{suffix}"
            try:
                shutil.copy2(last_hourly_path, dst)
                self.logger.info(f"Monthly copy saved: {dst}")
            except Exception as e:
                self.logger.warning(f"Monthly copy failed: {e}")

            files = sorted([p for p in monthly_dir.iterdir() if p.is_file() and p.suffix.lower() in {'.dt', '.zip'}], key=lambda p: p.stat().st_mtime, reverse=True)
            for old in files[self.keep_monthly_count:]:
                try:
                    old.unlink()
                except Exception as e:
                    self.logger.warning(f"Can't remove monthly {old}: {e}")

        yearly_dir.mkdir(parents=True, exist_ok=True)
        if (
            last_hourly_path
            and now.month == getattr(self, 'yearly_copy_month', 1)
            and now.day == getattr(self, 'yearly_copy_day', 1)
            and now.hour == getattr(self, 'yearly_copy_hour', 23)
        ):
            suffix = Path(last_hourly_path).suffix
            dst = yearly_dir / f"{self.file_prefix}{now.strftime('%Y')}{suffix}"
            try:
                shutil.copy2(last_hourly_path, dst)
                self.logger.info(f"Yearly copy saved: {dst}")
            except Exception as e:
                self.logger.warning(f"Yearly copy failed: {e}")

            files = sorted([p for p in yearly_dir.iterdir() if p.is_file() and p.suffix.lower() in {'.dt', '.zip'}], key=lambda p: p.stat().st_mtime, reverse=True)
            for old in files[getattr(self, 'keep_yearly_count', 5)]:
                try:
                    old.unlink()
                except Exception as e:
                    self.logger.warning(f"Can't remove yearly {old}: {e}")

        halfyearly_dir.mkdir(parents=True, exist_ok=True)
        try:
            months = set(getattr(self, 'halfyearly_months', [1, 7]) or [1, 7])
        except Exception:
            months = {1, 7}
        if (
            last_hourly_path
            and now.month in months
            and now.day == getattr(self, 'halfyearly_copy_day', 1)
            and now.hour == getattr(self, 'halfyearly_copy_hour', 23)
        ):
            suffix = Path(last_hourly_path).suffix
            half = 1 if now.month <= 6 else 2
            dst = halfyearly_dir / f"{self.file_prefix}{now.strftime('%Y')}-H{half}{suffix}"
            try:
                shutil.copy2(last_hourly_path, dst)
                self.logger.info(f"HalfYearly copy saved: {dst}")
            except Exception as e:
                self.logger.warning(f"HalfYearly copy failed: {e}")

            files = sorted([p for p in halfyearly_dir.iterdir() if p.is_file() and p.suffix.lower() in {'.dt', '.zip'}], key=lambda p: p.stat().st_mtime, reverse=True)
            for old in files[getattr(self, 'keep_halfyearly_count', 6):]:
                try:
                    old.unlink()
                except Exception as e:
                    self.logger.warning(f"Can't remove halfyearly {old}: {e}")
