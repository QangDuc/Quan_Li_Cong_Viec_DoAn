"""
Khởi tạo bảng và nạp dữ liệu mẫu ban đầu + Hồ sơ giả lập 1 năm công việc của Giảng viên (2026-2027):
- 24 Bộ môn
- 35 Loại công việc & thang quy đổi
- Danh mục công việc cấp Trường (FR-06)
- Người dùng mẫu (Admin, Trưởng Khoa TS. Nguyễn Văn Lễ, Trưởng Bộ môn, Giảng viên)
- Hồ sơ công việc 1 năm (HK1, HK2, Hè 2026-2027) của ThS. Nguyễn Minh Khoa (gv_k01_1 - GV0101),
  TS. Trần Thị Mai Anh (gv_k01_2 - GV0102) và ThS. Lê Hoàng Nam (gv_k01_3 - GV0103, nhóm Cold-Start < 5 việc).
"""
import os
import sys
import json
from datetime import date, datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


from sqlalchemy.orm import Session
from app.db import engine, SessionLocal, Base
from app.models import (
    Department, User, LecturerProfile, TaskType, TaskTypeScale,
    SchoolCatalogItem, CalendarEvent, Plan, Task, TaskAssignment,
    ProgressUpdate, ExtensionRequest, Notification, RiskPrediction,
    ROLE_ADMIN, ROLE_MANAGER, ROLE_LECTURER,
    ST_NEW, ST_DOING, ST_DONE, EXT_PENDING, EXT_APPROVED
)
from app.security import hash_password

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "seed_data", "catalog.json")


def init_db(reset: bool = False):
    if reset:
        print("Đang xóa và tạo lại toàn bộ bảng CSDL...")
        Base.metadata.drop_all(bind=engine)
    print("Đang tạo bảng CSDL...")
    Base.metadata.create_all(bind=engine)
    print("Đã tạo xong bảng.")


