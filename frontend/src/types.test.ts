import test from "node:test";
import assert from "node:assert/strict";
import { formatFeatureName } from "./types";
import { MOCK_STATS, MOCK_LECTURER_EVALUATION, MOCK_TASKS, MOCK_USERS } from "./mockData";
import { handleMockResponse } from "./mockApi";
import {
  calculateProjectProgressFromMembers,
  evaluateTaskRoleAndVisibility,
  isTaskManagedByDepartmentHead,
  filterTasksByRoleAndDepartment,
  SQL_RBAC_DDL_TEXT,
} from "./rbacWorkflow";

test("formatFeatureName maps causal feature keys to Vietnamese labels", () => {
  assert.equal(
    formatFeatureName("hist_late_rate_smooth"),
    "Tỷ lệ trễ hạn lịch sử của cá nhân"
  );
  assert.equal(formatFeatureName("unknown_feature_xyz"), "unknown_feature_xyz");
});

test("MOCK_STATS and MOCK_LECTURER_EVALUATION have complete arrays for dashboard and evaluation views", () => {
  assert.equal(Array.isArray(MOCK_STATS.by_group), true);
  assert.equal(MOCK_STATS.by_group.length > 0, true);
  assert.equal(Array.isArray(MOCK_LECTURER_EVALUATION.semesters), true);
  assert.equal(Array.isArray(MOCK_LECTURER_EVALUATION.by_group), true);
  assert.equal(Array.isArray(MOCK_LECTURER_EVALUATION.task_personnel_matrix), true);
  assert.equal(Array.isArray(MOCK_LECTURER_EVALUATION.ml_audit.records), true);
});

test("calculateProjectProgressFromMembers computes automatic project progress from 3 group members", () => {
  const pct1 = calculateProjectProgressFromMembers([
    { progress_pct: 70 },
    { progress_pct: 80 },
    { progress_pct: 45 },
  ]);
  assert.equal(pct1, 65);

  const pct2 = calculateProjectProgressFromMembers([
    { progress_pct: 90 },
    { progress_pct: 85 },
    { progress_pct: 80 },
  ]);
  assert.equal(pct2, 85);
});

test("evaluateTaskRoleAndVisibility enforces 5-tier RBAC rules (Member, Lead, Reviewer, Dept Head, Dean, and Admin 15/15 permissions)", () => {
  const groupTask = MOCK_TASKS.find((t) => t.id === 29);
  const adminUser = MOCK_USERS.find((u) => u.username === "admin");
  const deanUser = MOCK_USERS.find((u) => u.username === "truongkhoa");
  const deptHeadUser = MOCK_USERS.find((u) => u.username === "tbm_k01");
  const reviewerUser = MOCK_USERS.find((u) => u.id === 7 || u.rbac_role_code === "TASK_REVIEWER");
  const leadUser = MOCK_USERS.find((u) => u.username === "gv_k01_1");
  const memberUser = MOCK_USERS.find((u) => u.username === "gv_k01_2");

  // 0. Quản trị viên Hệ thống (admin - SYSTEM • 15/15 quyền nguyên tử theo Bảng 3.4):
  assert.equal(MOCK_USERS.length, 18);
  assert.equal(adminUser?.scope_level, "SYSTEM");
  assert.equal(adminUser?.permissions?.length, 15);
  assert.equal(adminUser?.permissions?.includes("USER_MANAGE"), true);
  assert.equal(adminUser?.permissions?.includes("DEPT_MANAGE"), true);
  assert.equal(deanUser?.permissions?.length, 12);
  assert.equal(deanUser?.permissions?.includes("USER_MANAGE"), false);
  assert.equal(deptHeadUser?.permissions?.length, 12);
  assert.equal(memberUser?.permissions?.length, 5);

  const adminEval = evaluateTaskRoleAndVisibility(adminUser, groupTask, "AUTO");
  assert.equal(adminEval.canSelfUpdateProgress, true);
  assert.equal(adminEval.canLeadApproveMembers, true);
  assert.equal(adminEval.canReviewerApproveDecision, true);

  // 1. Trưởng Khoa (DEAN) và Trưởng Bộ môn (DEPT_HEAD): Chỉ hiển thị % tiến độ chung công việc, không cần soi xét từng thành viên
  const deanEval = evaluateTaskRoleAndVisibility(deanUser, groupTask, "AUTO");
  assert.equal(deanEval.effectiveRole, "DEAN");
  assert.equal(deanEval.showIndividualMemberProgress, false);
  assert.equal(deanEval.projectProgressPct, 65);

  const deptHeadEval = evaluateTaskRoleAndVisibility(deptHeadUser, groupTask, "AUTO");
  assert.equal(deptHeadEval.effectiveRole, "DEPT_HEAD");
  assert.equal(deptHeadEval.showIndividualMemberProgress, false);
  assert.equal(deptHeadEval.projectProgressPct, 65);

  // 2. Người kiểm tra (REVIEWER): Quan sát được tiến độ từng thành viên & phê duyệt quyết định Trưởng nhóm
  const reviewerEval = evaluateTaskRoleAndVisibility(reviewerUser, groupUserTaskOrFallback(groupTask), "AUTO");
  assert.equal(reviewerEval.effectiveRole, "REVIEWER");
  assert.equal(reviewerEval.showIndividualMemberProgress, true);
  assert.equal(reviewerEval.canReviewerApproveDecision, true);

  // 3. Trưởng nhóm / Người phụ trách chính (GROUP_LEAD): Phê duyệt tiến độ thành viên & tự cập nhật phần mình
  const leadEval = evaluateTaskRoleAndVisibility(leadUser, groupTask, "AUTO");
  assert.equal(leadEval.effectiveRole, "GROUP_LEAD");
  assert.equal(leadEval.showIndividualMemberProgress, true);
  assert.equal(leadEval.canLeadApproveMembers, true);
  assert.equal(leadEval.canSelfUpdateProgress, true);

  // 4. Giảng viên Thành viên (MEMBER): Tự cập nhật tiến độ cá nhân, không có quyền duyệt nhóm
  const memberEval = evaluateTaskRoleAndVisibility(memberUser, groupTask, "AUTO");
  assert.equal(memberEval.effectiveRole, "MEMBER");
  assert.equal(memberEval.showIndividualMemberProgress, true);
  assert.equal(memberEval.canSelfUpdateProgress, true);
  assert.equal(memberEval.canLeadApproveMembers, false);
  assert.equal(memberEval.canReviewerApproveDecision, false);
});

