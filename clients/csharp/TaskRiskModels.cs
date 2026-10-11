using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace HuitTaskManagement.Clients.ML
{
    public class TaskRiskInputDto
    {
        [JsonPropertyName("task_id")]
        public string TaskId { get; set; } = string.Empty;

        [JsonPropertyName("lecturer_id")]
        public string LecturerId { get; set; } = string.Empty;

        [JsonPropertyName("faculty")]
        public string Faculty { get; set; } = "CNTT";

        [JsonPropertyName("department")]
        public string? Department { get; set; }

        [JsonPropertyName("assigned_date")]
        public string? AssignedDate { get; set; }

        [JsonPropertyName("task_group")]
        public string? TaskGroup { get; set; }

        [JsonPropertyName("task_type")]
        public string? TaskType { get; set; }

        [JsonPropertyName("task_subtype")]
        public string? TaskSubtype { get; set; }

        [JsonPropertyName("priority")]
        public string Priority { get; set; } = "Trung bình"; // Thấp, Trung bình, Cao, Khẩn cấp

        [JsonPropertyName("complexity")]
        public string Complexity { get; set; } = "Trung bình"; // Thấp, Trung bình, Cao

        [JsonPropertyName("available_days")]
        public double AvailableDays { get; set; } = 7.0;

        [JsonPropertyName("estimated_effort_hours")]
        public double EstimatedEffortHours { get; set; } = 10.0;

        [JsonPropertyName("subtask_count")]
        public double SubtaskCount { get; set; } = 1.0;

        [JsonPropertyName("dependency_count")]
        public double DependencyCount { get; set; } = 0.0;

        [JsonPropertyName("require_external_input")]
        public double RequireExternalInput { get; set; } = 0.0;

        [JsonPropertyName("peak_season")]
        public int PeakSeason { get; set; } = 0;

        [JsonPropertyName("active_tasks")]
        public double? ActiveTasks { get; set; }

        [JsonPropertyName("overdue_open_tasks")]
        public double? OverdueOpenTasks { get; set; }
    }

    public class TaskRiskResponseDto
    {
        [JsonPropertyName("task_id")]
        public string TaskId { get; set; } = string.Empty;

        [JsonPropertyName("lecturer_id")]
        public string LecturerId { get; set; } = string.Empty;

        [JsonPropertyName("risk_probability")]
        public double RiskProbability { get; set; }

        [JsonPropertyName("risk_level")]
        public string RiskLevel { get; set; } = string.Empty; // "Thấp", "Trung bình", "Cao"

        [JsonPropertyName("risk_uncertainty")]
        public double? RiskUncertainty { get; set; }

        [JsonPropertyName("top_factors")]
        public string? TopFactors { get; set; }

        [JsonPropertyName("notes")]
        public string? Notes { get; set; }
    }

    public class BatchTaskRiskRequestDto
    {
        [JsonPropertyName("tasks")]
        public List<TaskRiskInputDto> Tasks { get; set; } = new();
    }

    public class BatchTaskRiskResponseDto
    {
        [JsonPropertyName("total")]
        public int Total { get; set; }

        [JsonPropertyName("results")]
        public List<TaskRiskResponseDto> Results { get; set; } = new();
    }

    public class LecturerCandidateDto
    {
        [JsonPropertyName("lecturer_id")]
        public string LecturerId { get; set; } = string.Empty;

        [JsonPropertyName("lecturer_name")]
        public string? LecturerName { get; set; }

        [JsonPropertyName("department")]
        public string? Department { get; set; }

        [JsonPropertyName("active_tasks")]
        public double? ActiveTasks { get; set; }

        [JsonPropertyName("overdue_open_tasks")]
        public double? OverdueOpenTasks { get; set; }
    }

    public class RecommendationRequestDto
    {
        [JsonPropertyName("task")]
        public TaskRiskInputDto Task { get; set; } = new();

        [JsonPropertyName("candidate_lecturers")]
        public List<LecturerCandidateDto> CandidateLecturers { get; set; } = new();
    }

    public class RecommendationItemDto
    {
        [JsonPropertyName("rank")]
        public int Rank { get; set; }

        [JsonPropertyName("lecturer_id")]
        public string LecturerId { get; set; } = string.Empty;

        [JsonPropertyName("lecturer_name")]
        public string? LecturerName { get; set; }

        [JsonPropertyName("department")]
        public string? Department { get; set; }

        [JsonPropertyName("risk_probability")]
        public double RiskProbability { get; set; }

        [JsonPropertyName("risk_level")]
        public string RiskLevel { get; set; } = string.Empty;

        [JsonPropertyName("risk_uncertainty")]
        public double? RiskUncertainty { get; set; }

        [JsonPropertyName("top_factors")]
        public string? TopFactors { get; set; }

        [JsonPropertyName("recommendation_note")]
        public string RecommendationNote { get; set; } = string.Empty;
    }

    public class RecommendationResponseDto
    {
        [JsonPropertyName("task_id")]
        public string TaskId { get; set; } = string.Empty;

        [JsonPropertyName("recommended_candidates")]
        public List<RecommendationItemDto> RecommendedCandidates { get; set; } = new();
    }
}