def seed(reset: bool = False):
    init_db(reset=reset)
    db = SessionLocal()
    try:
        if db.query(Department).first():
            print("CSDL đã có dữ liệu mẫu, bỏ qua seed.")
            return

        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        print("1. Seed Departments...")
        dept_map = {}
        for dept_str in catalog["categories"]["department"]:
            parts = dept_str.split(" - ")
            code = parts[0].strip()
            name = parts[1].strip() if len(parts) > 1 else code
            d = Department(code=dept_str, name=f"{name} ({code})", ml_name=dept_str)
            db.add(d)
            db.flush()
            dept_map[dept_str] = d

        print("2. Seed Task Types & Scales (Chuẩn hóa theo khung Thông tư 20/2020/TT-BGDĐT)...")
        # Định mức giờ chuẩn quy đổi và số ngày thực hiện chuẩn hóa (số nguyên / 0.5h, đơn điệu theo quy mô)
        # Căn cứ khung chế độ làm việc giảng viên ĐH tại Thông tư 20/2020/TT-BGDĐT (270 giờ chuẩn giảng dạy / 1.760 giờ hành chính/năm)
        STANDARD_SCALES = {
            "Chuẩn bị bài giảng/cập nhật slide": {"quy mô nhỏ": (4.0, 3), "quy mô chuẩn": (6.0, 5), "quy mô lớn": (8.0, 7)},
            "Chuẩn bị bài thực hành/lab CNTT": {"quy mô nhỏ": (5.0, 3), "quy mô chuẩn": (7.0, 5), "quy mô lớn": (10.0, 7)},
            "Chuẩn bị tiếp đoàn đánh giá": {"quy mô nhỏ": (12.0, 14), "quy mô chuẩn": (15.0, 21), "quy mô lớn": (20.0, 30)},
            "Chấm bài tập/đồ án môn học": {"quy mô nhỏ": (5.0, 3), "quy mô chuẩn": (7.0, 5), "quy mô lớn": (10.0, 7)},
            "Chấm thi cuối kỳ": {"quy mô nhỏ": (6.0, 4), "quy mô chuẩn": (9.0, 6), "quy mô lớn": (12.0, 9)},
            "Chấm/phản biện khóa luận": {"quy mô nhỏ": (3.0, 4), "quy mô chuẩn": (4.0, 6), "quy mô lớn": (6.0, 8)},
            "Coi thi": {"quy mô nhỏ": (1.0, 1), "quy mô chuẩn": (1.5, 1), "quy mô lớn": (2.0, 2)},
            "Công tác Đảng/đoàn thể/công đoàn": {"quy mô nhỏ": (2.0, 2), "quy mô chuẩn": (3.0, 4), "quy mô lớn": (4.0, 6)},
            "Cố vấn học tập": {"quy mô nhỏ": (12.0, 120), "quy mô chuẩn": (15.0, 150), "quy mô lớn": (18.0, 180)},
            "Giảng dạy học phần": {"quy mô nhỏ": (30.0, 75), "quy mô chuẩn": (45.0, 105), "quy mô lớn": (60.0, 135)},
            "Hoạt động chuyển giao/tư vấn CNTT": {"quy mô nhỏ": (15.0, 30), "quy mô chuẩn": (25.0, 60), "quy mô lớn": (40.0, 90)},
            "Hướng dẫn khóa luận/đồ án tốt nghiệp": {"quy mô nhỏ": (20.0, 90), "quy mô chuẩn": (25.0, 120), "quy mô lớn": (30.0, 150)},
            "Hướng dẫn luận văn cao học": {"quy mô nhỏ": (30.0, 120), "quy mô chuẩn": (35.0, 180), "quy mô lớn": (40.0, 240)},
            "Hướng dẫn đồ án môn học": {"quy mô nhỏ": (5.0, 45), "quy mô chuẩn": (7.0, 75), "quy mô lớn": (9.0, 90)},
            "Họp lớp/CVHT định kỳ": {"quy mô nhỏ": (1.0, 1), "quy mô chuẩn": (1.5, 2), "quy mô lớn": (2.0, 3)},
            "Hội thảo/chuyên đề cho cộng đồng": {"quy mô nhỏ": (6.0, 7), "quy mô chuẩn": (8.0, 12), "quy mô lớn": (10.0, 20)},
            "Kết nối doanh nghiệp/thực tập": {"quy mô nhỏ": (6.0, 10), "quy mô chuẩn": (8.0, 15), "quy mô lớn": (10.0, 21)},
            "Ngày hội tư vấn tuyển sinh": {"quy mô nhỏ": (4.0, 2), "quy mô chuẩn": (6.0, 3), "quy mô lớn": (8.0, 5)},
            "Nhập/nộp điểm": {"quy mô nhỏ": (1.0, 2), "quy mô chuẩn": (1.5, 3), "quy mô lớn": (2.0, 4)},
            "Phản biện/duyệt đề thi": {"quy mô nhỏ": (1.5, 2), "quy mô chuẩn": (2.0, 3), "quy mô lớn": (3.0, 5)},
            "Ra đề thi": {"quy mô nhỏ": (2.5, 4), "quy mô chuẩn": (3.5, 6), "quy mô lớn": (5.0, 9)},
            "Rà soát chương trình đào tạo": {"quy mô nhỏ": (20.0, 45), "quy mô chuẩn": (30.0, 90), "quy mô lớn": (40.0, 120)},
            "Soạn báo cáo/tổng hợp số liệu": {"quy mô nhỏ": (4.0, 3), "quy mô chuẩn": (6.0, 5), "quy mô lớn": (8.0, 9)},
            "Sửa bài theo phản biện": {"quy mô nhỏ": (8.0, 10), "quy mô chuẩn": (12.0, 15), "quy mô lớn": (18.0, 28)},
            "Tham gia họp Bộ môn/Khoa": {"quy mô nhỏ": (1.0, 1), "quy mô chuẩn": (1.5, 1), "quy mô lớn": (2.0, 2)},
            "Tham gia hội đồng chuyên môn": {"quy mô nhỏ": (2.5, 2), "quy mô chuẩn": (3.5, 4), "quy mô lớn": (5.0, 6)},
            "Thu thập minh chứng kiểm định": {"quy mô nhỏ": (15.0, 20), "quy mô chuẩn": (20.0, 30), "quy mô lớn": (25.0, 45)},
            "Thực hiện đề tài NCKH": {"quy mô nhỏ": (45.0, 180), "quy mô chuẩn": (60.0, 270), "quy mô lớn": (90.0, 360)},
            "Tư vấn/hướng nghiệp sinh viên": {"quy mô nhỏ": (3.0, 3), "quy mô chuẩn": (4.0, 5), "quy mô lớn": (5.0, 8)},
            "Viết bài báo khoa học": {"quy mô nhỏ": (30.0, 45), "quy mô chuẩn": (45.0, 65), "quy mô lớn": (60.0, 110)},
            "Viết báo cáo tự đánh giá": {"quy mô nhỏ": (24.0, 60), "quy mô chuẩn": (30.0, 90), "quy mô lớn": (36.0, 120)},
            "Xây dựng học phần mới": {"quy mô nhỏ": (20.0, 30), "quy mô chuẩn": (25.0, 45), "quy mô lớn": (30.0, 60)},
            "Xây dựng/cập nhật đề cương học phần": {"quy mô nhỏ": (12.0, 10), "quy mô chuẩn": (16.0, 15), "quy mô lớn": (20.0, 21)},
            "Xử lý cảnh báo học vụ của SV": {"quy mô nhỏ": (1.5, 2), "quy mô chuẩn": (2.0, 3), "quy mô lớn": (3.0, 5)},
            "Đề xuất/đăng ký đề tài NCKH": {"quy mô nhỏ": (8.0, 10), "quy mô chuẩn": (12.0, 15), "quy mô lớn": (15.0, 21)},
        }

        tt_by_name = {}
        tt_list = []
        for tt_data in catalog["task_types"]:
            tt = TaskType(
                name=tt_data["name"],
                task_group=tt_data["task_group"],
                default_complexity=tt_data["default_complexity"],
                default_subtask_count=tt_data["default_subtask_count"],
                default_dependency_count=tt_data["default_dependency_count"]
            )
            db.add(tt)
            db.flush()
            tt_by_name[tt.name] = tt
            tt_list.append(tt)

            norm_scales = STANDARD_SCALES.get(
                tt.name,
                {"quy mô nhỏ": (4.0, 5), "quy mô chuẩn": (6.0, 7), "quy mô lớn": (8.0, 10)}
            )
            for scale_name in ("quy mô nhỏ", "quy mô chuẩn", "quy mô lớn"):
                hrs, days = norm_scales[scale_name]
                tts = TaskTypeScale(
                    task_type_id=tt.id,
                    scale=scale_name,
                    expected_duration_days=float(days),
                    conversion_hours=float(hrs)
                )
                db.add(tts)

        def pick_tt(preferred_keywords: list[str], fallback_idx: int = 0) -> TaskType:
            for kw in preferred_keywords:
                for name, obj in tt_by_name.items():
                    if kw.lower() in name.lower():
                        return obj
            return tt_list[fallback_idx % len(tt_list)]

        print("3. Seed School Catalog Items (FR-06)...")
        school_items_data = [
            ("TR-01", "Tham gia Ban coi thi tốt nghiệp THPT Quốc gia", 16.0, "Công tác coi thi cấp Quốc gia/Trường phân công"),
            ("TR-02", "Đoàn đánh giá ngoài kiểm định cơ sở giáo dục", 30.0, "Tham gia đoàn kiểm định chất lượng cấp Trường"),
            ("TR-03", "Ban chỉ đạo tư vấn tuyển sinh cấp Trường", 20.0, "Hoạt động truyền thông & tư vấn tuyển sinh Trường"),
            ("TR-04", "Hội đồng đánh giá sáng kiến cải tiến cấp Trường", 12.0, "Thẩm định sáng kiến kinh nghiệm cấp Trường"),
            ("TR-05", "Bồi dưỡng chuyên đề chuyển đổi số cấp Trường", 15.0, "Báo cáo viên chuyên đề cấp Trường"),
        ]
        school_map = {}
        for code, name, hours, note in school_items_data:
            sci = SchoolCatalogItem(code=code, name=name, conversion_hours=hours, note=note)
            db.add(sci)
            db.flush()
            school_map[code] = sci

        print("4. Seed Calendar Events...")
        events = [
            ("holiday", "Nghỉ Quốc khánh 2/9", date(2026, 9, 1), date(2026, 9, 3)),
            ("accreditation", "Đợt tự đánh giá kiểm định ABET", date(2026, 10, 1), date(2026, 10, 20)),
            ("holiday", "Nghỉ Tết Nguyên Đán Đinh Mùi", date(2027, 2, 5), date(2027, 2, 20)),
            ("accreditation", "Đợt kiểm định chất lượng MOET", date(2027, 3, 10), date(2027, 3, 25)),
            ("holiday", "Nghỉ lễ 30/4 - 1/5", date(2027, 4, 30), date(2027, 5, 2)),
        ]
        for kind, name, s, e in events:
            db.add(CalendarEvent(kind=kind, name=name, start_date=s, end_date=e))

        print("5. Seed Users & Profiles...")
        admin = User(
            username="admin",
            password_hash=hash_password("Admin@123"),
            full_name="Quản trị viên Hệ thống",
            email="admin@huit.edu.vn",
            role=ROLE_ADMIN
        )
        db.add(admin)

        dean = User(
            username="truongkhoa",
            password_hash=hash_password("Manager@123"),
            full_name="TS. Nguyễn Văn Lễ (Trưởng Khoa CNTT)",
            email="lenv@huit.edu.vn",
            role=ROLE_MANAGER,
            department_id=None
        )
        db.add(dean)
        db.flush()

        depts = list(dept_map.values())[:4]
        lecturer_names = {
            (1, 1): ("ThS. Nguyễn Minh Khoa", "Giảng viên", "Thạc sĩ", date(2019, 9, 1), date(2020, 9, 1), 135.0, 3, 240, 4),
            (1, 2): ("TS. Trần Thị Mai Anh", "Giảng viên chính", "Tiến sĩ", date(2014, 9, 1), date(2016, 3, 1), 135.0, 2, 160, 6),
            (1, 3): ("ThS. Lê Hoàng Nam", "Giảng viên", "Thạc sĩ", date(2025, 9, 1), date(2026, 3, 1), 120.0, 2, 120, 1),
            (2, 1): ("TS. Phạm Quốc Bảo", "Giảng viên chính", "Tiến sĩ", date(2015, 9, 1), date(2017, 9, 1), 135.0, 3, 210, 5),
            (2, 2): ("ThS. Võ Thị Thanh Thảo", "Giảng viên", "Thạc sĩ", date(2020, 9, 1), date(2021, 9, 1), 135.0, 3, 220, 3),
            (2, 3): ("ThS. Đặng Gia Huy", "Giảng viên", "Thạc sĩ", date(2021, 9, 1), date(2022, 9, 1), 135.0, 4, 260, 2),
            (3, 1): ("TS. Phan Hữu Phúc", "Giảng viên chính", "Tiến sĩ", date(2016, 9, 1), date(2018, 2, 1), 135.0, 3, 195, 5),
            (3, 2): ("ThS. Bùi Thị Lan Hương", "Giảng viên", "Thạc sĩ", date(2019, 9, 1), date(2020, 9, 1), 135.0, 3, 215, 3),
            (3, 3): ("ThS. Ngô Đình Tuấn", "Giảng viên", "Thạc sĩ", date(2022, 9, 1), date(2023, 3, 1), 135.0, 3, 230, 2),
            (4, 1): ("TS. Trịnh Quốc Khánh", "Giảng viên chính", "Tiến sĩ", date(2015, 2, 1), date(2017, 9, 1), 135.0, 2, 170, 6),
            (4, 2): ("ThS. Đỗ Mai Phương", "Giảng viên", "Thạc sĩ", date(2020, 9, 1), date(2021, 9, 1), 135.0, 3, 210, 3),
            (4, 3): ("ThS. Lý Minh Tâm", "Giảng viên", "Thạc sĩ", date(2021, 9, 1), date(2022, 9, 1), 135.0, 3, 225, 2),
        }
        tbm_names = [
            "PGS.TS. Hoàng Văn Minh (TBM CNPM)",
            "TS. Lê Thị Hồng Nhung (TBM HTTT)",
            "TS. Nguyễn Hữu Toàn (TBM KHMT)",
            "TS. Phan Thanh Tùng (TBM MMT&ATTT)",
        ]

        users_by_username = {"admin": admin, "truongkhoa": dean}
        for i, d in enumerate(depts):
            tbm = User(
                username=f"tbm_k{i+1:02d}",
                password_hash=hash_password("Manager@123"),
                full_name=tbm_names[i] if i < len(tbm_names) else f"Trưởng Bộ môn {d.name}",
                email=f"tbm.k{i+1}@huit.edu.vn",
                role=ROLE_MANAGER,
                department_id=d.id
            )
            db.add(tbm)
            db.flush()
            users_by_username[tbm.username] = tbm

            db.add(LecturerProfile(
                user_id=tbm.id,
                lecturer_code=f"TBM{i+1:02d}",
                academic_rank="Giảng viên chính",
                degree="Tiến sĩ",
                management_role="Trưởng bộ môn",
                career_start_date=date(2010, 9, 1),
                join_date=date(2015, 1, 1),
                teaching_hours_semester=110.0,
                course_count=2,
                student_count=150,
                supervised_student_count=5
            ))

            for j in range(1, 4):
                info = lecturer_names.get(
                    (i + 1, j),
                    (f"ThS. Nguyễn Văn K{i+1:02d}.{j}", "Giảng viên", "Thạc sĩ", date(2018, 9, 1), date(2020, 2, 1), 135.0, 3, 220, 2)
                )
                gv = User(
                    username=f"gv_k{i+1:02d}_{j}",
                    password_hash=hash_password("Lecturer@123"),
                    full_name=info[0],
                    email=f"gv{j}.k{i+1}@huit.edu.vn",
                    role=ROLE_LECTURER,
                    department_id=d.id
                )
                db.add(gv)
                db.flush()
                users_by_username[gv.username] = gv

                db.add(LecturerProfile(
                    user_id=gv.id,
                    lecturer_code=f"GV{i+1:02d}{j:02d}",
                    academic_rank=info[1],
                    degree=info[2],
                    management_role="Không",
                    career_start_date=info[3],
                    join_date=info[4],
                    teaching_hours_semester=info[5],
                    course_count=info[6],
                    student_count=info[7],
                    supervised_student_count=info[8]
                ))

        print("6. Seed Hồ sơ công việc 1 năm (2026-2027) cho ThS. Nguyễn Minh Khoa (gv_k01_1)...")
        gv1 = users_by_username["gv_k01_1"]
        gv2 = users_by_username["gv_k01_2"]
        gv3 = users_by_username["gv_k01_3"]
        tbm1 = users_by_username["tbm_k01"]
        today = date.today()

        # Tạo Kế hoạch năm đã import cho ThS. Nguyễn Minh Khoa
        plan_gv1 = Plan(
            lecturer_id=gv1.id,
            academic_year="2026-2027",
            file_name="KeHoach_CongTac_Nam_2026_2027_GV0101_NguyenMinhKhoa.xlsx",
            imported_by=dean.id,
            imported_at=datetime(2026, 9, 2, 8, 30)
        )
        db.add(plan_gv1)
        db.flush()


        # Danh sách 18 đầu việc trải dài HK1, HK2, Hè năm học 2026-2027 của ThS. Nguyễn Minh Khoa
        gv1_tasks_spec = [
            # --- HỌC KỲ 1 (09/2026 - 01/2027): 8 công việc đã hoàn thành ---
            {
                "code": "CV-2609-HK101",
                "title": "Giảng dạy học phần Công nghệ phần mềm (3 tín chỉ - Lớp 14DHTH01, 02)",
                "tt": pick_tt(["Giảng dạy", "học phần"], 0),
                "scale": "quy mô lớn",
                "priority": "Cao",
                "complexity": "Trung bình",
                "assigned_at": datetime(2026, 9, 5, 8, 0),
                "original_deadline": date(2026, 12, 20),
                "current_deadline": date(2026, 12, 20),
                "status": ST_DONE,
                "progress_pct": 100,
                "completed_at": datetime(2026, 12, 18, 16, 0),
                "is_late": False,
                "delay_days": -2,
                "school_code": None,
                "plan_id": plan_gv1.id,
                "ml_prob": 0.118,
                "ml_level": "Thấp",
                "ml_unc": 0.019,
                "ml_factors": [
                    {"feature": "hist_late_rate_smooth", "direction": "giảm rủi ro", "delta_logit": -0.42},
                    {"feature": "lead_vs_expected_ratio", "direction": "giảm rủi ro", "delta_logit": -0.31},
                ],
                "ml_rec": "Rủi ro thấp: tiếp tục theo dõi định kỳ theo kế hoạch giảng dạy HK1."
            },
            {
                "code": "CV-2609-HK102",
                "title": "Biên soạn đề cương chi tiết học phần Kiểm thử phần mềm tự động",
                "tt": pick_tt(["đề cương", "biên soạn", "giáo trình"], 1),
                "scale": "quy mô chuẩn",
                "priority": "Trung bình",
                "complexity": "Trung bình",
                "assigned_at": datetime(2026, 9, 12, 9, 0),
                "original_deadline": date(2026, 9, 28),
                "current_deadline": date(2026, 9, 28),
                "status": ST_DONE,
                "progress_pct": 100,
                "completed_at": datetime(2026, 9, 28, 14, 30),
                "is_late": False,
                "delay_days": 0,
                "school_code": None,
                "plan_id": plan_gv1.id,
                "ml_prob": 0.164,
                "ml_level": "Thấp",
                "ml_unc": 0.022,
                "ml_factors": [
                    {"feature": "lead_time_days", "direction": "giảm rủi ro", "delta_logit": -0.28},
                    {"feature": "current_open_tasks", "direction": "giảm rủi ro", "delta_logit": -0.19},
                ],
                "ml_rec": "Rủi ro thấp: thời gian giao việc thoải mái so với định mức chuẩn."
            },
            {
                "code": "CV-2610-HK103",
                "title": "Viết báo cáo tự đánh giá Tiêu chuẩn 4 kiểm định ABET ngành CNPM",
                "tt": pick_tt(["kiểm định", "đánh giá", "báo cáo"], 2),
                "scale": "quy mô lớn",
                "priority": "Khẩn cấp",
                "complexity": "Rất cao",
                "assigned_at": datetime(2026, 10, 2, 10, 0),
                "original_deadline": date(2026, 10, 14),
                "current_deadline": date(2026, 10, 14),
                "status": ST_DONE,
                "progress_pct": 100,
                "completed_at": datetime(2026, 10, 18, 17, 45),
                "is_late": True,
                "delay_days": 4,
                "school_code": None,
                "plan_id": None,
                "ml_prob": 0.612,
                "ml_level": "Cao",
                "ml_unc": 0.045,
                "ml_factors": [
                    {"feature": "is_Compressed", "direction": "tăng rủi ro", "delta_logit": 0.84},
                    {"feature": "accreditation_overlap_days", "direction": "tăng rủi ro", "delta_logit": 0.56},
                    {"feature": "complexity_num", "direction": "tăng rủi ro", "delta_logit": 0.39},
                ],
                "ml_rec": "Rủi ro cao (61.2%): Thời hạn gấp trong đợt cao điểm kiểm định ABET; khuyến nghị bổ sung 1 giảng viên hỗ trợ thu thập minh chứng."
            },
            {
                "code": "CV-2610-HK104",
                "title": "Tham gia Ban coi thi & giám sát kỳ thi cấp Quốc gia / Trường phân công",
                "tt": pick_tt(["coi thi", "thi", "tuyển sinh"], 3),
                "scale": "quy mô chuẩn",
                "priority": "Cao",
                "complexity": "Trung bình",
                "assigned_at": datetime(2026, 10, 22, 8, 30),
                "original_deadline": date(2026, 11, 5),
                "current_deadline": date(2026, 11, 5),
                "status": ST_DONE,
                "progress_pct": 100,
                "completed_at": datetime(2026, 11, 4, 17, 0),
                "is_late": False,
                "delay_days": -1,
                "school_code": "TR-01",
                "plan_id": plan_gv1.id,
                "ml_prob": 0.142,
                "ml_level": "Thấp",
                "ml_unc": 0.018,
                "ml_factors": [
                    {"feature": "mat_global_type_late_rate", "direction": "giảm rủi ro", "delta_logit": -0.35},
                ],
                "ml_rec": "Rủi ro thấp: công việc theo lịch cố định của Trường."
            },
            {
                "code": "CV-2611-HK105",
                "title": "Hướng dẫn đồ án môn học Công nghệ phần mềm (Nhóm 35 sinh viên)",
                "tt": pick_tt(["đồ án", "hướng dẫn", "khóa luận"], 4),
                "scale": "quy mô chuẩn",
                "priority": "Trung bình",
                "complexity": "Cao",
                "assigned_at": datetime(2026, 11, 2, 9, 0),
                "original_deadline": date(2026, 12, 15),
                "current_deadline": date(2026, 12, 15),
                "status": ST_DONE,
                "progress_pct": 100,
                "completed_at": datetime(2026, 12, 14, 15, 0),
                "is_late": False,
                "delay_days": -1,
                "school_code": None,
                "plan_id": plan_gv1.id,
                "ml_prob": 0.195,
                "ml_level": "Thấp",
                "ml_unc": 0.025,
                "ml_factors": [
                    {"feature": "lead_time_days", "direction": "giảm rủi ro", "delta_logit": -0.33},
                ],
                "ml_rec": "Rủi ro thấp: tiến độ hướng dẫn đồ án ổn định."
            },
            {
                "code": "CV-2611-HK106",
                "title": "Xây dựng ngân hàng 300 câu hỏi chuẩn đầu ra học phần Lập trình Web",
                "tt": pick_tt(["ngân hàng câu hỏi", "đề thi", "ra đề"], 5),
                "scale": "quy mô lớn",
                "priority": "Cao",
                "complexity": "Cao",
                "assigned_at": datetime(2026, 11, 18, 10, 0),
                "original_deadline": date(2026, 11, 28),
                "current_deadline": date(2026, 12, 2),
                "status": ST_DONE,
                "progress_pct": 100,
                "completed_at": datetime(2026, 12, 1, 16, 20),
                "is_late": True,
                "delay_days": 3,
                "school_code": None,
                "plan_id": None,
                "ml_prob": 0.548,
                "ml_level": "Cao",
                "ml_unc": 0.041,
                "ml_factors": [
                    {"feature": "lead_vs_expected_ratio", "direction": "tăng rủi ro", "delta_logit": 0.69},
                    {"feature": "workload_vs_teaching_Load", "direction": "tăng rủi ro", "delta_logit": 0.44},
                ],
                "ml_rec": "Rủi ro cao (54.8%): Khối lượng 300 câu hỏi lớn nhưng thời hạn gốc chỉ 10 ngày; nên chia mốc nghiệm thu 50%."
            },
            {
                "code": "CV-2612-HK107",
                "title": "Ra đề và chấm thi kết thúc học phần Học kỳ 1 năm học 2026-2027",
                "tt": pick_tt(["chấm thi", "ra đề", "thi"], 6),
                "scale": "quy mô lớn",
                "priority": "Cao",
                "complexity": "Trung bình",
                "assigned_at": datetime(2026, 12, 15, 8, 0),
                "original_deadline": date(2027, 1, 5),
                "current_deadline": date(2027, 1, 5),
                "status": ST_DONE,
                "progress_pct": 100,
                "completed_at": datetime(2027, 1, 5, 11, 0),
                "is_late": False,
                "delay_days": 0,
                "school_code": None,
                "plan_id": plan_gv1.id,
                "ml_prob": 0.286,
                "ml_level": "Trung bình",
                "ml_unc": 0.031,
                "ml_factors": [
                    {"feature": "teaching_hours_semester", "direction": "tăng rủi ro", "delta_logit": 0.29},
                    {"feature": "hist_late_rate_smooth", "direction": "giảm rủi ro", "delta_logit": -0.21},
                ],
                "ml_rec": "Rủi ro trung bình (28.6%): Nhắc hạn tự động trước 3 ngày để nộp bảng điểm đúng hạn."
            },
            {
                "code": "CV-2701-HK108",
                "title": "Tham gia Đoàn đánh giá ngoài kiểm định cơ sở giáo dục cấp Trường",
                "tt": pick_tt(["kiểm định", "đánh giá", "chất lượng"], 7),
                "scale": "quy mô lớn",
                "priority": "Cao",
                "complexity": "Cao",
                "assigned_at": datetime(2027, 1, 2, 8, 0),
                "original_deadline": date(2027, 1, 14),
                "current_deadline": date(2027, 1, 14),
                "status": ST_DONE,
                "progress_pct": 100,
                "completed_at": datetime(2027, 1, 12, 17, 0),
                "is_late": False,
                "delay_days": -2,
                "school_code": "TR-02",
                "plan_id": plan_gv1.id,
                "ml_prob": 0.312,
                "ml_level": "Trung bình",
                "ml_unc": 0.033,
                "ml_factors": [
                    {"feature": "complexity_num", "direction": "tăng rủi ro", "delta_logit": 0.32},
                ],
                "ml_rec": "Rủi ro trung bình (31.2%): Theo dõi mốc hoàn thiện báo cáo đoàn đánh giá ngoài."
            },

            # --- HỌC KỲ 2 (01/2027 - 05/2027): 4 việc đã xong + 3 việc đang mở ---
            {
                "code": "CV-2701-HK201",
                "title": "Giảng dạy học phần Kiến trúc và Thiết kế Phần mềm HK2 (3 tín chỉ)",
                "tt": pick_tt(["Giảng dạy", "học phần"], 0),
                "scale": "quy mô chuẩn",
                "priority": "Cao",
                "complexity": "Trung bình",
                "assigned_at": datetime(2027, 1, 18, 8, 0),
                "original_deadline": date(2027, 5, 10),
                "current_deadline": date(2027, 5, 10),
                "status": ST_DONE,
                "progress_pct": 100,
                "completed_at": datetime(2027, 5, 7, 16, 0),
                "is_late": False,
                "delay_days": -3,
                "school_code": None,
                "plan_id": plan_gv1.id,
                "ml_prob": 0.125,
                "ml_level": "Thấp",
                "ml_unc": 0.017,
                "ml_factors": [
                    {"feature": "lead_time_days", "direction": "giảm rủi ro", "delta_logit": -0.45},
                ],
                "ml_rec": "Rủi ro thấp: lịch giảng dạy cố định theo thời khóa biểu HK2."
            },
            {
                "code": "CV-2702-HK202",
                "title": "Hoàn thiện bài báo khoa học quốc tế Scopus Q2 về Học máy ứng dụng",
                "tt": pick_tt(["bài báo", "nghiên cứu", "NCKH", "khoa học"], 8),
                "scale": "quy mô lớn",
                "priority": "Cao",
                "complexity": "Rất cao",
                "assigned_at": datetime(2027, 2, 1, 9, 0),
                "original_deadline": date(2027, 3, 15),
                "current_deadline": date(2027, 3, 15),
                "status": ST_DONE,
                "progress_pct": 100,
                "completed_at": datetime(2027, 3, 20, 21, 0),
                "is_late": True,
                "delay_days": 5,
                "school_code": None,
                "plan_id": plan_gv1.id,
                "ml_prob": 0.675,
                "ml_level": "Cao",
                "ml_unc": 0.049,
                "ml_factors": [
                    {"feature": "holiday_overlap_days", "direction": "tăng rủi ro", "delta_logit": 0.72},
                    {"feature": "complexity_num", "direction": "tăng rủi ro", "delta_logit": 0.61},
                    {"feature": "require_external_input", "direction": "tăng rủi ro", "delta_logit": 0.38},
                ],
                "ml_rec": "Rủi ro cao (67.5%): Thời gian thực hiện trùng kỳ nghỉ Tết Nguyên Đán 15 ngày; khuyến nghị giãn hạn chót thêm 7 ngày."
            },
            {
                "code": "CV-2703-HK203",
                "title": "Tổ chức vòng chung kết Olympic Tin học sinh viên Khoa CNTT năm 2027",
                "tt": pick_tt(["sự kiện", "cuộc thi", "sinh viên", "hội thảo"], 9),
                "scale": "quy mô chuẩn",
                "priority": "Trung bình",
                "complexity": "Trung bình",
                "assigned_at": datetime(2027, 3, 5, 8, 30),
                "original_deadline": date(2027, 4, 5),
                "current_deadline": date(2027, 4, 5),
                "status": ST_DONE,
                "progress_pct": 100,
                "completed_at": datetime(2027, 4, 4, 17, 0),
                "is_late": False,
                "delay_days": -1,
                "school_code": None,
                "plan_id": None,
                "ml_prob": 0.182,
                "ml_level": "Thấp",
                "ml_unc": 0.021,
                "ml_factors": [
                    {"feature": "lead_vs_expected_ratio", "direction": "giảm rủi ro", "delta_logit": -0.29},
                ],
                "ml_rec": "Rủi ro thấp: kế hoạch tổ chức đã chuẩn bị đầy đủ."
            },
            {
                "code": "CV-2703-HK204",
                "title": "Tham gia Ban chỉ đạo tư vấn tuyển sinh cấp Trường năm 2027",
                "tt": pick_tt(["tuyển sinh", "truyền thông", "cố vấn"], 10),
                "scale": "quy mô chuẩn",
                "priority": "Cao",
                "complexity": "Trung bình",
                "assigned_at": datetime(2027, 3, 18, 9, 0),
                "original_deadline": date(2027, 4, 25),
                "current_deadline": date(2027, 4, 25),
                "status": ST_DONE,
                "progress_pct": 100,
                "completed_at": datetime(2027, 4, 25, 16, 0),
                "is_late": False,
                "delay_days": 0,
                "school_code": "TR-03",
                "plan_id": plan_gv1.id,
                "ml_prob": 0.154,
                "ml_level": "Thấp",
                "ml_unc": 0.020,
                "ml_factors": [
                    {"feature": "hist_late_rate_smooth", "direction": "giảm rủi ro", "delta_logit": -0.34},
                ],
                "ml_rec": "Rủi ro thấp: hoàn thành đúng lịch tư vấn tuyển sinh của Trường."
            },
            # 3 công việc ĐANG THỰC HIỆN (1 sắp đến hạn, 1 đang chờ duyệt gia hạn, 1 quá hạn)
            {
                "code": "CV-2704-HK205",
                "title": "Hướng dẫn 04 sinh viên thực hiện Khóa luận tốt nghiệp Đại học Khóa 14",
                "tt": pick_tt(["khóa luận", "hướng dẫn", "đồ án"], 4),
                "scale": "quy mô lớn",
                "priority": "Cao",
                "complexity": "Cao",
                "assigned_at": datetime.now() - timedelta(days=25),
                "original_deadline": today + timedelta(days=2),
                "current_deadline": today + timedelta(days=2),
                "status": ST_DOING,
                "progress_pct": 75,
                "completed_at": None,
                "is_late": None,
                "delay_days": None,
                "school_code": None,
                "plan_id": plan_gv1.id,
                "ml_prob": 0.345,
                "ml_level": "Trung bình",
                "ml_unc": 0.032,
                "ml_factors": [
                    {"feature": "current_open_tasks", "direction": "tăng rủi ro", "delta_logit": 0.36},
                    {"feature": "supervised_student_count", "direction": "tăng rủi ro", "delta_logit": 0.24},
                ],
                "ml_rec": "Rủi ro trung bình (34.5%): Công việc sắp đến hạn (còn 2 ngày), cần đôn đốc sinh viên nộp quyển báo cáo cuối."
            },
            {
                "code": "CV-2704-HK206",
                "title": "Rà soát và đối sánh bộ minh chứng kiểm định MOET năm học 2026-2027",
                "tt": pick_tt(["kiểm định", "minh chứng", "đánh giá"], 2),
                "scale": "quy mô lớn",
                "priority": "Khẩn cấp",
                "complexity": "Rất cao",
                "assigned_at": datetime.now() - timedelta(days=12),
                "original_deadline": today + timedelta(days=4),
                "current_deadline": today + timedelta(days=4),
                "status": ST_DOING,
                "progress_pct": 60,
                "completed_at": None,
                "is_late": None,
                "delay_days": None,
                "school_code": None,
                "plan_id": None,
                "ml_prob": 0.584,
                "ml_level": "Cao",
                "ml_unc": 0.044,
                "ml_factors": [
                    {"feature": "current_high_priority_open_tasks", "direction": "tăng rủi ro", "delta_logit": 0.71},
                    {"feature": "require_external_input", "direction": "tăng rủi ro", "delta_logit": 0.49},
                    {"feature": "mat_lecturer_type_late_rate", "direction": "tăng rủi ro", "delta_logit": 0.38},
                ],
                "ml_rec": "Rủi ro cao (58.4%): Phụ thuộc dữ liệu từ các phòng ban ngoài Khoa; khuyến nghị xem xét phê duyệt gia hạn hoặc bổ sung nhân sự hỗ trợ."
            },
            {
                "code": "CV-2704-HK207",
                "title": "Biên soạn bài giảng điện tử E-Learning học phần Phân tích thiết kế HTTT",
                "tt": pick_tt(["bài giảng", "giáo trình", "biên soạn"], 1),
                "scale": "quy mô chuẩn",
                "priority": "Cao",
                "complexity": "Cao",
                "assigned_at": datetime.now() - timedelta(days=20),
                "original_deadline": today - timedelta(days=3),
                "current_deadline": today - timedelta(days=3),
                "status": ST_DOING,
                "progress_pct": 40,
                "completed_at": None,
                "is_late": None,
                "delay_days": None,
                "school_code": None,
                "plan_id": plan_gv1.id,
                "ml_prob": 0.642,
                "ml_level": "Cao",
                "ml_unc": 0.047,
                "ml_factors": [
                    {"feature": "current_open_tasks", "direction": "tăng rủi ro", "delta_logit": 0.68},
                    {"feature": "workload_vs_teaching_Load", "direction": "tăng rủi ro", "delta_logit": 0.52},
                ],
                "ml_rec": "Rủi ro cao (64.2%): Giảng viên đang quá tải công việc trong HK2; cần nhắc nhở cập nhật tiến độ hoặc xin gia hạn."
            },

            # --- HỌC KỲ HÈ (06/2027 - 08/2027): 3 công việc Kế hoạch năm ---
            {
                "code": "CV-2706-HE01",
                "title": "Chấm báo cáo thực tập doanh nghiệp Học kỳ Hè năm học 2026-2027",
                "tt": pick_tt(["thực tập", "chấm", "đồ án"], 11),
                "scale": "quy mô chuẩn",
                "priority": "Trung bình",
                "complexity": "Trung bình",
                "assigned_at": datetime(2027, 6, 5, 8, 0),
                "original_deadline": date(2027, 7, 20),
                "current_deadline": date(2027, 7, 20),
                "status": ST_NEW,
                "progress_pct": 0,
                "completed_at": None,
                "is_late": None,
                "delay_days": None,
                "school_code": None,
                "plan_id": plan_gv1.id,
                "ml_prob": 0.172,
                "ml_level": "Thấp",
                "ml_unc": 0.023,
                "ml_factors": [
                    {"feature": "lead_time_days", "direction": "giảm rủi ro", "delta_logit": -0.37},
                ],
                "ml_rec": "Rủi ro thấp: công việc thuộc kế hoạch Học kỳ Hè."
            },
            {
                "code": "CV-2706-HE02",
                "title": "Tham gia Hội đồng đánh giá sáng kiến cải tiến giảng dạy cấp Trường",
                "tt": pick_tt(["hội đồng", "đánh giá", "nghiên cứu"], 12),
                "scale": "quy mô chuẩn",
                "priority": "Trung bình",
                "complexity": "Trung bình",
                "assigned_at": datetime(2027, 6, 15, 9, 0),
                "original_deadline": date(2027, 7, 30),
                "current_deadline": date(2027, 7, 30),
                "status": ST_NEW,
                "progress_pct": 0,
                "completed_at": None,
                "is_late": None,
                "delay_days": None,
                "school_code": "TR-04",
                "plan_id": plan_gv1.id,
                "ml_prob": 0.205,
                "ml_level": "Thấp",
                "ml_unc": 0.024,
                "ml_factors": [
                    {"feature": "hist_late_rate_smooth", "direction": "giảm rủi ro", "delta_logit": -0.26},
                ],
                "ml_rec": "Rủi ro thấp: đã ánh xạ danh mục công việc cấp Trường (TR-04)."
            },
            {
                "code": "CV-2707-HE03",
                "title": "Tổng kết công tác cố vấn học tập và đánh giá điểm rèn luyện năm học 2026-2027",
                "tt": pick_tt(["cố vấn", "sinh viên", "hành chính"], 13),
                "scale": "quy mô chuẩn",
                "priority": "Cao",
                "complexity": "Trung bình",
                "assigned_at": datetime(2027, 7, 10, 8, 30),
                "original_deadline": date(2027, 8, 15),
                "current_deadline": date(2027, 8, 15),
                "status": ST_NEW,
                "progress_pct": 0,
                "completed_at": None,
                "is_late": None,
                "delay_days": None,
                "school_code": None,
                "plan_id": plan_gv1.id,
                "ml_prob": 0.268,
                "ml_level": "Trung bình",
                "ml_unc": 0.029,
                "ml_factors": [
                    {"feature": "priority_num", "direction": "tăng rủi ro", "delta_logit": 0.22},
                ],
                "ml_rec": "Rủi ro trung bình (26.8%): Nhắc hạn tự động trước ngày 12/08/2027."
            },
        ]

        for spec in gv1_tasks_spec:
            sci_id = school_map[spec["school_code"]].id if spec["school_code"] else None
            t = Task(
                code=spec["code"],
                title=spec["title"],
                description=f"Nhiệm vụ năm học 2026-2027 giao cho {gv1.full_name} ({gv1.profile.lecturer_code}).",
                task_type_id=spec["tt"].id,
                scale=spec["scale"],
                school_catalog_id=sci_id,
                priority=spec["priority"],
                complexity=spec["complexity"],
                assignment_mode="Individual",
                assignment_level="Trường" if sci_id else "Khoa",
                assignment_channel="Hệ thống",
                subtask_count=spec["tt"].default_subtask_count,
                dependency_count=spec["tt"].default_dependency_count,
                require_external_input=(spec["ml_level"] == "Cao"),
                require_approval=True,
                assigned_at=spec["assigned_at"],
                original_deadline=spec["original_deadline"],
                current_deadline=spec["current_deadline"],
                status=spec["status"],
                created_by=dean.id,
                plan_id=spec["plan_id"],
                created_at=spec["assigned_at"]
            )
            db.add(t)
            db.flush()

            a = TaskAssignment(
                task_id=t.id,
                lecturer_id=gv1.id,
                progress_pct=spec["progress_pct"],
                status=spec["status"],
                completed_at=spec["completed_at"],
                is_late=spec["is_late"],
                is_late_current=(spec["delay_days"] > 0 if spec["delay_days"] is not None else None),
                delay_days=spec["delay_days"]
            )
            db.add(a)
            db.flush()

            # Nhật ký tiến độ mẫu
            if spec["progress_pct"] >= 40:
                db.add(ProgressUpdate(
                    assignment_id=a.id,
                    progress_pct=40,
                    note="Đã hoàn thành thu thập tài liệu và khung đề cương bước 1.",
                    created_by=gv1.id,
                    created_at=spec["assigned_at"] + timedelta(days=4)
                ))
            if spec["progress_pct"] >= 60:
                db.add(ProgressUpdate(
                    assignment_id=a.id,
                    progress_pct=spec["progress_pct"] if spec["progress_pct"] < 100 else 75,
                    note="Đã hoàn thành bản thảo chính, đang rà soát số liệu minh chứng.",
                    created_by=gv1.id,
                    created_at=spec["assigned_at"] + timedelta(days=8)
                ))
            if spec["progress_pct"] == 100 and spec["completed_at"]:
                db.add(ProgressUpdate(
                    assignment_id=a.id,
                    progress_pct=100,
                    note="Đã hoàn tất 100% và nộp hồ sơ nghiệm thu lên hệ thống.",
                    created_by=gv1.id,
                    created_at=spec["completed_at"]
                ))

            # Lưu lịch sử dự đoán ML
            db.add(RiskPrediction(
                task_id=t.id,
                assignment_id=a.id,
                lecturer_id=gv1.id,
                trigger="assign",
                status="ok",
                probability=spec["ml_prob"],
                level=spec["ml_level"],
                uncertainty=spec["ml_unc"],
                top_factors=json.dumps(spec["ml_factors"], ensure_ascii=False),
                recommendation=spec["ml_rec"],
                low_confidence=False,
                model_version="2026-10-10T01:49:15",
                latency_ms=34,
                created_at=spec["assigned_at"],
                predicted_at=spec["assigned_at"],
                actual_is_late=spec["is_late"],
                resolved_at=spec["completed_at"]
            ))

            # Tạo yêu cầu gia hạn mẫu cho CV-2611-HK106 (Đã duyệt) và CV-2704-HK206 (Chờ duyệt)
            if spec["code"] == "CV-2611-HK106":
                db.add(ExtensionRequest(
                    task_id=t.id,
                    requested_by=gv1.id,
                    reason="Cần bổ sung thêm 80 câu hỏi mức độ Vận dụng cao theo góp ý của Tổ bộ môn.",
                    old_deadline=date(2026, 11, 28),
                    proposed_deadline=date(2026, 12, 2),
                    status=EXT_APPROVED,
                    created_at=datetime(2026, 11, 26, 14, 0),
                    reviewed_by=dean.id,
                    reviewed_at=datetime(2026, 11, 27, 9, 0),
                    review_note="Đồng ý gia hạn thêm 4 ngày để đảm bảo chất lượng ngân hàng câu hỏi."
                ))
            elif spec["code"] == "CV-2704-HK206":
                db.add(ExtensionRequest(
                    task_id=t.id,
                    requested_by=gv1.id,
                    reason="Đang chờ Phòng Đào tạo và Phòng Khảo thí cung cấp bổ sung số liệu khảo sát sinh viên tốt nghiệp.",
                    old_deadline=spec["original_deadline"],
                    proposed_deadline=spec["original_deadline"] + timedelta(days=7),
                    status=EXT_PENDING,
                    created_at=datetime.now() - timedelta(days=1)
                ))


        print("7. Seed lịch sử mẫu cho TS. Trần Thị Mai Anh (gv_k01_2) & ThS. Lê Hoàng Nam (gv_k01_3 - Cold Start)...")
        # TS. Trần Thị Mai Anh: 8 công việc hoàn thành đúng hạn/sớm 100% -> Rủi ro cực thấp khi xếp hạng phân công
        for idx in range(1, 9):
            tt_obj = tt_list[idx % len(tt_list)]
            ass_dt = datetime(2026, 9, 10, 8, 0) + timedelta(days=idx * 18)
            dl_dt = (ass_dt + timedelta(days=14)).date()
            comp_dt = ass_dt + timedelta(days=11)
            t2 = Task(
                code=f"CV-2610-MA{idx:02d}",
                title=f"{tt_obj.name} - Đợt {idx} (TS. Trần Thị Mai Anh)",
                task_type_id=tt_obj.id,
                scale="quy mô chuẩn",
                priority="Trung bình",
                complexity="Trung bình",
                assigned_at=ass_dt,
                original_deadline=dl_dt,
                current_deadline=dl_dt,
                status=ST_DONE,
                created_by=dean.id,
                created_at=ass_dt
            )
            db.add(t2)
            db.flush()
            a2 = TaskAssignment(
                task_id=t2.id,
                lecturer_id=gv2.id,
                progress_pct=100,
                status=ST_DONE,
                completed_at=comp_dt,
                is_late=False,
                is_late_current=False,
                delay_days=-3
            )
            db.add(a2)
            db.flush()
            db.add(RiskPrediction(
                task_id=t2.id,
                assignment_id=a2.id,
                lecturer_id=gv2.id,
                trigger="assign",
                status="ok",
                probability=0.095,
                level="Thấp",
                uncertainty=0.015,
                top_factors=json.dumps([{"feature": "hist_late_rate_smooth", "direction": "giảm rủi ro", "delta_logit": -0.55}], ensure_ascii=False),
                recommendation="Rủi ro thấp: tiếp tục theo dõi định kỳ.",
                low_confidence=False,
                model_version="2026-10-10T01:49:15",
                latency_ms=28,
                created_at=ass_dt,
                predicted_at=ass_dt,
                actual_is_late=False,
                resolved_at=comp_dt
            ))

        # ThS. Lê Hoàng Nam (gv_k01_3): chỉ mới có 2 công việc hoàn thành (< 5 việc -> Cold Start low_confidence=True)
        for idx in range(1, 3):
            tt_obj = tt_list[(idx + 3) % len(tt_list)]
            ass_dt = datetime(2026, 11, 1, 8, 0) + timedelta(days=idx * 20)
            dl_dt = (ass_dt + timedelta(days=12)).date()
            comp_dt = ass_dt + timedelta(days=11)
            t3 = Task(
                code=f"CV-2611-LN{idx:02d}",
                title=f"{tt_obj.name} - Tập sự đợt {idx} (ThS. Lê Hoàng Nam)",
                task_type_id=tt_obj.id,
                scale="quy mô nhỏ",
                priority="Trung bình",
                complexity="Thấp",
                assigned_at=ass_dt,
                original_deadline=dl_dt,
                current_deadline=dl_dt,
                status=ST_DONE,
                created_by=tbm1.id,
                created_at=ass_dt
            )
            db.add(t3)
            db.flush()
            a3 = TaskAssignment(
                task_id=t3.id,
                lecturer_id=gv3.id,
                progress_pct=100,
                status=ST_DONE,
                completed_at=comp_dt,
                is_late=False,
                is_late_current=False,
                delay_days=-1
            )
            db.add(a3)
            db.flush()
            db.add(RiskPrediction(
                task_id=t3.id,
                assignment_id=a3.id,
                lecturer_id=gv3.id,
                trigger="assign",
                status="ok",
                probability=0.215,
                level="Thấp",
                uncertainty=0.058,
                top_factors=json.dumps([{"feature": "is_new_lecturer", "direction": "tăng rủi ro", "delta_logit": 0.31}], ensure_ascii=False),
                recommendation="Rủi ro thấp: tiếp tục theo dõi định kỳ. Lưu ý: giảng viên có ít lịch sử (<5 việc), dự đoán có độ không chắc chắn cao.",
                low_confidence=True,
                model_version="2026-10-10T01:49:15",
                latency_ms=29,
                created_at=ass_dt,
                predicted_at=ass_dt,
                actual_is_late=False,
                resolved_at=comp_dt
            ))

        print("8. Seed Thông báo mẫu (FR-02)...")
        db.add_all([
            Notification(
                user_id=dean.id,
                kind="risk_high",
                title="Cảnh báo rủi ro trễ hạn Mức Cao (58.4%): CV-2704-HK206",
                content="Công việc 'Rà soát và đối sánh bộ minh chứng kiểm định MOET năm học 2026-2027' giao cho ThS. Nguyễn Minh Khoa có rủi ro trễ hạn mức CAO (58.4%). Khuyến nghị xem xét phê duyệt gia hạn hoặc bổ sung nhân sự hỗ trợ.",
                dedupe_key="seed_notif_dean_1"
            ),
            Notification(
                user_id=dean.id,
                kind="extension",
                title="Yêu cầu gia hạn mới: Rà soát và đối sánh bộ minh chứng kiểm định MOET",
                content="Giảng viên ThS. Nguyễn Minh Khoa xin gia hạn thêm 7 ngày. Lý do: Đang chờ Phòng Đào tạo và Phòng Khảo thí cung cấp bổ sung số liệu.",
                dedupe_key="seed_notif_dean_2"
            ),
            Notification(
                user_id=gv1.id,
                kind="due_soon",
                title="Sắp đến hạn (còn 2 ngày): Hướng dẫn 04 sinh viên thực hiện Khóa luận tốt nghiệp",
                content="Công việc CV-2704-HK205 sẽ đến hạn sau 2 ngày. Tiến độ hiện tại: 75%. Vui lòng hoàn tất và cập nhật lên 100%.",
                dedupe_key="seed_notif_gv1_1"
            ),
            Notification(
                user_id=gv1.id,
                kind="overdue",
                title="Quá hạn (3 ngày): Biên soạn bài giảng điện tử E-Learning HTTT",
                content="Công việc CV-2704-HK207 đã quá hạn 3 ngày (Tiến độ: 40%). Vui lòng cập nhật tiến độ hoặc gửi yêu cầu gia hạn.",
                dedupe_key="seed_notif_gv1_2"
            ),
        ])

        db.commit()
        print("Đã hoàn tất seed dữ liệu mẫu và Hồ sơ 1 năm của Giảng viên.")

    except Exception as e:
        db.rollback()
        print(f"Lỗi khi seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset_flag = "--reset" in sys.argv
    seed(reset=reset_flag)


