"""Học tiếp TỰ ĐỘNG có rào chắn (dành cho TabPFN trên máy có GPU). Chạy theo lịch (ví dụ hằng quý) bằng:
    python -m hoc_tiep.cli retrain-auto --registry registry --store feedback.db --base data/ml_training_set_with_matrix.csv \
        --mode auto --service-url http://localhost:8001
Các bước: khóa tệp (một job một lúc) -> huấn luyện lại + so sánh + rào chắn (retrain_job.run) -> nếu nâng cấp: chờ dịch vụ nạp phiên bản mới
(/health.registry_version) -> nếu dịch vụ không nạp được hoặc lỗi thì QUAY LẠI phiên bản trước -> ghi quyết định ra last_decision.json.
Chế độ: dry-run (mặc định, chỉ ghi quyết định) | auto (nâng cấp thật). Mã thoát: 0 thành công (kể cả giữ nguyên), 2 lỗi, 3 đang có job khác chạy."""
import json, os, time
import pandas as pd

from . import retrain_job
from .config import Config
from .tabpfn_backend import get_backend


class JobLocked(RuntimeError):
    pass


class _Lock:
    """Khóa bằng tệp tạo nguyên tử; khóa cũ hơn stale_hours bị coi là bỏ hoang (job trước chết giữa chừng)."""
    def __init__(self, path, stale_hours=12):
        self.path, self.stale = path, stale_hours * 3600

    def __enter__(self):
        if os.path.exists(self.path) and time.time() - os.path.getmtime(self.path) > self.stale:
            os.remove(self.path)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise JobLocked(f"đang có job học tiếp khác chạy ({self.path})")
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
        return self

    def __exit__(self, *a):
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass


def _wait_service(url, version, timeout=120, interval=3, fetch=None):
    """Chờ /health báo registry_version == version. fetch(url) -> dict, mặc định dùng httpx."""
    if fetch is None:
        import httpx
        fetch = lambda u: httpx.get(u.rstrip("/") + "/health", timeout=90).json()
    t0, last = time.time(), None
    while time.time() - t0 < timeout:
        try:
            h = fetch(url); last = h
            if h.get("status") == "ok" and h.get("registry_version") == version:
                return True, h
        except Exception as e:      # dịch vụ đang khởi động lại
            last = {"error": str(e)[:200]}
        time.sleep(interval)
    return False, last


def run_auto(store, registry, base_df, as_of, cfg=None, mode="dry-run", service_url=None, backend_kw=None,
             wait_timeout=120, fetch=None, now=None):
    cfg = cfg or Config()
    assert mode in ("dry-run", "auto")
    with _Lock(os.path.join(registry.root, "retrain.lock")):
        cur = registry.load(registry.current())
        backend = get_backend(cur.get("backend", "hgb"), **(backend_kw or {}))
        t0 = time.time()
        dec = retrain_job.run(store, registry, base_df, as_of, cfg, backend=backend, dry_run=(mode != "auto"), now=now)
        dec["mode"], dec["seconds"] = mode, round(time.time() - t0, 1)
        dec["service_check"] = None
        if dec.get("promoted") and service_url:
            ok, h = _wait_service(service_url, dec["candidate"], wait_timeout, fetch=fetch)
            dec["service_check"] = dict(ok=ok, health=h)
            if not ok:
                dec["promoted"] = False
                dec["rolled_back_to"] = registry.rollback(f"dịch vụ không nạp được {dec['candidate']}", now=now)
                dec["reasons"].append(f"dịch vụ không nạp được {dec['candidate']}: đã quay lại {dec['rolled_back_to']}")
        out = {k: v for k, v in dec.items() if k != "details"}
        if "details" in dec:
            out["delta"] = dec["details"]["delta"]
        with open(os.path.join(registry.root, "last_decision.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1, default=str)
        return dec
