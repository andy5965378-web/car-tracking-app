import streamlit as st
import pandas as pd

# 1. 頁面設定
st.set_page_config(page_title="車輛軌跡分析系統 (專業版)", layout="wide")

# 2. CSS 專業化修正
st.markdown("""
<style>
    /* 全域字體設定 */
    html, body, [class*="css"] {
        font-family: "Microsoft JhengHei", "Segoe UI", Roboto, sans-serif !important;
    }

    /* 表格樣式：專業商務風格 */
    div[data-testid="stTable"] table {
        background-color: white !important;
        color: #333 !important;
        border-collapse: collapse !important;
    }
    
    div[data-testid="stTable"] td, div[data-testid="stTable"] th {
        color: #333 !important;
        background-color: white !important;
        font-size: 16px !important;
        border: 1px solid #e0e0e0 !important;
        padding: 12px 15px !important;
        white-space: normal !important;
        word-wrap: break-word !important;
        vertical-align: middle !important;
    }
    
    /* 表頭樣式：深藍色底白字 */
    div[data-testid="stTable"] thead th {
        background-color: #2c3e50 !important; 
        color: white !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        text-transform: uppercase;
    }
    
    /* Expander 樣式微調 */
    .streamlit-expanderHeader {
        font-size: 18px !important;
        font-weight: 600 !important;
        background-color: #f8f9fa !important;
        color: #2c3e50 !important;
        border: 1px solid #ddd;
        border-radius: 4px;
    }
    
    /* Pandas Styler 背景修正 */
    #T_ { background-color: white !important; color: #333 !important; }
</style>
""", unsafe_allow_html=True)

st.title("車輛軌跡與關聯分析系統")
st.caption("版本: Professional v1.1 | 模式: 完整時間軸分析 | 狀態: 異常標記強化")

# --- 側邊欄：上傳資料 ---
st.sidebar.header("資料匯入作業")
uploaded_file = st.sidebar.file_uploader("請上傳 Excel 或 CSV 來源檔案", type=["xlsx", "csv"])

