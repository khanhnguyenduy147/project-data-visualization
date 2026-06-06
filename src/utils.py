"""
utils.py — Hàm dùng chung cho dự án SuperStore Dashboard.

Tách logic lặp lại ra khỏi notebook để:
  - tránh trùng code giữa các notebook (pipeline, EDA, modeling)
  - dễ kiểm thử và tái sử dụng
  - giữ notebook tập trung vào phần trình bày/phân tích

Dùng trong notebook:
    import sys; sys.path.append('src')
    from utils import load_and_shift, monthly_weights, pace_weight, pct_chg
"""

import calendar
import pandas as pd


def shift_date(dt, years):
    """Dịch năm của một mốc thời gian, xử lý 29/2 của năm nhuận an toàn."""
    try:
        return dt.replace(year=dt.year + years)
    except ValueError:  # 29/2 -> năm đích không nhuận
        return dt.replace(year=dt.year + years, day=28)


def load_and_shift(csv_path, shift_years=9, encoding='latin1'):
    """Đọc CSV SuperStore và dịch 'Order Date' thêm `shift_years` năm.

    Trả về DataFrame đã parse ngày tháng. Mặc định +9 năm để
    2014–2017 → 2023–2026 (khớp chủ đề 'Dashboard 2026').
    """
    df = pd.read_csv(csv_path, encoding=encoding)
    df['Order Date'] = pd.to_datetime(df['Order Date'])
    df['Order Date'] = df['Order Date'].apply(lambda d: shift_date(d, shift_years))
    return df


def monthly_weights(df, date_col='Order Date', value_col='Sales'):
    """Trọng số mùa vụ từng tháng = tỷ trọng doanh thu tháng / tổng năm.

    Nhận một DataFrame của MỘT năm tham chiếu, trả về Series index 1..12.
    Dùng để xác định kỳ vọng phân bổ doanh thu theo mùa vụ.
    """
    by_month = (
        df.assign(_m=df[date_col].dt.month)
          .groupby('_m')[value_col].sum()
          .reindex(range(1, 13), fill_value=0)
    )
    total = by_month.sum()
    if total == 0:
        return by_month  # tránh chia 0; trả trọng số 0
    return by_month / total


def monthly_weights_multi(df, years, date_col='Order Date', value_col='Sales'):
    """Trọng số mùa vụ TRUNG BÌNH qua nhiều năm (làm mượt nhiễu của 1 năm).

    Tính vector trọng số 1..12 cho từng năm trong `years` rồi lấy trung bình
    đều. Ổn định hơn so với chỉ dùng 1 năm trước khi mùa vụ dao động.
    Trả về Series index 1..12.
    """
    years = list(years)
    if not years:
        raise ValueError('Cần ít nhất 1 năm để tính trọng số mùa vụ.')
    yr = df[date_col].dt.year
    per_year = [monthly_weights(df[yr == y], date_col, value_col) for y in years]
    return sum(per_year) / len(per_year)


def cagr(first_value, last_value, n_years):
    """Tốc độ tăng trưởng kép hằng năm (CAGR) giữa 2 mốc cách nhau n_years năm.

    Trả về tỷ lệ (vd. 0.087 = +8.7%/năm). Trả None nếu không tính được.
    """
    if n_years <= 0 or first_value <= 0 or last_value <= 0:
        return None
    return (last_value / first_value) ** (1 / n_years) - 1


def pace_weight(weights, cutoff):
    """Tỷ lệ kế hoạch năm 'lẽ ra đã đạt' tính đến `cutoff`, theo mùa vụ.

    pace_weight = Σ weight(tháng đã xong) + weight(tháng hiện tại) × (ngày đã qua / số ngày tháng)

    Trả về dict gồm pace_weight và các thành phần để giải thích/log.
    """
    cutoff = pd.Timestamp(cutoff)
    cut_m, cut_d = cutoff.month, cutoff.day
    days_in_month = calendar.monthrange(cutoff.year, cut_m)[1]

    full = float(sum(weights[m] for m in range(1, cut_m)))
    partial = float(weights[cut_m]) * (cut_d / days_in_month)
    return {
        'pace_weight': full + partial,
        'full_weight': full,
        'partial_weight': partial,
        'cut_month': cut_m,
        'cut_day': cut_d,
        'days_in_month': days_in_month,
        'formula': f'Σ weight(T1-T{cut_m - 1}) + weight(T{cut_m}) × ({cut_d}/{days_in_month})',
    }


def pct_chg(curr, prev):
    """% thay đổi của curr so với prev (0 nếu prev rỗng), làm tròn 1 chữ số."""
    return round((curr - prev) / prev * 100, 1) if prev else 0
