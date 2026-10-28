"""Dòng lệnh. Ví dụ:
  python -m hoc_tiep.cli init     --base data/ml_training_set_with_matrix.csv --registry registry --cutoff 2025-12-31
  python -m hoc_tiep.cli predict  --registry registry --store feedback.db --input viec_moi.csv --output ketqua.csv
  python -m hoc_tiep.cli outcome  --store feedback.db --input ket_qua_that.csv      # task_id,lecturer_id,completed_date,is_late
  python -m hoc_tiep.cli retrain  --registry registry --store feedback.db --base data/ml_training_set_with_matrix.csv --as-of 2026-07-01 [--dry-run]
  python -m hoc_tiep.cli status   --registry registry --store feedback.db
  python -m hoc_tiep.cli rollback --registry registry --reason "..."
  python -m hoc_tiep.cli export   --store feedback.db --as-of 2026-07-01 --output viec_co_nhan.csv   # để huấn luyện TabPFN trên Colab
  python -m hoc_tiep.cli compare  --input du_doan.csv    # cột: y, p_current, p_candidate, lecturer_id (đường TabPFN)"""
import argparse, json
import pandas as pd
from .config import Config
from .feedback_store import FeedbackStore
from .model_registry import ModelRegistry
from . import retrain_job
from .serving import RiskService


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hoc_tiep")
    sp = ap.add_subparsers(dest="cmd", required=True)
    for n in ["init", "predict", "outcome", "retrain", "status", "rollback", "compare", "export"]:
        p = sp.add_parser(n)
        p.add_argument("--registry", default="registry"); p.add_argument("--store", default="feedback.db")
        p.add_argument("--base"); p.add_argument("--input"); p.add_argument("--output"); p.add_argument("--cutoff")
        p.add_argument("--as-of"); p.add_argument("--dry-run", action="store_true"); p.add_argument("--reason", default="")
        p.add_argument("--thr-current", default="0.2,0.5"); p.add_argument("--thr-candidate", default="0.2,0.5")
    a = ap.parse_args(argv)
    cfg = Config()
    if a.cmd == "init":
        d = pd.read_csv(a.base, parse_dates=["assigned_date"])
        if a.cutoff:
            d = d[d.assigned_date <= pd.Timestamp(a.cutoff)]
        print("đã tạo", retrain_job.init_model(d, ModelRegistry(a.registry), cfg))
    elif a.cmd == "predict":
        svc = RiskService(ModelRegistry(a.registry), FeedbackStore(a.store))
        r = svc.predict(pd.read_csv(a.input, parse_dates=["assigned_date"]))
        r.to_csv(a.output, index=False, encoding="utf-8-sig"); print(r.model_version.iloc[0], len(r), "dòng")
    elif a.cmd == "outcome":
        print("đã ghi", FeedbackStore(a.store).record_outcomes(pd.read_csv(a.input)), "kết quả")
    elif a.cmd == "retrain":
        d = pd.read_csv(a.base, parse_dates=["assigned_date"])
        dec = retrain_job.run(FeedbackStore(a.store), ModelRegistry(a.registry), d, a.as_of, cfg, dry_run=a.dry_run)
        print(json.dumps({k: v for k, v in dec.items() if k != "details"}, ensure_ascii=False, indent=1, default=str))
    elif a.cmd == "status":
        r = ModelRegistry(a.registry)
        print("CURRENT:", r.current(), "| phiên bản:", r.versions()); print(json.dumps(FeedbackStore(a.store).stats(), ensure_ascii=False, indent=1))
        for e in r.history()[-8:]:
            print(e["ts"][:10], e["event"], e.get("version") or e.get("candidate") or "", (e.get("reasons") or e.get("reason") or ""))
    elif a.cmd == "rollback":
        print("đã quay lại", ModelRegistry(a.registry).rollback(a.reason))
    elif a.cmd == "export":      # đường TabPFN: xuất việc có nhãn từ kho phản hồi để huấn luyện trên Colab bằng train_model.py
        fb = FeedbackStore(a.store).labeled_frame(a.as_of, intervention_policy=cfg.intervention_policy)
        fb.drop(columns=["completed_date", "risk_logged", "model_version_logged", "intervened"]).to_csv(a.output, index=False, encoding="utf-8-sig")
        print("đã xuất", len(fb), "việc có nhãn ->", a.output)
    elif a.cmd == "compare":
        d = pd.read_csv(a.input)
        ok, checks, det = retrain_job.gate(d.y.values, d.p_current.values, d.p_candidate.values, d.lecturer_id.values,
                                           [float(x) for x in a.thr_current.split(",")], [float(x) for x in a.thr_candidate.split(",")], cfg)
        print("ĐẠT" if ok else "KHÔNG ĐẠT")
        for k, v in checks.items(): print(("  ✓ " if v[0] else "  ✗ ") + k + ": " + v[1])
        print(json.dumps(det["delta"], indent=1))


if __name__ == "__main__":
    main()