if uploaded_file is not None:
    # --------------------------
    # 資料讀取與前處理
    # --------------------------
    try:
        if uploaded_file.name.endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8', dtype=str)
            except UnicodeDecodeError:
                df = pd.read_csv(uploaded_file, encoding='big5', dtype=str)
        else:
            df = pd.read_excel(uploaded_file, dtype=str)
    except Exception as e:
        st.error(f"系統錯誤：檔案讀取失敗 - {e}")
        st.stop()

    df.columns = df.columns.str.strip()
    required_cols = ['車牌', '地點', '日期', '時間']
    if not set(required_cols).issubset(df.columns):
        st.error(f"資料格式錯誤：缺少必要欄位，請檢查是否包含 {required_cols}")
        st.stop()

    try:
        df['車牌'] = df['車牌'].str.strip()
        df['地點'] = df['地點'].str.strip()
        
        # 日期標準化
        df['temp_date'] = pd.to_datetime(df['日期'])
        df['日期'] = df['temp_date'].dt.strftime('%Y-%m-%d')
        df['完整時間'] = pd.to_datetime(df['日期'] + ' ' + df['時間'].astype(str))
        
        # === 全域計算：下筆時間與停留 ===
        df = df.sort_values(by=['車牌', '完整時間'])
        df['下筆時間'] = df.groupby('車牌')['完整時間'].shift(-1)
        df['停留秒數'] = (df['下筆時間'] - df['完整時間']).dt.total_seconds()
        
    except Exception as e:
        st.error(f"資料處理例外狀況: {e}")
        st.stop()

    # --------------------------
    # 輔助函式
    # --------------------------
    def format_detail_table(data_chunk):
        display = data_chunk.copy()
        display['抵達時間'] = display['完整時間'].dt.strftime('%H:%M:%S')
        
        def format_next_time(row):
            if pd.isna(row['下筆時間']):
                return "無 (紀錄結束)"
            if row['下筆時間'].date() == row['完整時間'].date():
                return row['下筆時間'].strftime('%H:%M:%S')
            else:
                days_diff = (row['下筆時間'].date() - row['完整時間'].date()).days
                return f"{row['下筆時間'].strftime('%H:%M:%S')} (+{days_diff}天)"

        display['離開/下筆時間'] = display.apply(format_next_time, axis=1)
        
        def format_duration(sec):
            if pd.isna(sec):
                return "-"
            m = int(sec // 60)
            h = int(m // 60)
            rem_m = m % 60
            if h > 0:
                return f"{h}小時 {rem_m}分"
            else:
                return f"{m}分鐘"

        display['停留時長'] = display['停留秒數'].apply(format_duration)
        return display[['日期', '抵達時間', '離開/下筆時間', '停留時長']].sort_values(by=['日期', '抵達時間'])

    # 樣式函式 (根據文字關鍵字變色) - 這裡做了強化
    def highlight_rows(row):
        status_str = str(row['狀態'])
        if "🔴" in status_str: 
            # 異常：淺紅背景 + 深紅字 + 粗體 (警示效果強)
            return ['background-color: #ffe6e6; color: #a94442; font-weight: bold; border-top: 1px solid #ffa3a3; border-bottom: 1px solid #ffa3a3;'] * len(row)
        elif "🟢" in status_str: 
            # 正常：白底 + 深灰字
            return ['background-color: white; color: #444;'] * len(row)
        else:
            return ['background-color: white; color: #333'] * len(row)

    # --------------------------
    # 主頁面內容
    # --------------------------
    tab1, tab2, tab3, tab4 = st.tabs(["熱點統計分析", "居住地判讀", "每日行程詳情", "關聯性比對"])

    # === 分頁 1: 熱點分析 ===
    with tab1:
        st.subheader("地點造訪頻率統計")
        
        all_cars = sorted(df['車牌'].unique())
        selected_car_hot = st.selectbox("目標車輛", all_cars, key="hot_car")

        if selected_car_hot:
            st.markdown("---")
            car_data = df[df['車牌'] == selected_car_hot]
            
            place_counts = car_data['地點'].value_counts().reset_index()
            place_counts.columns = ['地點', '次數']
            
            st.info("提示：點擊下方列表可展開查看該地點的詳細進出時間。")
            
            for index, row in place_counts.head(20).iterrows():
                place = row['地點']
                count = row['次數']
                rank = index + 1
                
                records = car_data[car_data['地點'] == place]
                formatted_table = format_detail_table(records)
                
                # 純文字標題
                label = f"[第 {rank} 名] {place} - 共 {count} 次"
                
                with st.expander(label):
                    st.table(formatted_table)

    # === 分頁 2: 疑似住處分析 ===
    with tab2:
        st.subheader("長時間停留 / 過夜地點分析")
        
        with st.expander("進階參數設定", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                min_stay = st.slider("最小停留時數 (小時)", 1, 12, 4)
            with c2:
                night_hr = st.selectbox("夜間時段起始 (時)", list(range(18, 25)), index=2)
            st.caption(f"分析邏輯：篩選於 {night_hr}:00 至 06:00 間抵達，且停留超過 {min_stay} 小時之地點。")

        selected_car_home = st.selectbox("目標車輛", all_cars, key="home_car")

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
                st.success(f"系統推測結果：主要落腳點為 **{top_place}**")
                
                st.write("詳細清單：")
                
                for idx, row in home_stats.iterrows():
                    place = row['地點']
                    count = row['過夜次數']
                    
                    details = candidates[candidates['地點'] == place]
                    formatted_table = format_detail_table(details)
                    
                    # 純文字標題
                    expand_label = f"{place} (符合條件 {count} 次)"
                    with st.expander(expand_label, expanded=(idx==0)):
                        st.table(formatted_table)
            else:
                st.warning("查無符合過夜條件之紀錄。")

    # === 分頁 3: 每日行程 ===
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
                    
                    next_time_obj = row['下筆時間']
                    if pd.isna(next_time_obj):
                        leave_time = "-"
                    elif next_time_obj.date() == row['完整時間'].date():
                        leave_time = next_time_obj.strftime('%H:%M:%S')
                    else:
                        days = (next_time_obj.date() - row['完整時間'].date()).days
                        leave_time = f"{next_time_obj.strftime('%H:%M:%S')} (+{days}天)"
                    
                    status = ""
                    note = ""
                    
                    if pd.isna(dur):
                        status = "🏁 紀錄結束"
                        note = "無後續資料"
                    else:
                        m = int(dur // 60)
                        h = int(m // 60)
                        rem_m = m % 60
                        time_txt = f"{m}分" if h == 0 else f"{h}小時{rem_m}分"
                        
                        # 這裡加入圖案邏輯
                        if m >= alert_val:
                            status = "🔴 異常 (停留過久)"
                            note = f"停留 {time_txt}"
                        else:
                            status = "🟢 正常 (移動/短停)"
                            note = f"間隔 {time_txt}"

                    display_list.append({
                        "抵達時間": arr_time,
                        "地點": loc,
                        "離開/下筆時間": leave_time,
                        "狀態": status,
                        "備註說明": note
                    })
                
                res_df = pd.DataFrame(display_list)
                st.write(f"日期：{date_daily} | 警示門檻：> {alert_val} 分鐘")
                st.table(res_df.style.apply(highlight_rows, axis=1))

    # === 分頁 4: 同夥比對 ===
    with tab4:
        st.subheader("車輛接觸關聯分析")
        c1, c2 = st.columns(2)
        with c1: car_a = st.selectbox("目標車輛 A", all_cars, index=0, key="pa")
        with c2: 
            idx = 1 if len(all_cars) > 1 else 0
            car_b = st.selectbox("目標車輛 B", all_cars, index=idx, key="pb")
            
        sec_diff = st.number_input("時間容許誤差值 (秒)", 0, 3600, 60)
        
        if st.button("執行比對"):
            if car_a == car_b:
                st.error("操作錯誤：請選擇兩台不同的車輛進行比對。")
            else:
                da = df[df['車牌'] == car_a]
                db = df[df['車牌'] == car_b]
                merged = pd.merge(da, db, on='地點', suffixes=('_A', '_B'))
                merged['秒差'] = (merged['完整時間_A'] - merged['完整時間_B']).abs().dt.total_seconds()
                res = merged[merged['秒差'] <= sec_diff].sort_values(by='完整時間_A')
                
                if not res.empty:
                    st.warning(f"分析結果：發現 {len(res)} 筆接觸紀錄")
                    out = pd.DataFrame({
                        '地點': res['地點'],
                        '日期': res['日期_A'],
                        'A車時間': res['完整時間_A'].dt.strftime('%H:%M:%S'),
                        'B車時間': res['完整時間_B'].dt.strftime('%H:%M:%S'),
                        '時間誤差': res['秒差'].astype(int).astype(str) + "秒"
                    })
                    st.table(out)
                else:
                    st.success("分析結果：無接觸紀錄")
else:
    st.info("請由左側選單匯入資料以開始分析。")