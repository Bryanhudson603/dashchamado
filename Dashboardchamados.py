import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt

# Configurações da página
st.set_page_config(page_title="Dashboard de Chamados", layout="wide")

# Dicionários de mapeamento
EQUIPES = {
    1.0: "Service Desk",
    3.0: "Suporte Técnico"
}

OPERADORES = {
    497: "Bryan Hudson do Nascimento Silva",
    462: "Maria Priscila Barros Pinheiro",
    122: "Anderlan Davi dos Santos Pontes",
    63: "Victor Salvador de Araújo",
    206: "João Saulo da costa Almeida",
    133: "Pedro Henrique Pereira da Rocha",
    240: "Alan Mendonça dos Santos",
    258: "Bayron Rafael Pires de Lima",
    103: "Flávio Oliveira de Morais Sarmento",
    229: "João Marcos Correia da Silva",
    158: "Thiago Ferreira Silva"
}

# Função para carregar dados
@st.cache_data
def carregar_dados():
    df_chamados = pd.read_csv('hd_chamado.csv')
    df_chamados['dtchamado'] = pd.to_datetime(df_chamados['dtchamado'])
    df_chamados['dttermino'] = pd.to_datetime(df_chamados['dttermino'])
    
    df_acompanhamentos = pd.read_csv('hd_acompanhamento.csv')
    df_acompanhamentos['cdacompanhamento'] = df_acompanhamentos['cdacompanhamento'].astype(str)
    df_acompanhamentos['dtacompanhamento'] = pd.to_datetime(df_acompanhamentos['dtacompanhamento'], errors='coerce')
    df_acompanhamentos['cdtipoacompanhamento'] = pd.to_numeric(df_acompanhamentos['cdtipoacompanhamento'], errors='coerce')
    
    return df_chamados, df_acompanhamentos

# Carregar os dados
df, df_acompanhamentos = carregar_dados()

# ======================================
# FILTROS
# ======================================
st.sidebar.header("Filtros")

# Filtro de data
min_date = df['dtchamado'].min().date()
max_date = df['dtchamado'].max().date()

data_inicio = st.sidebar.date_input("Data inicial", min_date, min_value=min_date, max_value=max_date)
data_fim = st.sidebar.date_input("Data final", max_date, min_value=min_date, max_value=max_date)

# Filtro de equipes
equipes_selecionadas = st.sidebar.multiselect("Selecione as equipes:", options=list(EQUIPES.values()), default=list(EQUIPES.values()))

# Converter seleções para códigos
codigos_equipes = [k for k, v in EQUIPES.items() if v in equipes_selecionadas]

# Aplicar filtros
df_filtrado = df[(df['dtchamado'].dt.date >= data_inicio) & (df['dtchamado'].dt.date <= data_fim) & (df['cdequipe'].isin(codigos_equipes))]

# ======================================
# GRÁFICO 1 - Chamados por Equipe/Mês (Estilo Gráfico 2)
# ======================================
st.header("Chamados por Equipe e Mês")

# Mapeamento e preparação dos dados (mantido igual)
EQUIPES_POR_OPERADOR = {
    497: "Service Desk", 462: "Service Desk", 122: "Service Desk", 63: "Service Desk",
    206: "Suporte Técnico", 133: "Suporte Técnico", 240: "Suporte Técnico",
    258: "Suporte Técnico", 103: "Suporte Técnico", 229: "Suporte Técnico", 158: "Suporte Técnico"
}

df_equipes = df_filtrado.copy()
df_equipes['mes'] = df_equipes['dtchamado'].dt.strftime('%Y-%m')
df_equipes['equipe'] = df_equipes['cdusuario'].map(EQUIPES_POR_OPERADOR)

# Agrupar dados
dados_equipe = df_equipes.groupby(['mes', 'equipe']).size().reset_index(name='total')

# Criar gráfico ajustável
import altair as alt

# Criar gráfico agrupado
grafico1 = alt.Chart(dados_equipe).mark_bar(
    cornerRadius=5,
    size=25  # Largura das barras
).encode(
    x=alt.X('mes:N', title='Mês', axis=alt.Axis(labelAngle=0)),
    y=alt.Y('total:Q', title='Total de Chamados'),
    color=alt.Color('equipe:N', 
                   scale=alt.Scale(range=['#1f77b4', '#ff7f0e']),
                   legend=alt.Legend(title="Equipe")),
    xOffset=alt.XOffset('equipe:N')  # Agrupa as barras por equipe
).properties(
    width=alt.Step(40)  # Largura responsiva
)

st.altair_chart(grafico1, use_container_width=True)
# ======================================
# GRÁFICO 2 - Chamados por Operador (Versão Final)
# ======================================
st.header("Chamados por Operador")

