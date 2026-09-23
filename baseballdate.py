import pandas as pd
import streamlit as st
import re

# ページのレイアウト設定
st.set_page_config(page_title="選手成績検索システム", layout="wide")

st.title("⚾ 2026年 選手成績・データ検索システム")

# データの読み込み関数
@st.cache_data
def load_data():
    sheet_id_base = "1I1JsaaQlYHj1zIsOKkFWkc1yAuoNDnpVdy_pLNW5na8"
    gid_base = "0"          
    gid_pitcher = "249999559"  
    gid_batter = "729396171"   

    url_base = f"https://docs.google.com/spreadsheets/d/{sheet_id_base}/gviz/tq?tqx=out:csv&gid={gid_base}"
    url_pitcher = f"https://docs.google.com/spreadsheets/d/{sheet_id_base}/gviz/tq?tqx=out:csv&gid={gid_pitcher}"
    url_batter = f"https://docs.google.com/spreadsheets/d/{sheet_id_base}/gviz/tq?tqx=out:csv&gid={gid_batter}"

    df_base = pd.read_csv(url_base)
    df_pitcher = pd.read_csv(url_pitcher)
    df_batter = pd.read_csv(url_batter)

    # --- 守備成績スプレッドシートの読み込み ---
    # ポジション名を英字略称に変更
    sheet_id_defense = "15OAG6-1-VehH05uvBk2y0xbwp5hB0zvpGvu7epVcW-c"
    defense_gids = {
        "C": "268651673",
        "1B": "2086594429",
        "2B": "505305239",
        "3B": "2096599227",
        "SS": "1958929802",
        "LF": "48917827",
        "CF": "810163329",
        "RF": "1692410818"
    }

    defense_dfs = []
    loaded_positions = []  # 読み込めたポジションを記録するリスト

    for pos_name, gid in defense_gids.items():
        url_def = f"https://docs.google.com/spreadsheets/d/{sheet_id_defense}/gviz/tq?tqx=out:csv&gid={gid}"
        try:
            df_pos = pd.read_csv(url_def)
            if not df_pos.empty:
                # 上部のメタヘッダーをスキップし、「選手」が含まれる行を真のカラム名に設定する
                if not any("選手" in str(c) for c in df_pos.columns):
                    for i, row in df_pos.head(10).iterrows(): # 念のため10行目まで検索
                        if any("選手" in str(val) for val in row.values):
                            df_pos.columns = row.astype(str)
                            # ヘッダー行より下のデータを抽出
                            df_pos = df_pos.iloc[i + 1:].reset_index(drop=True)
                            break
                
                # 改行(\n)や連続スペースを1つの半角スペースに統一してから記号を削除
                df_pos.columns = [re.sub(r'\s+', ' ', str(c)) for c in df_pos.columns]
                df_pos.columns = [re.sub(r'[↕▼▲]', '', str(c)).strip() for c in df_pos.columns]

                # カラムの中から「選手」が含まれるものを探す
                name_col = None
                for col in df_pos.columns:
                    if "選手" in str(col):
                        name_col = col
                        break
                
                if name_col:
                    def clean_defense_name(val):
                        if pd.isna(val):
                            return ""
                        val_str = str(val).strip()
                        # 最初に出現するアルファベットより前を切り出し、スペースを削除
                        match = re.split(r'[A-Za-zＡ-Ｚａ-ｚ]', val_str)
                        jp_part = match[0] if match else val_str
                        return re.sub(r'\s+', '', jp_part)

                    # 正規化された選手名列を新しく作成
                    df_pos["選手名"] = df_pos[name_col].apply(clean_defense_name)
                    
                    # 古い「選手」列などは削除
                    if name_col != "選手名":
                        df_pos = df_pos.drop(columns=[name_col])

                    # 重複する不要な列を削除
                    cols_to_drop = ["年", "球団", "Age", "プロ年数", "助っ人", "新人王資格", "守備位置", "nan"]
                    df_pos = df_pos.drop(columns=[c for c in cols_to_drop if c in df_pos.columns])

                    # 【新規追加】データが全員分「空っぽ」の列（例: RFシートにあるSS列など）を完全に削除する
                    # スペースやハイフンしかないセルも一旦NaNとみなして、列ごと消し去ります
                    df_pos = df_pos.replace([r'^\s*$', r'^\s*-\s*$', 'NaN', 'nan'], pd.NA, regex=True)
                    df_pos = df_pos.dropna(axis=1, how='all')

                    # 「選手名」以外の列名に(1B)などの英字ポジション名を付ける
                    rename_dict = {}
                    for col in df_pos.columns:
                        if col != "選手名":
                            rename_dict[col] = f"{col}({pos_name})"
                    df_pos = df_pos.rename(columns=rename_dict)

                    defense_dfs.append(df_pos)
                    loaded_positions.append(pos_name) # 成功したポジションを記録
        except Exception as e:
            # ターミナルにのみエラーを出力
            print(f"[{pos_name}] 守備データの読み込みエラー: {e}")
            pass
    
    # 守備データを統合（すべてのポジションデータを横に結合する）
    if defense_dfs:
        df_defense_all = defense_dfs[0]
        for df_pos in defense_dfs[1:]:
            df_defense_all = pd.merge(df_defense_all, df_pos, on="選手名", how="outer")
    else:
        df_defense_all = pd.DataFrame()

    # シート1：C列が選手名（インデックス2）
    df_base = df_base.rename(columns={df_base.columns[2]: "選手名"})
    df_pitcher = df_pitcher.rename(columns={df_pitcher.columns[1]: "選手名"})
    df_batter = df_batter.rename(columns={df_batter.columns[1]: "選手名"})

    # --- 基本・投手・野手側の選手名のスペースもすべて削除して統一 ---
    for df in [df_base, df_pitcher, df_batter]:
        if "選手名" in df.columns:
            df["選手名"] = df["選手名"].astype(str).str.replace(r'\s+', '', regex=True)
    
    if not df_defense_all.empty and "選手名" in df_defense_all.columns:
        df_defense_all["選手名"] = df_defense_all["選手名"].astype(str).str.replace(r'\s+', '', regex=True)

    if "年齢" in df_base.columns:
        df_base["年齢"] = df_base["年齢"].astype(str).str.replace("歳", "", regex=False).str.strip()
        df_base["年齢"] = pd.to_numeric(df_base["年齢"], errors="coerce")

    if "年数" in df_base.columns:
        df_base["年数"] = df_base["年数"].astype(str).str.replace("年目", "", regex=False).str.replace("年", "", regex=False).str.strip()
        df_base["年数"] = pd.to_numeric(df_base["年数"], errors="coerce")

    return df_base, df_pitcher, df_batter, df_defense_all, loaded_positions


