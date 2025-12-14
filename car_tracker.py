import streamlit as st
import pandas as pd
import itertools
import altair as alt

# 1. 頁面設定
st.set_page_config(page_title="車輛軌跡分析系統", layout="wide")

# 2. CSS 強制修正 (手機/電腦通用深色戰情風格)
st.markdown("""
<style>
    /* =========================================
       1. 全域配色鎖定 (強制深色模式)
       ========================================= */
    :root {
        color-scheme: dark;
    }
    
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0E1117 !important;
        color: #FAFAFA !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #262730 !important;
    }

    /* 強制所有文字顏色 */
    p, div, span, label, h1, h2, h3, h4, h5, h6, li {
        color: #E0E0E0 !important;
    }

    html, body, [class*="css"] {
        font-family: "Microsoft JhengHei", "Segoe UI", Roboto, sans-serif !important;
    }

    /* =========================================
       2. 手機下拉選單強力修復
       ========================================= */
    
    /* 輸入框本體 */
    div[data-baseweb="select"] > div, div[data-baseweb="base-input"] {
        background-color: #262730 !important;
        color: #FAFAFA !important;
        border-color: #444 !important;
    }

    /* 彈出視窗 (Popover) 與 選單 (Menu) */
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {
        background-color: #262730 !important;
        border: 1px solid #444 !important;
    }

    /* 選項文字 */
    div[data-baseweb="menu"] li, div[data-baseweb="menu"] div {
        color: #FAFAFA !important;
        background-color: #262730 !important;
    }

    /* 滑鼠滑過 / 手機按壓高亮 */
    div[data-baseweb="menu"] li:hover, 
    div[data-baseweb="menu"] li[aria-selected="true"] {
        background-color: #4DA6FF !important;
        color: #FFFFFF !important;
    }
    
    /* 多選標籤 */
    div[data-baseweb="tag"] {
        background-color: #4DA6FF !important;
        color: white !important;
    }

    /* =========================================
       3. 表格樣式 (手機橫向滑動 + 無索引)
       ========================================= */
    .table-container {
        width: 100%;
        overflow-x: auto; 
        -webkit-overflow-scrolling: touch;
        margin-bottom: 1rem;
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-radius: 4px;
    }

    .custom-table {
        width: 100%;
        border-collapse: collapse;
        background-color: #1E1E1E !important; 
        min-width: 600px; /* 強制最小寬度，觸發滑動 */
    }
    
    .custom-table th {
        background-color: #000000 !important;
        color: #4DA6FF !important;
        font-weight: 600;
        text-transform: uppercase;
        padding: 10px 8px;
        border-bottom: 2px solid #4DA6FF;
        border-right: 1px solid #333;
        white-space: nowrap; 
        text-align: left;
        font-size: 14px;
    }
    
    .custom-table td {
        background-color: #1E1E1E !important;
        color: #E0E0E0 !important; 
        padding: 8px 8px;
        border: 1px solid #333;
        white-space: nowrap; 
        vertical-align: middle;
        font-size: 14px;
    }

    /* =========================================
       4. 狀態標籤與圖表
       ========================================= */
    .status-red {
        background-color: #3A0000 !important;
        color: #FF4D4D !important;
        font-weight: bold;
        border: 1px solid #FF4D4D;
        padding: 2px 6px;
        border-radius: 4px;
        white-space: nowrap;
    }
    .status-green {
        background-color: #0d330e !important;
        color: #4CAF50 !important;
        font-weight: bold;
        border: 1px solid #4CAF50;
        padding: 2px 6px;
        border-radius: 4px;
        white-space: nowrap;
    }
    
    .streamlit-expanderHeader {
        background-color: #262730 !important;
        color: #FAFAFA !important;
        border: 1px solid #444 !important;
    }
    
    /* 讓 Altair 圖表不被反轉顏色 */
    [data-testid="stChart"] { filter: none !important; }
</style>
""", unsafe_allow_html=True)

st.title("車輛軌跡分析系統")

# --- 側邊欄：多檔案上傳 ---
st.sidebar.header("資料匯入")
uploaded_files = st.sidebar.file_uploader(
    "請上傳 Excel 或 CSV 檔案 (支援多選)", 
    type=["xlsx", "csv"], 
    accept_multiple_files=True
)

