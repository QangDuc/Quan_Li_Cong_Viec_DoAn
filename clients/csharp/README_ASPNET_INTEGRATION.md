# Hướng dẫn tích hợp Task Risk Prediction Service vào ASP.NET Core Backend

## 1. Cấu hình địa chỉ API trong `appsettings.json`
Thêm cấu hình URL của Python ML Service vào file cấu hình của project ASP.NET Core Web API:

```json
{
  "MlService": {
    "BaseUrl": "http://localhost:8000",
    "TimeoutSeconds": 10
  }
}
```

## 2. Đăng ký Dependency Injection trong `Program.cs`
Trong file `Program.cs` của ứng dụng ASP.NET Core (.NET 7/8):

```csharp
using HuitTaskManagement.Clients.ML;

var builder = WebApplication.CreateBuilder(args);

// Đăng ký Typed HttpClient cho TaskRiskPredictionClient
builder.Services.AddHttpClient<ITaskRiskPredictionClient, TaskRiskPredictionClient>(client =>
{
    var baseUrl = builder.Configuration["MlService:BaseUrl"] ?? "http://localhost:8000";
    client.BaseAddress = new Uri(baseUrl);
    client.Timeout = TimeSpan.FromSeconds(
        builder.Configuration.GetValue<int>("MlService:TimeoutSeconds", 10));
});
```

## 3. Sử dụng trong Controller (ví dụ `TasksController.cs`)

```csharp
[ApiController]
[Route("api/[controller]")]
public class TasksController : ControllerBase
{
    private readonly ITaskRiskPredictionClient _riskClient;
    private readonly ITaskRepository _taskRepo;

    public TasksController(ITaskRiskPredictionClient riskClient, ITaskRepository taskRepo)
    {
        _riskClient = riskClient;
        _taskRepo = taskRepo;
    }

    /// <summary>
    /// API kiểm tra rủi ro trước khi Trưởng khoa / Trưởng bộ môn bấm xác nhận giao việc
    /// </summary>
    [HttpPost("preview-assignment-risk")]
    public async Task<IActionResult> PreviewAssignmentRisk([FromBody] TaskRiskInputDto dto)
    {
        var result = await _riskClient.PredictTaskRiskAsync(dto);
        if (result == null)
        {
            return StatusCode(500, "Không thể kết nối đến dịch vụ phân tích rủi ro.");
        }
        return Ok(result);
    }

    /// <summary>
    /// API gợi ý phân công: Đưa ra danh sách giảng viên trong bộ môn xếp hạng theo độ rủi ro thấp nhất
    /// </summary>
    [HttpPost("recommend-lecturers")]
    public async Task<IActionResult> RecommendLecturers([FromBody] RecommendationRequestDto request)
    {
        var result = await _riskClient.RecommendAssigneeAsync(request);
        if (result == null)
        {
            return StatusCode(500, "Không thể kết nối đến dịch vụ gợi ý phân công.");
        }
        return Ok(result);
    }
}
```

## 4. Hiển thị trên Giao diện Web (React / Razor)
- Khi người dùng chọn một giảng viên để giao việc, popup hiển thị:
  - **Mức cảnh báo**: Badge màu Xanh (Thấp - Rủi ro $\le 22\%$), Vàng (Trung bình), hoặc Đỏ (Cao - Rủi ro $\ge 44\%$).
  - **Tỷ lệ rủi ro trễ hạn**: ví dụ `87.5%`.
  - **Lý do cảnh báo (Top factors)**: `"Số việc đang mở = 14; áp lực deadline = 1.6; tỉ lệ trễ lịch sử = 38%"`.
  - Giúp Trưởng khoa/bộ môn có cơ sở khoa học để điều chỉnh phân công sang giảng viên khác ít tải hơn.
