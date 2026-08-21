"""Dashboard Streamlit — công cụ khám phá dữ liệu câu lạc bộ.

Bộ lọc ở thanh bên dựng lại một đối tượng Club thu gọn, nên MỌI phân tích
trong các tab đều được tính lại trên tập dữ liệu đã lọc, không chỉ ẩn bớt
dòng hiển thị.
"""

from __future__ import annotations

import streamlit as st

from src.analysis.stats import (
    churn_risk,
    class_participation_test,
    engagement_with_stats,
    event_retention_power,
    growth_trend,
    mandatory_vs_optional_test,
    participation_decline_test,
)
from src.models.club import Club
from src.models.event import MandatoryEvent
from src.models.member import Officer
from src.processing.loader import load_club_from_csv
from src.visualization.charts import (
    plot_attendance_heatmap,
    plot_churn_risk,
    plot_event_retention,
    plot_member_growth,
    plot_participation_by_event,
    plot_top_engaged_members,
)

# Dưới ngưỡng này, z-score và các kiểm định giả thuyết không còn đáng tin.
MIN_MEMBERS_FOR_STATS = 12
MIN_EVENTS_FOR_STATS = 6

st.set_page_config(page_title="Quản lý CLB IT Club", layout="wide")


@st.cache_resource
def get_club() -> Club:
    return load_club_from_csv("data/raw")


def build_filtered_club(source: Club, member_ids: set[str], event_ids: set[str]) -> Club:
    """Dựng một Club mới chỉ gồm thành viên và sự kiện được chọn.

    Chỉ dùng interface công khai của Club (members/events/attendance +
    add_member/add_event/check_in), không đụng tới thuộc tính nội bộ.
    """
    view = Club()
    for member_id in member_ids:
        view.add_member(source.members[member_id])
    for event_id in event_ids:
        view.add_event(source.events[event_id])
    for record in source.attendance:
        if record.member_id in member_ids and record.event_id in event_ids:
            view.check_in(record.member_id, record.event_id, record.checkin_time)
    return view


def stats_are_reliable(view: Club) -> tuple[bool, str]:
    """Cảnh báo khi tập đã lọc quá nhỏ để phân tích thống kê có ý nghĩa."""
    n_members, n_events = len(view.members), len(view.events)
    if n_members < MIN_MEMBERS_FOR_STATS or n_events < MIN_EVENTS_FOR_STATS:
        return False, (
            f"Tập dữ liệu sau khi lọc chỉ còn **{n_members} thành viên** và "
            f"**{n_events} sự kiện**. Ở cỡ mẫu này, z-score và các kiểm định giả "
            f"thuyết không còn đáng tin — kết quả bên dưới chỉ mang tính minh hoạ, "
            f"không được dùng để kết luận. Ngưỡng khuyến nghị: "
            f"≥ {MIN_MEMBERS_FOR_STATS} thành viên và ≥ {MIN_EVENTS_FOR_STATS} sự kiện."
        )
    return True, ""


def show_test_result(title: str, result: dict) -> None:
    """Trình bày kết quả kiểm định dưới dạng thẻ chỉ số thay vì dump JSON."""
    st.markdown(f"**{title}**")
    if "error" in result:
        st.info(result["error"])
        return

    p_value = result.get("p_value")
    numeric = {
        k: v
        for k, v in result.items()
        if k not in ("conclusion", "p_value") and isinstance(v, (int, float))
    }
    cols = st.columns(min(len(numeric), 4) + 1)
    cols[0].metric("p-value", f"{p_value:.4g}")
    for col, (key, value) in zip(cols[1:], list(numeric.items())[:4]):
        col.metric(key, f"{value:.4f}" if isinstance(value, float) else str(value))

    if p_value < 0.05:
        st.success(f"Bác bỏ H₀ (p < 0.05) — {result['conclusion']}")
    else:
        st.warning(f"Chưa bác bỏ được H₀ (p ≥ 0.05) — {result['conclusion']}")


club = get_club()

st.title("Dashboard quản lý câu lạc bộ — IT Club")

# ---------------------------------------------------------------- Bộ lọc
st.sidebar.header("Bộ lọc dữ liệu")

all_classes = sorted({m.class_name for m in club.members.values() if m.class_name})
sel_classes = st.sidebar.multiselect("Lớp", all_classes, default=all_classes)

sel_roles = st.sidebar.multiselect(
    "Vai trò", ["Thành viên", "Ban chủ nhiệm"], default=["Thành viên", "Ban chủ nhiệm"]
)

sel_types = st.sidebar.multiselect(
    "Loại sự kiện", ["Bắt buộc", "Tự chọn"], default=["Bắt buộc", "Tự chọn"]
)

event_dates = sorted(e.date for e in club.events.values())
date_from, date_to = st.sidebar.select_slider(
    "Khoảng thời gian sự kiện",
    options=event_dates,
    value=(event_dates[0], event_dates[-1]),
    format_func=lambda d: d.strftime("%m/%Y"),
)