# Checkbox para controle
mostrar_tabela = st.checkbox("Mostrar tabela detalhada", key="tabela_operadores")

# Preparar dados
df_operadores = df_filtrado[df_filtrado['cdusuario'].isin(OPERADORES.keys())]
contagem = df_operadores['cdusuario'].value_counts().reset_index()
contagem.columns = ['cdusuario', 'total']
contagem['operador'] = contagem['cdusuario'].map(OPERADORES)
contagem = contagem.sort_values('total', ascending=False)

# Gráfico principal
st.bar_chart(contagem.set_index('operador')['total'], height=400, color='#2ca02c')

# Tabela abaixo (condicional)
if mostrar_tabela:
    st.subheader("Detalhamento por Operador")
    
    # Tabela estilizada
    tabela = contagem[['operador', 'total']].rename(columns={
        'operador': 'Operador',
        'total': 'Total de Chamados'
    })
    
    st.dataframe(
        tabela.style
            .background_gradient(subset=['Total de Chamados'], cmap='Greens')
            .format({'Total de Chamados': '{:.0f}'})
            .set_properties(**{'text-align': 'left'}),
        height=400,
        use_container_width=True
    )

# ======================================
# NOVO GRÁFICO 3 - Chamados Atendidos por Operador (via Acompanhamentos)
# ======================================
st.header("Chamados Atendidos por Operador (via Acompanhamentos)")

# Aplicar filtros de data nos acompanhamentos
df_acomp_filtrado = df_acompanhamentos[
    (df_acompanhamentos['dtacompanhamento'] >= pd.to_datetime(data_inicio)) &
    (df_acompanhamentos['dtacompanhamento'] <= pd.to_datetime(data_fim))
]

# Contar chamados distintos por operador
contagem_chamados = (
    df_acomp_filtrado
    .groupby('cdusuario')['cdchamado']
    .nunique()  # Conta chamados únicos
    .reset_index(name='total')
    .sort_values('total', ascending=False)
)

# Mapear nomes dos operadores
contagem_chamados['operador'] = contagem_chamados['cdusuario'].map(OPERADORES)

# Filtrar apenas operadores válidos
contagem_chamados = contagem_chamados[contagem_chamados['cdusuario'].isin(OPERADORES.keys())]

# Gráfico de barras
if not contagem_chamados.empty:
    st.bar_chart(
        contagem_chamados.set_index('operador')['total'], 
        height=400, 
        color='#9467bd'  # Cor roxa
    )
else:
    st.warning("Nenhum chamado encontrado no período!")

# Tabela detalhada
mostrar_tabela_acomp = st.checkbox("Mostrar detalhes de chamados por operador", key="tabela_chamados_operador")
if mostrar_tabela_acomp and not contagem_chamados.empty:
    st.subheader("Detalhamento de Chamados Atendidos")
    
    tabela_acomp = contagem_chamados[['operador', 'total']].rename(columns={
        'operador': 'Operador',
        'total': 'Chamados Atendidos'
    })
    
    st.dataframe(
        tabela_acomp.style
            .background_gradient(subset=['Chamados Atendidos'], cmap='Purples')
            .format({'Chamados Atendidos': '{:.0f}'}),
        height=400,
        use_container_width=True
    )

# Verificação de operadores sem registros
if not contagem_chamados.empty:
    usuarios_sem_chamados = set(OPERADORES.keys()) - set(contagem_chamados['cdusuario'])
    if usuarios_sem_chamados:
        st.warning(f"Operadores sem chamados atendidos: {', '.join(OPERADORES[id] for id in usuarios_sem_chamados)}")

# ======================================
# GRÁFICO 4 - Chamados por Meio de Solicitação
# ======================================
st.header("Chamados por Meio de Solicitação")

# Mapeamento dos códigos de origem para categorias
mapeamento_origem = {
    1: "Telefone",
    18: "Telefone",
    5: "Telefone",
    2: "Email",
    6: "Email",
    4: "Pessoalmente",
    7: "Pessoalmente",
    17: "Pessoalmente",
    14: "Web Service",
    3: "Web Service",
    8: "Web Service",
    13: "Web Service",
    20: "Web Service",
    15: "Chat",
    9: "Chat",
    10: "Operação Monitoramento",
    11: "Oficio",
    12: "URA",
    19: "URA"
}

# Criar uma coluna com a categoria baseada no cdorigem
df_filtrado['meio_solicitacao'] = df_filtrado['cdorigem'].map(mapeamento_origem)

# Contar chamados por meio de solicitação
contagem_meios = df_filtrado['meio_solicitacao'].value_counts().reset_index()
contagem_meios.columns = ['Meio de Solicitação', 'Total']

