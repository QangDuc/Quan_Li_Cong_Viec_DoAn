"""Kho phiên bản mô hình: mỗi phiên bản BẤT BIẾN (không ghi đè), con trỏ CURRENT đổi nguyên tử, lịch sử ghi vào history.jsonl.
Quay lại (rollback) = trả CURRENT về phiên bản đang chạy trước đó."""
import hashlib, json, os, warnings
import joblib
import pandas as pd


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


class ModelRegistry:
    def __init__(self, root):
        self.root = root
        os.makedirs(os.path.join(root, "versions"), exist_ok=True)

    def _p(self, *a):
        return os.path.join(self.root, *a)

    def _log(self, event, now=None, **kw):
        rec = dict(ts=str(pd.Timestamp(now) if now is not None else pd.Timestamp.now()), event=event, **kw)
        with open(self._p("history.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

    def history(self):
        p = self._p("history.jsonl")
        return [json.loads(x) for x in open(p, encoding="utf-8")] if os.path.exists(p) else []

    def versions(self):
        return sorted(os.listdir(self._p("versions")))

    def current(self):
        p = self._p("CURRENT")
        return open(p, encoding="utf-8").read().strip() if os.path.exists(p) else None

    def _set_current(self, v):
        tmp = self._p("CURRENT.tmp")
        open(tmp, "w", encoding="utf-8").write(v)
        os.replace(tmp, self._p("CURRENT"))

    def register(self, bundle, meta, now=None):
        """Lưu phiên bản mới (chưa chạy). Trả về mã phiên bản, ví dụ v0003."""
        import sklearn
        vs = self.versions()
        v = f"v{(int(vs[-1][1:]) + 1) if vs else 1:04d}"
        d = self._p("versions", v)
        os.makedirs(d)
        joblib.dump(bundle, os.path.join(d, "model.joblib"))
        meta = dict(meta, version=v, sha256=_sha(os.path.join(d, "model.joblib")), sklearn=sklearn.__version__,
                    thresholds=bundle.get("thresholds"), data_end=bundle.get("data_end"))
        json.dump(meta, open(os.path.join(d, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=str)
        self._log("register", now, version=v)
        return v

    def promote(self, v, reason="", now=None):
        if v not in self.versions():
            raise KeyError(v)
        prev = self.current()
        self._set_current(v)
        self._log("promote", now, version=v, previous=prev, reason=reason)

    def rollback(self, reason="", now=None):
        """Trả về phiên bản chạy ngay trước đó (lặp lại được nhiều bước)."""
        stack = []
        for e in self.history():
            if e["event"] == "promote":
                stack.append(e["version"])
            elif e["event"] == "rollback" and stack:
                stack.pop()
        if len(stack) < 2:
            raise RuntimeError("không có phiên bản trước để quay lại")
        bad, good = stack[-1], stack[-2]
        self._set_current(good)
        self._log("rollback", now, version=good, rolled_back=bad, reason=reason)
        return good

    def meta(self, v=None):
        v = v or self.current()
        return json.load(open(self._p("versions", v, "meta.json"), encoding="utf-8"))

    def load(self, v=None):
        """Nạp mô hình. Kiểm tra SHA-256 (toàn vẹn) và cảnh báo lệch phiên bản scikit-learn. CHỈ nạp từ nguồn tin cậy (joblib = pickle)."""
        import sklearn
        v = v or self.current()
        m = self.meta(v)
        f = self._p("versions", v, "model.joblib")
        if _sha(f) != m["sha256"]:
            raise RuntimeError(f"{v}: SHA-256 không khớp, file bị thay đổi")
        if m.get("sklearn") != sklearn.__version__:
            warnings.warn(f"{v} huấn luyện với scikit-learn {m.get('sklearn')} nhưng đang chạy {sklearn.__version__}")
        return joblib.load(f)
