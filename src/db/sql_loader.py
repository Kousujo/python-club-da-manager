"""Tạo schema SQL Server + nạp dữ liệu, cộng vài query demo
(JOIN/GROUP BY/window function) đối chiếu lại kết quả engagement_ranking
của Python.

Dữ liệu nạp vào SQL Server được lấy TỪ ĐỐI TƯỢNG Club, không đọc lại CSV.
Nhờ vậy quy tắc lọc (FK sai, điểm danh trùng) chỉ tồn tại một chỗ duy nhất
là loader.py + Club.check_in(); hai bên Python và SQL chắc chắn nhìn thấy
đúng cùng một tập dữ liệu, nên phần đối chiếu kết quả trong báo cáo mới có
giá trị.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, create_engine, text

from src.config import get_sql_connection_string
from src.models.club import Club
from src.models.event import MandatoryEvent, OptionalEvent
from src.models.member import Officer

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_engine() -> Engine:
    return create_engine(get_sql_connection_string())


def create_schema(engine: Engine) -> None:
    """Chạy schema.sql — xoá và tạo lại 3 bảng."""
    sql_script = SCHEMA_PATH.read_text(encoding="utf-8")
    with engine.begin() as conn:
        for statement in sql_script.split(";"):
            if statement.strip():
                conn.execute(text(statement))


def _event_type_of(event) -> str:
    if isinstance(event, MandatoryEvent):
        return "mandatory"
    if isinstance(event, OptionalEvent):
        return "optional"
    return "other"


def load_club_to_sql(engine: Engine, club: Club) -> None:
    """Nạp toàn bộ nội dung một Club đã dựng sẵn vào 3 bảng SQL Server.

    Không cần lọc FK hay lọc trùng ở đây: Club.check_in() đã từ chối mọi
    bản ghi không hợp lệ ngay từ lúc nạp CSV.
    """
    with engine.begin() as conn:
        for member in club.members.values():
            is_officer = isinstance(member, Officer)
            conn.execute(
                text(
                    "INSERT INTO dbo.Members "
                    "(member_id, full_name, class_name, join_date, role, position) "
                    "VALUES (:member_id, :full_name, :class_name, :join_date, "
                    ":role, :position)"
                ),
                {
                    "member_id": member.member_id,
                    "full_name": member.full_name,
                    "class_name": member.class_name or None,
                    "join_date": member.join_date,
                    "role": "officer" if is_officer else "member",
                    "position": member.position if is_officer else None,
                },
            )

        for event in club.events.values():
            conn.execute(
                text(
                    "INSERT INTO dbo.Events "
                    "(event_id, name, date, category, event_type) "
                    "VALUES (:event_id, :name, :date, :category, :event_type)"
                ),
                {
                    "event_id": event.event_id,
                    "name": event.name,
                    "date": event.date,
                    "category": event.category or None,
                    "event_type": _event_type_of(event),
                },
            )

        for record in club.attendance:
            conn.execute(
                text(
                    "INSERT INTO dbo.Attendance (member_id, event_id, checkin_time) "
                    "VALUES (:member_id, :event_id, :checkin_time)"
                ),
                {
                    "member_id": record.member_id,
                    "event_id": record.event_id,
                    "checkin_time": record.checkin_time,
                },
            )


def query_participation_detail(engine: Engine) -> pd.DataFrame:
    """JOIN 3 bảng — chi tiết từng lượt điểm danh."""
    sql = """
        SELECT m.full_name, m.class_name, m.role, e.name AS event_name,
               e.event_type, a.checkin_time
        FROM dbo.Attendance a
        JOIN dbo.Members m ON m.member_id = a.member_id
        JOIN dbo.Events e ON e.event_id = a.event_id
        ORDER BY a.checkin_time
    """
    return pd.read_sql(sql, engine)


def query_attendance_count_by_event(engine: Engine) -> pd.DataFrame:
    """GROUP BY — số người điểm danh mỗi sự kiện (LEFT JOIN nên sự kiện
    không ai tham gia vẫn hiện với 0)."""
    sql = """
        SELECT e.event_id, e.name, e.date,
               COUNT(a.member_id) AS attendee_count
        FROM dbo.Events e
        LEFT JOIN dbo.Attendance a ON a.event_id = e.event_id
        GROUP BY e.event_id, e.name, e.date
        ORDER BY e.date
    """
    return pd.read_sql(sql, engine)


def query_participation_by_class(engine: Engine) -> pd.DataFrame:
    """GROUP BY lớp — đối chiếu với Club.participation_rate_by_class()."""
    sql = """
        SELECT m.class_name,
               COUNT(DISTINCT m.member_id)  AS member_count,
               COUNT(a.member_id)           AS total_attendances,
               CAST(COUNT(a.member_id) AS FLOAT)
                   / NULLIF(COUNT(DISTINCT m.member_id)
                            * (SELECT COUNT(*) FROM dbo.Events), 0)
                                            AS avg_participation_rate
        FROM dbo.Members m
        LEFT JOIN dbo.Attendance a ON a.member_id = m.member_id
        GROUP BY m.class_name
        ORDER BY avg_participation_rate DESC
    """
    return pd.read_sql(sql, engine)


def query_member_rank_window(engine: Engine) -> pd.DataFrame:
    """Window function RANK() — xếp hạng điểm tích cực, công thức khớp
    engagement_ranking() bên Python (trọng số 1.5/0.8/1.0, hệ số officer 1.2).

    Dùng LEFT JOIN từ dbo.Members: thành viên chưa tham gia buổi nào vẫn
    phải có mặt trong bảng xếp hạng với điểm 0. Nếu JOIN thẳng từ
    dbo.Attendance thì những người này biến mất và kết quả SQL sẽ lệch số
    dòng so với Python, làm hỏng phần đối chiếu.
    """
    sql = """
        WITH member_scores AS (
            SELECT
                m.member_id, m.full_name, m.class_name, m.role,
                ISNULL(SUM(
                    CASE e.event_type
                        WHEN 'mandatory' THEN 1.5
                        WHEN 'optional'  THEN 0.8
                        ELSE 1.0
                    END
                ), 0)
                * CASE WHEN m.role = 'officer' THEN 1.2 ELSE 1.0 END
                    AS engagement_score
            FROM dbo.Members m
            LEFT JOIN dbo.Attendance a ON a.member_id = m.member_id
            LEFT JOIN dbo.Events e     ON e.event_id  = a.event_id
            GROUP BY m.member_id, m.full_name, m.class_name, m.role
        )
        SELECT *, RANK() OVER (ORDER BY engagement_score DESC) AS rank_in_club
        FROM member_scores
        ORDER BY rank_in_club
    """
    return pd.read_sql(sql, engine)


if __name__ == "__main__":
    from src.config import setup_utf8_stdout
    from src.processing.loader import load_club_from_csv

    setup_utf8_stdout()
    club = load_club_from_csv("data/raw")

    engine = get_engine()
    create_schema(engine)
    load_club_to_sql(engine, club)

    print("=== Số người điểm danh mỗi sự kiện (GROUP BY) ===")
    print(query_attendance_count_by_event(engine).to_string(index=False))
    print("\n=== Tỉ lệ tham gia theo lớp (GROUP BY) ===")
    print(query_participation_by_class(engine).to_string(index=False))
    print("\n=== Xếp hạng điểm tích cực (RANK window function) ===")
    print(query_member_rank_window(engine).to_string(index=False))