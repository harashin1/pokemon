import streamlit as st
import pandas as pd

st.set_page_config(layout="wide") # 画面を横いっぱいに広く使う設定

st.title("⚔️ ポケモン ダメージ計算システム")
st.caption("ポケモン、覚える技、タイプ相性がすべて自動で連動します！")
st.divider()

# --- データの読み込み関数 ---
@st.cache_data
def load_all_data():
    # 修正していただいたファイル名と文字コードで正確に読み込みます
    pokemon_df = pd.read_csv("pokemon_name_stats.csv", encoding="shift_jis")
    moves_df = pd.read_csv("pokemon_move_name.csv", encoding="shift_jis")
    pokemon_moves_df = pd.read_csv("pokemon_remember_move_name.csv", encoding="shift_jis")
    type_chart_df = pd.read_csv("type_chart.csv", encoding="shift_jis")
    return pokemon_df, moves_df, pokemon_moves_df, type_chart_df

# --- データの読み込み実行 ---
try:
    pokemon_df, moves_df, pokemon_moves_df, type_chart_df = load_all_data()
except Exception as e:
    st.error(f"❌ データの読み込みでエラーが発生しました。ファイル名や文字コードを確認してください: {e}")
    st.stop()

# --- 画面を左右2つに分ける ---
col1, col2 = st.columns(2)

# --- 🚀 左側：攻撃側の設定 ---
with col1:
    st.subheader("🚀 攻撃側")
    # ポケモンの日本語名を選ばせる
    atk_pokemon = st.selectbox("攻撃するポケモンを選択", pokemon_df["jp_name"].unique(), key="atk_poke")
    # 選ばれたポケモンのデータを取得
    atk_status = pokemon_df[pokemon_df["jp_name"] == atk_pokemon].iloc[0]
    
    # 攻撃実数値の入力（デフォルト値は種族値+32）
    default_atk = int(atk_status["base_atk"])
    atk_real = st.number_input(f"{atk_pokemon}の攻撃実数値（努力値等で調整可）", min_value=1, max_value=500, value=default_atk + 32)
    
    st.markdown("---")
    
    # 【連動処理】そのポケモンが覚える技だけを絞り込む
    atk_api_name = atk_status["api_name"]
    learned_move_ids = pokemon_moves_df[pokemon_moves_df["api_name"] == atk_api_name]["move"].tolist()
    available_moves = moves_df[moves_df["api_name_move"].isin(learned_move_ids)]
    
    if not available_moves.empty:
        selected_move_name = st.selectbox("使う技を選択", available_moves["技名"].unique())
        move_info = available_moves[available_moves["技名"] == selected_move_name].iloc[0]
        
        try:
            move_power = int(move_info["技威力"])
        except:
            move_power = 0
            
        move_type = move_info["技タイプ"]
        st.info(f"🔮 選択中の技: **{selected_move_name}**\n* タイプ: {move_type} / 威力: {move_power}")
    else:
        st.warning("⚠️ 覚える技のデータが見つかりませんでした。")
        selected_move_name = "カスタム技"
        move_power = st.number_input("技の威力（手動入力）", min_value=0, max_value=250, value=90)
        move_type = "normal"

# --- 🛡️ 右側：防御側の設定 ---
with col2:
    st.subheader("🛡️ 防御側")
    # 防御するポケモンを選ばせる
    def_pokemon = st.selectbox("防御するポケモンを選択", pokemon_df["jp_name"].unique(), key="def_poke")
    def_status = pokemon_df[pokemon_df["jp_name"] == def_pokemon].iloc[0]
    
    # 防御実数値の入力（デフォルト値は種族値+32）
    default_def = int(def_status["base_def"])
    dfn_real = st.number_input(f"{def_pokemon}の防御実数値（努力値等で調整可）", min_value=1, max_value=500, value=default_def + 32)
    
    st.markdown("---")
    # 防御側のタイプを表示
    t1 = def_status['type1']
    t2 = def_status['type2'] if pd.notna(def_status['type2']) else 'なし'
    st.write(f"📊 **{def_pokemon} のタイプ:** `{t1}` / `{t2}`")
    st.write(f"❤️ **HP種族値:** {def_status['base_hp']}")

st.divider()

# --- 📊 ダメージ計算・タイプ相性の裏処理 ---
type_modifier = 1.0

# 技のタイプ名（日本語）を小文字の英語に変換して相性表と照合（例：ほのお -> fire）
type_translation = {
    "ノーマル": "normal", "ほのお": "fire", "みず": "water", "でんき": "electric",
    "くさ": "grass", "こおり": "ice", "かくとう": "fighting", "どく": "poison",
    "じめん": "ground", "ひこう": "flying", "エスパー": "psychic", "むし": "bug",
    "いわ": "rock", "ゴースト": "ghost", "ドラゴン": "dragon", "あく": "dark",
    "はがね": "steel", "フェアリー": "fairy"
}

move_type_en = type_translation.get(move_type, str(move_type).lower().strip())

# 相性表（type_chart.csv）から倍率を探す
matching_rows = type_chart_df[type_chart_df.iloc[:, 0] == move_type_en]
if not matching_rows.empty:
    type_row = matching_rows.iloc[0]
    
    # 防御側タイプ1への相性
    def_type1_en = str(def_status["type1"]).lower().strip()
    if def_type1_en in type_chart_df.columns:
        type_modifier *= float(type_row[def_type1_en])
        
    # 防御側タイプ2への相性（ある場合のみ）
    def_type2_en = str(def_status["type2"]).lower().strip() if pd.notna(def_status["type2"]) else "na"
    if def_type2_en != "na" and def_type2_en in type_chart_df.columns:
        type_modifier *= float(type_row[def_type2_en])

# ダメージ公式の適応（レベル50固定）
if move_power > 0:
    base_damage = int(((22 * move_power * atk_real / dfn_real) / 50) + 2)
    base_damage = int(base_damage * type_modifier)
    
    # 乱数幅（最少値は0.85倍〜最大値は1.0倍）
    min_damage = int(base_damage * 0.85)
    max_damage = base_damage
else:
    min_damage = 0
    max_damage = 0

# --- 🎉 計算結果の画面表示 ---
st.header("📊 計算結果")

if type_modifier == 0:
    st.error(f"🚫 効果がないようだ… ({type_modifier}倍)")
elif type_modifier >= 2.0:
    st.success(f"💥 効果はばつぐんだ！ ({type_modifier}倍)")
elif type_modifier < 1.0 and type_modifier > 0:
    st.warning(f"🍃 効果は今ひとつのようだ… ({type_modifier}倍)")
else:
    st.info(f"⚖️ 効果は等倍だ。 ({type_modifier}倍)")

# 大きな文字でダメージを表示
st.metric(label="🎯 与えるダメージの範囲（乱数幅）", value=f"{min_damage} ～ {max_damage} ダメージ")