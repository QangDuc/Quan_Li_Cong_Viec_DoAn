from dataclasses import dataclass, asdict


@dataclass
class Config:
    # --- cửa sổ thời gian (ngày). Chỉ dùng các việc "đã chín": giao trước as_of - maturity_days ---
    maturity_days: int = 120      # P90 thời gian giao->hoàn thành trên bộ v2 = 90 ngày [đo]; thêm đệm vì nhãn chưa xong thường là việc trễ
    holdout_days: int = 90        # cửa sổ giữ lại để so sánh ứng viên với mô hình hiện tại (mô hình hiện tại CHƯA thấy)
    val_days: int = 90            # cửa sổ chọn ngưỡng mức cảnh báo cho ứng viên
    # --- rào chắn dữ liệu ---
    min_new_labeled: int = 2000   # số việc mới có nhãn (giao sau mô hình hiện tại)
    min_new_late: int = 200
    min_holdout_rows: int = 2000
    min_holdout_late: int = 200
    min_holdout_lecturers: int = 30
    late_rate_bounds: tuple = (0.05, 0.50)
    max_missing_feature_share: float = 0.05
    # --- rào chắn chất lượng (so cặp theo cụm giảng viên, KTC 95%) ---
    auc_noninf_margin: float = 0.002      # cận dưới KTC của ΔAUC phải >= -margin
    logloss_noninf_margin: float = 0.002  # cận trên KTC của Δlogloss phải <= +margin
    require_significant_gain: bool = True  # chỉ nâng cấp khi Δlogloss có cận trên KTC < 0 (tốt hơn có ý nghĩa)
    min_auc: float = 0.65
    n_boot: int = 300
    seed: int = 0
    # --- mức cảnh báo (cùng mục tiêu với train_model.pick_thresholds) ---
    max_late_low: float = 0.10
    min_prec_high: float = 0.60
    level_slack_low: float = 0.02
    level_slack_high: float = 0.05
    # --- chính sách khi có can thiệp: exclude = loại việc đã được can thiệp khỏi dữ liệu huấn luyện ---
    intervention_policy: str = "exclude"

    def to_dict(self):
        return asdict(self)
