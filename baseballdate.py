import pandas as pd

def normalize_player_name(name):
    """選手名の表記揺れ（旧字体・異体字・スペース）を標準化する関数"""
    if pd.isna(name) or not isinstance(name, str):
        return name
        
    # プロ野球の登録名で頻出する表記揺れ変換マップ
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
        '德': '徳',
        '嶋': '島', 
        '彌': '弥',
        '壽': '寿',
        '齊': '斉',
        '齋': '斎'
    })
    
    # 1. 全角・半角スペースを除去（サイトによって姓名間のスペース有無が異なるため）
    name = name.replace(" ", "").replace(" ", "")
    
    # 2. 異体字を新字体に変換
    return name.translate(kanji_mapping)

def main():
    # ==========================================
    # 1. データの読み込み
    # ==========================================
    # ※ご自身の環境に合わせて、抽出元のCSVファイル名を指定してください
    # df_batting = pd.read_csv('batting_raw.csv')
    # df_fielding = pd.read_csv('fielding_raw.csv')
    
    # 【テスト用ダミーデータ】動作確認用
    df_batting = pd.DataFrame({
        'チーム': ['西武', '阪神', 'ソフトバンク'],
        '選手名': ['滝澤 夏央', '髙寺望夢', '廣瀨 隆太'], # スペースや旧字体が混入した打撃データ
        '打席数': [447, 331, 98],
        'OPS': [0.674, 0.593, 0.600]
    })
    
    df_fielding = pd.DataFrame({
        'チーム': ['西武', '阪神', 'ソフトバンク'],
        '選手名': ['滝沢夏央', '高寺望夢', '広瀬隆太'], # 新字体・スペースなしの守備データ
        'Fielding RV(まとめ)': ['SS:2.5', '2B:1.0', '1B:-0.5'],
        '守備イニング(SS)': [800.0, None, None],
        '守備イニング(2B)': [None, 500.0, None],
        '守備イニング(1B)': [None, None, 150.0]
    })

    # ==========================================
    # 2. 結合用キーの作成（名寄せ処理）
    # ==========================================
    # 元の選手名を上書きせず、結合専用の新しいカラムを作成する
    df_batting['選手名_結合用'] = df_batting['選手名'].apply(normalize_player_name)
    df_fielding['選手名_結合用'] = df_fielding['選手名'].apply(normalize_player_name)

    # ==========================================
    # 3. データの結合
    # ==========================================
    # 同姓同名対策として、「チーム」と「標準化された選手名」の2つをキーにして結合
    df_merged = pd.merge(
        df_batting, 
        df_fielding, 
        on=['チーム', '選手名_結合用'], 
        how='left',
        suffixes=('', '_守備側') # 元から同名のカラムがあった場合に接尾辞をつける
    )

    # ==========================================
    # 4. データの整理と出力
    # ==========================================
    # 結合用に使った一時的なカラムや、重複した選手名カラムを削除
    if '選手名_守備側' in df_merged.columns:
        df_merged = df_merged.drop(columns=['選手名_守備側'])
    df_merged = df_merged.drop(columns=['選手名_結合用'])

    # 結果の表示（滝澤選手らに守備データが結びついているか確認）
    print(df_merged)
    
    # 修正されたデータを新しいCSVとして書き出す
    # df_merged.to_csv('cleaned_export.csv', index=False, encoding='utf-8-sig')

if __name__ == "__main__":
    main()
