using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace HuitTaskManagement.Clients.ML
{
    public interface ITaskRiskPredictionClient
    {
        Task<TaskRiskResponseDto?> PredictTaskRiskAsync(TaskRiskInputDto input, CancellationToken cancellationToken = default);
        Task<BatchTaskRiskResponseDto?> PredictBatchAsync(BatchTaskRiskRequestDto batch, CancellationToken cancellationToken = default);
        Task<RecommendationResponseDto?> RecommendAssigneeAsync(RecommendationRequestDto request, CancellationToken cancellationToken = default);
    }

    public class TaskRiskPredictionClient : ITaskRiskPredictionClient
    {
        private readonly HttpClient _httpClient;
        private readonly ILogger<TaskRiskPredictionClient> _logger;
        private readonly JsonSerializerOptions _jsonOptions;

        public TaskRiskPredictionClient(HttpClient httpClient, ILogger<TaskRiskPredictionClient> logger)
        {
            _httpClient = httpClient;
            _logger = logger;
            _jsonOptions = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            };
        }

        public async Task<TaskRiskResponseDto?> PredictTaskRiskAsync(TaskRiskInputDto input, CancellationToken cancellationToken = default)
        {
            try
            {
                var response = await _httpClient.PostAsJsonAsync("/api/predict", input, _jsonOptions, cancellationToken);
                response.EnsureSuccessStatusCode();
                return await response.Content.ReadFromJsonAsync<TaskRiskResponseDto>(_jsonOptions, cancellationToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Lỗi khi gọi API dự đoán rủi ro cho TaskId: {TaskId}", input.TaskId);
                return null;
            }
        }

        public async Task<BatchTaskRiskResponseDto?> PredictBatchAsync(BatchTaskRiskRequestDto batch, CancellationToken cancellationToken = default)
        {
            try
            {
                var response = await _httpClient.PostAsJsonAsync("/api/predict-batch", batch, _jsonOptions, cancellationToken);
                response.EnsureSuccessStatusCode();
                return await response.Content.ReadFromJsonAsync<BatchTaskRiskResponseDto>(_jsonOptions, cancellationToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Lỗi khi gọi API dự đoán batch ({Count} tasks)", batch.Tasks.Count);
                return null;
            }
        }

        public async Task<RecommendationResponseDto?> RecommendAssigneeAsync(RecommendationRequestDto request, CancellationToken cancellationToken = default)
        {
            try
            {
                var response = await _httpClient.PostAsJsonAsync("/api/recommend-assignee", request, _jsonOptions, cancellationToken);
                response.EnsureSuccessStatusCode();
                return await response.Content.ReadFromJsonAsync<RecommendationResponseDto>(_jsonOptions, cancellationToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Lỗi khi gọi API gợi ý giảng viên cho TaskId: {TaskId}", request.Task.TaskId);
                return null;
            }
        }
    }
}