if uploaded_files:
    # --------------------------
    # 資料讀取與合併處理
    # --------------------------
    all_data_frames = []
    
    try:
        for file in uploaded_files:
            if file.name.endswith('.csv'):
                try:
                    temp_df = pd.read_csv(file, encoding='utf-8', dtype=str)
                except UnicodeDecodeError:
                    temp_df = pd.read_csv(file, encoding='big5', dtype=str)
            else:
                temp_df = pd.read_excel(file, dtype=str)
            
            all_data_frames.append(temp_df)
            
        if not all_data_frames:
            st.error("未讀取到有效資料")
            st.stop()
            
        df = pd.concat(all_data_frames, ignore_index=True)
        
    except Exception as e:
        st.error(f"檔案讀取失敗: {e}")
        st.stop()

    # === 欄位標準化 ===
    df.columns = df.columns.str.strip()
    
    rename_map = {
        '車號': '車牌', '路口': '地點', '監視器': '地點',
        'location': '地點', 'plate': '車牌', 'date': '日期', 'time': '時間'
    }
    df.rename(columns=rename_map, inplace=True)
    df = df.loc[:, ~df.columns.duplicated()]

    required_cols = ['車牌', '地點', '日期', '時間']
    if not set(required_cols).issubset(df.columns):
        st.error(f"資料格式錯誤，缺少欄位: {required_cols}。目前欄位: {list(df.columns)}")
        st.stop()

    try:
        df['車牌'] = df['車牌'].str.strip()
        df['地點'] = df['地點'].str.strip()
        
        df['temp_date'] = pd.to_datetime(df['日期'])
        df['日期'] = df['temp_date'].dt.strftime('%Y-%m-%d')
        df['完整時間'] = pd.to_datetime(df['日期'] + ' ' + df['時間'].astype(str))
        
        # === 全域計算 ===
        df = df.sort_values(by=['車牌', '完整時間'])
        df['下筆時間'] = df.groupby('車牌')['完整時間'].shift(-1)
        df['下筆地點'] = df.groupby('車牌')['地點'].shift(-1)
        df['停留秒數'] = (df['下筆時間'] - df['完整時間']).dt.total_seconds()
        
    except Exception as e:
        st.error(f"資料處理錯誤: {e}")
        st.stop()

    # --------------------------
    # 繪圖函式 (已移除 padding 參數以修復 Crash)
    # --------------------------
    def render_regularity_chart(data, color_hex="#4DA6FF"):
        chart_data = data.copy()
        chart_data['Hour'] = chart_data['完整時間'].dt.hour
        
        hourly_stats = chart_data.groupby('Hour')['日期'].nunique().reset_index(name='DaysCount')
        full_hours = pd.DataFrame({'Hour': range(24)})
        final_data = pd.merge(full_hours, hourly_stats, on='Hour', how='left').fillna(0)
        
        # 深色背景圖表
        chart = alt.Chart(final_data).mark_bar(color=color_hex).encode(
            x=alt.X('Hour:O', title='時段 (0-23點)', scale=alt.Scale(domain=list(range(24)))), 
            y=alt.Y('DaysCount:Q', title='出現天數', axis=alt.Axis(tickMinStep=1, format='d')),
            tooltip=[alt.Tooltip('Hour', title='時段'), alt.Tooltip('DaysCount', title='累計天數')]
        ).properties(
            height=180, 
            background='#1E1E1E'
            # padding=10  <-- 已移除此行，修復 TypeError
        ).configure_axis(
            labelFontSize=11, titleFontSize=13, grid=True, 
            gridColor='#444', labelColor='#E0E0E0', titleColor='#E0E0E0'
        ).configure_view(strokeWidth=0).interactive()
        
        st.altair_chart(chart, use_container_width=True)

    def render_heatmap_chart(data, color_scheme='blues'):
        chart_data = data.copy()
        chart_data['Hour'] = chart_data['完整時間'].dt.hour
        
        chart = alt.Chart(chart_data).mark_rect(stroke='black', strokeWidth=0.5).encode(
            x=alt.X('Hour:O', title='時段', scale=alt.Scale(domain=list(range(24)))), 
            y=alt.Y('日期:O', title='日期'),
            color=alt.Color('count()', title='頻率', scale=alt.Scale(scheme=color_scheme)),
            tooltip=['日期', 'Hour', 'count()']
        ).properties(
            height=200, background='#1E1E1E'
            # padding=10 <-- 已移除此行，修復 TypeError
        ).configure_axis(
            labelFontSize=11, titleFontSize=13, grid=True, gridColor='#444',
            labelColor='#E0E0E0', titleColor='#E0E0E0'
        ).configure_legend(
            labelColor='#E0E0E0', titleColor='#E0E0E0'
        ).configure_view(strokeWidth=0).interactive()
        
        st.altair_chart(chart, use_container_width=True)

    # --------------------------
    # HTML 表格渲染
    # --------------------------
    def render_html_table(dataframe):
        if dataframe.empty:
            st.warning("無資料")
            return
        
        table_html = dataframe.to_html(index=False, classes="custom-table", escape=False)
        final_html = f'<div class="table-container">{table_html}</div>'
        st.markdown(final_html, unsafe_allow_html=True)

    # --------------------------
    # 資料格式化函式
    # --------------------------
    def format_full_detail_table(data_chunk):
        display = data_chunk.copy()
        display['抵達時間'] = display['完整時間'].dt.strftime('%H:%M:%S')
        
        def format_next_info(row):
            if pd.isna(row['下筆時間']): return "-"
            if row['下筆時間'].date() == row['完整時間'].date():
                return row['下筆時間'].strftime('%H:%M:%S')
            else:
                days_diff = (row['下筆時間'].date() - row['完整時間'].date()).days
                return f"{row['下筆時間'].strftime('%H:%M:%S')} (+{days_diff}天)"
            
        display['離開時間'] = display.apply(format_next_info, axis=1)
        display['前往地點'] = display['下筆地點'].fillna("-")

        def format_duration(sec):
            if pd.isna(sec): return "-"
            m = int(sec // 60)
            h = int(m // 60)
            rem_m = m % 60
            if h > 0: return f"{h}小時{rem_m}分"
            else: return f"{m}分"

        display['停留'] = display['停留秒數'].apply(format_duration)
        return display[['日期', '抵達時間', '離開時間', '前往地點', '停留']].sort_values(by=['日期', '抵達時間'], ascending=[False, True])

    # --------------------------
    # 主頁面內容
    # --------------------------
    st.sidebar.info(f"已載入 {len(uploaded_files)} 個檔案，共 {len(df)} 筆資料")
    
    tab1, tab2, tab3, tab4 = st.tabs(["熱點統計分析", "居住地判讀", "每日行程統計", "同夥比對 (多車)"])

    # === 分頁 1: 熱點分析 ===
    with tab1:
        st.subheader("地點造訪頻率統計")
        
        all_cars = sorted(df['車牌'].unique())
        selected_car_hot = st.selectbox("選擇車輛", all_cars, key="hot_car")

        if selected_car_hot:
            st.markdown("---")
            car_data = df[df['車牌'] == selected_car_hot].copy()
            place_counts = car_data['地點'].value_counts().reset_index()
            place_counts.columns = ['地點', '次數']
            
            st.info("💡 柱狀圖越高，代表該時段「經常出現」(天數多)。")
            
            for index, row in place_counts.head(20).iterrows():
                place = row['地點']
                count = row['次數']
                rank = index + 1
                
                records = car_data[car_data['地點'] == place].copy()
                formatted_table = format_full_detail_table(records)
                
                label = f"#{rank} {place} (共 {count} 次)"
                
                with st.expander(label):
                    st.markdown("##### 📊 規律性分析")
                    render_regularity_chart(records, color_hex="#4DA6FF")
                    
                    st.markdown("##### 📋 詳細動線紀錄")
                    render_html_table(formatted_table)

    # === 分頁 2: 居住地判讀 ===
    with tab2:
        st.subheader("長時間停留 / 過夜地點分析")
        
        with st.expander("參數設定", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                min_stay = st.slider("最小停留時數 (小時)", 1, 12, 4)
            with c2:
                night_hr = st.selectbox("夜間時段起始 (時)", list(range(18, 25)), index=2)
            st.markdown(f"💡 **邏輯：** `{night_hr}:00~06:00` 抵達且停留 > `{min_stay}小時`")

        selected_car_home = st.selectbox("選擇車輛", all_cars, key="home_car")

        if selected_car_home:
            st.markdown("---")
            car_data = df[df['車牌'] == selected_car_home].copy()
            
            is_night = (car_data['完整時間'].dt.hour >= night_hr) | (car_data['完整時間'].dt.hour < 6)
            is_long = car_data['停留秒數'].fillna(0) >= (min_stay * 3600)
            candidates = car_data[is_night & is_long]

            if not candidates.empty:
                home_stats = candidates['地點'].value_counts().reset_index()
                home_stats.columns = ['地點', '過夜次數']
                
                top_place = home_stats.iloc[0]['地點']
                st.success(f"推測落腳點： **{top_place}**")
                
                st.write("詳細清單：")
                for idx, row in home_stats.iterrows():
                    place = row['地點']
                    count = row['過夜次數']
                    details = candidates[candidates['地點'] == place].copy()
                    formatted_table = format_full_detail_table(details)
                    
                    expand_label = f"{place} (符合條件 {count} 次)"
                    with st.expander(expand_label, expanded=(idx==0)):
                        st.markdown("##### 📅 過夜規律分析")
                        # 修正：這裡傳入 color_hex 參數
                        render_regularity_chart(details, color_hex="#FF6B6B")
                        
                        st.markdown("##### 📋 停留與動線")
                        render_html_table(formatted_table)
            else:
                st.warning("查無符合過夜條件之紀錄")

    # === 分頁 3: 每日行程統計 ===
    with tab3:
        st.subheader("每日軌跡詳細列表")
        
        c1, c2 = st.columns(2)
        with c1:
            car_daily = st.selectbox("1. 選擇車輛", all_cars, key="d_car")
        with c2:
            date_daily = None
            if car_daily:
                dates = sorted(df[df['車牌'] == car_daily]['日期'].unique())
                date_daily = st.selectbox("2. 選擇日期", dates, key="d_date")
        
        alert_val = st.slider("異常停留警示門檻 (分鐘)", 10, 300, 60, step=10)

        if car_daily and date_daily:
            st.markdown("---")
            
            daily_data = df[
                (df['車牌'] == car_daily) & 
                (df['日期'] == date_daily)
            ].sort_values(by="完整時間").copy()
            
            if daily_data.empty:
                st.warning("該日期無資料")
            else:
                display_list = []
                for idx, row in daily_data.iterrows():
                    arr_time = row['完整時間'].strftime('%H:%M:%S')
                    loc = row['地點']
                    dur = row['停留秒數']
                    
                    # 離開時間
                    next_time_obj = row['下筆時間']
                    if pd.isna(next_time_obj):
                        leave_time = "-"
                    elif next_time_obj.date() == row['完整時間'].date():
                        leave_time = f"{next_time_obj.strftime('%H:%M:%S')}"
                    else:
                        days = (next_time_obj.date() - row['完整時間'].date()).days
                        leave_time = f"{next_time_obj.strftime('%H:%M:%S')} (+{days}天)"
                    
                    if pd.isna(dur):
                        status_html = '<span class="status-green">🟢 正常</span>'
                        note = "無後續"
                    else:
                        m = int(dur // 60)
                        h = int(m // 60)
                        rem_m = m % 60
                        time_txt = f"{m}分" if h == 0 else f"{h}時{rem_m}分"
                        
                        if m >= alert_val:
                            status_html = f'<span class="status-red">🔴 異常</span>'
                            note = f"停留 {time_txt}"
                        else:
                            status_html = f'<span class="status-green">🟢 正常</span>'
                            note = f"間隔 {time_txt}"

                    display_list.append({
                        "抵達時間": arr_time,
                        "地點": loc,
                        "離開時間": leave_time,
                        "狀態": status_html,
                        "說明": note
                    })
                
                res_df = pd.DataFrame(display_list)
                st.write(f"日期：{date_daily}")
                render_html_table(res_df)

    # === 分頁 4: 同夥比對 (多車版) ===
    with tab4:
        st.subheader("多車接觸關聯分析")
        
        selected_cars = st.multiselect("請選擇比對車輛 (至少 2 台)", all_cars, default=all_cars[:2] if len(all_cars)>=2 else None)
        min_diff = st.number_input("時間容許誤差值 (分鐘)", 1, 60, 5)
        sec_diff = min_diff * 60
        
        if st.button("執行群組比對"):
            if len(selected_cars) < 2:
                st.error("請至少選擇兩台車輛")
            else:
                results_list = []
                combinations = list(itertools.combinations(selected_cars, 2))
                
                progress_text = st.empty()
                
                for idx, (car_a, car_b) in enumerate(combinations):
                    progress_text.text(f"正在比對：{car_a} vs {car_b} ...")
                    da = df[df['車牌'] == car_a]
                    db = df[df['車牌'] == car_b]
                    merged = pd.merge(da, db, on='地點', suffixes=('_A', '_B'))
                    
                    if not merged.empty:
                        merged['秒差'] = (merged['完整時間_A'] - merged['完整時間_B']).abs().dt.total_seconds()
                        valid = merged[merged['秒差'] <= sec_diff].copy()
                        
                        if not valid.empty:
                            for _, row in valid.iterrows():
                                results_list.append({
                                    '地點': row['地點'],
                                    '日期': row['日期_A'],
                                    '車輛 1': car_a,
                                    '時間 1': row['完整時間_A'].strftime('%H:%M:%S'),
                                    '車輛 2': car_b,
                                    '時間 2': row['完整時間_B'].strftime('%H:%M:%S'),
                                    '誤差': f"{int(row['秒差'] // 60)}分{int(row['秒差'] % 60)}秒",
                                    'sort_time': row['完整時間_A'] 
                                })
                
                progress_text.empty()
                
                if results_list:
                    st.warning(f"分析完成！共發現 {len(results_list)} 筆接觸紀錄")
                    res_df = pd.DataFrame(results_list)
                    res_df = res_df.sort_values(by='sort_time', ascending=False)
                    res_df = res_df.drop(columns=['sort_time'])
                    render_html_table(res_df)
                else:
                    st.success("分析完成：無符合條件的接觸紀錄")
else:
    st.info("請由左側選單匯入資料以開始分析")
