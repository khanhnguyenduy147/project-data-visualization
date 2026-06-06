# 📊 SuperStore Executive Dashboard

Dashboard điều hành (executive dashboard) trực quan hóa kết quả kinh doanh của chuỗi bán lẻ **SuperStore**, so sánh hiệu suất thực tế với mục tiêu năm và **mục tiêu theo tiến độ mùa vụ (pace goal)**.

---

## 🎯 Mục đích

Dự án biến dữ liệu giao dịch thô thành một dashboard quản trị một trang, giúp trả lời nhanh các câu hỏi:

- Doanh thu / lợi nhuận **YTD** (từ đầu năm đến hiện tại) đang ở đâu so với kế hoạch?
- Đang **đi nhanh hay chậm** so với tiến độ kỳ vọng — có tính đến **yếu tố mùa vụ** (không chia đều theo thời gian)?
- Danh mục (Category), phân khúc khách hàng (Segment), khu vực (Region), nhóm sản phẩm con (Sub-Category) nào dẫn đầu / cần chú ý?
- Tăng trưởng so với cùng kỳ năm trước (**YoY**) như thế nào?

---

## 🗂️ Cấu trúc dự án

| File | Vai trò |
|------|---------|
| `SampleSuperstore.csv` | Dữ liệu nguồn — giao dịch bán lẻ SuperStore (Order Date, Sales, Profit, Category, Segment, Region, Sub-Category, Discount...) |
| `src/utils.py` | **Hàm dùng chung** — đọc & dịch dữ liệu, tính trọng số mùa vụ, pace weight, % thay đổi. Được các notebook import để tránh trùng code |
| `src/export_analysis.py` | **Exporter EDA** — sinh `analysis.json` (các bảng tổng quan EDA) cho trang phân tích |
| `01_eda.ipynb` | **Khám phá dữ liệu (EDA)** — chất lượng dữ liệu, phân phối, outlier, đơn lỗ, tương quan Discount→Profit, kiểm chứng tính mùa vụ |
| `02_profit_model.ipynb` | **Mô hình Profit-Driver** — XGBoost + SHAP dự đoán đơn lỗ và định lượng yếu tố phá biên lợi nhuận |
| `superstore_dashboard.ipynb` | **Pipeline xử lý dữ liệu** — đọc CSV, tính toán toàn bộ tham số, xuất ra file JSON |
| `kpi.json` | Cấu hình & kết quả mục tiêu: growth targets, CAGR lịch sử, annual/pace goals, trọng số tháng |
| `parameter_chart.json` | Toàn bộ dữ liệu đã tính sẵn để dashboard vẽ biểu đồ (KPI cards, pace chart, trend, mix...) |
| `analysis.json` | Các bảng tổng quan EDA cho trang phân tích |
| `index.html` | **Dashboard** — trang chính, đọc từ `parameter_chart.json` |
| `analyse.html` | **Trang Phân tích (EDA)** — bảng tổng quan: chất lượng dữ liệu, đơn lỗ, Discount→Profit, biên LN, mùa vụ |
| `result.html` | **Trang Kết quả & Pace** — giải thích pace weight, biên lợi nhuận và biện minh CAGR |

Ba trang HTML liên kết với nhau qua thanh điều hướng: **📊 Dashboard · 🔍 Phân tích · 🎯 Kết quả & Pace**.

**Luồng dữ liệu:**
```
                          ┌→ superstore_dashboard.ipynb → kpi.json + parameter_chart.json → index.html, result.html
SampleSuperstore.csv ─────┤  (đều import src/utils.py)
                          └→ src/export_analysis.py     → analysis.json                   → analyse.html, result.html
```

Chỉnh mục tiêu trong notebook (biến `GROWTH`) → chạy lại notebook → dashboard tự cập nhật.

---

## 🛠️ Công cụ sử dụng

**Xử lý dữ liệu (Python):**
- `pandas` — đọc, lọc, nhóm (groupby) và tổng hợp dữ liệu
- `numpy` — tính toán số học
- `calendar`, `datetime` — xử lý ngày tháng, số ngày trong tháng
- `json` — xuất kết quả ra file
- Jupyter Notebook — môi trường chạy pipeline

