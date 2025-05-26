
import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Robô de Bombeamento", layout="wide")
st.title("🚰 Robô para Dimensionamento de Conjuntos Motorbomba")

# Sessão para armazenar cargas
if "cargas" not in st.session_state:
    st.session_state["cargas"] = []

st.subheader("➕ Adicionar Conjunto Motorbomba")

col1, col2, col3 = st.columns(3)
with col1:
    tensao = st.selectbox("Tensão Trifásica (V)", [220, 380, 440], index=1)
    pot_unidade = st.selectbox("Unidade de Potência", ["kW", "CV"])
    potencia = st.number_input(f"Potência do Motor ({pot_unidade})", min_value=0.0, value=10.0)

with col2:
    rendimento = st.number_input("Rendimento (%)", min_value=50.0, max_value=100.0, value=92.0)
    fp = st.number_input("Fator de Potência", min_value=0.5, max_value=1.0, value=0.90)
    fs = st.number_input("Fator de Serviço", min_value=1.0, max_value=2.0, value=1.0)

with col3:
    n_conjuntos = st.number_input("Qtde em Paralelo", min_value=1, value=1)
    partida = st.selectbox("Tipo de Partida", ["Inversor", "Soft-starter"])
    aplicacao = st.selectbox("Aplicação", ["Água", "Esgoto"])
    tipo_cabo = st.selectbox("Tipo de Cabo", ["PVC", "XLPE"])

if st.button("➕ Adicionar"):
    pot_kw = potencia if pot_unidade == "kW" else potencia * 0.736
    eta = rendimento / 100
    mult_partida = 1.5 if partida == "Inversor" else 2.5

    # Corrente por conjunto motorbomba
    i_motor = (pot_kw * 1000 * fs) / (math.sqrt(3) * tensao * eta * fp)
    i_total = i_motor * n_conjuntos
    i_partida = i_total * mult_partida

    # Grupo gerador se for esgoto
    kva_gerador = None
    if aplicacao == "Esgoto":
        kva_gerador = (i_total * math.sqrt(3) * tensao * mult_partida) / 1000

    st.session_state["cargas"].append({
        "Potência (kW)": round(pot_kw, 2),
        "Rendimento (%)": rendimento,
        "FP": fp,
        "FS": fs,
        "Tensão (V)": tensao,
        "Qtde": n_conjuntos,
        "Tipo Cabo": tipo_cabo,
        "Corrente (A)": round(i_total, 2),
        "Corrente c/ Partida (A)": round(i_partida, 2),
        "Grupo Gerador (kVA)": round(kva_gerador, 2) if kva_gerador else "Não aplicável",
        "Partida": partida,
        "Aplicação": aplicacao
    })

# Exibir resultados
if st.session_state["cargas"]:
    df = pd.DataFrame(st.session_state["cargas"])

    # Bitola por tipo de cabo
    capacidade_cabos = {
        "PVC": {1.5: 15, 2.5: 21, 4: 28, 6: 36, 10: 50, 16: 68, 25: 89, 35: 112, 50: 138},
        "XLPE": {1.5: 18, 2.5: 24, 4: 32, 6: 41, 10: 55, 16: 76, 25: 101, 35: 125, 50: 150}
    }

    def bitola_recomendada(row):
        tipo = row["Tipo Cabo"]
        corrente = row["Corrente (A)"]
        tabela = capacidade_cabos[tipo]
        for bit, cap in tabela.items():
            if corrente <= cap:
                return bit
        return "≥70 mm²"

    df["Bitola Recomendada (mm²)"] = df.apply(bitola_recomendada, axis=1)

    st.subheader("📊 Resultados")
    st.dataframe(df)

    st.download_button("📥 Baixar Excel", data=df.to_excel(index=False), file_name="dimensionamento_motorbombas.xlsx")


    # Adiciona proteção geral e fusível ultrarrápido tipo aR se houver inversor
    disjuntores = [6,10,16,20,25,32,40,50,63,70,80,100,125,160,200,250,300,400]
    fusiveis_ar = [2,4,6,10,16,20,25,32,40,50,63,80,100,125,160,200]

    def disjuntor_geral(i):
        for d in disjuntores:
            if i <= d:
                return f"Disjuntor {d}A"
        return "≥400A"

    def fusivel_ar(row):
        if row["Partida"] == "Inversor":
            corrente = row["Corrente (A)"] * 1.5
            for f in fusiveis_ar:
                if corrente <= f:
                    return f"Fusível aR {f}A"
            return "≥200A"
        return "Não se aplica"

    df["Disjuntor Geral (A)"] = df["Corrente (A)"].apply(disjuntor_geral)
    df["Fusível aR para Inversor"] = df.apply(fusivel_ar, axis=1)
