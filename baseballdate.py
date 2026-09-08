import pandas as pd
import streamlit as st

# ページのレイアウト設定
st.set_page_config(page_title="選手成績検索システム", layout="wide")

st.title("⚾ 2026年 選手成績・データ検索システム")


# データの読み込み関数
@st.cache_data
def load_data():
  sheet_id = "1I1JsaaQlYHj1zIsOKkFWkc1yAuoNDnpVdy_pLNW5na8"

  gid_base = "0"  # シート1（基本データ）
  gid_pitcher = "249999559"  # シート2（投手）
  gid_batter = "729396171"  # シート3（野手）

  # gviz/tq エンドポイントを使用
  url_base = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid_base}"
  url_pitcher = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid_pitcher}"
  url_batter = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid_batter}"

  df_base = pd.read_csv(url_base)
  df_pitcher = pd.read_csv(url_pitcher)
  df_batter = pd.read_csv(url_batter)

  # シート1：C列が選手名（インデックス2）
  df_base = df_base.rename(columns={df_base.columns[2]: "選手名"})
  # シート2・3：B列が選手名（インデックス1）
  df_pitcher = df_pitcher.rename(columns={df_pitcher.columns[1]: "選手名"})
  df_batter = df_batter.rename(columns={df_batter.columns[1]: "選手名"})

  # --- 「年齢」の数値化 ---
  if "年齢" in df_base.columns:
    df_base["年齢"] = (
        df_base["年齢"]
        .astype(str)
        .str.replace("歳", "", regex=False)
        .str.strip()
    )
    df_base["年齢"] = pd.to_numeric(df_base["年齢"], errors="coerce")

  # --- 「年数」の数値化 ---
  if "年数" in df_base.columns:
    df_base["年数"] = (
        df_base["年数"]
        .astype(str)
        .str.replace("年目", "", regex=False)
        .str.replace("年", "", regex=False)
        .str.strip()
    )
    df_base["年数"] = pd.to_numeric(df_base["年数"], errors="coerce")

  return df_base, df_pitcher, df_batter


# 数値を見やすくフォーマットする関数
def format_value(col_name, val):
  if pd.isna(val):
    return val
  
  try:
    num = float(val)
  except (ValueError, TypeError):
    return val

  col_str = str(col_name)

  # wRCやwRC+など、整数表示にしたい指標
  if col_str == "wRC" or col_str == "wRC+" or "wRC" in col_str:
    return f"{round(num)}"

  # 防御率・WHIP・FIP（小数点第2位まで）
  if "防御率" in col_str or "WHIP" in col_str or "FIP" in col_str:
    return f"{num:.2f}"

  # wOBA、打率、出塁率、長打率、OPS、勝率、BABIPなどの率系・小数系
  is_rate_col = any(kw in col_str for kw in ["wOBA", "打率", "出塁率", "長打率", "OPS", "勝率", "BABIP"])

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


# データのロード
try:
  df_base, df_pitcher, df_batter = load_data()
except Exception as e:
  st.error(
      f"データの読み込みに失敗しました。スプレッドシートの共有設定や内容を確認してください。\nエラー内容: {e}"
  )
  st.stop()

# --- サイドバー：条件設定 ---
st.sidebar.header("🔍 検索・絞り込み条件")

# キャッシュクリア＆再読み込みボタン
if st.sidebar.button("🔄 データを最新に更新（キャッシュクリア）"):
  st.cache_data.clear()
  st.success("キャッシュをクリアしました！")
  st.rerun()

player_type = st.sidebar.radio("表示カテゴリ", ["投手成績", "野手成績"])

# データの結合
if player_type == "投手成績":
  df_merged = pd.merge(df_base, df_pitcher, on="選手名", how="inner")
else:
  df_merged = pd.merge(df_base, df_batter, on="選手名", how="inner")

st.sidebar.markdown("---")
st.sidebar.markdown(
    "💡 **各項目の結合方法（AND / OR）を個別に指定できます**"
)

# リスト管理用のグループ
condition_groups = []

# --- 1. チーム条件 ---
if "チーム" in df_merged.columns:
  st.sidebar.subheader("⚾ チーム")
  teams = list(df_merged["チーム"].dropna().unique())
  selected_teams = st.sidebar.multiselect("チームを選択（複数可）", teams, key="m_team")
  team_logic = st.sidebar.radio("チームの結合", ["AND（絶対満たす）", "OR（どちらか）"], key="l_team", horizontal=True)
  if selected_teams:
    m = df_merged["チーム"].isin(selected_teams)
    condition_groups.append((m, "AND" if "AND" in team_logic else "OR"))

# --- 2. 選手名条件 ---
st.sidebar.subheader("👤 選手名")
search_name = st.sidebar.text_input("選手名（部分一致）", "", key="m_name")
name_logic = st.sidebar.radio("選手名の結合", ["AND（絶対満たす）", "OR（どちらか）"], key="l_name", horizontal=True)
if search_name:
  m = df_merged["選手名"].str.contains(search_name, na=False)
  condition_groups.append((m, "AND" if "AND" in name_logic else "OR"))

# --- 3. 年齢条件 ---
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

# --- 4. プロ入り年数条件 ---
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

# --- 5. 生まれ年条件 ---
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

# --- 6. 出身条件 ---
target_col = "出身" if "出身" in df_merged.columns else "出身地"
st.sidebar.subheader("📍 出身地")
use_birthplace_input = st.sidebar.checkbox("出身条件を有効にする", key="c_bp")
if use_birthplace_input and target_col in df_merged.columns:
  bp_mode = st.sidebar.radio("方式", ["日本か海外か", "特定の地域選択"], key="bp_m")
  
  japan_regions = [
      "北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木",
      "群馬", "埼玉", "千葉", "東京", "神奈川", "新潟", "富山", "石川", "福井",
      "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪",
      "兵庫", "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島",
      "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎",
      "鹿児島", "沖縄"
  ]
  
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