# Ordenar por total (opcional, mas pode ajudar na visualização)
contagem_meios = contagem_meios.sort_values('Total', ascending=False)

# Criar gráfico de pizza com Altair
grafico_pizza = alt.Chart(contagem_meios).mark_arc().encode(
    theta=alt.Theta(field="Total", type="quantitative"),
    color=alt.Color(field="Meio de Solicitação", type="nominal", 
                   scale=alt.Scale(scheme='category20')),
    tooltip=['Meio de Solicitação', 'Total']
).properties(
    width=500,
    height=400,
    title="Distribuição de Chamados por Meio de Solicitação"
)

# Criar gráfico de barras
grafico_barras = alt.Chart(contagem_meios).mark_bar().encode(
    x=alt.X('Meio de Solicitação:N', axis=alt.Axis(labelAngle=0), sort='-y'),
    y='Total:Q',
    color=alt.Color('Meio de Solicitação:N', scale=alt.Scale(scheme='category20')),
    tooltip=['Meio de Solicitação', 'Total']
).properties(
    width=600,
    height=400,
    title="Chamados por Meio de Solicitação"
)

# Mostrar gráficos em abas
aba1, aba2 = st.tabs(["Gráfico de Pizza", "Gráfico de Barras"])

with aba1:
    st.altair_chart(grafico_pizza, use_container_width=True)
    
with aba2:
    st.altair_chart(grafico_barras, use_container_width=True)

# Tabela detalhada
mostrar_tabela_meios = st.checkbox("Mostrar tabela detalhada", key="tabela_meios")
if mostrar_tabela_meios:
    st.subheader("Detalhamento por Meio de Solicitação")
    
    # Formatar tabela
    tabela_meios = contagem_meios.copy()
    tabela_meios['Percentual'] = (tabela_meios['Total'] / tabela_meios['Total'].sum() * 100).round(2)
    
    st.dataframe(
        tabela_meios.style
            .background_gradient(subset=['Total'], cmap='Blues')
            .format({'Total': '{:.0f}', 'Percentual': '{:.2f}%'}),
        height=400,
        use_container_width=True
    )

# ======================================
# GRÁFICO 5 - Acompanhamentos Tipo 22.0 por Operador (Corrigido)
# ======================================
st.header("Acompanhamentos Tipo 22.0 por Operador")

# 1. Criar DataFrame com todos os operadores
todos_operadores = pd.DataFrame({
    'cdusuario': list(OPERADORES.keys()),
    'operador': [OPERADORES[id] for id in OPERADORES.keys()]
})

# 2. Filtrar acompanhamentos tipo 22.0 com base nas datas
df_acomp_tipo22 = df_acompanhamentos[
    (df_acompanhamentos['dtacompanhamento'] >= pd.to_datetime(data_inicio)) &
    (df_acompanhamentos['dtacompanhamento'] <= pd.to_datetime(data_fim)) &
    (df_acompanhamentos['cdtipoacompanhamento'].isin([20.0, 22.0]))
    
]

# 3. Contar acompanhamentos por operador
contagem_acomp = df_acomp_tipo22.groupby('cdusuario').size().reset_index(name='total')

# 4. Combinar com todos os operadores para incluir os que não tiveram registros
dados_grafico5 = todos_operadores.merge(
    contagem_acomp, 
    on='cdusuario', 
    how='left'
).fillna(0)  # Preencher valores ausentes com 0

# 5. Ordenar por total
dados_grafico5 = dados_grafico5.sort_values('total', ascending=False)

# 6. Criar gráfico
if not dados_grafico5.empty:
    # Gráfico de barras com Altair
    grafico_barras = alt.Chart(dados_grafico5).mark_bar(
        color='#17becf',  # Cor azul-turquesa
        cornerRadius=5
    ).encode(
        x=alt.X('operador:N', title='Operador', sort='-y'),
        y=alt.Y('total:Q', title='Total de Acompanhamentos'),
        tooltip=['operador', 'total']
    ).properties(
        height=400,
        title="Acompanhamentos Tipo 22.0 por Operador"
    )
    
    st.altair_chart(grafico_barras, use_container_width=True)
    
    # Tabela detalhada
    mostrar_tabela = st.checkbox("Mostrar tabela detalhada", key="tabela_grafico5")
    if mostrar_tabela:
        st.subheader("Detalhamento por Operador")
        
        # Calcular percentual
        total_geral = dados_grafico5['total'].sum()
        dados_grafico5['percentual'] = (dados_grafico5['total'] / total_geral * 100).round(1)
        
        tabela = dados_grafico5[['operador', 'total', 'percentual']].rename(columns={
            'operador': 'Operador',
            'total': 'Total',
            'percentual': 'Percentual (%)'
        })
        
        st.dataframe(
            tabela.style
                .background_gradient(subset=['Total'], cmap='Blues')
                .format({'Total': '{:.0f}', 'Percentual (%)': '{:.1f}%'}),
            height=400,
            use_container_width=True
        )
        
        # Estatísticas
        st.subheader("Estatísticas")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Geral", total_geral)
        col2.metric("Média por Operador", f"{total_geral / len(dados_grafico5):.1f}")
        
        top_operador = dados_grafico5.iloc[0]
        col3.metric("Operador com Mais Acompanhamentos", 
                   f"{top_operador['operador']} ({top_operador['total']})")
