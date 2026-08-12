"""Pipeline chính: load dữ liệu → phân tích → xuất biểu đồ."""

from __future__ import annotations

from pathlib import Path

from src.analysis.stats import (
    churn_risk,
    class_participation_test,
    engagement_with_stats,
    event_retention_power,
    growth_trend,
    mandatory_vs_optional_test,
    participation_decline_test,
)
from src.config import setup_utf8_stdout
from src.processing.loader import load_club_from_csv
from src.visualization.charts import (
    plot_attendance_heatmap,
    plot_churn_risk,
    plot_event_retention,
    plot_member_growth,
    plot_participation_by_event,
    plot_top_engaged_members,
)

FIGURES_DIR = Path("report/figures")


def main() -> None:
    setup_utf8_stdout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    club = load_club_from_csv("data/raw")

    print("=== Tỉ lệ tham gia theo sự kiện ===")
    print(club.participation_rate_by_event().to_string(index=False))

    print("\n=== Tỉ lệ tham gia theo thành viên ===")
    print(club.participation_rate_by_member().to_string(index=False))

    print("\n=== Tỉ lệ tham gia theo lớp ===")
    print(club.participation_rate_by_class().to_string(index=False))

    trend_df, trend_stats = growth_trend(club)
    print("\n=== Xu hướng tăng trưởng thành viên ===")
    print(
        f"slope={trend_stats['slope']:.3f} thành viên/ngày, "
        f"r={trend_stats['r_value']:.3f}, p={trend_stats['p_value']:.4f}"
    )

    print("\n=== Xếp hạng thành viên tích cực (kèm thống kê) ===")
    print(engagement_with_stats(club).to_string(index=False))

    risk_df = churn_risk(club)
    print("\n=== Nguy cơ ngừng tham gia ===")
    print(risk_df.to_string(index=False))

    print("\n=== Kiểm định 1: chênh lệch giữa các lớp (Kruskal-Wallis) ===")
    for key, value in class_participation_test(club).items():
        print(f"  {key}: {value}")

    print("\n=== Kiểm định 2: sự kiện bắt buộc vs tự chọn (chi-square) ===")
    for key, value in mandatory_vs_optional_test(club).items():
        print(f"  {key}: {value}")

    print("\n=== Kiểm định 3: mức tham gia có suy giảm không (Wilcoxon ghép cặp) ===")
    for key, value in participation_decline_test(club).items():
        print(f"  {key}: {value}")

    retention_df = event_retention_power(club)
    print("\n=== Sức giữ chân của sự kiện với nhóm nguy cơ ===")
    print(retention_df.to_string(index=False))

    plot_participation_by_event(club, str(FIGURES_DIR / "participation_by_event.png"))
    plot_member_growth(trend_df, trend_stats, str(FIGURES_DIR / "member_growth.png"))
    plot_top_engaged_members(club, save_path=str(FIGURES_DIR / "top_members.png"))
    plot_churn_risk(risk_df, save_path=str(FIGURES_DIR / "churn_risk.png"))
    plot_attendance_heatmap(club, str(FIGURES_DIR / "attendance_heatmap.png"))
    plot_event_retention(retention_df, str(FIGURES_DIR / "event_retention.png"))

    print(f"\nĐã lưu 6 biểu đồ vào {FIGURES_DIR}/")


if __name__ == "__main__":
    main()