# --- 7. 成績ベースの絞り込み（〇打席以上・〇試合以上・〇投球回以上・守備位置） ---
st.sidebar.subheader("📊 規定数・ポジション絞り込み")
if player_type == "野手成績":
  use_min_pa = st.sidebar.checkbox("打席数で絞り込む")
  min_pa_val = st.sidebar.number_input("最小打席数", min_value=1, max_value=700, value=100, step=1)
  use_min_g_bat = st.sidebar.checkbox("試合数で絞り込む（野手）")
  min_g_bat_val = st.sidebar.number_input("最小試合数（野手）", min_value=1, max_value=150, value=20, step=1)
  
  use_pos_filter = st.sidebar.checkbox("守備位置で絞り込む", key="c_pos")
  if use_pos_filter:
    pos_col = None
    for candidate in ["守備", "守備位置", "ポジション"]:
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


# --- 絞り込みロジック (ANDグループ と ORグループの分離処理) ---
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

# 規定数チェックの適用
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


# --- メイン画面：表示項目・並び替え設定エリア ---
st.markdown("### ⚙️ 表示・並び替え設定")
all_cols = [c for c in filtered_df.columns if c != "__西暦"]

# カテゴリに応じたデフォルト選択項目と初期ソート項目
if player_type == "野手成績":
  default_selected = ["選手名", "チーム", "試合", "打席数", "打率", "安打", "本塁打", "盗塁", "出塁率", "OPS"]
  default_sort_col = "安打"
else:
  default_selected = ["選手名", "チーム", "試合", "投球回", "防御率", "勝利", "敗北", "ホールド", "セーブ", "奪三振", "WHIP", "FIP"]
  default_sort_col = "投球回"

default_selected = [c for c in default_selected if c in all_cols]
if not default_selected and all_cols:
  default_selected = all_cols[:5]

selected_columns = st.multiselect("表示する項目を選択（複数可）", all_cols, default=default_selected)

# --- 並び替え設定（第1ソート ＆ 第2ソート） ---
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

# --- チームのカスタム順序定義（降順：阪神始まり、昇順：ロッテ始まり） ---
team_order_desc = [
    "阪神", "ＤｅＮＡ", "DeNA", "巨人", "中日", "広島", "ヤクルト",
    "ソフトバンク", "日本ハム", "オリックス", "楽天", "西武", "ロッテ"
]

def get_team_sort_key(val, is_ascending):
  val_str = str(val)
  for idx, t in enumerate(team_order_desc):
    if t in val_str:
      return idx if not is_ascending else (len(team_order_desc) - 1 - idx)
  return 999

# --- 並び替えの適用（マルチカラムソート） ---
if sort_target_1 and not filtered_df.empty:
  sort_cols = []
  ascending_list = []

  # 第1ソートの設定
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

  # 第2ソートの設定（有効な場合のみ）
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

  # 実行
  filtered_df = filtered_df.sort_values(by=sort_cols, ascending=ascending_list, na_position='last')

  # 一時キーの削除
  for k in ["__sort_key_1", "__sort_key_2"]:
    if k in filtered_df.columns:
      filtered_df = filtered_df.drop(columns=[k])


# --- 表示用のデータフレーム作成（フォーマット適用 ＆ 選択列の絞り込み ＆ 順位列の追加） ---
if selected_columns:
  display_df = filtered_df[selected_columns].copy()
  for col in display_df.columns:
    display_df[col] = display_df[col].apply(lambda x: format_value(col, x))
  
  # 1から順に並ぶ「順位」列を先頭に挿入
  display_df.insert(0, "No.", range(1, len(display_df) + 1))
else:
  display_df = pd.DataFrame()


# --- メイン画面への結果表示 ---
st.markdown("---")
st.subheader(f"📋 検索結果 ({len(display_df)}件)")

if display_df.empty:
  st.info("条件に一致する選手が見つかりませんでした。")
else:
  # スプレッドシートの高さをデータ数に合わせて動的に拡張し、スクロールをなくす
  row_height = 35
  header_height = 40
  calculated_height = header_height + (len(display_df) * row_height)

  st.dataframe(
      display_df,
      use_container_width=True,
      height=calculated_height,
  )

  st.markdown("---")
  st.subheader("👤 選手詳細カード")
  selected_player = st.selectbox(
      "詳細を確認したい選手を選択", filtered_df["選手名"].unique()
  )

  if selected_player:
    p_data = filtered_df[filtered_df["選手名"] == selected_player].iloc[0]

    cols = st.columns(3)
    with cols[0]:
      st.metric(label="選手名", value=p_data["選手名"])
      if "チーム" in p_data and "守備" in p_data:
        st.metric(
            label="チーム / 守備",
            value=f"{p_data['チーム']} / {p_data['守備']}",
        )
    with cols[1]:
      if "年齢" in p_data and pd.notna(p_data["年齢"]):
        st.metric(label="年齢", value=f"{int(p_data['年齢'])}歳")
      if "年数" in p_data and pd.notna(p_data["年数"]):
        st.metric(label="プロ入り年数", value=f"{int(p_data['年数'])}年目")
    with cols[2]:
      st.write("**その他データ・成績:**")
      for col in p_data.index:
        if col not in [
            "選手名",
            "チーム",
            "守備",
            "年齢",
            "年数",
            "年俸",
            "__西暦",
        ]:
          formatted_val = format_value(col, p_data[col])
          st.write(f"- **{col}**: {formatted_val}")
