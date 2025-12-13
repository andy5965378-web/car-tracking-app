import streamlit as st
import pandas as pd
import itertools # 用於處理多車排列組合

# 1. 頁面設定
st.set_page_config(page_title="車輛軌跡分析系統", layout="wide")

# 2. CSS 強制修正 (深色極簡 / 無索引表格 / 戰情風格)
st.markdown("""
<style>
    /* === 全域深色主題 === */
    .stApp {
        background-color: #0E1117 !important;
        color: #FAFAFA !important;
    }

    /* 全域字體 */
    html, body, [class*="css"] {
        font-family: "Microsoft JhengHei", "Segoe UI", Roboto, sans-serif !important;
    }

    /* === 自定義 HTML 表格樣式 (取代 st.table 以移除索引) === */
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        background-color: #1E1E1E;
        color: #E0E0E0;
        font-size: 15px;
    }
    
    .custom-table th {
        background-color: #000000;
        color: #4DA6FF;
        font-weight: 600;
        text-transform: uppercase;
        padding: 10px 12px;
        border-bottom: 2px solid #4DA6FF;
        border: 1px solid #333;
        white-space: nowrap; /* 表頭不換行 */
        text-align: left;
    }
    
    .custom-table td {
        padding: 8px 12px;
        border: 1px solid #333;
        white-space: nowrap; /* 強制內容不換行 */
        vertical-align: middle;
    }

    /* 狀態顏色 CSS 類別 */
    .status-red {
        background-color: #3A0000;
        color: #FF4D4D;
        font-weight: bold;
        border: 1px solid #FF4D4D !important;
    }
    .status-green {
        background-color: #1E1E1E;
        color: #E0E0E0;
    }
    
    /* Expander 樣式 */
    .streamlit-expanderHeader {
        background-color: #262730 !important;
        color: #FAFAFA !important;
        border: 1px solid #444 !important;
        border-radius: 4px;
        font-size: 16px !important;
    }
    
    /* Chart 適應 */
    [data-testid="stChart"] { filter: invert(0); }
    
    /* 隱藏預設表格索引的備用方案 (若有漏網之魚) */
    thead tr th:first-child { display:none }
    tbody tr td:first-child { display:none }
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
        'location': '地點', 'plate': '車牌'
    }
    df.rename(columns=rename_map, inplace=True)

    required_cols = ['車牌', '地點', '日期', '時間']
    if not set(required_cols).issubset(df.columns):
        st.error(f"資料格式錯誤，缺少欄位: {required_cols}")
        st.stop()

    try:
        df['車牌'] = df['車牌'].str.strip()
        df['地點'] = df['地點'].str.strip()
        
        # 日期標準化
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
    # 核心：HTML 表格渲染函式 (移除索引的關鍵)
    # --------------------------
    def render_html_table(dataframe, highlight_col=None):
        """
        將 DataFrame 轉換為無索引的 HTML 表格
        """
        if dataframe.empty:
            st.warning("無資料")
            return

        # 1. 轉換為 HTML，設定 index=False 徹底移除左側數字
        # escape=False 允許我們在儲存格內放 HTML (例如顏色標記)
        html = dataframe.to_html(index=False, classes="custom-table", escape=False)
        
        # 2. 顯示
        st.markdown(html, unsafe_allow_html=True)

    # --------------------------
    # 資料處理函式
    # --------------------------
    
    # 模式 A: 詳細版 (含前往地點)
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
            if h > 0: return f"{h}時{rem_m}分"
            else: return f"{m}分"

        display['停留'] = display['停留秒數'].apply(format_duration)
        return display[['日期', '抵達時間', '離開時間', '前往地點', '停留']].sort_values(by=['日期', '抵達時間'])

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
            
            st.info("點擊列表展開查看詳細資料")
            
            for index, row in place_counts.head(20).iterrows():
                place = row['地點']
                count = row['次數']
                rank = index + 1
                
                records = car_data[car_data['地點'] == place].copy()
                formatted_table = format_full_detail_table(records)
                
                label = f"#{rank} {place} (共 {count} 次)"
                
                with st.expander(label):
                    st.markdown("##### 時段分佈")
                    records['Hour'] = records['完整時間'].dt.hour
                    hourly_counts = records['Hour'].value_counts().sort_index()
                    full_index = pd.Series(0, index=range(24))
                    final_counts = full_index.add(hourly_counts, fill_value=0)
                    st.bar_chart(final_counts, color="#4DA6FF", height=180)
                    
                    st.markdown("##### 詳細動線紀錄")
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
                        st.markdown(f"##### 時段分佈")
                        details['Hour'] = details['完整時間'].dt.hour
                        hourly_counts = details['Hour'].value_counts().sort_index()
                        full_index = pd.Series(0, index=range(24))
                        final_counts = full_index.add(hourly_counts, fill_value=0)
                        st.bar_chart(final_counts, color="#FF6B6B", height=180)
                        
                        st.markdown("##### 停留與動線")
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
                    
                    # 狀態處理：嵌入 HTML class
                    if pd.isna(dur):
                        status_html = '<span class="status-green">紀錄結束</span>'
                        note = "無後續"
                    else:
                        m = int(dur // 60)
                        h = int(m // 60)
                        rem_m = m % 60
                        time_txt = f"{m}分" if h == 0 else f"{h}時{rem_m}分"
                        
                        if m >= alert_val:
                            # 紅色異常狀態 class
                            status_html = f'<span class="status-red">🔴 異常</span>'
                            note = f"停留 {time_txt}"
                        else:
                            # 綠色正常狀態 class
                            status_html = f'<span class="status-green">🟢 正常</span>'
                            note = f"間隔 {time_txt}"

                    display_list.append({
                        "抵達時間": arr_time,
                        "地點": loc,
                        "離開時間": leave_time,
                        "狀態": status_html, # 這裡放入 HTML
                        "說明": note
                    })
                
                res_df = pd.DataFrame(display_list)
                st.write(f"日期：{date_daily}")
                # 使用 render_html_table 渲染，自動解析 HTML 標籤
                render_html_table(res_df)

    # === 分頁 4: 同夥比對 (多車版) ===
    with tab4:
        st.subheader("多車接觸關聯分析")
        
        # 1. 多選選單
        selected_cars = st.multiselect("請選擇比對車輛 (至少 2 台，可多選)", all_cars, default=all_cars[:2] if len(all_cars)>=2 else None)
        
        # 2. 時間容許值 (分鐘)
        min_diff = st.number_input("時間容許誤差值 (分鐘)", 1, 60, 5)
        sec_diff = min_diff * 60 # 轉為秒數計算
        
        if st.button("執行群組比對"):
            if len(selected_cars) < 2:
                st.error("請至少選擇兩台車輛進行比對")
            else:
                results_list = []
                
                # 產生所有排列組合 (Pairwise)
                # 例如選 [A, B, C] -> 比對 (A,B), (A,C), (B,C)
                combinations = list(itertools.combinations(selected_cars, 2))
                
                progress_text = st.empty()
                
                for idx, (car_a, car_b) in enumerate(combinations):
                    progress_text.text(f"正在比對：{car_a} vs {car_b} ...")
                    
                    da = df[df['車牌'] == car_a]
                    db = df[df['車牌'] == car_b]
                    
                    # Inner Join 找出同地點
                    merged = pd.merge(da, db, on='地點', suffixes=('_A', '_B'))
                    
                    if not merged.empty:
                        # 計算時間差
                        merged['秒差'] = (merged['完整時間_A'] - merged['完整時間_B']).abs().dt.total_seconds()
                        # 篩選
                        valid = merged[merged['秒差'] <= sec_diff].copy()
                        
                        if not valid.empty:
                            # 整理格式
                            for _, row in valid.iterrows():
                                results_list.append({
                                    '地點': row['地點'],
                                    '日期': row['日期_A'],
                                    '車輛 1': car_a,
                                    '時間 1': row['完整時間_A'].strftime('%H:%M:%S'),
                                    '車輛 2': car_b,
                                    '時間 2': row['完整時間_B'].strftime('%H:%M:%S'),
                                    '誤差': f"{int(row['秒差'] // 60)}分{int(row['秒差'] % 60)}秒",
                                    # 用於排序的隱藏欄位
                                    'sort_time': row['完整時間_A'] 
                                })
                
                progress_text.empty()
                
                if results_list:
                    st.warning(f"分析完成！共發現 {len(results_list)} 筆接觸紀錄")
                    
                    # 轉為 DataFrame 並排序
                    res_df = pd.DataFrame(results_list)
                    res_df = res_df.sort_values(by='sort_time', ascending=False)
                    
                    # 移除排序用的暫存欄位
                    res_df = res_df.drop(columns=['sort_time'])
                    
                    # 顯示無索引表格
                    render_html_table(res_df)
                else:
                    st.success("分析完成：所選車輛群組間無符合條件的接觸紀錄")
else:
    st.info("請由左側選單匯入資料 (支援多檔上傳) 以開始分析")
