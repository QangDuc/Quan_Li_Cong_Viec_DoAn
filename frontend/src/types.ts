export const API_BASE = "http://localhost:8000/api";

export const FEATURE_LABELS_VI: Record<string, string> = {
  lead_time_days: "Số ngày từ lúc giao đến hạn chót",
  expected_duration_days: "Thời lượng thực hiện điển hình",
  lead_vs_expected_ratio: "Tỷ lệ thời hạn / định mức kỳ vọng",
  is_Compressed: "Thời hạn gấp so với định mức",
  complexity_num: "Độ phức tạp công việc",
  priority_num: "Mức độ ưu tiên công việc",
  subtask_count: "Số đầu việc con",
  dependency_count: "Số phụ thuộc đầu vào",
  require_external_input: "Phụ thuộc dữ liệu đơn vị ngoài",
  require_approval: "Yêu cầu phê duyệt nhiều cấp",
  current_open_tasks: "Số việc đang thực hiện đồng thời",
  current_high_priority_open_tasks: "Số việc ưu tiên cao đang mở",
  current_overdue_tasks: "Số việc đang quá hạn",
  current_due_within_7d_tasks: "Số việc sắp đến hạn trong 7 ngày",
  workload_vs_teaching_Load: "Tải công việc so với giờ giảng dạy",
  teaching_hours_semester: "Số giờ giảng dạy trong học kỳ",
  supervised_student_count: "Số sinh viên hướng dẫn KLTN/ĐA",
  student_count: "Tổng số sinh viên lớp giảng dạy",
  hist_completed_count: "Số việc đã hoàn thành trong lịch sử",
  hist_late_rate_smooth: "Tỷ lệ trễ hạn lịch sử của cá nhân",
  hist_recent_late_rate_5: "Tỷ lệ trễ 5 công việc gần nhất",
  hist_avg_delay_days: "Số ngày trễ trung bình lịch sử",
  mat_lecturer_type_late_rate: "Tỷ lệ trễ của GV ở loại việc này",
  mat_lecturer_type_count: "Kinh nghiệm của GV ở loại việc này",
  mat_dept_type_late_rate: "Tỷ lệ trễ trung bình của Bộ môn",
  mat_global_type_late_rate: "Tỷ lệ trễ trung bình toàn Khoa",
  accreditation_overlap_days: "Trùng đợt cao điểm kiểm định chất lượng",
  accreditation_flag: "Giao trong đợt kiểm định chất lượng",
  holiday_overlap_days: "Trùng kỳ nghỉ Lễ / Tết Nguyên Đán",
  holiday_in_window: "Có ngày nghỉ lễ trong thời gian làm",
  peak_season: "Mùa cao điểm học vụ (Thi/Nộp điểm/KLTN)",
  is_new_lecturer: "Giảng viên mới (< 5 công việc lịch sử)",
};

export function formatFeatureName(feat: string): string {
  return FEATURE_LABELS_VI[feat] || feat;
}

export interface TopFactor {
  feature: string;
  direction: string;
  delta_logit: number;
}

export interface MLPredictionInfo {
  id?: number;
  status?: string;
  probability: number | null;
  level: string;
  uncertainty?: number | null;
  top_factors?: TopFactor[];
  recommendation?: string;
  notes?: string;
  low_confidence?: boolean;
  actual_is_late?: boolean | null;
  is_correct?: boolean | null;
}