def format_value(col_name, val):
    if pd.isna(val):
        return val
    try:
        num = float(val)
    except (ValueError, TypeError):
        return val

    col_str = str(col_name)

    if col_str == "wRC" or col_str == "wRC+" or "wRC" in col_str:
        return f"{round(num)}"
    if "防御率" in col_str or "WHIP" in col_str or "FIP" in col_str:
        return f"{num:.2f}"
    if "Fielding" in col_str or "sUZR" in col_str or "RV" in col_str:
        return f"{num:.1f}"

    is_rate_col = any(kw in col_str for kw in ["wOBA", "打率", "出塁率", "長打率", "OPS", "勝率", "BABIP", "試行率"])
    if is_rate_col:
        if num >= 1.0:
            return f"{num:.3f}"
        else:
            formatted = f"{num:.3f}"
            if formatted.startswith("0"):
                return formatted[1:]
            elif formatted.startswith("-0"):
                return "-" + formatted[2:]
            return formatted

    return val


try:
    df_base, df_pitcher, df_batter, df_defense, loaded_positions = load_data()
except Exception as e:
    st.error(f"データの読み込みに失敗しました。\nエラー内容: {e}")
    st.stop()


# --- サイドバー設定 ---
st.sidebar.header("🔍 検索・絞り込み条件")
if st.sidebar.button("🔄 データを最新に更新（キャッシュクリア）"):
    st.cache_data.clear()
    st.success("キャッシュをクリアしました！")
    st.rerun()