else:
    st.warning("Nenhum acompanhamento tipo 22.0 encontrado no período!")

# 7. Verificar operadores sem registros
operadores_sem = dados_grafico5[dados_grafico5['total'] == 0]
if not operadores_sem.empty:
    st.warning(
        "Operadores sem acompanhamentos tipo 22.0: " +
        ", ".join(operadores_sem['operador'].tolist())
    )

# ======================================
# GRÁFICO 6 - Chamados Finalizados por Operador
# ======================================
st.header("Chamados Finalizados por Operador")

# 1. Filtrar chamados finalizados (cdsituacao = 7)
df_finalizados = df_filtrado[df_filtrado['cdsituacao'] == 7.0]

# 2. Contar chamados por responsável
contagem_finalizados = df_finalizados['cdresponsavel'].value_counts().reset_index()
contagem_finalizados.columns = ['cdresponsavel', 'total']

# 3. Mapear nomes dos operadores e equipes
contagem_finalizados['operador'] = contagem_finalizados['cdresponsavel'].map(OPERADORES)
contagem_finalizados['equipe'] = contagem_finalizados['cdresponsavel'].map(EQUIPES_POR_OPERADOR)

# 4. Combinar com todos os operadores para mostrar inclusive quem não finalizou
todos_operadores = pd.DataFrame({
    'cdresponsavel': list(OPERADORES.keys()),
    'operador': [OPERADORES[id] for id in OPERADORES.keys()],
    'equipe': [EQUIPES_POR_OPERADOR[id] for id in OPERADORES.keys()]
})

dados_grafico6 = todos_operadores.merge(
    contagem_finalizados[['cdresponsavel', 'total']], 
    on='cdresponsavel', 
    how='left'
).fillna(0)  # Preencher NaN com 0

# 5. Ordenar por total
dados_grafico6 = dados_grafico6.sort_values('total', ascending=False)

# 6. Criar gráfico de barras agrupado por equipe
grafico_barras = alt.Chart(dados_grafico6).mark_bar(
    cornerRadius=5,
    size=25
).encode(
    x=alt.X('operador:N', title='Operador', sort='-y'),
    y=alt.Y('total:Q', title='Chamados Finalizados'),
    color=alt.Color('equipe:N', 
                   scale=alt.Scale(range=['#1f77b4', '#ff7f0e']),
                   legend=alt.Legend(title="Equipe")),
    tooltip=['operador', 'equipe', 'total']
).properties(
    height=400,
    title="Chamados Finalizados por Operador"
)

st.altair_chart(grafico_barras, use_container_width=True)

# 7. Tabela detalhada
mostrar_tabela_finalizados = st.checkbox("Mostrar tabela detalhada", key="tabela_finalizados")
if mostrar_tabela_finalizados:
    st.subheader("Detalhamento de Chamados Finalizados")
    
    # Formatar tabela
    tabela_finalizados = dados_grafico6[['operador', 'equipe', 'total']].rename(columns={
        'operador': 'Operador',
        'equipe': 'Equipe',
        'total': 'Chamados Finalizados'
    })
    
    st.dataframe(
        tabela_finalizados.style
            .background_gradient(subset=['Chamados Finalizados'], cmap='Oranges')
            .format({'Chamados Finalizados': '{:.0f}'}),
        height=400,
        use_container_width=True
    )
    
    # Estatísticas
    st.subheader("Estatísticas")
    col1, col2 = st.columns(2)
    total_geral = tabela_finalizados['Chamados Finalizados'].sum()
    col1.metric("Total de Chamados Finalizados", total_geral)
    col2.metric("Operador com Mais Finalizações", 
               f"{tabela_finalizados.iloc[0]['Operador']} ({tabela_finalizados.iloc[0]['Chamados Finalizados']})")

# 8. Verificar operadores sem finalizações
operadores_sem_finalizados = dados_grafico6[dados_grafico6['total'] == 0]
if not operadores_sem_finalizados.empty:
    st.warning(
        "Operadores sem chamados finalizados: " +
        ", ".join(operadores_sem_finalizados['operador'].tolist())
    )