**Trực quan hóa (Frontend):**
- `Chart.js 4.4.1` — vẽ biểu đồ (qua CDN)
- HTML / CSS thuần — bố cục dashboard, font Inter + JetBrains Mono

---

## 🧮 Thuật toán & phương pháp tính

### 1. Dịch thời gian (+9 năm)
Dữ liệu mẫu gốc từ **2014–2017** được dịch sang **2023–2026** (`SHIFT_YEARS = 9`) để mô phỏng dữ liệu hiện tại và khớp chủ đề "Dashboard 2026" (có xử lý ngày 29/2 của năm nhuận). Nhờ vậy năm hiện tại (2026) có dữ liệu YTD và năm trước (2025) đủ 12 tháng để làm tham chiếu.

### 2. Trọng số mùa vụ (seasonal weighting)
Thay vì giả định doanh thu trải đều theo thời gian, mô hình tính **tỷ trọng doanh thu thực tế của từng tháng**, lấy **trung bình qua vài năm gần nhất** (`SEASONALITY_YEARS`, mặc định 3) để làm mượt nhiễu của một năm đơn lẻ:

```
weight(tháng m) = trung bình qua N năm của [ doanh_thu(m) / tổng_doanh_thu_năm ]
```

> EDA (notebook 01) cho thấy mùa vụ khá ổn định qua các năm (chênh tối đa ~4.9 điểm %), nên trung bình nhiều năm cho trọng số đáng tin hơn dùng 1 năm.

### 3. Pace weight — tiến độ kỳ vọng theo mùa vụ
Tỷ lệ phần trăm mục tiêu *lẽ ra phải đạt được* tính đến thời điểm hiện tại:

```
pace_weight = Σ weight(các tháng đã hoàn thành) + weight(tháng hiện tại) × (số ngày đã qua / số ngày trong tháng)
```

> Ví dụ tại 05/06: pace_weight ≈ **29.5%** (thay vì 42.5% nếu chia tuyến tính) — phản ánh nửa cuối năm là mùa cao điểm.

### 4. Mục tiêu năm & mục tiêu hiện tại
```
annual_goal = doanh_thu_năm_trước × (1 + % tăng trưởng mục tiêu)
pace_goal   = annual_goal × pace_weight
```
Áp dụng cho tổng doanh thu, từng Category và từng Segment.

**Biện minh mục tiêu tăng trưởng (CAGR):** mục tiêu trong `GROWTH` không phải số áp đặt — pipeline đối chiếu từng mục tiêu với **CAGR (tốc độ tăng trưởng kép hằng năm)** thực tế của các năm đã qua và gắn nhãn *thận trọng / sát lịch sử / tham vọng*. Ví dụ với dữ liệu mẫu:

| Chỉ số | CAGR lịch sử | Mục tiêu | Đánh giá |
|--------|-------------:|---------:|----------|
| Tổng doanh thu | +14.8% | +15% | 🟡 Sát lịch sử |
| Office Supplies | +17.5% | +12% | 🟢 Thận trọng |
| Technology | +15.7% | +18% | 🔴 Tham vọng |
| Consumer (segment) | +7.6% | +12% | 🔴 Tham vọng |

CAGR thực tế được lưu vào `kpi.json` (`historical_cagr`) để truy vết.

### 5. Các chỉ số & thành phần dashboard
- **KPI cards**: Doanh thu, Lợi nhuận, Biên lợi nhuận, Số giao dịch, AOV (giá trị đơn TB), Chiết khấu TB — kèm so sánh YoY và pace goal
- **Pace chart**: phân loại trạng thái `ahead` / `on_pace` / `behind` dựa trên độ lệch giữa % thực đạt và % kỳ vọng (ngưỡng ±1 điểm %)
- **Monthly / Quarterly trend**: xu hướng theo tháng/quý, năm nay vs năm trước, kèm đường mục tiêu theo trọng số mùa vụ
- **Category mix, Region performance, Top Sub-Categories**: cơ cấu doanh thu, biên LN và YoY theo từng chiều
- **Bullet points**: tự động sinh nhận định trọng yếu (dẫn đầu / cần chú ý / tình trạng biên LN)

---

## 🔍 Khám phá dữ liệu (EDA) — `01_eda.ipynb`

