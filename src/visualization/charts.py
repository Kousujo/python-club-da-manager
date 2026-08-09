"""Biểu đồ Matplotlib cho báo cáo (CLO3, ≥3 biểu đồ có title/label/legend)."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from src.models.club import Club


def plot_participation_by_event(
    club: Club, save_path: str | None = None
) -> plt.Figure:
    """Biểu đồ cột: tỉ lệ tham gia theo sự kiện."""
    df = club.participation_rate_by_event().sort_values(
        "participation_rate", ascending=False
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(df["event_name"], df["participation_rate"] * 100, color="#4C72B0")
    ax.set_title("Tỉ lệ tham gia theo sự kiện")
    ax.set_xlabel("Sự kiện")
    ax.set_ylabel("Tỉ lệ tham gia (%)")
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df["event_name"], rotation=30, ha="right")
    for i, v in enumerate(df["participation_rate"] * 100):
        ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=8)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


def plot_member_growth(
    trend_df: pd.DataFrame, trend_stats: dict, save_path: str | None = None
) -> plt.Figure:
    """Biểu đồ đường: số thành viên tích lũy theo thời gian + đường xu hướng."""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(
        trend_df["join_date"],
        trend_df["cumulative_members"],
        marker="o",
        label="Thực tế",
        color="#55A868",
    )
    ax.plot(
        trend_df["join_date"],
        trend_df["trend"],
        linestyle="--",
        label=f"Xu hướng ({trend_stats['slope']:.2f} thành viên/ngày)",
        color="#C44E52",
    )
    ax.set_title("Tăng trưởng thành viên theo thời gian")
    ax.set_xlabel("Ngày gia nhập")
    ax.set_ylabel("Số thành viên tích lũy")
    ax.legend()
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


def plot_top_engaged_members(
    club: Club, top_n: int = 10, save_path: str | None = None
) -> plt.Figure:
    """Biểu đồ cột ngang: top thành viên tích cực nhất (điểm có trọng số đa hình)."""
    df = club.engagement_ranking(top_n=top_n).sort_values("engagement_score")
    colors = [
        "#DD8452" if "Ban chủ nhiệm" in role else "#4C72B0" for role in df["role"]
    ]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(df["member_name"], df["engagement_score"], color=colors)
    ax.set_title(f"Top {top_n} thành viên tích cực nhất")
    ax.set_xlabel("Điểm tích cực (có trọng số)")
    ax.set_ylabel("Thành viên")
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


def plot_churn_risk(df: pd.DataFrame, top_n: int = 10, save_path: str | None = None) -> plt.Figure:
    """Biểu đồ cột ngang: xếp hạng nguy cơ ngừng tham gia theo churn_score."""
    color_map = {"Nguy cơ cao": "#C44E52", "Bình thường": "#4C72B0", "Ổn định": "#55A868"}
    top = df.sort_values("churn_score", ascending=False).head(top_n).sort_values("churn_score")
    colors = [color_map.get(level, "#999999") for level in top["risk_level"]]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(top["member_name"], top["churn_score"], color=colors)
    ax.set_title(f"Top {top_n} thành viên có nguy cơ ngừng tham gia cao nhất")
    ax.set_xlabel("Churn score (càng cao = nguy cơ càng lớn)")
    ax.set_ylabel("Thành viên")
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


def plot_attendance_heatmap(club, save_path: str | None = None) -> plt.Figure:
    """Bản đồ nhiệt điểm danh: hàng = thành viên, cột = sự kiện theo thời gian.

    Hàng sắp theo điểm tích cực giảm dần, cột sắp theo ngày diễn ra. Nhờ vậy
    các kiểu hành vi hiện thành hình: người tham gia đều đặn tạo dải liền
    ngang, người giảm dần tạo hình tam giác nhạt về bên phải, người chỉ đến
    theo hứng tạo các ô rời rạc.
    """
    df = club.to_dataframe()
    ranking = club.engagement_ranking()
    events_sorted = sorted(club.events.values(), key=lambda e: e.date)
    event_ids = [e.event_id for e in events_sorted]
    member_ids = list(ranking["member_id"])

    matrix = (
        df.assign(present=1)
        .pivot_table(
            index="member_id",
            columns="event_id",
            values="present",
            fill_value=0,
            aggfunc="max",
        )
        .reindex(index=member_ids, columns=event_ids, fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(matrix.values, cmap="Blues", aspect="auto", vmin=0, vmax=1)

    # Nhãn cột gộp luôn loại sự kiện và tô màu theo loại — tránh vẽ chữ đè lên
    # vùng ảnh hoặc đè lên tiêu đề.
    ax.set_xticks(range(len(event_ids)))
    ax.set_xticklabels(
        [
            f"{e.event_id}\n{e.date:%m/%y}\n{'BB' if e.get_attendance_weight() > 1.0 else 'TC'}"
            for e in events_sorted
        ],
        fontsize=8,
    )
    for label, event in zip(ax.get_xticklabels(), events_sorted):
        label.set_color("#C44E52" if event.get_attendance_weight() > 1.0 else "#55A868")

    ax.set_yticks(range(len(member_ids)))
    ax.set_yticklabels(ranking["member_name"], fontsize=7)

    ax.set_title(
        "Bản đồ nhiệt điểm danh — ô đậm = có mặt\n"
        "hàng: thành viên xếp theo điểm tích cực giảm dần | "
        "cột: sự kiện theo thời gian (BB = bắt buộc, TC = tự chọn)",
        fontsize=11,
    )
    ax.set_xlabel("Sự kiện")
    ax.set_ylabel("Thành viên")
    ax.set_xticks([x - 0.5 for x in range(1, len(event_ids))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(member_ids))], minor=True)
    ax.grid(which="minor", color="white", linewidth=0.5)
    ax.tick_params(which="minor", length=0)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig


def plot_event_retention(
    retention_df: pd.DataFrame, save_path: str | None = None
) -> plt.Figure:
    """Cột ngang: sức giữ chân của từng sự kiện với nhóm có nguy cơ rời bỏ.

    Cột dương = sự kiện kéo nhóm nguy cơ đến nhiều hơn nhóm còn lại.
    """
    df = retention_df.dropna(subset=["retention_lift"]).sort_values("retention_lift")
    colors = ["#55A868" if v > 0 else "#C44E52" for v in df["retention_lift"]]

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(df["event_name"], df["retention_lift"], color=colors)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_title(
        "Sức giữ chân của sự kiện\n"
        "(chênh lệch tỉ lệ tham gia: nhóm nguy cơ - nhóm còn lại)"
    )
    ax.set_xlabel("Retention lift (dương = kéo được nhóm nguy cơ)")
    ax.set_ylabel("Sự kiện")
    ax.tick_params(axis="y", labelsize=8)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
    return fig
