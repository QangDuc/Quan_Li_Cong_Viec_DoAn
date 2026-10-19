#!/usr/bin/env python3
"""
XUẤT DANH MỤC + GIÁ TRỊ ĐIỂN HÌNH TỪ MÔ HÌNH ĐÃ LƯU (chỉ đọc model/risk_model.joblib, không sửa).

  python backend/scripts/export_catalog.py

Mục đích: CSDL web phải dùng ĐÚNG các giá trị phân loại mà bộ mã hóa của mô hình đã thấy (giá trị lạ -> coi là thiếu),
và các giá trị "điển hình" theo loại việc (thời lượng điển hình, giờ chuẩn quy đổi) phải cùng thang với lúc huấn luyện.
Mọi giá trị ở đây suy ra từ NGỮ CẢNH (40.000 dòng) đã lưu trong mô hình — tức là từ DỮ LIỆU MÔ PHỎNG, không phải văn bản của Trường.
Ghi ra backend/app/seed_data/catalog.json.
"""
import json, os
import joblib, numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL = os.path.join(ROOT, "model", "risk_model.joblib")
OUT = os.path.join(ROOT, "backend", "app", "seed_data", "catalog.json")
SCALES = ["quy mô nhỏ", "quy mô chuẩn", "quy mô lớn"]


def r2(v):
    return None if v is None or v != v else round(float(v), 2)


def main():
    m = joblib.load(MODEL)
    X = pd.DataFrame(np.vstack([c[0] for c in m["contexts"]]), columns=m["features"])
    inv = {c: {v: k for k, v in mp.items()} for c, mp in m["encoder"]["maps"].items()}
    for c in inv:
        X[c] = X[c].map(inv[c])
    X["scale"] = X.task_subtype.str.split(" - ").str[-1]

    types = []
    for t, g in X.groupby("task_type"):
        sub = {}
        for sc in SCALES:
            gs = g[g.scale == sc]
            if len(gs):
                sub[sc] = dict(expected_duration_days=r2(gs.expected_duration_days.median()),
                               converted_workload=r2(gs.converted_workload.median()) if gs.converted_workload.notna().any() else None,
                               n=int(len(gs)))
        types.append(dict(
            name=t,
            task_group=g.task_group.value_counts().index[0],
            scales=sub,
            # mặc định khi tạo việc (trung vị theo loại việc)
            default_complexity=g.complexity.value_counts().index[0],
            default_subtask_count=int(g.subtask_count.median()) if g.subtask_count.notna().any() else 1,
            default_dependency_count=int(g.dependency_count.median()) if g.dependency_count.notna().any() else 0,
            has_conversion=bool(g.converted_workload.notna().any()),
        ))
    out = dict(
        source="Suy ra từ ngữ cảnh đã lưu trong model/risk_model.joblib (dữ liệu mô phỏng)",
        categories={c: sorted(inv[c].values()) for c in m["encoder"]["cat"]},
        task_types=types,
        # phân phối hồ sơ GV trong ngữ cảnh -> dùng để sinh dữ liệu mẫu MÔ PHỎNG cho hợp thang
        profile_quantiles={c: [r2(X[c].quantile(q)) for q in (0.1, 0.25, 0.5, 0.75, 0.9)]
                           for c in ["years_experience", "tenure_days", "teaching_hours_semester", "student_count",
                                     "supervised_student_count", "hist_avg_delay", "hist_early_rate", "hist_late_rate"]},
        profile_shares={c: X[c].value_counts(normalize=True).round(3).to_dict()
                        for c in ["academic_rank", "degree", "management_role"]},
        # giờ công TB một việc đến hạn trong 14 ngày (để ước lượng estimated_effort_hours mặc định)
        hours_per_due_task=r2((X.workload_next_14d / X.deadlines_next_14d.replace(0, np.nan)).median()),
        baseline={k: (r2(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in m["baseline"].items()},
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Đã ghi {OUT}: {len(types)} loại việc, {len(out['categories']['department'])} bộ môn")


if __name__ == "__main__":
    main()
