import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt
import pyodbc
import plotly.express as px
from datetime import timedelta

# Configurações da página
st.set_page_config(page_title="Dashboard de Chamados", layout="wide")

# Configurar a conexão com o SQL Server
server = 'SFZ-MSQL-003'
database = 'QualitorProd'
conn_str = (
    f'DRIVER=ODBC Driver 17 for SQL Server;'
    f'SERVER={server};'
    f'DATABASE={database};'
    f'Trusted_Connection=yes;'
)

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

# Função para conectar ao banco de dados
def conectar_bd():
    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        st.error(f"Erro na conexão com o banco de dados: {str(e)}")
        return None

# Função para carregar dados
@st.cache_data(ttl=3600)  # Cache de 1 hora
def carregar_dados():
    conn = conectar_bd()
    if conn is None:
        return pd.DataFrame(), pd.DataFrame()
    
    try:
        # Carregar dados de hd_chamado
        query_chamados = """
        SELECT cdchamado, dtchamado, dttermino, cdequipe, cdusuario, cdorigem, cdsituacao, cdresponsavel
        FROM [dbo].[hd_chamado]
        """
        df_chamados = pd.read_sql(query_chamados, conn)
        df_chamados['dtchamado'] = pd.to_datetime(df_chamados['dtchamado'])
        df_chamados['dttermino'] = pd.to_datetime(df_chamados['dttermino'])
        
        # Carregar dados de hd_acompanhamento
        query_acompanhamentos = """
        SELECT dsacompanhamento, cdchamado, dtacompanhamento, cdusuario, cdtipoacompanhamento
        FROM [dbo].[hd_acompanhamento]
        """
        df_acompanhamentos = pd.read_sql(query_acompanhamentos, conn)
        df_acompanhamentos['dsacompanhamento'] = df_acompanhamentos['dsacompanhamento'].astype(str)
        df_acompanhamentos['dtacompanhamento'] = pd.to_datetime(df_acompanhamentos['dtacompanhamento'], errors='coerce')
        df_acompanhamentos['cdtipoacompanhamento'] = pd.to_numeric(df_acompanhamentos['cdtipoacompanhamento'], errors='coerce')
        
        return df_chamados, df_acompanhamentos
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()
    finally:
        conn.close()

# Carregar os dados
df, df_acompanhamentos = carregar_dados()

# Verificar se os dados foram carregados corretamente
if df.empty or df_acompanhamentos.empty:
    st.warning("Não foi possível carregar os dados. Verifique a conexão com o banco de dados.")
    st.stop()

# from datetime import datetime, timedelta

# ======================================
# FILTROS
# ======================================
st.sidebar.header("Filtros")

# Filtro de data
min_date = df['dtchamado'].min().date()
max_date = df['dtchamado'].max().date()

