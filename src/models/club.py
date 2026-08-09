"""Club — lớp điều phối, tổng hợp (composition) Member và Event.

Club không kế thừa từ đâu; nó SỬ DỤNG đa hình của Member/Event (gọi
get_score_multiplier() / get_attendance_weight() qua interface chung)
mà không cần biết đối tượng cụ thể là lớp con nào.

Trạng thái nội bộ (_members/_events/_attendance) chỉ đọc được qua các
property members/events/attendance — tầng analysis và dashboard không
truy cập thuộc tính private.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

import pandas as pd

from src.models.event import Event
from src.models.exceptions import (
    DuplicateAttendanceError,
    EventNotFoundError,
    MemberNotFoundError,
)
from src.models.member import Member


@dataclass
class AttendanceRecord:
    """Một lượt điểm danh: thành viên nào, sự kiện nào, lúc nào."""

    member_id: str
    event_id: str
    checkin_time: datetime


class Club:
    """Quản lý danh sách Member, Event và lịch sử điểm danh của câu lạc bộ."""

    def __init__(self) -> None:
        self._members: dict[str, Member] = {}
        self._events: dict[str, Event] = {}
        self._attendance: list[AttendanceRecord] = []
        # Chống điểm danh trùng trong O(1) thay vì quét tuyến tính _attendance.
        self._attendance_keys: set[tuple[str, str]] = set()
        # Cache của to_dataframe(); huỷ mỗi khi dữ liệu thay đổi.
        self._df_cache: pd.DataFrame | None = None

    # -- Truy cập chỉ đọc (giữ đóng gói) -------------------------------
    @property
    def members(self) -> Mapping[str, Member]:
        """Danh sách thành viên, dạng mapping chỉ đọc."""
        return MappingProxyType(self._members)

    @property
    def events(self) -> Mapping[str, Event]:
        """Danh sách sự kiện, dạng mapping chỉ đọc."""
        return MappingProxyType(self._events)

    @property
    def attendance(self) -> tuple[AttendanceRecord, ...]:
        """Lịch sử điểm danh, dạng tuple bất biến."""
        return tuple(self._attendance)

    # -- Đăng ký dữ liệu ------------------------------------------------
    def add_member(self, member: Member) -> None:
        self._members[member.member_id] = member
        self._df_cache = None

    def add_event(self, event: Event) -> None:
        self._events[event.event_id] = event
        self._df_cache = None

    # -- Điểm danh --------------------------------------------------------
    def check_in(self, member_id: str, event_id: str, checkin_time: datetime) -> None:
        """Ghi nhận điểm danh. Ném exception nếu dữ liệu không hợp lệ."""
        if member_id not in self._members:
            raise MemberNotFoundError(member_id)
        if event_id not in self._events:
            raise EventNotFoundError(event_id)
        key = (member_id, event_id)
        if key in self._attendance_keys:
            raise DuplicateAttendanceError(member_id, event_id)
        self._attendance.append(AttendanceRecord(member_id, event_id, checkin_time))
        self._attendance_keys.add(key)
        self._df_cache = None

    # -- Tổng hợp dữ liệu ---------------------------------------------------
    def to_dataframe(self) -> pd.DataFrame:
        """Ghép điểm danh với thông tin thành viên/sự kiện thành 1 DataFrame.

        Kết quả được cache; cache tự huỷ khi add_member/add_event/check_in.
        """
        if self._df_cache is not None:
            return self._df_cache

        rows = []
        for r in self._attendance:
            member = self._members[r.member_id]
            event = self._events[r.event_id]
            rows.append(
                {
                    "member_id": member.member_id,
                    "member_name": member.full_name,
                    "class_name": member.class_name,
                    "role": member.get_role_label(),
                    "event_id": event.event_id,
                    "event_name": event.name,
                    "event_category": event.category,
                    "event_date": event.date,
                    "attendance_weight": event.get_attendance_weight(),
                    "checkin_time": r.checkin_time,
                }
            )
        self._df_cache = pd.DataFrame(rows)
        return self._df_cache

    # -- Tỉ lệ tham gia (theo đề bài) ----------------------------------------
    def participation_rate_by_event(self) -> pd.DataFrame:
        """Tỉ lệ tham gia = số người điểm danh / tổng số thành viên.

        Liệt kê ĐỦ mọi sự kiện, kể cả sự kiện không ai tham gia (0%) —
        đây chính là các sự kiện ban chủ nhiệm cần biết.
        """
        total_members = len(self._members)
        df = self.to_dataframe()
        counts = (
            df.groupby("event_id")["member_id"].nunique()
            if not df.empty
            else pd.Series(dtype="int64")
        )

        rows = []
        for event in sorted(self._events.values(), key=lambda e: e.date):
            attendee_count = int(counts.get(event.event_id, 0))
            rows.append(
                {
                    "event_id": event.event_id,
                    "event_name": event.name,
                    "attendee_count": attendee_count,
                    "total_members": total_members,
                    "participation_rate": (
                        attendee_count / total_members if total_members else 0.0
                    ),
                }
            )
        return pd.DataFrame(
            rows,
            columns=[
                "event_id",
                "event_name",
                "attendee_count",
                "total_members",
                "participation_rate",
            ],
        )

    def participation_rate_by_member(self) -> pd.DataFrame:
        """Tỉ lệ tham gia = số sự kiện đã điểm danh / tổng số sự kiện.

        Liệt kê ĐỦ mọi thành viên, kể cả người chưa tham gia buổi nào (0%).
        """
        total_events = len(self._events)
        df = self.to_dataframe()
        counts = (
            df.groupby("member_id")["event_id"].nunique()
            if not df.empty
            else pd.Series(dtype="int64")
        )

        rows = []
        for member in self._members.values():
            attended_count = int(counts.get(member.member_id, 0))
            rows.append(
                {
                    "member_id": member.member_id,
                    "member_name": member.full_name,
                    "class_name": member.class_name,
                    "role": member.get_role_label(),
                    "attended_count": attended_count,
                    "total_events": total_events,
                    "participation_rate": (
                        attended_count / total_events if total_events else 0.0
                    ),
                }
            )
        return pd.DataFrame(
            rows,
            columns=[
                "member_id",
                "member_name",
                "class_name",
                "role",
                "attended_count",
                "total_events",
                "participation_rate",
            ],
        ).sort_values("participation_rate", ascending=False, ignore_index=True)

    def participation_rate_by_class(self) -> pd.DataFrame:
        """Tỉ lệ tham gia trung bình theo lớp (chiều phân tích từ class_name).

        avg_participation_rate = trung bình tỉ lệ tham gia của các thành viên
        cùng lớp. Lớp không có thành viên nào điểm danh vẫn hiện với 0%.
        """
        per_member = self.participation_rate_by_member()
        if per_member.empty:
            return pd.DataFrame(
                columns=[
                    "class_name",
                    "member_count",
                    "total_attendances",
                    "avg_participation_rate",
                ]
            )

        grouped = (
            per_member.groupby("class_name")
            .agg(
                member_count=("member_id", "nunique"),
                total_attendances=("attended_count", "sum"),
                avg_participation_rate=("participation_rate", "mean"),
            )
            .reset_index()
        )
        return grouped.sort_values(
            "avg_participation_rate", ascending=False, ignore_index=True
        )

    # -- Điểm tích cực (nơi đa hình được dùng thật) --------------------------
    def engagement_ranking(self, top_n: int | None = None) -> pd.DataFrame:
        """Xếp hạng thành viên tích cực bằng điểm có trọng số đa hình:

        engagement_score = tổng(trọng số các sự kiện đã tham gia)
                            * hệ số nhân của thành viên

        Thành viên chưa tham gia buổi nào vẫn có mặt với điểm 0.
        """
        df = self.to_dataframe()
        weighted_sum = (
            df.groupby("member_id")["attendance_weight"].sum()
            if not df.empty
            else pd.Series(dtype="float64")
        )

        rows = []
        for member in self._members.values():
            weighted = float(weighted_sum.get(member.member_id, 0.0))
            multiplier = member.get_score_multiplier()
            rows.append(
                {
                    "member_id": member.member_id,
                    "member_name": member.full_name,
                    "role": member.get_role_label(),
                    "weighted_attendance": weighted,
                    "score_multiplier": multiplier,
                    "engagement_score": weighted * multiplier,
                }
            )

        result = pd.DataFrame(
            rows,
            columns=[
                "member_id",
                "member_name",
                "role",
                "weighted_attendance",
                "score_multiplier",
                "engagement_score",
            ],
        ).sort_values("engagement_score", ascending=False, ignore_index=True)
        return result.head(top_n) if top_n else result

    def member_growth_over_time(self) -> pd.DataFrame:
        """Số lượng thành viên tích lũy theo thời gian (theo join_date).

        Gộp theo NGÀY trước khi cộng dồn: nhiều người cùng ngày gia nhập
        phải là MỘT điểm dữ liệu, không phải nhiều điểm chồng lên nhau
        (nếu không, hồi quy ở stats.growth_trend sẽ bị lệch).
        """
        if not self._members:
            return pd.DataFrame(
                columns=["join_date", "new_members", "cumulative_members"]
            )

        joins = pd.Series([m.join_date for m in self._members.values()])
        daily = joins.value_counts().sort_index()
        df = daily.reset_index()
        df.columns = ["join_date", "new_members"]
        df["cumulative_members"] = df["new_members"].cumsum()
        return df