member_ids = {
    mid
    for mid, m in club.members.items()
    if (m.class_name in sel_classes)
    and (("Ban chủ nhiệm" if isinstance(m, Officer) else "Thành viên") in sel_roles)
}
event_ids = {
    eid
    for eid, e in club.events.items()
    if (("Bắt buộc" if isinstance(e, MandatoryEvent) else "Tự chọn") in sel_types)
    and (date_from <= e.date <= date_to)
}

if not member_ids or not event_ids:
    st.error("Bộ lọc hiện tại không còn thành viên hoặc sự kiện nào. Nới bộ lọc để tiếp tục.")
    st.stop()

view = build_filtered_club(club, member_ids, event_ids)
reliable, warning_text = stats_are_reliable(view)

st.sidebar.divider()
st.sidebar.caption(
    f"Đang phân tích {len(view.members)}/{len(club.members)} thành viên "
    f"và {len(view.events)}/{len(club.events)} sự kiện."
)

# ------------------------------------------------------------ Hàng chỉ số
part = view.participation_rate_by_event()
risk_df = churn_risk(view)

k1, k2, k3, k4 = st.columns(4)
d_mem = len(view.members) - len(club.members)
d_evt = len(view.events) - len(club.events)
k1.metric("Thành viên", len(view.members), delta=d_mem or None, delta_color="off")
k2.metric("Sự kiện", len(view.events), delta=d_evt or None, delta_color="off")
k3.metric("Tỉ lệ tham gia trung bình", f"{part['participation_rate'].mean() * 100:.1f}%")
k4.metric(
    "Thành viên nguy cơ cao",
    int((risk_df["risk_level"] == "Nguy cơ cao").sum()) if not risk_df.empty else 0,
)

if not reliable:
    st.warning(warning_text)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Tỉ lệ tham gia",
        "Tăng trưởng thành viên",
        "Xếp hạng tích cực",
        "Nguy cơ ngừng tham gia",
        "Bản đồ nhiệt",
        "Kiểm định & sức giữ chân",
    ]
)

with tab1:
    st.pyplot(plot_participation_by_event(view), clear_figure=True)
    st.dataframe(part, width="stretch")
    st.subheader("Theo lớp")
    st.dataframe(view.participation_rate_by_class(), width="stretch")
    st.caption(
        "Lưu ý: chênh lệch giữa các lớp KHÔNG có ý nghĩa thống kê "
        "(Kruskal-Wallis, xem tab Kiểm định). Không đọc bảng này như xếp hạng."
    )

with tab2:
    trend_df, trend_stats = growth_trend(view)
    st.pyplot(plot_member_growth(trend_df, trend_stats), clear_figure=True)
    st.write(
        f"Tốc độ tăng trưởng: **{trend_stats['slope']:.2f} thành viên/ngày** "
        f"(R² = {trend_stats['r_value'] ** 2:.3f})"
    )

with tab3:
    if not reliable:
        st.caption("Cỡ mẫu nhỏ — z-score và phân loại bên dưới chỉ mang tính minh hoạ.")
    top_n = st.slider(
        "Số thành viên hiển thị", min_value=1, max_value=len(view.members),
        value=min(10, len(view.members)),
    )
    st.pyplot(plot_top_engaged_members(view, top_n=top_n), clear_figure=True)
    st.dataframe(engagement_with_stats(view), width="stretch")

with tab4:
    if not reliable:
        st.caption("Cỡ mẫu nhỏ — churn_score bên dưới chỉ mang tính minh hoạ.")
    risk_top_n = st.slider(
        "Số thành viên hiển thị ", min_value=1, max_value=len(view.members),
        value=min(10, len(view.members)),
    )
    st.pyplot(plot_churn_risk(risk_df, top_n=risk_top_n), clear_figure=True)
    st.dataframe(risk_df, width="stretch")

with tab5:
    st.pyplot(plot_attendance_heatmap(view), clear_figure=True)
    st.caption(
        "Ô đậm = có mặt. Hàng xếp theo điểm tích cực giảm dần, cột theo thời gian. "
        "Người tham gia đều tạo dải liền ngang; người giảm dần nhạt về bên phải."
    )

with tab6:
    if not reliable:
        st.caption("Cỡ mẫu nhỏ — các p-value bên dưới không đủ tin cậy để kết luận.")
    show_test_result(
        "Kiểm định 1 — chênh lệch giữa các lớp (Kruskal-Wallis)",
        class_participation_test(view),
    )
    st.divider()
    show_test_result(
        "Kiểm định 2 — bắt buộc vs tự chọn (chi-square)",
        mandatory_vs_optional_test(view),
    )
    st.divider()
    show_test_result(
        "Kiểm định 3 — mức tham gia có suy giảm không (Wilcoxon ghép cặp)",
        participation_decline_test(view),
    )
    st.divider()
    st.subheader("Sức giữ chân của sự kiện")
    retention_df = event_retention_power(view)
    if retention_df.empty:
        st.info("Không đủ dữ liệu để tính sức giữ chân với bộ lọc hiện tại.")
    else:
        st.pyplot(plot_event_retention(retention_df), clear_figure=True)
        st.dataframe(retention_df, width="stretch")