# どの守備データが読み込めたかをUIでフィードバック
if loaded_positions:
    st.sidebar.success(f"✅ 守備データ読込完了: {', '.join(loaded_positions)}")
else:
    st.sidebar.error("❌ 守備データが一つも読み込めませんでした")


player_type = st.sidebar.radio("表示カテゴリ", ["投手成績", "野手成績"])

if player_type == "投手成績":
    df_merged = pd.merge(df_base, df_pitcher, on="選手名", how="inner")
else:
    df_temp = pd.merge(df_base, df_batter, on="選手名", how="inner")
    if not df_defense.empty:
        df_merged = pd.merge(df_temp, df_defense, on="選手名", how="left")
        
        # 数値のあるポジションだけを抜き出して文字列にする関数（英字略称版）
        def make_defense_summary(row, stat_name):
            results = []
            positions = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"]
            for pos in positions:
                col = f"{stat_name}({pos})"
                if col in row.index and pd.notna(row[col]):
                    val = str(row[col]).strip()
                    if val != "" and val != "nan":
                        try:
                            num = float(val)
                            results.append(f"{pos}:{num:.1f}")
                        except ValueError:
                            results.append(f"{pos}:{val}")
            return " / ".join(results) if results else "-"
        
        # まとめ列の作成（Fielding RVのみ）
        if any("Fielding RV" in c for c in df_merged.columns):
            df_merged["Fielding RV(まとめ)"] = df_merged.apply(lambda r: make_defense_summary(r, "Fielding RV"), axis=1)
    else:
        df_merged = df_temp

st.sidebar.markdown("---")
st.sidebar.markdown("💡 **各項目の結合方法（AND / OR）を個別に指定できます**")

condition_groups = []

if "チーム" in df_merged.columns:
    st.sidebar.subheader("⚾ チーム")
    teams = list(df_merged["チーム"].dropna().unique())
    selected_teams = st.sidebar.multiselect("チームを選択（複数可）", teams, key="m_team")
    team_logic = st.sidebar.radio("チームの結合", ["AND（絶対満たす）", "OR（どちらか）"], key="l_team", horizontal=True)
    if selected_teams:
        m = df_merged["チーム"].isin(selected_teams)
        condition_groups.append((m, "AND" if "AND" in team_logic else "OR"))

st.sidebar.subheader("👤 選手名")
search_name = st.sidebar.text_input("選手名（部分一致）", "", key="m_name")
name_logic = st.sidebar.radio("選手名の結合", ["AND（絶対満たす）", "OR（どちらか）"], key="l_name", horizontal=True)
if search_name:
    clean_search = search_name.replace(" ", "").replace(" ", "")
    m = df_merged["選手名"].str.contains(clean_search, na=False)
    condition_groups.append((m, "AND" if "AND" in name_logic else "OR"))

st.sidebar.subheader("🎂 年齢")
use_age_input = st.sidebar.checkbox("年齢条件を有効にする", key="c_age")
if use_age_input and "年齢" in df_merged.columns:
    col_a1, col_a2 = st.sidebar.columns(2)
    with col_a1:
        age_cond = st.selectbox("条件", ["以下", "以上", "ちょうど"], key="age_c")
    with col_a2:
        age_val = st.number_input("歳", min_value=10, max_value=60, value=25, step=1, key="age_v")
    age_logic = st.sidebar.radio("年齢の結合", ["AND（絶対満たす）", "OR（どちらか）"], key="l_age", horizontal=True)
    if age_cond == "以下":
        m = df_merged["年齢"] <= age_val
    elif age_cond == "以上":
        m = df_merged["年齢"] >= age_val
    else:
        m = df_merged["年齢"] == age_val
    condition_groups.append((m, "AND" if "AND" in age_logic else "OR"))