function groupUserTaskOrFallback(task: any) {
  return task;
}

test("Department Head (Trưởng Bộ môn) can only manage and view tasks belonging to their own department in the Faculty", async () => {
  const deanUser = MOCK_USERS.find((u) => u.username === "truongkhoa");
  const deptHeadK01 = MOCK_USERS.find((u) => u.username === "tbm_k01"); // department_id = 1 (CNPM)
  const deptHeadK02 = MOCK_USERS.find((u) => u.username === "tbm_k02"); // department_id = 2 (HTTT)

  // Trưởng Khoa (DEAN, department_id = null) quản lý toàn bộ 9 công việc của tất cả các Bộ môn trong Khoa
  const deanTasks = filterTasksByRoleAndDepartment(MOCK_TASKS, deanUser, "AUTO");
  assert.equal(deanTasks.length, 9);

  // Trưởng Bộ môn CNPM (K01, department_id = 1) chỉ quản lý các công việc thuộc Bộ môn CNPM (7 công việc)
  const k01Tasks = filterTasksByRoleAndDepartment(MOCK_TASKS, deptHeadK01, "AUTO");
  assert.equal(k01Tasks.length, 7);
  assert.equal(
    k01Tasks.every((t) => t.department_id === 1),
    true
  );

  // Trưởng Bộ môn HTTT (K02, department_id = 2) chỉ quản lý công việc thuộc Bộ môn HTTT (1 công việc: CV-2611-HTTT01)
  const k02Tasks = filterTasksByRoleAndDepartment(MOCK_TASKS, deptHeadK02, "AUTO");
  assert.equal(k02Tasks.length, 1);
  assert.equal(k02Tasks[0].code, "CV-2611-HTTT01");
  assert.equal(k02Tasks[0].department_id, 2);

  // Trưởng Bộ môn KHMT (K03, department_id = 3) qua bộ chọn phạm vi Bộ môn chỉ quản lý công việc của K03 (CV-2611-KHMT01)
  const k03Tasks = filterTasksByRoleAndDepartment(MOCK_TASKS, deanUser, "DEPT_HEAD", 3);
  assert.equal(k03Tasks.length, 1);
  assert.equal(k03Tasks[0].code, "CV-2611-KHMT01");

  // Kiểm tra hàm isTaskManagedByDepartmentHead giữa task của K01 (id=29) và task của K02 (id=31)
  const taskK01 = MOCK_TASKS.find((t) => t.id === 29);
  const taskK02 = MOCK_TASKS.find((t) => t.id === 31);
  assert.equal(isTaskManagedByDepartmentHead(taskK01, deptHeadK01?.department_id), true);
  assert.equal(isTaskManagedByDepartmentHead(taskK02, deptHeadK01?.department_id), false);

  // Kiểm tra API chặn Trưởng Bộ môn CNPM (K01) giao việc sang Bộ môn HTTT (K02) -> HTTP 403
  const forbiddenCreateRes = handleMockResponse("http://localhost:8000/api/tasks", {
    method: "POST",
    body: JSON.stringify({
      title: "Công việc của Bộ môn HTTT",
      task_type_id: 2,
      acting_dept_head_department_id: 1,
      department_id: 2,
      lecturer_ids: [8],
    }),
  });
  assert.equal(forbiddenCreateRes.status, 403);
});

