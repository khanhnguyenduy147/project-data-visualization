"""
export_analysis.py — Sinh `analysis.json` chứa các bảng tổng quan từ EDA + mô hình.

Đây là bước "xuất dữ liệu" cho trang analyse.html (giống cách
superstore_dashboard.ipynb xuất parameter_chart.json cho index.html).

Chạy:  python src/export_analysis.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from utils import load_and_shift, monthly_weights

ROOT = Path(__file__).resolve().parent.parent
SHIFT_YEARS = 9


def build():
    df = load_and_shift(ROOT / 'SampleSuperstore.csv', shift_years=SHIFT_YEARS)
    df['Year'] = df['Order Date'].dt.year

    loss = df[df['Profit'] < 0]
    profit_pos = df[df['Profit'] > 0]

    # --- Lợi nhuận TB theo mức chiết khấu + ngưỡng chuyển âm ---
    by_disc = (df.groupby('Discount')
                 .agg(avg_profit=('Profit', 'mean'), n=('Profit', 'size'))
                 .reset_index())
    neg = by_disc[by_disc['avg_profit'] < 0]
    threshold = float(neg['Discount'].min() * 100) if len(neg) else None

    # --- Biên LN theo Category & Sub-Category ---
    def margin_table(group_col):
        g = df.groupby(group_col).agg(sales=('Sales', 'sum'),
                                      profit=('Profit', 'sum')).reset_index()
        g['margin'] = (g['profit'] / g['sales'] * 100).round(1)
        return g

    cat = margin_table('Category').sort_values('sales', ascending=False)
    sub = margin_table('Sub-Category').sort_values('margin')  # thấp → cao

    # --- Region ---
    reg = (df.groupby('Region')
             .agg(sales=('Sales', 'sum'), profit=('Profit', 'sum'), txn=('Sales', 'size'))
             .reset_index())
    reg['margin'] = (reg['profit'] / reg['sales'] * 100).round(1)
    reg = reg.sort_values('sales', ascending=False)

    # --- Tính ổn định mùa vụ qua các năm ---
    month_cnt = df.groupby('Year')['Order Date'].apply(lambda s: s.dt.month.nunique())
    full_years = [int(y) for y in sorted(month_cnt.index) if month_cnt[y] == 12]
    wmat = pd.DataFrame({y: monthly_weights(df[df['Year'] == y]).values for y in full_years})
    spread = (wmat.max(axis=1) - wmat.min(axis=1)) * 100
    max_spread_month = int(spread.values.argmax()) + 1

    analysis = {
        '_meta': {
            'generated': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'shift_years': SHIFT_YEARS,
            'date_range': f"{df['Order Date'].min().date()} → {df['Order Date'].max().date()}",
            'rows': int(len(df)),
            'orders': int(df['Order ID'].nunique()),
            'customers': int(df['Customer ID'].nunique()),
            'n_columns': int(df.shape[1]) - 2,  # trừ 2 cột Year/Month tự thêm
        },
        'data_quality': {
            'missing_total': int(df.drop(columns=['Year', 'Month'], errors='ignore').isna().sum().sum()),
            'duplicates': int(df.duplicated().sum()),
        },
        'distributions': {
            'skew_sales': round(float(df['Sales'].skew()), 2),
            'skew_profit': round(float(df['Profit'].skew()), 2),
            'loss_orders': int(len(loss)),
            'loss_pct': round(len(loss) / len(df) * 100, 1),
            'loss_total': round(float(loss['Profit'].sum()), 0),
            'profit_total': round(float(profit_pos['Profit'].sum()), 0),
            'net_profit': round(float(df['Profit'].sum()), 0),
        },
        'loss_by_subcategory': [
            {'label': k, 'loss': round(float(v), 0)}
            for k, v in loss.groupby('Sub-Category')['Profit'].sum().sort_values().head(6).items()
        ],
        'discount_profit': {
            'corr': round(float(df['Discount'].corr(df['Profit'])), 3),
            'threshold_pct': threshold,
            'by_discount': [
                {'discount': round(float(r['Discount']) * 100, 0),
                 'avg_profit': round(float(r['avg_profit']), 1),
                 'n': int(r['n'])}
                for _, r in by_disc.iterrows()
            ],
        },
        'category': [
            {'label': r['Category'], 'sales': round(float(r['sales']), 0),
             'profit': round(float(r['profit']), 0), 'margin': float(r['margin'])}
            for _, r in cat.iterrows()
        ],
        'subcategory_margin': [
            {'label': r['Sub-Category'], 'sales': round(float(r['sales']), 0),
             'profit': round(float(r['profit']), 0), 'margin': float(r['margin'])}
            for _, r in sub.iterrows()
        ],
        'region': [
            {'region': r['Region'], 'sales': round(float(r['sales']), 0),
             'profit': round(float(r['profit']), 0), 'margin': float(r['margin']),
             'txn': int(r['txn'])}
            for _, r in reg.iterrows()
        ],
        'seasonality': {
            'years': full_years,
            'weights_by_year': {str(y): [round(float(x) * 100, 2) for x in wmat[y].values]
                                for y in full_years},
            'max_spread_pct': round(float(spread.max()), 2),
            'max_spread_month': f'T{max_spread_month}',
        },
    }

    out = ROOT / 'analysis.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(f'✅ Đã ghi {out}')
    print(f"   {analysis['_meta']['rows']:,} dòng | đơn lỗ {analysis['distributions']['loss_pct']}% "
          f"| corr Discount-Profit {analysis['discount_profit']['corr']} "
          f"| ngưỡng lỗ {threshold:.0f}%")


if __name__ == '__main__':
    build()