st.sidebar.subheader("📅 プロ入り年数")
use_years_input = st.sidebar.checkbox("プロ入り年数条件を有効にする", key="c_yrs")
if use_years_input and "年数" in df_merged.columns:
    col_y1, col_y2 = st.sidebar.columns(2)
    with col_y1:
        years_cond = st.selectbox("条件", ["以下", "以上", "ちょうど"], key="yrs_c")
    with col_y2:
        years_val = st.number_input("年", min_value=1, max_value=30, value=5, step=1, key="yrs_v")
    years_logic = st.sidebar.radio("年数の結合", ["AND（絶対満たす）", "OR（どちらか）"], key="l_yrs", horizontal=True)
    if years_cond == "以下":
        m = df_merged["年数"] <= years_val
    elif years_cond == "以上":
        m = df_merged["年数"] >= years_val
    else:
        m = df_merged["年数"] == years_val
    condition_groups.append((m, "AND" if "AND" in years_logic else "OR"))

st.sidebar.subheader("👶 生まれ年")
use_birth_input = st.sidebar.checkbox("生まれ年条件を有効にする", key="c_birth")
if use_birth_input:
    if "生年月日" in df_merged.columns:
        df_merged["__西暦"] = df_merged["生年月日"].astype(str).str.extract(r"(\d{4})").astype(float)
    birth_year_val = st.sidebar.number_input("何年生まれ以降", min_value=1970, max_value=2010, value=2000, step=1, key="birth_v")
    birth_logic = st.sidebar.radio("生まれ年の結合", ["AND（絶対満たす）", "OR（どちらか）"], key="l_birth", horizontal=True)
    if "__西暦" in df_merged.columns:
        m = df_merged["__西暦"] >= birth_year_val
        condition_groups.append((m, "AND" if "AND" in birth_logic else "OR"))

target_col = "出身" if "出身" in df_merged.columns else "出身地"
st.sidebar.subheader("📍 出身地")
use_birthplace_input = st.sidebar.checkbox("出身条件を有効にする", key="c_bp")
if use_birthplace_input and target_col in df_merged.columns:
    bp_mode = st.sidebar.radio("方式", ["日本か海外か", "特定の地域選択"], key="bp_m")
    japan_regions = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川", "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
    if bp_mode == "日本か海外か":
        sel_jo = st.sidebar.selectbox("区分", ["日本国内", "日本以外（海外）"], key="bp_jo")
        if sel_jo == "日本国内":
            m = df_merged[target_col].astype(str).apply(lambda x: any(reg in x for reg in japan_regions))
        else:
            m = df_merged[target_col].astype(str).apply(lambda x: not any(reg in x for reg in japan_regions))
    else:
        bp_list = sorted(list(df_merged[target_col].dropna().unique()))
        sel_bp = st.sidebar.selectbox("地域を選択", bp_list, key="bp_sel")
        m = df_merged[target_col] == sel_bp
    bp_logic = st.sidebar.radio("出身の結合", ["AND（絶対満たす）", "OR（どちらか）"], key="l_bp", horizontal=True)
    condition_groups.append((m, "AND" if "AND" in bp_logic else "OR"))

st.sidebar.subheader("📊 規定数・ポジション絞り込み")
if player_type == "野手成績":
    use_min_pa = st.sidebar.checkbox("打席数で絞り込む")
    min_pa_val = st.sidebar.number_input("最小打席数", min_value=1, max_value=700, value=100, step=1)
    use_min_g_bat = st.sidebar.checkbox("試合数で絞り込む（野手）")
    min_g_bat_val = st.sidebar.number_input("最小試合数（野手）", min_value=1, max_value=150, value=20, step=1)
    use_pos_filter = st.sidebar.checkbox("守備位置で絞り込む", key="c_pos")
    if use_pos_filter:
        pos_col = None
        for candidate in ["守備位置", "守備", "ポジション"]:
            if candidate in df_merged.columns:
                pos_col = candidate
                break
        if pos_col:
            positions = sorted([p for p in df_merged[pos_col].dropna().unique() if p != "投手"])
            selected_positions = st.sidebar.multiselect("守備位置を選択（複数可）", positions, key="m_pos")
        else:
            st.sidebar.warning("データ内に守備位置の列が見つかりませんでした。")
            selected_positions = []
