import pandas as pd

def normalize_name(name):
    """
    選手名の表記揺れ（旧字体・異体字・スペース）を解消し、標準化する関数
    """
    if pd.isna(name):
        return name
        
    # 異体字・旧字体を標準的な新字体に変換するマッピング
    kanji_mapping = str.maketrans({
        '髙': '高',
        '澤': '沢',
        '﨑': '崎',
        '廣': '広',
        '瀨': '瀬',
        '濱': '浜',
        '邊': '辺',
        '邉': '辺',
        '櫻': '桜',
        '縣': '県',
        '眞': '真',
        '榮': '栄',
        '德': '徳'
    })
    
    # 漢字の変換に加え、姓名間の全角・半角スペースも削除して完全一致しやすくする
    return str(name).translate(kanji_mapping).replace(" ", "").replace(" ", "")

def main():
    # 1. 結合前の元データ（打撃成績と守備成績）を読み込む
    # ※ファイル名はご自身のローカルにある元データの名前に変更してください
    try:
        df_batting = pd.read_csv('batting_data.csv')
        df_fielding = pd.read_csv('fielding_data.csv')
    except FileNotFoundError:
        print("エラー: 読み込むCSVファイルが見つかりません。ファイルパスを確認してください。")
        return

    # 2. 結合用のキーとして「選手名_標準化」カラムを両方に作成
    df_batting['選手名_標準化'] = df_batting['選手名'].apply(normalize_name)
    df_fielding['選手名_標準化'] = df_fielding['選手名'].apply(normalize_name)

    # 3. 標準化した選手名をキーにして左外部結合 (Left Join)
    df_merged = pd.merge(
        df_batting, 
        df_fielding, 
        on='選手名_標準化', 
        how='left',
        suffixes=('', '_守備') # カラム名が重複した場合の接尾辞
    )

    # 4. 各選手の主な守備位置を算出する関数
    def get_primary_pos_jp(row):
        positions = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF']
        jp_map = {
            'C': '捕手', '1B': '一塁手', '2B': '二塁手', '3B': '三塁手', 
            'SS': '遊撃手', 'LF': '左翼手', 'CF': '中堅手', 'RF': '右翼手'
        }
        max_inn = 0
        prim_pos = '-'
        for pos in positions:
            col = f'守備イニング({pos})'
            # カラムが存在し、かつ値が欠損していない場合
            if col in row.index and pd.notna(row[col]):
                try:
                    inn = float(row[col])
                    if inn > max_inn:
                        max_inn = inn
                        prim_pos = jp_map[pos]
                except ValueError:
                    pass
        return prim_pos

    # 結合したデータフレームに「主なポジション」カラムを追加
    df_merged['主なポジション'] = df_merged.apply(get_primary_pos_jp, axis=1)

    # 5. データ型の整理（打席数とOPSを確実に数値として扱う）
    df_merged['打席数'] = pd.to_numeric(df_merged['打席数'], errors='coerce')
    df_merged['OPS'] = pd.to_numeric(df_merged['OPS'], errors='coerce')

    # 6. 150打席以上の野手を対象に、OPS順でトップ15を抽出
    top_15 = df_merged[df_merged['打席数'] >= 150].sort_values(by='OPS', ascending=False).head(15)

    # 7. 出力用のカラムを整理してMarkdown形式で表示
    out_cols = ['主なポジション', '選手名', 'チーム', '試合', '打席数', '打率', '本塁打', 'OPS']
    # 元データに存在しないカラムが指定されるエラーを防ぐ
    out_cols = [col for col in out_cols if col in top_15.columns]
    
    print("--- 150打席以上 OPSトップ15（ポジション欠損修正版） ---")
    print(top_15[out_cols].to_markdown(index=False))

    # 8. 結合・修正が完了した完全版のデータをCSVとして保存
    # 結合用の仮カラムを削除してから書き出す
    df_merged.drop(columns=['選手名_標準化']).to_csv('fixed_export.csv', index=False, encoding='utf-8-sig')
    print("\n※修正済みの全データを 'fixed_export.csv' として保存しました。")

if __name__ == "__main__":
    main()
