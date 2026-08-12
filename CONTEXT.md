# CONTEXT.md — BTL Python cho Phân tích Dữ liệu (Club Management System)

> Dán vào đầu phiên chat mới (Claude web, Gemini) hoặc để ở repo root cho Cline
> đọc. Cập nhật "Trạng thái hiện tại" và "Nhật ký phiên" cuối mỗi phiên có tiến triển.
> Cập nhật lần cuối: 12/08/2026.

## 1. Tóm tắt
Đồ án cuối kỳ môn "Lập trình Python cho Phân tích Dữ liệu". Chủ đề 9: Hệ thống
đăng ký & quản lý câu lạc bộ sinh viên (Member/Event/Club, OOP + Pandas + SciPy
+ Matplotlib, mở rộng SQL Server + Streamlit). Nhóm đăng ký 4 người nhưng thực
tế 1 mình làm hết (plan, code, GitHub, report).

## 2. Thuật ngữ / quy ước đặt tên
| Thuật ngữ | Ý nghĩa |
|---|---|
| Officer | Subclass của Member, engagement multiplier = 1.2 (Member gốc = 1.0) |
| MandatoryEvent / OptionalEvent | Subclass của Event, attendance weight lần lượt 1.5 / 0.8 |
| engagement_score | tổng(trọng số sự kiện đã tham gia) × hệ số nhân của thành viên |
| churn risk | nguy cơ ngừng tham gia, gộp z-score của recency và độ sụt giữa nửa đầu/nửa sau |
| retention lift | chênh tỉ lệ tham gia của nhóm nguy cơ so với nhóm còn lại, tính riêng từng sự kiện |

## 3. Stack kỹ thuật & ràng buộc
- Python 3.12 (máy thật 3.12.10, CI khớp), OOP (≥2 class, ≥1 kế thừa/đa hình —
  bắt buộc theo rubric R05)
- Pandas/NumPy (có try/except), SciPy (hồi quy + 3 kiểm định giả thuyết),
  Matplotlib (6 biểu đồ)
- Mở rộng cho điểm cộng: SQL Server qua SQLAlchemy + pyodbc; dashboard Streamlit 6 tab
- Quy tắc code: bộ Coding Guidelines (karpathy-guidelines + ponytail) đã chuyển
  sang **global rules** của Cline, không còn nằm trong `.clinerules/` của repo.
  Trong repo chỉ giữ `.clinerules/project-rule.md`.

## 4. Kiến trúc (tóm tắt, không lặp lại code)
- `src/models/` — Member → Officer; Event → MandatoryEvent/OptionalEvent;
  `exceptions.py`; `Club` dùng composition, gọi đa hình qua interface chung
  (không isinstance). Trạng thái nội bộ chỉ đọc qua property
  `members` / `events` / `attendance`.
- `src/processing/loader.py` — 3 CSV → Club, bắt lỗi từng dòng, không crash.
- `src/analysis/stats.py` — `growth_trend`, `engagement_with_stats`,
  `churn_risk`, `class_participation_test`, `mandatory_vs_optional_test`,
  `participation_decline_test`, `event_retention_power`.
- `src/visualization/charts.py` — 6 chart: participation, growth+trend,
  top_engaged, churn_risk, attendance_heatmap, event_retention.
- `src/db/` — `schema.sql` (3 bảng, FK + UNIQUE), `sql_loader.py`
  (nạp thẳng từ đối tượng Club, không đọc lại CSV; 4 query demo
  JOIN / GROUP BY / RANK window function).
- `main.py` pipeline tổng, xuất 6 PNG vào `report/figures/`.
  `dashboard.py` Streamlit 6 tab. `tests/` assert-based + CI GitHub Actions.
- **Loại vai trò và loại sự kiện đọc THẲNG từ cột CSV** (`role`, `event_type`).
  Không có heuristic suy đoán nào.
- Đã bỏ `src/analysis/network.py` (đồ thị đồng tham gia): nhiều sự kiện bắt buộc
  khiến nó gần như complete graph, không đọc ra thông tin gì.

## 5. Dữ liệu — MÔ PHỎNG 100%
Ban đầu dùng dữ liệu thật (Excel trộn 3 CLB, lọc ra 1 CLB). Review phát hiện
**tên thật đã bị commit và push lên GitHub** → bỏ hẳn nguồn dữ liệu thật, thay
bằng dữ liệu bịa. Đây là quyết định quan trọng nhất của dự án, phải ghi vào báo cáo.

- 30 thành viên (tên bịa, toàn ASCII), trong đó **2 officer** (M001, M002)
- 5 lớp × 6 người: CNTT1 / CNTT2 / KHMT1 / ATTT1 / HTTT1. Lớp được gán vòng
  tròn theo chỉ số, **cố ý không trùng với các nhóm hành vi** → chênh lệch giữa
  các lớp là nhiễu, và `class_participation_test()` chứng minh điều đó (p≈0.84).
- 12 sự kiện (09/2025–05/2026): 7 mandatory / 5 optional
- 194 dòng điểm danh = 190 hợp lệ + **4 dòng lỗi chủ ý** để demo exception:
  `M998/E006`, `M999/E001` (FK sai) và trùng `M001/E012`, `M002/E008`