else:
    use_min_ip = st.sidebar.checkbox("投球回で絞り込む")
    min_ip_val = st.sidebar.number_input("最小投球回", min_value=1.0, max_value=300.0, value=30.0, step=1.0)
    use_min_g_pit = st.sidebar.checkbox("試合数で絞り込む（投手）")
    min_g_pit_val = st.sidebar.number_input("最小試合数（投手）", min_value=1, max_value=100, value=10, step=1)

filtered_df = df_merged.copy()

if condition_groups:
    and_masks = [mask for mask, logic in condition_groups if logic == "AND"]
    for m in and_masks:
        filtered_df = filtered_df[m]
    or_masks = [mask for mask, logic in condition_groups if logic == "OR"]
    if or_masks:
        or_combined = or_masks[0]
        for m in or_masks[1:]:
            or_combined = or_combined | m
        filtered_df = filtered_df[or_combined]

if player_type == "野手成績":
    if use_min_pa and "打席数" in filtered_df.columns:
        filtered_df = filtered_df[pd.to_numeric(filtered_df["打席数"], errors="coerce") >= min_pa_val]
    if use_min_g_bat and "試合" in filtered_df.columns:
        filtered_df = filtered_df[pd.to_numeric(filtered_df["試合"], errors="coerce") >= min_g_bat_val]
    if use_pos_filter and 'pos_col' in locals() and pos_col and selected_positions:
        filtered_df = filtered_df[filtered_df[pos_col].isin(selected_positions)]
else:
    if use_min_ip and "投球回" in filtered_df.columns:
        filtered_df = filtered_df[pd.to_numeric(filtered_df["投球回"], errors="coerce") >= min_ip_val]
    if use_min_g_pit and "試合" in filtered_df.columns:
        filtered_df = filtered_df[pd.to_numeric(filtered_df["試合"], errors="coerce") >= min_g_pit_val]

st.markdown("### ⚙️ 表示・並び替え設定")
all_cols = [c for c in filtered_df.columns if c != "__西暦"]

if player_type == "野手成績":
    # デフォルトの選択肢
    default_selected = ["選手名", "チーム", "試合", "打席数", "打率", "安打", "本塁打", "盗塁", "出塁率", "OPS", "Fielding RV(まとめ)"]
    default_sort_col = "安打"
else:
    default_selected = ["選手名", "チーム", "試合", "投球回", "防御率", "勝利", "敗北", "ホールド", "セーブ", "奪三振", "WHIP", "FIP"]
    default_sort_col = "投球回"

default_selected = [c for c in default_selected if c in all_cols]
if not default_selected and all_cols:
    default_selected = all_cols[:5]

selected_columns = st.multiselect("表示する項目を選択（複数可）", all_cols, default=default_selected)

st.markdown("#### 🔄 並び替え条件")
col_s1, col_s2 = st.columns(2)
with col_s1:
    st.write("**【第1ソート】**")
    default_sort_idx = selected_columns.index(default_sort_col) if default_sort_col in selected_columns else 0
    sort_target_1 = st.selectbox("基準にする項目 (1)", selected_columns if selected_columns else all_cols, index=default_sort_idx, key="sort_t1")
    sort_order_1 = st.radio("順序 (1)", ["降順（高い順・大きい順）", "昇順（低い順・小さい順）"], horizontal=True, key="sort_o1")
with col_s2:
    st.write("**【第2ソート】**")
    default_s2_idx = 1 if len(selected_columns) > 1 else 0
    sort_target_2 = st.selectbox("基準にする項目 (2)", selected_columns if selected_columns else all_cols, index=default_s2_idx, key="sort_t2")
    sort_order_2 = st.radio("順序 (2)", ["降順（高い順・大きい順）", "昇順（低い順・小さい順）"], horizontal=True, key="sort_o2")
    use_second_sort = st.checkbox("第2ソートを有効にする", value=False, key="use_s2")

team_order_desc = ["阪神", "ＤｅＮＡ", "DeNA", "巨人", "中日", "広島", "ヤクルト", "ソフトバンク", "日本ハム", "オリックス", "楽天", "西武", "ロッテ"]
def get_team_sort_key(val, is_ascending):
    val_str = str(val)
    for idx, t in enumerate(team_order_desc):
        if t in val_str:
            return idx if not is_ascending else (len(team_order_desc) - 1 - idx)
    return 999