Phân tích khám phá đặt nền cho pipeline và mô hình, gồm: kiểm tra chất lượng dữ liệu, phân phối biến số, outlier, đơn hàng lỗ, ma trận tương quan, quan hệ Discount→Profit, và kiểm chứng tính ổn định của mùa vụ.

**Một số phát hiện chính (dữ liệu mẫu):**

| Phát hiện | Con số |
|-----------|--------|
| Tỷ lệ đơn hàng **lỗ** | **18.7%** số đơn — tổng lỗ ~**$156k** |
| Phân phối Sales/Profit | Lệch phải mạnh (skew Sales ≈ 13) → có outlier |
| Tương quan **Discount ↔ Profit** | **−0.22** (âm) |
| Ngưỡng chiết khấu nguy hiểm | Lợi nhuận TB **chuyển âm khi Discount ≥ 30%** |
| Tính mùa vụ | Khá ổn định qua 4 năm (chênh trọng số tháng lớn nhất ~4.9 điểm %) |

➡️ Phát hiện Discount→Profit là động lực cho bước tiếp theo: mô hình **profit-driver** (`02_profit_model.ipynb`).

---

## 🤖 Mô hình Profit-Driver — `02_profit_model.ipynb`

Phân tích **chẩn đoán**: vì sao đơn hàng bị lỗ, và yếu tố nào phá biên lợi nhuận mạnh nhất?

- **Bài toán:** phân loại nhị phân — dự đoán đơn hàng có lỗ (`Profit < 0`) hay không, chỉ dùng đặc trưng *biết được tại thời điểm bán* (Discount, Sales, Quantity, Category, Sub-Category, Segment, Region, Ship Mode).
- **Mô hình:** `XGBoost` (gradient boosted trees) — phù hợp dữ liệu bảng, phi tuyến; xử lý mất cân bằng lớp bằng `scale_pos_weight`.
- **Giải thích:** `feature importance` (gain) + `SHAP` (chiều & độ lớn tác động) để ra khuyến nghị hành động, không chỉ dự đoán.
- **Chống rò rỉ dữ liệu (leakage):** target lấy từ `Profit` → KHÔNG đưa `Profit` vào đặc trưng.

**Kết quả (tập test 25%):**

| Chỉ số | Giá trị |
|--------|---------|
| ROC-AUC | **0.988** |
| Accuracy | **93%** |
| Recall lớp "Lỗ" | **0.92** |
| Yếu tố quan trọng nhất | **Discount** (importance ≈ 0.33, gấp ~3× yếu tố thứ hai) |

**Khuyến nghị rút ra:** đặt **trần chiết khấu** quanh ngưỡng nguy hiểm; rà soát giá cho các Sub-Category lỗ kinh niên (Storage, Paper, Binders...); dùng mô hình làm **cảnh báo sớm** gắn cờ đơn rủi ro lỗ trước khi chốt.

---

## ▶️ Cách chạy

1. (Khuyến nghị) Tạo môi trường ảo và cài thư viện:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. (Tùy chọn) Chạy `01_eda.ipynb` để xem phân tích khám phá dữ liệu.
3. (Tùy chọn) Chạy `02_profit_model.ipynb` để xem mô hình profit-driver (XGBoost + SHAP).
4. Chạy toàn bộ `superstore_dashboard.ipynb` (sinh `kpi.json` + `parameter_chart.json`; cập nhật `CUTOFF` nếu cần).
5. Sinh dữ liệu cho trang phân tích:
   ```powershell
   python src/export_analysis.py
   ```
6. Phục vụ trang qua HTTP server (vì các trang dùng `fetch` — không chạy được với `file://`):
   ```powershell
   python -m http.server 8000
   ```
   Mở `http://localhost:8000/index.html` rồi điều hướng giữa **Dashboard · Phân tích · Kết quả & Pace**.

> **Lưu ý về CUTOFF:** Dữ liệu sau khi dịch trải từ **2023 đến hết 2026**. `CUTOFF` mặc định `2026-06-05` (giữa năm) để mô phỏng "hôm nay" — năm 2026 có dữ liệu YTD (T1–T6), năm 2025 đủ 12 tháng làm tham chiếu. Nếu đổi `CUTOFF`, hãy giữ trong khoảng có dữ liệu này.