- 3 nhóm hành vi cài sẵn (steady / declining / casual) để churn chart và
  heatmap có tín hiệu thật

## 6. Trạng thái hiện tại
- **Đã xong:** OOP core, CSV loader, SciPy stats (hồi quy + 3 kiểm định),
  6 biểu đồ, SQL Server layer, Streamlit dashboard 6 tab, tests + CI.
- **Chưa xác nhận:** chạy lại `python -m src.db.sql_loader` sau khi viết lại
  `sql_loader.py`; kiểm tra mojibake tiếng Việt trong SSMS (xem mục 8).
- **Chưa bắt đầu:** báo cáo Word + slide thuyết trình 5–7 phút.

## 7. Kết quả chính (đã chạy, dùng để đối chiếu)
```
growth_trend    slope=0.211 thành viên/ngày, r=0.909, p<0.001
Kruskal-Wallis  statistic=1.4340, p=0.8383  → chênh lệch giữa các lớp là NHIỄU
chi-square      chi2=23.9085, p=1.01e-06    → bắt buộc vs tự chọn KHÁC BIỆT THẬT
                (62.1% vs 34.2%)
Wilcoxon        statistic=216.0, p=0.6329   → tổng thể KHÔNG suy giảm
                (13 người giảm nhưng 17 người tăng)
churn_risk      5 "Nguy cơ cao", 3 "Ổn định"; đầu bảng M012 (score 1.8957)
retention       E003 Workshop Git & GitHub lift=+0.581 (71.4% vs 13.3%)
                E006 Sinh hoat dinh ky thang 12 lift=-0.417
```

**Trục lập luận cho báo cáo:** Wilcoxon nói CLB không suy giảm, nhưng churn_risk
vẫn chỉ ra 5 người nguy cơ cao. Không mâu thuẫn — nhóm giảm và nhóm tăng triệt
tiêu nhau khi cộng gộp. *Số tổng gộp che mất vấn đề, phải xuống mức cá nhân mới
thấy.* Kruskal-Wallis là ví dụ thứ hai cho cùng bài học, theo chiều ngược lại:
bảng xếp hạng lớp trông như phát hiện nhưng thực ra là nhiễu.

**Khuyến nghị hành động (phần "giải pháp" của CLO4):** sinh hoạt định kỳ không
giữ được người, workshop kỹ năng thì có. Kèm cảnh báo trung thực: nhóm nguy cơ
chỉ 7–8 người nên đây là tín hiệu gợi ý, không phải bằng chứng chắc.

## 8. Vấn đề đã biết
- Mojibake tiếng Việt trong bảng SQL Server (nghi lỗi encoding pyodbc/ODBC
  driver). Đã thử sửa 1 lần làm tệ hơn, đã revert. **Cần kiểm lại:** dữ liệu mô
  phỏng hiện tại không có dấu tiếng Việt nên vấn đề có thể đã tự hết — xác nhận
  trong SSMS trước khi viết vào báo cáo.
- Toàn bộ phần kế thừa của `Member` chỉ tựa trên 2/30 dòng officer. Không đủ cỡ
  mẫu để kiểm định "officer tích cực hơn thành viên thường" (đã thử, n=2 vs 28,
  vô nghĩa) nên không đưa kiểm định đó vào bài.
- `sql_loader.py` có dùng `isinstance` để ánh xạ ngược đối tượng ra chuỗi cho
  SQL. Đây là ngoại lệ có chủ đích; `Club` vẫn đa hình thuần.

## 9. Nhật ký phiên (mới nhất lên trên)
- 12/08/2026 — Thêm Kruskal-Wallis; viết lại CONTEXT.md và sửa README theo đúng
  code hiện tại.
- 12/08/2026 — Đợt 2: điền `class_name`, thêm bản đồ nhiệt điểm danh, 2 kiểm
  định giả thuyết, phân tích sức giữ chân sự kiện; viết lại `sql_loader.py`
  (LEFT JOIN giữ thành viên 0 lượt, nạp thẳng từ Club thay vì đọc lại CSV).
- 12/08/2026 — Đợt 1: sửa 10 bug (gitignore chặn data, mojibake comment, vi phạm
  đóng gói, NaN truthy, check_in O(n²), bỏ sót entity 0 lượt, hồi quy lệch do
  điểm trùng ngày, lọc DataFrame trong vòng lặp, cache to_dataframe).

## 10. Lưu ý khi dùng file này
- Không copy nguyên code vào đây — chỉ ghi đường dẫn file / tên hàm liên quan.
- Workflow: Claude web/Gemini ra plan + code → review → Cline paste vào workspace
  + fix nhỏ. Cline hay làm dở dang hoặc bịa kết quả đọc file, nên mọi prompt gửi
  nó phải chia bước, mỗi bước có lệnh kiểm tra riêng, và kết thúc bằng bảng số
  liệu kỳ vọng (mục 7) để đối chiếu.
- **GitHub MCP connector hiện KHÔNG nạp được vào phiên chat** dù Settings báo đã
  kết nối. Nếu nghi chat và repo thật lệch nhau, đừng giả định theo trí nhớ —
  bảo Cline chạy `git log --oneline` / `git diff --stat`, hoặc nén repo gửi thẳng.