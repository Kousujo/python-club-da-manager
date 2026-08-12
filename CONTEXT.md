# CONTEXT.md — BTL Python cho Phân tích Dữ liệu (Club Management System)

> Dán vào đầu phiên chat mới (Claude web, Gemini) hoặc để ở repo root cho Cline đọc. Cập nhật "Trạng thái hiện tại" và "Nhật ký phiên" cuối mỗi phiên có tiến triển.

## 1. Tóm tắt
Đồ án cuối kỳ môn "Lập trình Python cho Phân tích Dữ liệu". Chủ đề 9: Hệ thống đăng ký & quản lý câu lạc bộ sinh viên (Member/Event/Club, OOP + Pandas + SciPy + Streamlit). Nhóm đăng ký 4 người nhưng thực tế 1 mình làm hết (plan, code, GitHub, report).

## 2. Thuật ngữ / quy ước đặt tên
| Thuật ngữ | Ý nghĩa |
|---|---|
| Officer | Subclass của Member, engagement multiplier = 1.2 (Member gốc = 1.0) |
| MandatoryEvent / OptionalEvent | Subclass của Event, attendance weight lần lượt 1.5 / 0.8 |
| C01 / C02 / C03 | Mã 3 CLB trong file dữ liệu gốc — C01 = IT Club (CLB đang dùng để phân tích), C02 = Cosplay & Culture, C03 = Valkyrie Security Team |

## 3. Stack kỹ thuật & ràng buộc
- Python, OOP (≥2 class, ≥1 quan hệ kế thừa/đa hình — bắt buộc theo rubric R05)
- Pandas/NumPy (data cleaning), SciPy (Phase 3), Matplotlib (≥3 biểu đồ), Streamlit (dashboard, chưa làm)
- Mở rộng thêm cho điểm cộng: SQL Server qua SQLAlchemy + pyodbc (cùng cách tiếp cận với dự án đồ hoạ máy tính)
- Quy tắc code: bộ Coding Guidelines gộp từ karpathy-guidelines + ponytail (đang đặt ở Project Instructions)

## 4. Kiến trúc (tóm tắt, không lặp lại code)
- `src/models/` — Member (base) → Officer; Event (base) → MandatoryEvent/OptionalEvent; Club dùng composition, đa hình thật (không isinstance check)
- Data gốc là Excel → convert CSV → lọc riêng IT Club: 31 thành viên, 6 sự kiện, 179 dòng attendance (tất cả status="Present")
- 2 thành viên gia nhập sớm nhất được auto gán làm Officer; phân loại sự kiện mandatory/optional theo heuristic từ khoá tên sự kiện (đã duyệt, không đổi lại trừ khi có lý do mới)
- README.md + `.clinerules/project-rule.md` theo cùng convention với dự án đồ hoạ máy tính

## 5. Trạng thái hiện tại
- Đã xong: Phase 1 (OOP core, smoke test pass), Phase 2 (CSV loader chuẩn hoá theo models)
- Đang làm: Phase 3 — `src/analysis/stats.py` (SciPy): linear regression xu hướng tăng trưởng thành viên, phân loại thành viên tích cực bằng z-score/percentile
- Chưa bắt đầu: Streamlit dashboard, report + slide thuyết trình

## 6. Nhật ký phiên (mới nhất lên trên)
- [điền ngày] — bắt đầu Phase 3 (SciPy stats)

## 7. Lưu ý khi dùng file này
- Không copy nguyên code vào đây — chỉ ghi đường dẫn file/tên hàm liên quan.
- Workflow: Claude web/Gemini ra plan + code → bạn review → Cline paste vào workspace + fix nhỏ. Nếu nghi ngờ chat và repo thật lệch nhau, kiểm tra qua GitHub connector trước khi giả định lại theo trí nhớ chat cũ.