if sort_target_1 and not filtered_df.empty:
    sort_cols = []
    ascending_list = []
    is_asc_1 = sort_order_1.startswith("昇順")
    if sort_target_1 == "チーム":
        filtered_df["__sort_key_1"] = filtered_df["チーム"].apply(lambda x: get_team_sort_key(x, is_asc_1))
        sort_cols.append("__sort_key_1")
        ascending_list.append(True)
    else:
        temp_key_1 = pd.to_numeric(filtered_df[sort_target_1], errors='coerce')
        if temp_key_1.notna().sum() > 0:
            filtered_df["__sort_key_1"] = temp_key_1
            sort_cols.append("__sort_key_1")
        else:
            sort_cols.append(sort_target_1)
        ascending_list.append(is_asc_1)

    if use_second_sort and sort_target_2:
        is_asc_2 = sort_order_2.startswith("昇順")
        if sort_target_2 == "チーム":
            filtered_df["__sort_key_2"] = filtered_df["チーム"].apply(lambda x: get_team_sort_key(x, is_asc_2))
            sort_cols.append("__sort_key_2")
            ascending_list.append(True)
        else:
            temp_key_2 = pd.to_numeric(filtered_df[sort_target_2], errors='coerce')
            if temp_key_2.notna().sum() > 0:
                filtered_df["__sort_key_2"] = temp_key_2
                sort_cols.append("__sort_key_2")
            else:
                sort_cols.append(sort_target_2)
            ascending_list.append(is_asc_2)

    filtered_df = filtered_df.sort_values(by=sort_cols, ascending=ascending_list, na_position='last')
    for k in ["__sort_key_1", "__sort_key_2"]:
        if k in filtered_df.columns:
            filtered_df = filtered_df.drop(columns=[k])

if selected_columns:
    display_df = filtered_df[selected_columns].copy()
    for col in display_df.columns:
        display_df[col] = display_df[col].apply(lambda x: format_value(col, x))
    display_df.insert(0, "No.", range(1, len(display_df) + 1))
else:
    display_df = pd.DataFrame()

st.markdown("---")
st.subheader(f"📋 検索結果 ({len(display_df)}件)")

if display_df.empty:
    st.info("条件に一致する選手が見つかりませんでした。")
else:
    row_height = 35
    header_height = 40
    calculated_height = header_height + (len(display_df) * row_height)
    st.dataframe(display_df, use_container_width=True, height=calculated_height)

    st.markdown("---")
    st.subheader("👤 選手詳細カード")
    selected_player = st.selectbox("詳細を確認したい選手を選択", filtered_df["選手名"].unique())
    if selected_player:
        p_data = filtered_df[filtered_df["選手名"] == selected_player].iloc[0]
        cols = st.columns(3)
        with cols[0]:
            st.metric(label="選手名", value=p_data["選手名"])
            if "チーム" in p_data:
                team_val = p_data['チーム']
                pos_val = p_data.get('守備位置', p_data.get('守備', ''))
                st.metric(label="チーム / 守備位置", value=f"{team_val} / {pos_val}" if pos_val else f"{team_val}")
        with cols[1]:
            if "年齢" in p_data and pd.notna(p_data["年齢"]):
                st.metric(label="年齢", value=f"{int(p_data['年齢'])}歳")
            if "年数" in p_data and pd.notna(p_data["年数"]):
                st.metric(label="プロ入り年数", value=f"{int(p_data['年数'])}年目")
        with cols[2]:
            st.write("**その他データ・成績:**")
            for col in p_data.index:
                if col not in ["選手名", "チーム", "守備", "守備位置", "年齢", "年数", "年俸", "__西暦"]:
                    val = p_data[col]
                    # 値が存在し、空文字や 'nan' でない場合のみ表示する
                    if pd.notna(val) and str(val).strip() != "" and str(val).strip().lower() != "nan":
                        formatted_val = format_value(col, val)
                        st.write(f"- **{col}**: {formatted_val}")
