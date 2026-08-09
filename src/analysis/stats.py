"""Phân tích thống kê nâng cao (SciPy) trên dữ liệu từ Club.

Tầng này KHÔNG chứa logic OOP, chỉ nhận Club đã build sẵn (từ
models/club.py, sau khi loader.py nạp dữ liệu) và làm phân tích bổ
sung: xu hướng tăng trưởng, phân loại thành viên bằng thống kê.

Mọi truy cập dữ liệu đi qua interface công khai của Club
(club.members / club.events / club.to_dataframe()).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from src.models.club import Club


def growth_trend(club: Club) -> tuple[pd.DataFrame, dict[str, float]]:
    """Xu hướng tăng trưởng thành viên theo thời gian bằng hồi quy tuyến tính.

    Lưu ý diễn giải: club chỉ tuyển thành viên trong một giai đoạn ngắn rồi
    dừng, nên đường tích luỹ có dạng BÃO HOÀ. Hồi quy tuyến tính ở đây mô tả
    tốc độ tuyển quân của giai đoạn đầu, KHÔNG dùng để ngoại suy tương lai.

    Trả về:
        - DataFrame (join_date, new_members, cumulative_members) kèm cột
          'trend' — giá trị dự đoán theo đường hồi quy, dùng để vẽ overlay.
        - dict thống kê: slope (thành viên/ngày), intercept, r_value,
          p_value, std_err — dùng để giải thích xu hướng trong báo cáo.
    """
    df = club.member_growth_over_time()
    if df.empty or len(df) < 2:
        return df.assign(trend=np.nan), {
            "slope": 0.0,
            "intercept": 0.0,
            "r_value": 0.0,
            "p_value": 1.0,
            "std_err": 0.0,
        }

    join_dates = pd.to_datetime(df["join_date"])
    x = (join_dates - join_dates.min()).dt.days
    y = df["cumulative_members"]

    result = stats.linregress(x, y)
    df = df.copy()
    df["trend"] = result.intercept + result.slope * x

    return df, {
        "slope": result.slope,
        "intercept": result.intercept,
        "r_value": result.rvalue,
        "p_value": result.pvalue,
        "std_err": result.stderr,
    }


def engagement_with_stats(club: Club, z_threshold: float = 1.0) -> pd.DataFrame:
    """engagement_ranking() bổ sung z-score, percentile và phân loại thống kê.

    Phân loại:
        - 'Nổi bật'       nếu z-score >= z_threshold
        - 'Cần khích lệ'  nếu z-score <= -z_threshold
        - 'Bình thường'   còn lại
    """
    df = club.engagement_ranking().reset_index(drop=True)
    if df.empty or df["engagement_score"].std(ddof=0) == 0:
        df = df.copy()
        df["z_score"] = 0.0
        df["percentile"] = 100.0
        df["classification"] = "Bình thường"
        return df

    df = df.copy()
    df["z_score"] = stats.zscore(df["engagement_score"])
    df["percentile"] = df["engagement_score"].rank(pct=True) * 100

    def classify(z: float) -> str:
        if z >= z_threshold:
            return "Nổi bật"
        if z <= -z_threshold:
            return "Cần khích lệ"
        return "Bình thường"

    df["classification"] = df["z_score"].apply(classify)
    return df


def churn_risk(club: Club, z_threshold: float = 1.0) -> pd.DataFrame:
    """Ước lượng nguy cơ ngừng tham gia CLB.

    2 yếu tố, chuẩn hoá z-score:
      - recency_days: số ngày kể từ lần tham gia gần nhất đến sự kiện
        cuối cùng trong dữ liệu (chưa từng tham gia = stale tối đa).
      - trend_drop: tỉ lệ tham gia nửa đầu khoảng thời gian - nửa cuối
        (dương = đang giảm dần).
    churn_score = trung bình 2 z-score, phân loại theo z_threshold,
    đồng bộ phong cách với engagement_with_stats().

    Toàn bộ tính bằng groupby vector hoá, không lọc DataFrame trong vòng lặp.
    """
    events = club.events
    members = club.members
    if not events or not members:
        return pd.DataFrame()

    event_dates = sorted(e.date for e in events.values())
    first_date, last_date = event_dates[0], event_dates[-1]
    mid_date = event_dates[len(event_dates) // 2]

    first_half_ids = {eid for eid, e in events.items() if e.date <= mid_date}
    second_half_ids = {eid for eid, e in events.items() if e.date > mid_date}

    index = pd.Index(list(members.keys()), name="member_id")
    df = club.to_dataframe()

    if df.empty:
        last_attend = pd.Series(pd.NaT, index=index)
        count_first = pd.Series(0, index=index)
        count_second = pd.Series(0, index=index)
    else:
        last_attend = (
            pd.to_datetime(df["checkin_time"])
            .groupby(df["member_id"])
            .max()
            .reindex(index)
        )
        count_first = (
            df[df["event_id"].isin(first_half_ids)]
            .groupby("member_id")["event_id"]
            .nunique()
            .reindex(index, fill_value=0)
        )
        count_second = (
            df[df["event_id"].isin(second_half_ids)]
            .groupby("member_id")["event_id"]
            .nunique()
            .reindex(index, fill_value=0)
        )

    stale_days = (last_date - first_date).days
    recency_days = last_attend.apply(
        lambda ts: stale_days if pd.isna(ts) else (last_date - ts.date()).days
    )

    rate_first = count_first / len(first_half_ids) if first_half_ids else 0.0
    rate_second = count_second / len(second_half_ids) if second_half_ids else 0.0

    result = pd.DataFrame(
        {
            "member_id": index,
            "member_name": [members[mid].full_name for mid in index],
            "recency_days": recency_days.to_numpy(),
            "trend_drop": (rate_first - rate_second).to_numpy(),
        }
    ).reset_index(drop=True)

    if len(result) < 2 or result["recency_days"].std(ddof=0) == 0:
        result["churn_score"] = 0.0
    else:
        z_recency = stats.zscore(result["recency_days"])
        z_trend = stats.zscore(result["trend_drop"])
        result["churn_score"] = (z_recency + z_trend) / 2

    result["risk_level"] = result["churn_score"].apply(
        lambda z: (
            "Nguy cơ cao"
            if z >= z_threshold
            else "Ổn định"
            if z <= -z_threshold
            else "Bình thường"
        )
    )
    return result.sort_values("churn_score", ascending=False, ignore_index=True)


# ---------------------------------------------------------------------------
# Kiểm định giả thuyết (B) — trả lời câu hỏi CÓ/KHÔNG, không chỉ mô tả số liệu
# ---------------------------------------------------------------------------
def participation_decline_test(club: Club) -> dict[str, float | str | int]:
    """Mức tham gia của CLB có SUY GIẢM theo thời gian một cách có ý nghĩa không?

    Với mỗi thành viên, tính tỉ lệ tham gia ở nửa đầu và nửa sau chuỗi sự
    kiện, rồi kiểm định Wilcoxon ghép cặp (một phía, H1: nửa đầu > nửa sau).

    Ghép cặp vì hai số đo đến từ CÙNG một người — dùng kiểm định độc lập ở
    đây sẽ bỏ phí thông tin và làm giảm lực kiểm định. Wilcoxon thay vì
    t-test ghép cặp vì tỉ lệ bị chặn trong [0, 1], không phân phối chuẩn.

    Đây là kiểm định đứng sau toàn bộ phần churn: nếu p không có ý nghĩa thì
    "nguy cơ rời bỏ" chỉ là nhiễu, không phải xu hướng.
    """
    events = club.events
    if len(events) < 2 or not club.members:
        return {"error": "Không đủ dữ liệu để kiểm định."}

    event_dates = sorted(e.date for e in events.values())
    mid_date = event_dates[len(event_dates) // 2]
    first_ids = {eid for eid, e in events.items() if e.date <= mid_date}
    second_ids = set(events) - first_ids
    if not first_ids or not second_ids:
        return {"error": "Không chia được nửa đầu / nửa sau."}

    df = club.to_dataframe()
    rate_first, rate_second = [], []
    for member_id in club.members:
        attended = (
            set(df.loc[df["member_id"] == member_id, "event_id"])
            if not df.empty
            else set()
        )
        rate_first.append(len(attended & first_ids) / len(first_ids))
        rate_second.append(len(attended & second_ids) / len(second_ids))

    diffs = np.array(rate_first) - np.array(rate_second)
    if np.all(diffs == 0):
        return {"error": "Hai nửa giống hệt nhau, không kiểm định được."}

    result = stats.wilcoxon(rate_first, rate_second, alternative="greater")
    return {
        "n_pairs": int(len(diffs)),
        "mean_rate_first_half": float(np.mean(rate_first)),
        "mean_rate_second_half": float(np.mean(rate_second)),
        "n_declined": int((diffs > 0).sum()),
        "n_improved": int((diffs < 0).sum()),
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "conclusion": (
            "Bác bỏ H0: mức tham gia suy giảm có ý nghĩa thống kê (α=0.05)."
            if result.pvalue < 0.05
            else "Chưa bác bỏ được H0: chưa đủ bằng chứng cho việc suy giảm (α=0.05)."
        ),
    }


def mandatory_vs_optional_test(club: Club) -> dict[str, float | str | int]:
    """Sự kiện bắt buộc có tỉ lệ tham gia cao hơn sự kiện tự chọn không?

    Bảng chéo 2x2 (có mặt / vắng) x (bắt buộc / tự chọn), kiểm định
    chi-square độc lập. Mẫu số = số thành viên x số sự kiện mỗi loại.
    """
    from src.models.event import MandatoryEvent

    n_members = len(club.members)
    df = club.to_dataframe()
    if n_members == 0 or not club.events:
        return {"error": "Không đủ dữ liệu để kiểm định."}

    mandatory_ids = {
        eid for eid, e in club.events.items() if isinstance(e, MandatoryEvent)
    }
    optional_ids = set(club.events) - mandatory_ids
    if not mandatory_ids or not optional_ids:
        return {"error": "Cần có cả sự kiện bắt buộc và tự chọn để kiểm định."}

    present_mandatory = int(df["event_id"].isin(mandatory_ids).sum())
    present_optional = int(df["event_id"].isin(optional_ids).sum())
    slots_mandatory = n_members * len(mandatory_ids)
    slots_optional = n_members * len(optional_ids)

    table = np.array(
        [
            [present_mandatory, slots_mandatory - present_mandatory],
            [present_optional, slots_optional - present_optional],
        ]
    )
    chi2, p_value, dof, _ = stats.chi2_contingency(table)

    return {
        "rate_mandatory": present_mandatory / slots_mandatory,
        "rate_optional": present_optional / slots_optional,
        "chi2": float(chi2),
        "dof": int(dof),
        "p_value": float(p_value),
        "conclusion": (
            "Bác bỏ H0: loại sự kiện có liên hệ với tỉ lệ tham gia (α=0.05)."
            if p_value < 0.05
            else "Chưa bác bỏ được H0: chưa thấy liên hệ có ý nghĩa (α=0.05)."
        ),
    }


# ---------------------------------------------------------------------------
# Sức giữ chân của SỰ KIỆN (C) — đảo góc nhìn churn từ người sang sự kiện
# ---------------------------------------------------------------------------
def event_retention_power(club: Club, top_frac: float = 0.25) -> pd.DataFrame:
    """Sự kiện nào kéo được nhóm thành viên đang có nguy cơ rời bỏ?

    Cách tính:
      1. Lấy churn_risk(), chọn nhóm top_frac có churn_score cao nhất
         làm nhóm "nguy cơ".
      2. Với mỗi sự kiện, chỉ xét những người CÒN HOẠT ĐỘNG tại thời điểm
         đó — tức đã gia nhập, và sự kiện diễn ra không muộn hơn lần điểm
         danh cuối cùng của họ.
      3. retention_lift = tỉ lệ tham gia của nhóm nguy cơ - nhóm còn lại.

    Bước 2 là bắt buộc, không phải tinh chỉnh. Nhóm "nguy cơ" được định
    nghĩa bằng chính việc họ đã ngừng đi, nên nếu lấy mẫu số là toàn bộ
    nhóm thì mọi sự kiện diễn ra muộn đều tự động có lift âm — chỉ số sẽ
    đo thứ tự thời gian chứ không đo sức hút của sự kiện.

    lift > 0 nghĩa là khi những người này còn hoạt động, sự kiện đó kéo họ
    đến MẠNH HƠN nhóm còn lại — loại sự kiện ban chủ nhiệm nên tổ chức lại.
    """
    risk = churn_risk(club)
    if risk.empty or not club.events:
        return pd.DataFrame()

    n_at_risk = max(1, int(round(len(risk) * top_frac)))
    at_risk_ids = set(risk.nlargest(n_at_risk, "churn_score")["member_id"])

    df = club.to_dataframe()
    # Cửa sổ hoạt động của từng người: [join_date, ngày điểm danh cuối cùng]
    last_active: dict[str, object] = {}
    if not df.empty:
        last_active = {
            mid: ts.date()
            for mid, ts in pd.to_datetime(df["checkin_time"])
            .groupby(df["member_id"])
            .max()
            .items()
        }

    def is_active(member_id: str, event_date) -> bool:
        member = club.members[member_id]
        if event_date < member.join_date:
            return False
        last = last_active.get(member_id)
        return last is not None and event_date <= last

    rows = []
    for event in sorted(club.events.values(), key=lambda e: e.date):
        attended = (
            set(df.loc[df["event_id"] == event.event_id, "member_id"])
            if not df.empty
            else set()
        )
        active_at_risk = {m for m in at_risk_ids if is_active(m, event.date)}
        active_others = {
            m
            for m in club.members
            if m not in at_risk_ids and is_active(m, event.date)
        }
        rate_at_risk = (
            len(attended & active_at_risk) / len(active_at_risk)
            if active_at_risk
            else float("nan")
        )
        rate_others = (
            len(attended & active_others) / len(active_others)
            if active_others
            else float("nan")
        )
        rows.append(
            {
                "event_id": event.event_id,
                "event_name": event.name,
                "event_type": type(event).__name__,
                "date": event.date,
                "n_active_at_risk": len(active_at_risk),
                "rate_at_risk": rate_at_risk,
                "rate_others": rate_others,
                "retention_lift": rate_at_risk - rate_others,
            }
        )

    result = pd.DataFrame(rows)
    return result.sort_values(
        "retention_lift", ascending=False, ignore_index=True, na_position="last"
    )