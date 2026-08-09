"""Đọc 3 file CSV trong data/raw/ và dựng thành đối tượng Club.

Dòng dữ liệu lỗi (thiếu thành viên/sự kiện, điểm danh trùng) được bắt
bằng exception nghiệp vụ và log ra, không làm crash toàn bộ pipeline.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.models.club import Club
from src.models.event import Event, MandatoryEvent, OptionalEvent
from src.models.exceptions import ClubManagementError
from src.models.member import Member, Officer

logger = logging.getLogger(__name__)

_EVENT_TYPE_MAP = {
    "mandatory": MandatoryEvent,
    "optional": OptionalEvent,
}

DEFAULT_POSITION = "Ban chủ nhiệm"


def _read_csv(path: Path) -> pd.DataFrame:
    """Đọc CSV toàn bộ dạng chuỗi, ô rỗng giữ nguyên là "" chứ không thành NaN.

    keep_default_na=False rất quan trọng: mặc định pandas biến ô rỗng thành
    float NaN, mà NaN lại là TRUTHY trong Python — biểu thức kiểu
    `row.get("position") or DEFAULT` sẽ trả về NaN thay vì giá trị mặc định.
    """
    return pd.read_csv(path, dtype=str, encoding="utf-8", keep_default_na=False)


def _build_member(row: pd.Series) -> Member:
    """Dựng Member hoặc Officer tùy cột 'role' trong CSV."""
    join_date = pd.to_datetime(row["join_date"]).date()
    if str(row["role"]).strip().lower() == "officer":
        position = str(row.get("position", "")).strip() or DEFAULT_POSITION
        return Officer(
            member_id=str(row["member_id"]).strip(),
            full_name=str(row["full_name"]).strip(),
            class_name=str(row.get("class_name", "")).strip(),
            join_date=join_date,
            position=position,
        )
    return Member(
        member_id=str(row["member_id"]).strip(),
        full_name=str(row["full_name"]).strip(),
        class_name=str(row.get("class_name", "")).strip(),
        join_date=join_date,
    )


def _build_event(row: pd.Series) -> Event:
    """Dựng MandatoryEvent hoặc OptionalEvent tùy cột 'event_type' trong CSV."""
    event_cls = _EVENT_TYPE_MAP.get(str(row["event_type"]).strip().lower(), Event)
    return event_cls(
        event_id=str(row["event_id"]).strip(),
        name=str(row["name"]).strip(),
        date=pd.to_datetime(row["date"]).date(),
        category=str(row["category"]).strip(),
    )


def load_club_from_csv(data_dir: str | Path) -> Club:
    """Đọc members.csv, events.csv, attendance.csv trong data_dir → Club."""
    data_dir = Path(data_dir)
    club = Club()

    members_df = _read_csv(data_dir / "members.csv")
    for _, row in members_df.iterrows():
        club.add_member(_build_member(row))

    events_df = _read_csv(data_dir / "events.csv")
    for _, row in events_df.iterrows():
        club.add_event(_build_event(row))

    attendance_df = _read_csv(data_dir / "attendance.csv")
    skipped = 0
    for _, row in attendance_df.iterrows():
        try:
            checkin_time = pd.to_datetime(row["checkin_time"]).to_pydatetime()
            club.check_in(
                member_id=str(row["member_id"]).strip(),
                event_id=str(row["event_id"]).strip(),
                checkin_time=checkin_time,
            )
        except ClubManagementError as exc:
            skipped += 1
            logger.warning("Bỏ qua dòng điểm danh lỗi: %s", exc)

    if skipped:
        logger.info("Đã bỏ qua %d dòng điểm danh không hợp lệ.", skipped)

    return club