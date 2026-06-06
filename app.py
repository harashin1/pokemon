import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="対戦マルチダメージシミュレータ", layout="wide")

# ==========================================
# 1. 関数・相性表の定義
# ==========================================
types_list = ["ノーマル", "ほのお", "みず", "でんき", "くさ", "こおり", "かくとう", "どく", "じめん", "ひこう", "エスパー", "むし", "いわ", "ゴースト", "ドラゴン", "あく", "ハガネ", "フェアリー", "－"]
type_chart = {t: {d: 1.0 for d in types_list} for t in types_list}
# (相性表は既存のものをここに記載してください)

def get_type_effectiveness(move_type, target_t1, target_t2):
    eff = type_chart.get(move_type, {}).get(target_t1, 1.0)
    if pd.notna(target_t2) and target_t2 != "" and target_t2 != "－":
        eff *= type_chart.get(move_type, {}).get(target_t2, 1.0)
    return eff

# 個体値調整用UI
def stat_adjuster(label, key):
    return st.number_input(label, min_value=0, max_value=31, value=31, key=key)

# ==========================================
# 2. データ読み込み
# ==========================================
@st.cache_data
def load_data():
    df_pokes = pd.read_csv("battle_memories_perfect.csv")
    df_moves = pd.read_csv("moves_master.csv")
    df = pd.merge(df_pokes.drop(columns=["技タイプ", "技威力", "技分類"], errors="ignore"), df_moves, on="覚える技名", how="left")
    
    stat_cols = ["実数値_H", "実数値_A", "実数値_B", "実数値_C", "実数値_D", "実数値_S"]
    for col in stat_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

df = load_data()

# ==========================================
# 3. アプリメイン画面
# ==========================================
st.title("🧮 対戦マルチダメージシミュレータ")
if df is not None:
    pokemon_list = sorted(df["ポケモン名"].unique())
    col_atk, col_moves, col_def_res = st.columns([1.1, 1.2, 1.7])

    # --- 攻撃側 ---
    with col_atk:
        st.header("🔴 攻撃側")
        atk_poke = st.selectbox("ポケモン選択", pokemon_list, key="atk_p")
        atk_first = df[df["ポケモン名"] == atk_poke].iloc[0]
        hit_count = st.selectbox("攻撃回数", [1, 2, 3, 4, 5])
        
        nature_mod = {"1.1倍": 1.1, "1.0倍": 1.0, "0.9倍": 0.9}[st.selectbox("性格補正", ["1.1倍", "1.0倍", "0.9倍"])]
        
        iv_a = stat_adjuster("攻撃(A)個体値", "atk_a_iv")
        iv_c = stat_adjuster("特攻(C)個体値", "atk_c_iv")

    # --- 技選択 ---
    with col_moves:
        st.header("⚔️ 技一覧")
        all_moves = df[df["ポケモン名"] == atk_poke][["覚える技名", "技タイプ", "技威力", "技分類"]].drop_duplicates()
        selected_move = st.selectbox("💥 技選択", sorted(all_moves["覚える技名"].unique()))
        move_row = all_moves[all_moves["覚える技名"] == selected_move].iloc[0]
        move_type, move_cat, move_power_raw = move_row["技タイプ"], move_row["技分類"], move_row["技威力"]

    # --- 防御側 ---
    with col_def_res:
        st.header("🔵 防御側")
        targets = st.multiselect("対戦相手", pokemon_list, default=[pokemon_list[0]])
        
        # 攻撃側ステータス確定
        base_stat_atk = int(atk_first["実数値_A" if move_cat == "物理" else "実数値_C"])
        atk_stat = math.floor((base_stat_atk + (iv_a if move_cat == "物理" else iv_c) - 31) * nature_mod)
        
        for idx, t_name in enumerate(targets[:6]):
            t_first = df[df["ポケモン名"] == t_name].iloc[0]
            with st.expander(f"🛡️ {t_name}", expanded=True):
                # 防御側の調整UI
                c1, c2, c3 = st.columns(3)
                iv_h = c1.number_input(f"HP個体", 0, 31, 31, key=f"def_h_{idx}")
                iv_b = c2.number_input(f"B個体", 0, 31, 31, key=f"def_b_{idx}")
                iv_d = c3.number_input(f"D個体", 0, 31, 31, key=f"def_d_{idx}")
                def_nat = st.selectbox(f"防御補正 ({t_name})", ["1.0倍", "1.1倍", "0.9倍"], key=f"def_nat_{idx}")
                def_mod = {"1.1倍": 1.1, "1.0倍": 1.0, "0.9倍": 0.9}[def_nat]

                # 防御側ステータス算出
                target_hp = int(t_first["実数値_H"]) + (iv_h - 31)
                def_val = int(t_first["実数値_B" if move_cat == "物理" else "実数値_D"])
                def_stat = math.floor((def_val + (iv_b if move_cat == "物理" else iv_d) - 31) * def_mod)

                # ダメージ計算
                move_power = int(float(move_power_raw)) if str(move_power_raw).isdigit() else 0
                mod = (1.5 if move_type in [atk_first["タイプ1"], atk_first["タイプ2"]] else 1.0) * get_type_effectiveness(move_type, t_first["タイプ1"], t_first["タイプ2"])
                base_dmg = math.floor(math.floor((50 * 2 / 5 + 2) * move_power * atk_stat / max(def_stat, 1)) / 50) + 2
                
                dmg_min, dmg_max = math.floor(base_dmg * 0.85 * mod) * hit_count, math.floor(base_dmg * 1.00 * mod) * hit_count
                
                st.metric("期待ダメージ", f"{dmg_min} 〜 {dmg_max}")
                st.progress(min(dmg_max / max(target_hp, 1), 1.0))
                st.write(f"HP削れ率: {min(round((dmg_min/target_hp)*100, 1), 100)}% 〜 {min(round((dmg_max/target_hp)*100, 1), 100)}%")