test("End-to-end 3-step workflow: Member self-update -> Lead approval & auto-calc -> Reviewer approval", async () => {
  // Bước 1: Thành viên 3 (lecturer_id = 6, đang 45%) tự cập nhật tiến độ cá nhân lên 75%
  // Khi đó 3 thành viên là: 70%, 80%, 75% -> Hệ thống tự động tính tiến độ dự án = (70+80+75)/3 = 75%
  const resMember = handleMockResponse("http://localhost:8000/api/tasks/29/progress", {
    method: "POST",
    body: JSON.stringify({
      lecturer_id: 6,
      progress_pct: 75,
      note: "Đã hoàn thành biểu mẫu khảo sát doanh nghiệp Tiêu chuẩn 6, 7",
    }),
  });
  assert.equal(resMember.status, 200);
  const dataMember = await resMember.json();
  assert.equal(dataMember.progress_pct, 75);
  assert.equal(dataMember.project_progress_pct, 75);
  assert.equal(dataMember.lead_approval_status, "Chờ Trưởng nhóm duyệt");

  // Bước 2: Trưởng nhóm (Người phụ trách chính) phê duyệt tiến độ của 3 thành viên và gửi lên hệ thống
  const resLead = handleMockResponse("http://localhost:8000/api/tasks/29/lead-approve", {
    method: "POST",
    body: JSON.stringify({
      member_approvals: [
        { lecturer_id: 2, approval_status: "Trưởng nhóm đã duyệt", review_note: "OK" },
        { lecturer_id: 4, approval_status: "Trưởng nhóm đã duyệt", review_note: "Đạt yêu cầu" },
        { lecturer_id: 6, approval_status: "Trưởng nhóm đã duyệt", review_note: "Đã bổ sung đầy đủ" },
      ],
      submit_to_reviewer: true,
      lead_decision_note: "Trưởng nhóm đã duyệt đủ 3 thành viên, trình Người kiểm tra.",
    }),
  });
  assert.equal(resLead.status, 200);
  const dataLead = await resLead.json();
  assert.equal(dataLead.project_progress_pct, 75);
  assert.equal(dataLead.lead_approval_status, "Đã duyệt & Trình Người kiểm tra");

  // Bước 3: Người kiểm tra phê duyệt quyết định của Trưởng nhóm
  const resReviewer = handleMockResponse(
    "http://localhost:8000/api/tasks/29/reviewer-approve",
    {
      method: "POST",
      body: JSON.stringify({
        approval_status: "Đã phê duyệt quyết định Trưởng nhóm",
        reviewer_decision_note: "Đồng ý với quyết định phê duyệt của Trưởng nhóm.",
      }),
    }
  );
  assert.equal(resReviewer.status, 200);
  const dataReviewer = await resReviewer.json();
  assert.equal(dataReviewer.project_progress_pct, 75);
  assert.equal(
    dataReviewer.reviewer_approval_status,
    "Đã phê duyệt quyết định Trưởng nhóm"
  );
});

test("SQL_RBAC_DDL_TEXT contains primary keys, foreign keys, auto-calc trigger, and RBAC view", () => {
  assert.equal(SQL_RBAC_DDL_TEXT.includes("PRIMARY KEY"), true);
  assert.equal(SQL_RBAC_DDL_TEXT.includes("FOREIGN KEY"), true);
  assert.equal(
    SQL_RBAC_DDL_TEXT.includes("trg_auto_calc_task_progress_on_update"),
    true
  );
  assert.equal(
    SQL_RBAC_DDL_TEXT.includes("vw_manager_project_progress_summary"),
    true
  );
  assert.equal(
    SQL_RBAC_DDL_TEXT.includes("vw_dept_head_department_tasks"),
    true
  );
});