# Calcular mês atual como padrão
hoje = datetime.now()
primeiro_dia_mes = hoje.replace(day=1).date()
ultimo_dia_mes_real = (hoje.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
ultimo_dia_mes = min(ultimo_dia_mes_real.date(), max_date)  # ✅ Garante que o valor esteja dentro do limite

# Usar mês atual como padrão
data_inicio = st.sidebar.date_input("Data inicial", 
                                    primeiro_dia_mes, 
                                    min_value=min_date, 
                                    max_value=max_date)

data_fim = st.sidebar.date_input("Data final", 
                                 ultimo_dia_mes, 
                                 min_value=min_date, 
                                 max_value=max_date)


# Filtro de equipes
equipes_selecionadas = st.sidebar.multiselect("Selecione as equipes:", 
                                            options=list(EQUIPES.values()), 
                                            default=list(EQUIPES.values()))

# Converter seleções para códigos
codigos_equipes = [k for k, v in EQUIPES.items() if v in equipes_selecionadas]

# Aplicar filtros
df_filtrado = df[
    (df['dtchamado'].dt.date >= data_inicio) & 
    (df['dtchamado'].dt.date <= data_fim) & 
    (df['cdequipe'].isin(codigos_equipes))
]

EQUIPES_POR_OPERADOR = {
    497: "Service Desk", 462: "Service Desk", 122: "Service Desk", 63: "Service Desk",
    206: "Suporte Técnico", 133: "Suporte Técnico", 240: "Suporte Técnico",
    258: "Suporte Técnico", 103: "Suporte Técnico", 229: "Suporte Técnico", 158: "Suporte Técnico"}

# ======================================
# GRÁFICO 1 - Chamados por Equipe/Mês (Versão Simplificada)
# ======================================
st.header("Chamados por Atendido Equipe")

# Mapeamento direto dos códigos de equipe
MAPEAMENTO_EQUIPES = {
    1: "Service Desk",
    3: "Suporte Técnico"
}

if not df_filtrado.empty:
    # Criar cópia do DataFrame
    df_equipes = df_filtrado.copy()
    
    # PASSO 1: Aplicar filtro de equipes
    df_equipes = df_equipes[df_equipes['cdequipe'].isin([1, 3])]
    
    # PASSO 2: Verificar colunas essenciais
    colunas_essenciais = ['dtchamado', 'cdequipe']
    for col in colunas_essenciais:
        if col not in df_equipes.columns:
            st.error(f"Coluna essencial faltante: {col}")
            st.stop()
    
    # PASSO 3: Processar os dados
    df_equipes['mes'] = df_equipes['dtchamado'].dt.strftime('%Y-%m')
    df_equipes['equipe'] = df_equipes['cdequipe'].map(MAPEAMENTO_EQUIPES)
    
    # PASSO 4: Agrupamento
    dados_equipe = df_equipes.groupby(['mes', 'equipe']).size().reset_index(name='total')
    
    # PASSO 5: Criar o gráfico
    grafico1 = alt.Chart(dados_equipe).mark_bar(
        cornerRadius=5,
        size=25
    ).encode(
        x=alt.X('mes:N', title='Mês', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('total:Q', title='Total de Chamados'),
        color=alt.Color('equipe:N', 
                       scale=alt.Scale(range=['#1f77b4', '#ff7f0e']),
                       legend=alt.Legend(title="Equipe")),
        xOffset=alt.XOffset('equipe:N')
    ).properties(
        width=alt.Step(40)
    )

    st.altair_chart(grafico1, use_container_width=True)
    
    # Exibir estatísticas de validação
    st.write(f"Total de chamados: {len(df_equipes)}")

    # ✅ Checkbox para exibir ou ocultar detalhes
    if st.checkbox("Mostrar detalhes de validação"):
        with st.expander("Detalhes de validação"):
            st.write("### Dados processados (amostra)")
            # Exibir somente colunas relevantes
            st.write(df_equipes[['dtchamado', 'cdequipe', 'mes', 'equipe']].head())
            
            st.write("### Valores únicos em cdequipe:")
            st.write(df_equipes['cdequipe'].value_counts())
            
            st.write("### Soma total por mês:")
            st.write(dados_equipe.groupby('mes')['total'].sum().astype(int))

else:
    st.warning("Nenhum dado disponível para o período selecionado")
# ======================================
# GRÁFICO 2 - Chamados Abertos por Operador por Mês
# ======================================
st.header("Chamados Abertos por Operador")

if not df_filtrado.empty:
    # Adicionar coluna de mês/ano formatado
    df_filtrado['mes'] = df_filtrado['dtchamado'].dt.strftime('%Y-%m')
    
    # Mapear código do operador para nome
    df_filtrado['operador'] = df_filtrado['cdusuario'].map(OPERADORES)
    
    # Filtrar apenas operadores válidos (excluir nulos)
    df_operadores = df_filtrado[df_filtrado['cdusuario'].isin(OPERADORES.keys())]
    
    if not df_operadores.empty:
        # Agrupar por mês e operador
        chamados_por_operador = df_operadores.groupby(['mes', 'operador']).size().reset_index(name='total')
        
        # Criar gráfico de barras agrupadas
        grafico2 = alt.Chart(chamados_por_operador).mark_bar(
            cornerRadius=3,
            size=20
        ).encode(
            x=alt.X('mes:N', title='Mês', axis=alt.Axis(labelAngle=0)),
            y=alt.Y('total:Q', title='Chamados Abertos'),
            color=alt.Color('operador:N', title='Operador', 
                           scale=alt.Scale(scheme='category20')),
            tooltip=['mes', 'operador', 'total']
        ).properties(
            width=alt.Step(40)
        )
        st.altair_chart(grafico2, use_container_width=True)
        
        # Tabela detalhada (opcional)
        mostrar_tabela = st.checkbox("Mostrar dados detalhados", key="tabela_operador_mes")
        if mostrar_tabela:
            st.subheader("Detalhamento por Operador e Mês")
            # Formatar tabela com pivot
            tabela_detalhes = chamados_por_operador.pivot(
                index='operador', 
                columns='mes', 
                values='total'
            ).fillna(0).astype(int)
            
            # Adicionar total por operador
            tabela_detalhes['Total'] = tabela_detalhes.sum(axis=1)
            
            # Ordenar pelo total
            tabela_detalhes = tabela_detalhes.sort_values('Total', ascending=False)
            
            st.dataframe(
                tabela_detalhes.style
                    .background_gradient(subset=tabela_detalhes.columns[:-1], cmap='Blues')
                    .background_gradient(subset=['Total'], cmap='Purples'),
                height=500,
                use_container_width=True
            )
    else:
        st.warning("Nenhum chamado encontrado para os operadores selecionados")
else:
    st.warning("Nenhum dado disponível para o período selecionado")

# ======================================
# GRÁFICO 3 - Chamados Atendidos por Operador (SOLUÇÃO DEFINITIVA)
# ======================================
st.header("Chamado Iniciado - Por Operador (Validar dados - inconsistencias entre 2 a 4 chamados)")

if not df_acompanhamentos.empty:
    # 1. Identificar automaticamente a coluna de descrição
    desc_columns = [col for col in df_acompanhamentos.columns 
                   if 'acompanhamento' in col.lower() or 'desc' in col.lower()]
    
    if not desc_columns:
        st.error("Não foi possível encontrar a coluna de descrição de acompanhamentos!")
        st.info("Colunas disponíveis:")
        st.write(df_acompanhamentos.columns.tolist())
        st.stop()
    
    COLUNA_DESCRICAO = desc_columns[0]
    st.info(f"Usando coluna: '{COLUNA_DESCRICAO}' para descrição de acompanhamentos")

    # 2. Verificar se as outras colunas existem
    colunas_necessarias = ['dtacompanhamento', 'cdusuario', 'cdchamado', COLUNA_DESCRICAO]
    colunas_faltantes = [col for col in colunas_necessarias if col not in df_acompanhamentos.columns]
    
    if colunas_faltantes:
        st.error(f"Colunas faltantes: {', '.join(colunas_faltantes)}")
        st.info(f"Colunas disponíveis: {', '.join(df_acompanhamentos.columns)}")
        st.stop()

    # 3. Converter datas se necessário
    if not pd.api.types.is_datetime64_any_dtype(df_acompanhamentos['dtacompanhamento']):
        df_acompanhamentos['dtacompanhamento'] = pd.to_datetime(
            df_acompanhamentos['dtacompanhamento'], errors='coerce')
    
    # 4. Filtro por data e conteúdo da descrição
    df_acomp_filtrado = df_acompanhamentos[
        (df_acompanhamentos['dtacompanhamento'].dt.date >= data_inicio) &
        (df_acompanhamentos['dtacompanhamento'].dt.date <= data_fim) &
        (df_acompanhamentos[COLUNA_DESCRICAO].str.contains('Chamado em atendimento', case=False, na=False))
    ]

    # 5. Contar chamados distintos por operador
    contagem_chamados = (
        df_acomp_filtrado
        .groupby('cdusuario')['cdchamado']
        .nunique()
        .reset_index(name='total_chamados')
        .sort_values('total_chamados', ascending=False)
    )

    # 6. Mapear nomes dos operadores
    contagem_chamados['operador'] = contagem_chamados['cdusuario'].map(OPERADORES)
    
    # 7. Filtrar apenas operadores válidos
    contagem_chamados = contagem_chamados[contagem_chamados['cdusuario'].isin(OPERADORES.keys())]

    # 8. Gráfico de barras
    if not contagem_chamados.empty:
        # Usar Plotly Express para melhor visualização
        try:
            import plotly.express as px
            fig = px.bar(
                contagem_chamados,
                x='operador',
                y='total_chamados',
                title='Chamados Atendidos por Operador',
                labels={'operador': 'Operador', 'total_chamados': 'Chamados Atendidos'},
                color='total_chamados',
                color_continuous_scale='Purples'
            )
            fig.update_layout(
                xaxis_tickangle=-45,
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)
        except:
            # Fallback para gráfico nativo do Streamlit
            st.bar_chart(
                contagem_chamados.set_index('operador')['total_chamados'],
                height=500,
                color='#9467bd'
            )
    else:
        st.warning("Nenhum chamado encontrado com 'Chamado em atendimento' no período!")

    # 9. Tabela detalhada
    mostrar_tabela_acomp = st.checkbox("Mostrar detalhes de chamados por operador", key="tabela_chamados_operador")
    if mostrar_tabela_acomp and not contagem_chamados.empty:
        st.subheader("Detalhamento de Chamados Atendidos")
        
        tabela_acomp = contagem_chamados[['operador', 'total_chamados']].rename(columns={
            'operador': 'Operador',
            'total_chamados': 'Chamados Atendidos'
        })
        
        st.dataframe(
            tabela_acomp.style
                .background_gradient(subset=['Chamados Atendidos'], cmap='Purples')
                .format({'Chamados Atendidos': '{:.0f}'}),
            height=400,
            use_container_width=True
        )

    # 10. Verificação de operadores sem registros
    if not contagem_chamados.empty:
        usuarios_sem_chamados = set(OPERADORES.keys()) - set(contagem_chamados['cdusuario'])
        if usuarios_sem_chamados:
            st.warning(f"Operadores sem chamados atendidos: {', '.join(OPERADORES[id] for id in usuarios_sem_chamados)}")
else:
    st.warning("Dados de acompanhamentos não disponíveis")

# ======================================
# GRÁFICO 4 - Chamados por Meio de Solicitação
# ======================================
st.header("Chamados por tipo de solicitação")

if not df_filtrado.empty:
    mapeamento_origem = {
        1: "Telefone", 18: "Telefone", 5: "Telefone",
        2: "Email", 6: "Email",
        4: "Pessoalmente", 7: "Pessoalmente", 17: "Pessoalmente",
        14: "Web Service", 3: "Web Service", 8: "Web Service", 13: "Web Service", 20: "Web Service",
        15: "Chat", 9: "Chat",
        10: "Operação Monitoramento",
        11: "Oficio",
        12: "URA", 19: "URA"
    }

    df_filtrado['meio_solicitacao'] = df_filtrado['cdorigem'].map(mapeamento_origem)
    contagem_meios = df_filtrado['meio_solicitacao'].value_counts().reset_index()
    contagem_meios.columns = ['Meio de Solicitação', 'Total']
    contagem_meios = contagem_meios.sort_values('Total', ascending=False)

    # Gráfico de Pizza
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

    # Gráfico de Barras
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

    aba1, aba2 = st.tabs(["Gráfico de Pizza", "Gráfico de Barras"])
    with aba1: st.altair_chart(grafico_pizza, use_container_width=True)
    with aba2: st.altair_chart(grafico_barras, use_container_width=True)

    mostrar_tabela_meios = st.checkbox("Mostrar tabela detalhada", key="tabela_meios")
    if mostrar_tabela_meios:
        st.subheader("Detalhamento por Meio de Solicitação")
        tabela_meios = contagem_meios.copy()
        tabela_meios['Percentual'] = (tabela_meios['Total'] / tabela_meios['Total'].sum() * 100).round(2)
        st.dataframe(
            tabela_meios.style
                .background_gradient(subset=['Total'], cmap='Blues')
                .format({'Total': '{:.0f}', 'Percentual': '{:.2f}%'}),
            height=400,
            use_container_width=True
        )
else:
    st.warning("Nenhum dado disponível para o período selecionado")

# ======================================
# GRÁFICO 5 - Acompanhamentos Tipo 22.0 por Operador ok
# ======================================
st.header("Acompanhamentos por Operador")

if not df_acompanhamentos.empty:
    todos_operadores = pd.DataFrame({
        'cdusuario': list(OPERADORES.keys()),
        'operador': [OPERADORES[id] for id in OPERADORES.keys()]
    })

    df_acomp_tipo22 = df_acompanhamentos[
        (df_acompanhamentos['dtacompanhamento'].dt.date >= data_inicio) &
        (df_acompanhamentos['dtacompanhamento'].dt.date <= data_fim) &
        (df_acompanhamentos['cdtipoacompanhamento'].isin([20.0, 22.0]))
    ]

    contagem_acomp = df_acomp_tipo22.groupby('cdusuario').size().reset_index(name='total')
    dados_grafico5 = todos_operadores.merge(
        contagem_acomp, 
        on='cdusuario', 
        how='left'
    ).fillna(0).sort_values('total', ascending=False)

    if not dados_grafico5.empty:
        grafico_barras = alt.Chart(dados_grafico5).mark_bar(
            color='#17becf',
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

        mostrar_tabela = st.checkbox("Mostrar tabela detalhada", key="tabela_grafico5")
        if mostrar_tabela:
            st.subheader("Detalhamento por Operador")
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
            
            st.subheader("Estatísticas")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Geral", total_geral)
            col2.metric("Média por Operador", f"{total_geral / len(dados_grafico5):.1f}")
            top_operador = dados_grafico5.iloc[0]
            col3.metric("Operador com Mais Acompanhamentos", 
                       f"{top_operador['operador']} ({top_operador['total']})")

        operadores_sem = dados_grafico5[dados_grafico5['total'] == 0]
        if not operadores_sem.empty:
            st.warning(
                "Operadores sem acompanhamentos tipo 22.0: " +
                ", ".join(operadores_sem['operador'].tolist())
            )
    else:
        st.warning("Nenhum acompanhamento tipo 22.0 encontrado no período!")
else:
    st.warning("Dados de acompanhamentos não disponíveis")

# ======================================
# GRÁFICO 6 - Chamados Finalizados por Operador
# ======================================
st.header("Chamados Finalizados por Operador")

if not df_filtrado.empty:
    df_finalizados = df_filtrado[df_filtrado['cdsituacao'] == 7.0]
    
    if not df_finalizados.empty:
        contagem_finalizados = df_finalizados['cdresponsavel'].value_counts().reset_index()
        contagem_finalizados.columns = ['cdresponsavel', 'total']
        contagem_finalizados['operador'] = contagem_finalizados['cdresponsavel'].map(OPERADORES)
        contagem_finalizados['equipe'] = contagem_finalizados['cdresponsavel'].map(EQUIPES_POR_OPERADOR)

        todos_operadores = pd.DataFrame({
            'cdresponsavel': list(OPERADORES.keys()),
            'operador': [OPERADORES[id] for id in OPERADORES.keys()],
            'equipe': [EQUIPES_POR_OPERADOR[id] for id in OPERADORES.keys()]
        })

        dados_grafico6 = todos_operadores.merge(
            contagem_finalizados[['cdresponsavel', 'total']], 
            on='cdresponsavel', 
            how='left'
        ).fillna(0).sort_values('total', ascending=False)

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

        mostrar_tabela_finalizados = st.checkbox("Mostrar tabela detalhada", key="tabela_finalizados")
        if mostrar_tabela_finalizados:
            st.subheader("Detalhamento de Chamados Finalizados")
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
            
            st.subheader("Estatísticas")
            col1, col2 = st.columns(2)
            total_geral = tabela_finalizados['Chamados Finalizados'].sum()
            col1.metric("Total de Chamados Finalizados", total_geral)
            col2.metric("Operador com Mais Finalizações", 
                       f"{tabela_finalizados.iloc[0]['Operador']} ({tabela_finalizados.iloc[0]['Chamados Finalizados']})")

        operadores_sem_finalizados = dados_grafico6[dados_grafico6['total'] == 0]
        if not operadores_sem_finalizados.empty:
            st.warning(
                "Operadores sem chamados finalizados: " +
                ", ".join(operadores_sem_finalizados['operador'].tolist())
            )
    else:
        st.warning("Nenhum chamado finalizado no período selecionado")
else:
    st.warning("Nenhum dado disponível para o período selecionado")

