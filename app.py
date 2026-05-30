import streamlit as st
import pandas as pd
import math

st.set_page_config(layout="wide") # 画面を横いっぱいに広く使う設定

st.title("⚔️ ポケモン ダメージ計算システム")
st.caption("ローカルのCSVファイルと連動中！確定数や残りHP%も自動計算します。")
st.divider()

# --- データの読み込み関数（元のCSV読み込み方式） ---
@st.cache_data
def load_all_data():
    # 以前正常に動いていたファイル名と文字コードで読み込みます
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

# --- 💡 タイプ名 英語➔日本語 変換用辞書 ---
inverse_type_translation = {
    "normal": "ノーマル", "fire": "ほのお", "water": "みず", "electric": "でんき",
    "grass": "くさ", "ice": "こおり", "fighting": "かくとう", "poison": "どく",
    "ground": "じめん", "flying": "ひこう", "psychic": "エスパー", "bug": "むし",
    "rock": "いわ", "ghost": "ゴースト", "dragon": "ドラゴン", "dark": "あく",
    "steel": "はがね", "fairy": "フェアリー"
}

# --- 画面を左右2つに分ける ---
col1, col2 = st.columns(2)

# --- 🚀 左側：攻撃側の設定 ---
with col1:
    st.subheader("🚀 攻撃側")
    atk_pokemon = st.selectbox("攻撃するポケモンを選択", pokemon_df["jp_name"].unique(), key="atk_poke")
    atk_status = pokemon_df[pokemon_df["jp_name"] == atk_pokemon].iloc[0]
    
    default_atk = int(atk_status["base_atk"])
    atk_real = st.number_input(f"{atk_pokemon}の攻撃実数値（努力値等で調整可）", min_value=1, max_value=500, value=default_atk + 32)
    
    st.markdown("---")
    
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
        move_type = "ノーマル"

# --- 🛡️ 右側：防御側の設定 ---
with col2:
    st.subheader("🛡️ 防御側")
    def_pokemon = st.selectbox("防御するポケモンを選択", pokemon_df["jp_name"].unique(), key="def_poke")
    def_status = pokemon_df[pokemon_df["jp_name"] == def_pokemon].iloc[0]
    
    default_def = int(def_status["base_def"])
    dfn_real = st.number_input(f"{def_pokemon}の防御実数値（努力値等で調整可）", min_value=1, max_value=500, value=default_def + 32)
    
    # 🎯 防御側のHP実数値の入力（デフォルト値は種族値+75：レベル50のHPぶっぱ調整を想定）
    default_hp = int(def_status["base_hp"])
    hp_real = st.number_input(f"{def_pokemon}のHP実数値（Lv.50時の実数値）", min_value=1, max_value=500, value=default_hp + 75)
    
    st.markdown("---")
    
    # 🌟 タイプの英語名と日本語名を両方綺麗に変換して表示する機能
    t1_raw = str(def_status['type1']).lower().strip()
    t2_raw = str(def_status['type2']).lower().strip() if pd.notna(def_status['type2']) else 'なし'
    
    t1_jp = inverse_type_translation.get(t1_raw, t1_raw)
    t2_jp = inverse_type_translation.get(t2_raw, t2_raw) if t2_raw != 'なし' else 'なし'
    
    if t2_jp != 'なし':
        st.write(f"📊 **{def_pokemon} のタイプ:** {t1_jp} (`{t1_raw}`) / {t2_jp} (`{t2_raw}`)")
    else:
        st.write(f"📊 **{def_pokemon} のタイプ:** {t1_jp} (`{t1_raw}`)")
        
    st.write(f"❤️ **HP種族値:** {def_status['base_hp']} ➔ **現在想定のHP実数値:** `{hp_real}`")

st.divider()

# --- 📊 ダメージ計算・タイプ相性の裏処理 ---
type_modifier = 1.0

type_translation = {
    "ノーマル": "normal", "ほのお": "fire", "みず": "water", "でんき": "electric",
    "くさ": "grass", "こおり": "ice", "かくとう": "fighting", "どく": "poison",
    "じめん": "ground", "ひこう": "flying", "エスパー": "psychic", "むし": "bug",
    "いわ": "rock", "ゴースト": "ghost", "ドラゴン": "dragon", "あく": "dark",
    "はがね": "steel", "フェアリー": "fairy"
}

move_type_en = type_translation.get(move_type, str(move_type).lower().strip())

matching_rows = type_chart_df[type_chart_df.iloc[:, 0] == move_type_en]
if not matching_rows.empty:
    type_row = matching_rows.iloc[0]
    
    def_type1_en = str(def_status["type1"]).lower().strip()
    if def_type1_en in type_chart_df.columns:
        type_modifier *= float(type_row[def_type1_en])
        
    def_type2_en = str(def_status["type2"]).lower().strip() if pd.notna(def_status["type2"]) else "na"
    if def_type2_en != "na" and def_type2_en in type_chart_df.columns:
        type_modifier *= float(type_row[def_type2_en])

# ダメージ公式の適応（レベル50固定）
if move_power > 0 and dfn_real > 0:
    base_damage = int(((22 * move_power * atk_real / dfn_real) / 50) + 2)
    base_damage = int(base_damage * type_modifier)
    
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

# --- 📈 確定数・残りHP割合の追加計算 ---
st.subheader("📈 耐久パフォーマンス（確定数・残りHP割合）")

if hp_real > 0 and max_damage > 0:
    # 割合の計算
    min_pct = (min_damage / hp_real) * 100
    max_pct = (max_damage / hp_real) * 100
    
    # 確定数の計算
    min_hits_to_kill = math.ceil(hp_real / max_damage)
    max_hits_to_kill = math.ceil(hp_real / min_damage)
    
    # 画面表示用の文言作成
    if min_hits_to_kill == 1 and max_hits_to_kill == 1:
        hit_summary = "🔴 **確定 1発** （どのような乱数を引いても1撃で倒せます）"
    elif min_hits_to_kill == 1 and max_hits_to_kill > 1:
        hit_summary = "🔶 **乱数 1発** （乱数次第で1撃、耐えられても次の1発で倒せます）"
    elif min_hits_to_kill == max_hits_to_kill:
        hit_summary = f"🔵 **確定 {min_hits_to_kill}発**"
    else:
        hit_summary = f"⚠️ **乱数 {min_hits_to_kill}発** （確定 {max_hits_to_kill}発）"
        
    # 残りHPの計算
    rem_hp_min = max(0, hp_real - max_damage)
    rem_hp_max = max(0, hp_real - min_damage)
    rem_pct_min = (rem_hp_min / hp_real) * 100
    rem_pct_max = (rem_hp_max / hp_real) * 100

    # カード形式（columns）で見せる
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.markdown(f"**【ダメージの割合】**\n### {min_pct:.1f}% ～ {max_pct:.1f}%")
    with kpi2:
        st.markdown(f"**【倒すために必要な手数】**\n### {hit_summary}")
    with kpi3:
        st.markdown(f"**【1発受けた後の残りHP】**\n### {rem_hp_min} 〜 {rem_hp_max} ({rem_pct_min:.1f}% 〜 {rem_pct_max:.1f}%)")

    # 視覚的なHPバーのシミュレーション
    st.markdown("**🛡️ 1発被弾後のHP残り予想ゲージ（最大ダメージ時）**")
    st.progress(float(rem_pct_min / 100))
    
else:
    st.info("💡 攻撃側か防御側の数値が正しく入力されると、ここに確定数が表示されます。")
