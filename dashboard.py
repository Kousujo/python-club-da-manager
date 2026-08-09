"""Dashboard Streamlit — hiển thị lại phân tích Club dưới dạng tương tác."""

from __future__ import annotations

import streamlit as st

from src.analysis.stats import (
    churn_risk,
    engagement_with_stats,
    event_retention_power,
    growth_trend,
    mandatory_vs_optional_test,
    participation_decline_test,
)
from src.processing.loader import load_club_from_csv
from src.visualization.charts import (
    plot_attendance_heatmap,
    plot_churn_risk,
    plot_event_retention,
    plot_member_growth,
    plot_participation_by_event,
    plot_top_engaged_members,
)

st.set_page_config(page_title="Quản lý CLB IT Club", layout="wide")


@st.cache_resource
def get_club():
    return load_club_from_csv("data/raw")


club = get_club()

st.title("Dashboard quản lý câu lạc bộ — IT Club")

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
    st.pyplot(plot_participation_by_event(club))
    st.dataframe(club.participation_rate_by_event(), width="stretch")
    st.subheader("Theo lớp")
    st.dataframe(club.participation_rate_by_class(), width="stretch")

with tab2:
    trend_df, trend_stats = growth_trend(club)
    st.pyplot(plot_member_growth(trend_df, trend_stats))
    st.write(
        f"Tốc độ tăng trưởng: **{trend_stats['slope']:.2f} thành viên/ngày** "
        f"(R² = {trend_stats['r_value'] ** 2:.3f})"
    )

with tab3:
    top_n = st.slider("Số thành viên hiển thị", min_value=5, max_value=len(club.members), value=10)
    st.pyplot(plot_top_engaged_members(club, top_n=top_n))
    st.dataframe(engagement_with_stats(club), width="stretch")

with tab4:
    risk_df = churn_risk(club)
    risk_top_n = st.slider("Số thành viên hiển thị ", min_value=5, max_value=len(club.members), value=10)
    st.pyplot(plot_churn_risk(risk_df, top_n=risk_top_n))
    st.dataframe(risk_df, width="stretch")

with tab5:
    st.pyplot(plot_attendance_heatmap(club))
    st.caption(
        "Ô đậm = có mặt. Hàng xếp theo điểm tích cực giảm dần, cột theo thời gian. "
        "Người tham gia đều tạo dải liền ngang; người giảm dần nhạt về bên phải."
    )

with tab6:
    st.subheader("Kiểm định 1 — bắt buộc vs tự chọn (chi-square)")
    st.json(mandatory_vs_optional_test(club))

    st.subheader("Kiểm định 2 — mức tham gia có suy giảm không (Wilcoxon ghép cặp)")
    st.json(participation_decline_test(club))

    st.subheader("Sức giữ chân của sự kiện")
    retention_df = event_retention_power(club)
    st.pyplot(plot_event_retention(retention_df))
    st.dataframe(retention_df, width="stretch")