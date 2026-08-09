# Hệ thống đăng ký & quản lý câu lạc bộ sinh viên

Dự án cuối kỳ học phần **Lập trình Python cho Phân tích Dữ liệu** — Chủ đề 9.

## 1. Giới thiệu

Hệ thống mô phỏng việc quản lý thành viên, sự kiện và điểm danh của một câu lạc bộ/đội nhóm sinh viên, phục vụ thống kê mức độ tham gia. Dự án được thiết kế để đáp ứng đầy đủ 5 chuẩn đầu ra học phần (CLO1–CLO5) theo Rubric R05.

| CLO | Nội dung | Thành phần đáp ứng |
|---|---|---|
| CLO1 (10%) | Cú pháp & cấu trúc Python | Toàn bộ codebase: PEP8, type hint, try/except, module rõ ràng |
| CLO2 (25%) | Xử lý & biến đổi dữ liệu (Pandas/NumPy) | `src/processing/`, `src/analysis/` |
| CLO3 (20%) | Trực quan hoá & giải thích kết quả | `src/visualization/` (≥3 biểu đồ Matplotlib) |
| CLO4 (30%) | Thiết kế OOP & giải pháp phân tích tổng thể | `src/models/` (kế thừa + đa hình), `src/db/` (SQL Server), `dashboard.py` (Streamlit) |
| CLO5 (15%) | Làm việc nhóm, báo cáo & thuyết trình | `report/`, slide thuyết trình |

## 2. Kiến trúc hướng đối tượng (CLO4)

```
Member (base)
└── Officer(Member)          # override get_score_multiplier() — cộng điểm vai trò quản lý

Event (base)
├── MandatoryEvent(Event)    # override get_attendance_weight() → trọng số cao
└── OptionalEvent(Event)     # override get_attendance_weight() → trọng số thấp

ClubManagementError(Exception)
├── MemberNotFoundError
├── EventNotFoundError
└── DuplicateAttendanceError

Club                          # lớp điều phối — không kế thừa, tổng hợp (composition) Member + Event
```

**Điểm đa hình cốt lõi**: khi `Club` tính tỉ lệ tham gia, nó gọi `event.get_attendance_weight()` và `member.get_score_multiplier()` mà không cần biết đối tượng cụ thể là lớp con nào — đúng nguyên lý đa hình, đồng thời là chỗ để giải thích trong báo cáo/thuyết trình.

| Class | Trách nhiệm chính |
|---|---|
| `Member` | Thông tin thành viên, lịch sử tham gia |
| `Officer` | Thành viên ban chủ nhiệm — override hệ số điểm tích cực |
| `Event` | Thông tin sự kiện |
| `MandatoryEvent` / `OptionalEvent` | Phân loại sự kiện — override trọng số điểm danh |
| `Club` | Quản lý danh sách Member/Event, điểm danh, thống kê tỉ lệ tham gia |
| `*Error` | Ngoại lệ nghiệp vụ dùng trong `try/except` khi điểm danh |

## 3. Cấu trúc thư mục

```
club-management/
├── data/
│   ├── raw/                    # members.csv, events.csv, attendance.csv
│   └── processed/              # dữ liệu đã xử lý (cache)
├── src/
│   ├── config.py
│   ├── models/
│   │   ├── member.py           # Member, Officer
│   │   ├── event.py            # Event, MandatoryEvent, OptionalEvent
│   │   ├── exceptions.py
│   │   └── club.py             # Club
│   ├── processing/
│   │   └── loader.py           # đọc CSV → dựng đối tượng, validate, bắt ngoại lệ
│   ├── analysis/
│   │   └── stats.py            # Pandas + SciPy (xu hướng, xếp hạng)
│   ├── visualization/
│   │   └── charts.py           # ≥3 biểu đồ Matplotlib
│   └── db/
│       ├── schema.sql          # mở rộng: SQL Server
│       └── sql_loader.py
├── dashboard.py                 # mở rộng: Streamlit
├── main.py                      # pipeline chạy toàn bộ
├── notebooks/                   # notebook tổng hợp để nộp bài
├── report/                      # báo cáo Word/PDF
├── tests/                        # sanity check nhanh cho models/
├── .clinerules/
│   └── project-rule.md
├── requirements.txt
├── .gitignore
└── README.md
```

## 4. Luồng dữ liệu (main.py)

1. `processing.loader` đọc 3 file CSV trong `data/raw/` → dựng các đối tượng `Member`/`Officer`, `Event` (Mandatory/Optional), nạp vào `Club`. Dòng dữ liệu lỗi (thành viên/sự kiện không tồn tại, điểm danh trùng) được bắt bằng exception riêng và log lại, không làm crash pipeline.
2. `analysis.stats` dùng `Club` để tính: tỉ lệ tham gia theo sự kiện, tỉ lệ tham gia theo thành viên (có trọng số đa hình), xếp hạng thành viên tích cực, xu hướng tăng trưởng thành viên (SciPy `linregress`).
3. `visualization.charts` xuất ≥3 biểu đồ Matplotlib từ kết quả bước 2.
4. (Mở rộng) `db.sql_loader` đẩy dữ liệu vào SQL Server, chạy vài query JOIN/GROUP BY/window function minh hoạ.
5. (Mở rộng) `dashboard.py` — Streamlit hiển thị lại toàn bộ phân tích dưới dạng tương tác cho phần thuyết trình.

## 5. Về dữ liệu

Dự án dùng **dữ liệu mô phỏng theo kịch bản thực tế** tại `data/raw/` — đúng theo lựa chọn nguồn dữ liệu mà đề bài cho phép (30 thành viên, 12 sự kiện, 190 lượt điểm danh hợp lệ + 4 dòng lỗi chủ ý để demo exception). Code được viết **generic theo tên cột** (không hard-code số liệu cụ thể): khi có dữ liệu thật, chỉ cần thay 3 file CSV đúng schema ở mục 2/3, không cần sửa logic.

## 6. Kế hoạch triển khai (theo pha)

| Pha | Nội dung |
|---|---|
| 0 | Khởi tạo repo, README, rule cho Cline, scaffold cấu trúc thư mục |
| 1 | Code `models/` (OOP core) + sinh bộ dữ liệu mô phỏng |
| 2 | Code `processing/loader.py` (đọc CSV, validate, exception) |
| 3 | Code `analysis/stats.py` (Pandas + SciPy) |
| 4 | Code `visualization/charts.py` (≥3 biểu đồ) |
| 5 | Mở rộng: SQL Server (`db/`) |
| 6 | Mở rộng: Streamlit (`dashboard.py`) |
| 7 | Thay dữ liệu mô phỏng bằng dữ liệu thật (khi CLB cung cấp) |
| 8 | Viết báo cáo + slide thuyết trình |

## 7. Cài đặt & chạy

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python main.py                   # chạy pipeline phân tích
streamlit run dashboard.py       # chạy dashboard (mở rộng)
```

## 8. Sản phẩm nộp

- [ ] Mã nguồn (`club-management/`)
- [ ] Dữ liệu CSV (`data/raw/`)
- [ ] Báo cáo (`report/`)
- [ ] Slide thuyết trình

## 9. Quy ước code

Xem chi tiết tại [`.clinerules/project-rule.md`](.clinerules/project-rule.md). Tóm tắt: định danh (tên class/hàm/biến) bằng tiếng Anh, docstring/comment giải thích nghiệp vụ bằng tiếng Việt, tuân thủ PEP8, mọi thao tác I/O hoặc tra cứu dữ liệu đều có `try/except` với exception nghiệp vụ riêng.
