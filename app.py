import streamlit as st
import pandas as pd
import numpy as np
import psycopg2
from datetime import datetime
import re
import plotly.express as px
import json

# Set page configuration
st.set_page_config(
    page_title="Premiação Anual dos Ministérios",
    page_icon="🏆",
    layout="wide"
)

# Database credentials
DB_HOST = "145.223.92.209"  # Host Externo
DB_PORT = "5432"  # Porta Externa
DB_NAME = "postgresql"  # Nome do Banco de Dados
DB_USER = "postgres"  # Usuário
DB_PASSWORD = "ZAvbW7c67IKjNF"  # Senha

# Database connection function
def connect_to_db():
    """Connect to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            client_encoding='UTF8'  # Força a codificação UTF-8
        )
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {str(e)}")
        return None

# Initialize the database and tables if they don't exist
def initialize_database():
    """Create the necessary tables if they don't exist."""
    conn = connect_to_db()
    if conn:
        try:
            cur = conn.cursor()
            
            # Check if table exists first
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'avaliacoes_ministerios'
                );
            """)
            
            table_exists = cur.fetchone()[0]
            
            # Only create table if it doesn't exist
            if not table_exists:
                # Create table for ministry evaluations
                cur.execute("""
                    CREATE TABLE avaliacoes_ministerios (
                        id SERIAL PRIMARY KEY,
                        ministerio VARCHAR(100) NOT NULL,
                        nome VARCHAR(255) NOT NULL,
                        email VARCHAR(255) NOT NULL,
                        
                        pontualidade INTEGER CHECK (pontualidade BETWEEN 1 AND 10),
                        assiduidade_celebracoes INTEGER CHECK (assiduidade_celebracoes BETWEEN 1 AND 10),
                        assiduidade_reunioes INTEGER CHECK (assiduidade_reunioes BETWEEN 1 AND 10),
                        trabalho_equipe INTEGER CHECK (trabalho_equipe BETWEEN 1 AND 10),
                        
                        consagracao_semana1 TEXT,
                        consagracao_semana2 TEXT,
                        consagracao_semana3 TEXT,
                        consagracao_semana4 TEXT,
                        consagracao_semana5 TEXT,
                        
                        preparo_tecnico_semana1 TEXT,
                        preparo_tecnico_semana2 TEXT,
                        preparo_tecnico_semana3 TEXT,
                        preparo_tecnico_semana4 TEXT,
                        preparo_tecnico_semana5 TEXT,
                        
                        reunioes_semana1 TEXT,
                        reunioes_semana2 TEXT,
                        reunioes_semana3 TEXT,
                        reunioes_semana4 TEXT,
                        reunioes_semana5 TEXT,
                        
                        treinamentos JSONB,
                        estrategias JSONB,
                        
                        novos_membros INTEGER,
                        membros_qualificacao INTEGER,
                        
                        comentarios TEXT,
                        
                        data_submissao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        mes_referencia VARCHAR(20),
                        ano_referencia INTEGER
                    )
                """)
                st.success("Banco de dados inicializado com sucesso!")
            else:
                # Verificar se precisa alterar a estrutura da tabela para usar JSONB
                try:
                    cur.execute("""
                        ALTER TABLE avaliacoes_ministerios 
                        ALTER COLUMN treinamentos TYPE JSONB USING treinamentos::JSONB,
                        ALTER COLUMN estrategias TYPE JSONB USING estrategias::JSONB;
                    """)
                except Exception as e:
                    # Se houver erro, é provável que a conversão já tenha sido feita
                    pass
            
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Erro ao inicializar o banco de dados: {e}")
            return False
        finally:
            cur.close()
            conn.close()
    return False

# Save form data to database
def save_evaluation(data):
    """Save the evaluation data to the database."""
    conn = connect_to_db()
    if conn:
        try:
            cur = conn.cursor()
            
            # Filtrar apenas os arrays não vazios
            treinamentos_clean = [t for t in data["treinamentos"] if t and t.strip()]
            estrategias_clean = [e for e in data["estrategias"] if e and e.strip()]
            
            # Insert query usando parâmetros diretamente para os arrays
            cur.execute("""
                INSERT INTO avaliacoes_ministerios (
                    ministerio, nome, email,
                    pontualidade, assiduidade_celebracoes, assiduidade_reunioes, trabalho_equipe,
                    consagracao_semana1, consagracao_semana2, consagracao_semana3, consagracao_semana4, consagracao_semana5,
                    preparo_tecnico_semana1, preparo_tecnico_semana2, preparo_tecnico_semana3, preparo_tecnico_semana4, preparo_tecnico_semana5,
                    reunioes_semana1, reunioes_semana2, reunioes_semana3, reunioes_semana4, reunioes_semana5,
                    treinamentos, estrategias,
                    novos_membros, membros_qualificacao,
                    comentarios, mes_referencia, ano_referencia
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s, %s
                )
            """, (
                data["ministerio"], data["nome"], data["email"],
                data["pontualidade"], data["assiduidade_celebracoes"], data["assiduidade_reunioes"], data["trabalho_equipe"],
                data["consagracao_semana1"], data["consagracao_semana2"], data["consagracao_semana3"], data["consagracao_semana4"], data["consagracao_semana5"],
                data["preparo_tecnico_semana1"], data["preparo_tecnico_semana2"], data["preparo_tecnico_semana3"], data["preparo_tecnico_semana4"], data["preparo_tecnico_semana5"],
                data["reunioes_semana1"], data["reunioes_semana2"], data["reunioes_semana3"], data["reunioes_semana4"], data["reunioes_semana5"],
                treinamentos_clean, estrategias_clean,
                data["novos_membros"], data["membros_qualificacao"],
                data["comentarios"], data["mes_referencia"], data["ano_referencia"]
            ))
            
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Erro ao salvar a avaliação: {e}")
            return False
        finally:
            cur.close()
            conn.close()
    return False

# Validate email format
def is_valid_email(email):
    """Check if the email has a valid format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None

# Main app navigation
def main():
    # Initialize database
    initialize_database()
    
    # Sidebar for navigation
    st.sidebar.title("Navegação")
    page = st.sidebar.radio("Ir para:", ["Formulário de Avaliação", "Área da Gestora"])
    
    if page == "Formulário de Avaliação":
        show_evaluation_form()
    else:
        show_admin_area()

# Evaluation form page
def show_evaluation_form():
    st.title("PREMIAÇÃO ANUAL DOS MINISTÉRIOS")
    
    st.markdown("""
    Serão avaliados por **voto**, podendo ficar em: **Primeiro**, **Segundo** ou **Terceiro**. 
    A avaliação será realizada mensalmente pelo **líder** ou **auxiliar** do ministério.
    
    *Preencha os dados com atenção para garantir uma análise precisa.**
    """)
    
    # Inicializar session state para contadores
    if "treinamento_count" not in st.session_state:
        st.session_state.treinamento_count = 1
    if "estrategia_count" not in st.session_state:
        st.session_state.estrategia_count = 1
    
    # Armazenar os dados do formulário no session state
    if "form_data" not in st.session_state:
        st.session_state.form_data = {}
    
    # Formulário principal - começa com as informações gerais até a seção 2
    with st.form("evaluation_form_part1"):
        # Seção 0: Informações Gerais
        st.subheader("Informações Gerais")
        col1, col2 = st.columns(2)
        
        with col1:
            ministerio = st.selectbox(
                "Ministério *",
                ["", "Intercessão", "Introdutores", "MIDAF", "MILAF", "Comunicação", "Técnica"],
                help="Selecione o ministério ao qual você pertence."
            )
            
            nome = st.text_input(
                "Nome do Líder ou Auxiliar *",
                help="Digite seu nome completo."
            )
        
        with col2:
            email = st.text_input(
                "Email *",
                help="Digite seu email para contato."
            )
            
            # Mês e ano de referência
            meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                     "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            mes_atual = datetime.now().month - 1  # Para selecionar o mês atual por padrão (0-indexed)
            
            mes_referencia = st.selectbox(
                "Mês de Referência *",
                meses,
                index=mes_atual,
                help="Selecione o mês ao qual esta avaliação se refere."
            )
            
            ano_atual = datetime.now().year
            ano_referencia = st.selectbox(
                "Ano de Referência *",
                list(range(ano_atual-2, ano_atual+1)),
                index=2,  # Seleciona o ano atual por padrão
                help="Selecione o ano ao qual esta avaliação se refere."
            )
        
        st.markdown("---")
        
        # Seção 1: Requisitos para o Ministério
        st.subheader("Seção 1 - Requisitos para o Ministério")
        st.markdown("""
        **Objetivo:** Avaliar os membros escalados nas celebrações.
        
        **Aviso:** Selecione um número de **1** (Nada comprometido) a **10** (Muito comprometido) para cada requisito, 
        refletindo a qualidade e comprometimento do ministério.
        """)
        
        pontualidade = st.slider("Pontualidade", 1, 10, 5, help="Avalie a pontualidade dos membros.")
        assiduidade_celebracoes = st.slider("Assiduidade nas Celebrações", 1, 10, 5, help="Avalie a assiduidade dos membros nas celebrações.")
        assiduidade_reunioes = st.slider("Assiduidade nas Reuniões do Ministério", 1, 10, 5, help="Avalie a assiduidade dos membros nas reuniões.")
        trabalho_equipe = st.slider("Trabalho em Equipe (cumplicidade, respeito, honra)", 1, 10, 5, help="Avalie o trabalho em equipe.")
        
        st.markdown("---")
        
        # Seção 2: Preparo da Equipe para a Celebração
        st.subheader("Seção 2 - Preparo da Equipe para a Celebração")
        
        # Consagração (Jejum e Oração)
        st.subheader("Consagração (Jejum e Oração)")

        st.markdown("**Primeira Semana**: (Ex.: A equipe realizou jejum na quarta-feira e oração coletiva antes do ensaio.)")
        consagracao_semana1 = st.text_area("", help="Descreva as atividades de jejum e oração realizadas na primeira semana.")

        st.markdown("**Segunda Semana**: (Ex.: Oração individual diária, leitura bíblica em grupo)")
        consagracao_semana2 = st.text_area("", help="Descreva as atividades de jejum e oração realizadas na segunda semana.")

        st.markdown("**Terceira Semana**: (Ex.: Tempo de louvor e adoração juntos)")
        consagracao_semana3 = st.text_area("", help="Descreva as atividades de jejum e oração realizadas na terceira semana.")

        st.markdown("**Quarta Semana**: (Ex.: Vigília de oração, intercessão por necessidades específicas)")
        consagracao_semana4 = st.text_area("", help="Descreva as atividades de jejum e oração realizadas na quarta semana.")

        st.markdown("**Quinta Semana (quando houver)**: (Ex.: Agradecimento e celebração, oração por frutos do trabalho)")
        consagracao_semana5 = st.text_area("", help="Descreva as atividades de jejum e oração realizadas na quinta semana, se houver.")

        # Preparo Técnico (Ensaio, preparo técnico e equipamentos)
        st.subheader("Preparo Técnico (Ensaio, preparo técnico e equipamentos)")

        st.markdown("**Primeira Semana**: (Ex: Estudo da documentação técnica, testes iniciais de equipamentos.)")
        preparo_tecnico_semana1 = st.text_area("", help="Descreva as atividades de preparo técnico realizadas na primeira semana.")

        st.markdown("**Segunda Semana**: (Ex: Desenvolvimento de protótipos, simulações e análises de desempenho.)")
        preparo_tecnico_semana2 = st.text_area("", help="Descreva as atividades de preparo técnico realizadas na segunda semana.")

        st.markdown("**Terceira Semana**: (Ex: Ajustes finais em equipamentos, preparação para testes de campo.)")
        preparo_tecnico_semana3 = st.text_area("", help="Descreva as atividades de preparo técnico realizadas na terceira semana.")

        st.markdown("**Quarta Semana**: (Ex: Realização de testes de campo, coleta e análise de dados.)")
        preparo_tecnico_semana4 = st.text_area("", help="Descreva as atividades de preparo técnico realizadas na quarta semana.")

        st.markdown("**Quinta Semana (quando houver)**: (Ex: Elaboração de relatório técnico, apresentação dos resultados.)")
        preparo_tecnico_semana5 = st.text_area("", help="Descreva as atividades de preparo técnico realizadas na quinta semana, se houver.")

        # Reuniões
        st.subheader("Reuniões")

        st.markdown("**Primeira Semana**: (Ex: Reunião de planejamento inicial, definição de metas e cronograma.)")
        reunioes_semana1 = st.text_area("", help="Descreva as reuniões realizadas na primeira semana.")

        st.markdown("**Segunda Semana**: (Ex: Reunião de acompanhamento do progresso, discussão de desafios e soluções.)")
        reunioes_semana2 = st.text_area("", help="Descreva as reuniões realizadas na segunda semana.")

        st.markdown("**Terceira Semana**: (Ex: Reunião de revisão de testes, ajustes e preparação para apresentação.)")
        reunioes_semana3 = st.text_area("", help="Descreva as reuniões realizadas na terceira semana.")

        st.markdown("**Quarta Semana**: (Ex: Reunião de avaliação dos resultados, feedback e planejamento para próximas etapas.)")
        reunioes_semana4 = st.text_area("", help="Descreva as reuniões realizadas na quarta semana.")

        st.markdown("**Quinta Semana (quando houver)**: (Ex: Reunião de encerramento, celebração das conquistas e aprendizados.)")
        reunioes_semana5 = st.text_area("", help="Descreva as reuniões realizadas na quinta semana, se houver.")
        st.markdown("---")
        # Botão de submissão para a primeira parte
        part1_submitted = st.form_submit_button("Continuar para próxima seção")
        
        if part1_submitted:
            # Salvar dados da parte 1 no session state
            st.session_state.form_data["ministerio"] = ministerio
            st.session_state.form_data["nome"] = nome
            st.session_state.form_data["email"] = email
            st.session_state.form_data["pontualidade"] = pontualidade
            st.session_state.form_data["assiduidade_celebracoes"] = assiduidade_celebracoes
            st.session_state.form_data["assiduidade_reunioes"] = assiduidade_reunioes
            st.session_state.form_data["trabalho_equipe"] = trabalho_equipe
            st.session_state.form_data["consagracao_semana1"] = consagracao_semana1
            st.session_state.form_data["consagracao_semana2"] = consagracao_semana2
            st.session_state.form_data["consagracao_semana3"] = consagracao_semana3
            st.session_state.form_data["consagracao_semana4"] = consagracao_semana4
            st.session_state.form_data["consagracao_semana5"] = consagracao_semana5
            st.session_state.form_data["preparo_tecnico_semana1"] = preparo_tecnico_semana1
            st.session_state.form_data["preparo_tecnico_semana2"] = preparo_tecnico_semana2
            st.session_state.form_data["preparo_tecnico_semana3"] = preparo_tecnico_semana3
            st.session_state.form_data["preparo_tecnico_semana4"] = preparo_tecnico_semana4
            st.session_state.form_data["preparo_tecnico_semana5"] = preparo_tecnico_semana5
            st.session_state.form_data["reunioes_semana1"] = reunioes_semana1
            st.session_state.form_data["reunioes_semana2"] = reunioes_semana2
            st.session_state.form_data["reunioes_semana3"] = reunioes_semana3
            st.session_state.form_data["reunioes_semana4"] = reunioes_semana4
            st.session_state.form_data["reunioes_semana5"] = reunioes_semana5
            st.session_state.form_data["mes_referencia"] = mes_referencia
            st.session_state.form_data["ano_referencia"] = ano_referencia
            st.success("Primeira parte salva! Continue com as próximas seções.")
    
    # Seção 3: Treinamento e Capacitação
    st.markdown("---")
    st.subheader("Seção 3 - Treinamento e Capacitação")
    st.markdown("Relate quais treinamentos e capacitações foram realizados pela equipe do ministério esse mês.")
    
    # Campos para treinamentos
    treinamentos = []
    for i in range(st.session_state.treinamento_count):
        key = f"treinamento_{i}"
        treinamento = st.text_area(
            f"Treinamento/Capacitação {i+1}",
            key=key,
            help="Descreva um treinamento ou capacitação realizado pela equipe."
        )
        treinamentos.append(treinamento)
    
    # Botão para adicionar mais treinamentos (fora do formulário)
    if st.button("Adicionar Mais Treinamentos"):
        st.session_state.treinamento_count += 1
        st.rerun()
    
    # Seção 4: Estratégias para Crescimento
    st.markdown("---")
    st.subheader("Seção 4 - Estratégias para Crescimento")
    st.markdown("Descreva as estratégias implementadas para o crescimento e desenvolvimento do ministério.")
    
    # Campos para estratégias
    estrategias = []
    for i in range(st.session_state.estrategia_count):
        key = f"estrategia_{i}"
        estrategia = st.text_area(
            f"Estratégia {i+1}",
            key=key,
            help="Descreva uma estratégia implementada para o crescimento do ministério."
        )
        estrategias.append(estrategia)
    
    # Botão para adicionar mais estratégias (fora do formulário)
    if st.button("Adicionar Mais Estratégias"):
        st.session_state.estrategia_count += 1
        st.rerun()
    
    # Formulário final - contém as seções 5 e 6 e o botão de envio
    with st.form("evaluation_form_part2"):
        st.markdown("---")
        
        # Seção 5: Novos Membros Qualificados
        st.subheader("Seção 5 - Novos Membros Qualificados")
        
        col1, col2 = st.columns(2)
        
        with col1:
            novos_membros = st.number_input(
                "Total de novos membros incorporados ao ministério",
                min_value=0,
                step=1,
                help="Informe o número total de novos membros incorporados ao ministério."
            )
        
        with col2:
            membros_qualificacao = st.number_input(
                "Total de membros em qualificação",
                min_value=0,
                step=1,
                help="Informe o número total de membros que estão em processo de qualificação."
            )
        
        st.markdown("---")
        
        # Seção 6: Feedback e Sugestões
        st.subheader("Seção 6 - Feedback e Sugestões")
        comentarios = st.text_area(
            "Comentários e Sugestões",
            help="Informe pontos de melhoria, dificuldades encontradas ou elogios."
        )
        
        # Botão final de envio
        final_submitted = st.form_submit_button("Enviar Avaliação")
        
        if final_submitted:
            # Validar e salvar os dados
            if not ministerio or not nome or not email:
                st.error("Por favor, preencha todos os campos obrigatórios marcados com *.")
            elif not is_valid_email(email):
                st.error("Por favor, insira um email válido.")
            else:
                # Prepare data
                data = {
                    "ministerio": ministerio,
                    "nome": nome,
                    "email": email,
                    "pontualidade": pontualidade,
                    "assiduidade_celebracoes": assiduidade_celebracoes,
                    "assiduidade_reunioes": assiduidade_reunioes,
                    "trabalho_equipe": trabalho_equipe,
                    "consagracao_semana1": consagracao_semana1,
                    "consagracao_semana2": consagracao_semana2,
                    "consagracao_semana3": consagracao_semana3,
                    "consagracao_semana4": consagracao_semana4,
                    "consagracao_semana5": consagracao_semana5,
                    "preparo_tecnico_semana1": preparo_tecnico_semana1,
                    "preparo_tecnico_semana2": preparo_tecnico_semana2,
                    "preparo_tecnico_semana3": preparo_tecnico_semana3,
                    "preparo_tecnico_semana4": preparo_tecnico_semana4,
                    "preparo_tecnico_semana5": preparo_tecnico_semana5,
                    "reunioes_semana1": reunioes_semana1,
                    "reunioes_semana2": reunioes_semana2,
                    "reunioes_semana3": reunioes_semana3,
                    "reunioes_semana4": reunioes_semana4,
                    "reunioes_semana5": reunioes_semana5,
                    "treinamentos": [t for t in treinamentos if t],
                    "estrategias": [e for e in estrategias if e],
                    "novos_membros": novos_membros,
                    "membros_qualificacao": membros_qualificacao,
                    "comentarios": comentarios,
                    "mes_referencia": mes_referencia,
                    "ano_referencia": ano_referencia
                }
                
                # Save to database
                if save_evaluation(data):
                    st.success("Avaliação enviada com sucesso! Obrigado pela sua participação.")
                    # Reset form
                    st.session_state.treinamento_count = 1
                    st.session_state.estrategia_count = 1
                    st.rerun()
                else:
                    st.error("Ocorreu um erro ao enviar a avaliação. Por favor, tente novamente.")

# Admin area page
def show_admin_area():
    st.title("Área da Gestora dos Ministérios")
    st.markdown("""
    Esta área é exclusiva para a gestora dos ministérios. Somente acessível mediante autenticação.
    """)
    
    # Authentication
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        with st.form("login_form"):
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            login_button = st.form_submit_button("Entrar")
            
            if login_button:
                if username == "EDILENE SANTOS" and password == "PASTORAEDILENE":
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
    else:
        # Admin content
        show_admin_dashboard()

# Admin dashboard with analytics
def show_admin_dashboard():
    st.subheader("Análise Geral dos Ministérios")
    
    # Add logout button in the sidebar
    if st.sidebar.button("Sair"):
        st.session_state.admin_authenticated = False
        st.rerun()
    
    # Date filters
    col1, col2 = st.columns(2)
    
    with col1:
        meses = ["Todos", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        mes_filtro = st.selectbox("Filtrar por Mês", meses)
    
    with col2:
        ano_atual = datetime.now().year
        anos = ["Todos"] + [str(year) for year in range(ano_atual-2, ano_atual+1)]
        ano_filtro = st.selectbox("Filtrar por Ano", anos)
    
    # Get data from the database
    conn = connect_to_db()
    if conn:
        try:
            # Build query with filters
            query = "SELECT * FROM avaliacoes_ministerios"
            params = []
            
            conditions = []
            if mes_filtro != "Todos":
                conditions.append("mes_referencia = %s")
                params.append(mes_filtro)
                
            if ano_filtro != "Todos":
                conditions.append("ano_referencia = %s")
                params.append(int(ano_filtro))
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            df = pd.read_sql_query(query, conn, params=params)
            
            if df.empty:
                st.warning("Não há dados disponíveis para o período selecionado.")
            else:
                # Calculate average scores for each ministry
                ministry_scores = df.groupby('ministerio')[
                    ['pontualidade', 'assiduidade_celebracoes', 'assiduidade_reunioes', 'trabalho_equipe']
                ].mean()
                
                # Calculate total score
                ministry_scores['pontuacao_total'] = ministry_scores.sum(axis=1)
                
                # Sort by total score
                ministry_scores = ministry_scores.sort_values('pontuacao_total', ascending=False)
                
                # Display ranking
                st.subheader("Classificação Geral dos Ministérios")
                
                # Creating a better visualization for the ranking
                ranking_df = pd.DataFrame({
                    'Colocação': range(1, len(ministry_scores) + 1),
                    'Ministério': ministry_scores.index,
                    'Pontuação Total': ministry_scores['pontuacao_total'].round(2)
                })
                
                # Highlight top 3
                def highlight_top_3(row):
                    if row['Colocação'] == 1:
                        return ['background-color: gold'] * len(row)
                    elif row['Colocação'] == 2:
                        return ['background-color: silver'] * len(row)
                    elif row['Colocação'] == 3:
                        return ['background-color: #cd7f32'] * len(row)  # bronze
                    return [''] * len(row)
                
                st.dataframe(ranking_df.style.apply(highlight_top_3, axis=1), width=600)
                
                # Visualizations
                st.subheader("Gráficos Gerais")
                
                # Overall comparison chart
                fig = px.bar(
                    ministry_scores.reset_index(), 
                    x='ministerio', 
                    y='pontuacao_total',
                    title="Pontuação Total por Ministério",
                    labels={'ministerio': 'Ministério', 'pontuacao_total': 'Pontuação Total'},
                    color='pontuacao_total',
                    color_continuous_scale='viridis'
                )
                st.plotly_chart(fig)
                
                # Detailed view for selected ministry
                st.subheader("Análise Detalhada por Ministério")
                selected_ministry = st.selectbox(
                    "Selecione um Ministério para Análise Detalhada",
                    ministry_scores.index.tolist()
                )
                
                # Filter data for selected ministry
                ministry_data = df[df['ministerio'] == selected_ministry]
                
                if not ministry_data.empty:
                    st.subheader(f"Análise Detalhada: {selected_ministry}")
                    
                    # Metrics overview
                    col1, col2, col3, col4 = st.columns(4)
                    
                    col1.metric(
                        "Pontualidade", 
                        f"{ministry_data['pontualidade'].mean():.2f}/10"
                    )
                    
                    col2.metric(
                        "Assiduidade nas Celebrações", 
                        f"{ministry_data['assiduidade_celebracoes'].mean():.2f}/10"
                    )
                    
                    col3.metric(
                        "Assiduidade nas Reuniões", 
                        f"{ministry_data['assiduidade_reunioes'].mean():.2f}/10"
                    )
                    
                    col4.metric(
                        "Trabalho em Equipe", 
                        f"{ministry_data['trabalho_equipe'].mean():.2f}/10"
                    )
                    
                    # Radar chart for requirements
                    categories = ['Pontualidade', 'Assiduidade Celebrações', 
                                 'Assiduidade Reuniões', 'Trabalho em Equipe']
                    
                    values = [
                        ministry_data['pontualidade'].mean(),
                        ministry_data['assiduidade_celebracoes'].mean(),
                        ministry_data['assiduidade_reunioes'].mean(),
                        ministry_data['trabalho_equipe'].mean()
                    ]
                    
                    fig = px.line_polar(
                        r=values,
                        theta=categories,
                        line_close=True,
                        range_r=[0, 10],
                        title=f"Perfil de Requisitos: {selected_ministry}"
                    )
                    st.plotly_chart(fig)
                    
                    # New members statistics
                    st.subheader("Estatísticas de Membros")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        total_new_members = ministry_data['novos_membros'].sum()
                        st.metric(
                            "Total de Novos Membros", 
                            total_new_members
                        )
                    
                    with col2:
                        total_qualifying_members = ministry_data['membros_qualificacao'].sum()
                        st.metric(
                            "Total de Membros em Qualificação", 
                            total_qualifying_members
                        )
                    
                    # Exibir detalhes da Seção 2, 3 e 4 para o ministério selecionado
                    st.subheader("Informações Detalhadas")
                    
                    # Obter a entrada mais recente para o ministério selecionado
                    latest_entry = ministry_data.sort_values('data_submissao', ascending=False).iloc[0]
                    
                    # Criar abas para cada seção
                    tabs = st.tabs(["Preparo da Equipe", "Treinamentos", "Estratégias", "Comentários"])
                    
                    # Seção 2: Preparo da Equipe para a Celebração
                    with tabs[0]:
                        st.subheader("Seção 2 - Preparo da Equipe para a Celebração")
                        
                        # Consagração (Jejum e Oração)
                        st.markdown("### Consagração (Jejum e Oração)")
                        
                        if pd.notna(latest_entry['consagracao_semana1']) and latest_entry['consagracao_semana1']:
                            st.markdown(f"**Primeira Semana:**")
                            st.write(latest_entry['consagracao_semana1'])
                        
                        if pd.notna(latest_entry['consagracao_semana2']) and latest_entry['consagracao_semana2']:
                            st.markdown(f"**Segunda Semana:**")
                            st.write(latest_entry['consagracao_semana2'])
                        
                        if pd.notna(latest_entry['consagracao_semana3']) and latest_entry['consagracao_semana3']:
                            st.markdown(f"**Terceira Semana:**")
                            st.write(latest_entry['consagracao_semana3'])
                        
                        if pd.notna(latest_entry['consagracao_semana4']) and latest_entry['consagracao_semana4']:
                            st.markdown(f"**Quarta Semana:**")
                            st.write(latest_entry['consagracao_semana4'])
                        
                        if pd.notna(latest_entry['consagracao_semana5']) and latest_entry['consagracao_semana5']:
                            st.markdown(f"**Quinta Semana:**")
                            st.write(latest_entry['consagracao_semana5'])
                        
                        # Preparo Técnico (Ensaio, preparo técnico e equipamentos)
                        st.markdown("### Preparo Técnico (Ensaio, preparo técnico e equipamentos)")
                        
                        if pd.notna(latest_entry['preparo_tecnico_semana1']) and latest_entry['preparo_tecnico_semana1']:
                            st.markdown(f"**Primeira Semana:**")
                            st.write(latest_entry['preparo_tecnico_semana1'])
                        
                        if pd.notna(latest_entry['preparo_tecnico_semana2']) and latest_entry['preparo_tecnico_semana2']:
                            st.markdown(f"**Segunda Semana:**")
                            st.write(latest_entry['preparo_tecnico_semana2'])
                        
                        if pd.notna(latest_entry['preparo_tecnico_semana3']) and latest_entry['preparo_tecnico_semana3']:
                            st.markdown(f"**Terceira Semana:**")
                            st.write(latest_entry['preparo_tecnico_semana3'])
                        
                        if pd.notna(latest_entry['preparo_tecnico_semana4']) and latest_entry['preparo_tecnico_semana4']:
                            st.markdown(f"**Quarta Semana:**")
                            st.write(latest_entry['preparo_tecnico_semana4'])
                        
                        if pd.notna(latest_entry['preparo_tecnico_semana5']) and latest_entry['preparo_tecnico_semana5']:
                            st.markdown(f"**Quinta Semana:**")
                            st.write(latest_entry['preparo_tecnico_semana5'])
                        
                        # Reuniões
                        st.markdown("### Reuniões")
                        
                        if pd.notna(latest_entry['reunioes_semana1']) and latest_entry['reunioes_semana1']:
                            st.markdown(f"**Primeira Semana:**")
                            st.write(latest_entry['reunioes_semana1'])
                        
                        if pd.notna(latest_entry['reunioes_semana2']) and latest_entry['reunioes_semana2']:
                            st.markdown(f"**Segunda Semana:**")
                            st.write(latest_entry['reunioes_semana2'])
                        
                        if pd.notna(latest_entry['reunioes_semana3']) and latest_entry['reunioes_semana3']:
                            st.markdown(f"**Terceira Semana:**")
                            st.write(latest_entry['reunioes_semana3'])
                        
                        if pd.notna(latest_entry['reunioes_semana4']) and latest_entry['reunioes_semana4']:
                            st.markdown(f"**Quarta Semana:**")
                            st.write(latest_entry['reunioes_semana4'])
                        
                        if pd.notna(latest_entry['reunioes_semana5']) and latest_entry['reunioes_semana5']:
                            st.markdown(f"**Quinta Semana:**")
                            st.write(latest_entry['reunioes_semana5'])
                    
                    # Seção 3: Treinamento e Capacitação
                    with tabs[1]:
                        st.subheader("Seção 3 - Treinamento e Capacitação")
                        
                        # Verificar o tipo de dados e processar de acordo
                        treinamentos_data = latest_entry['treinamentos']
                        
                        # Tentar interpretar como JSON se for string
                        if isinstance(treinamentos_data, str):
                            try:
                                treinamentos_list = json.loads(treinamentos_data)
                            except json.JSONDecodeError:
                                # Se falhar como JSON, verificar se é array PostgreSQL
                                if treinamentos_data.startswith('{') and treinamentos_data.endswith('}'):
                                    # Remover chaves e dividir por vírgulas
                                    treinamentos_raw = treinamentos_data[1:-1]
                                    if treinamentos_raw:  # Verificar se não está vazio
                                        # Dividir por vírgulas e tratar strings com aspas
                                        import re
                                        treinamentos_list = re.findall(r'"([^"]*)"', treinamentos_raw)
                                    else:
                                        treinamentos_list = []
                                else:
                                    treinamentos_list = []
                        elif isinstance(treinamentos_data, list):
                            # Já é uma lista
                            treinamentos_list = treinamentos_data
                        else:
                            treinamentos_list = []
                        
                        if treinamentos_list and len(treinamentos_list) > 0:
                            for i, treinamento in enumerate(treinamentos_list):
                                if treinamento:  # Verifica se não está vazio
                                    st.markdown(f"**Treinamento/Capacitação {i+1}:**")
                                    st.write(treinamento)
                                    st.markdown("---")
                        else:
                            st.info("Não foram registrados treinamentos ou capacitações.")
                    
                    # Seção 4: Estratégias para Crescimento
                    with tabs[2]:
                        st.subheader("Seção 4 - Estratégias para Crescimento")
                        
                        # Verificar o tipo de dados e processar de acordo
                        estrategias_data = latest_entry['estrategias']
                        
                        # Tentar interpretar como JSON se for string
                        if isinstance(estrategias_data, str):
                            try:
                                estrategias_list = json.loads(estrategias_data)
                            except json.JSONDecodeError:
                                # Se falhar como JSON, verificar se é array PostgreSQL
                                if estrategias_data.startswith('{') and estrategias_data.endswith('}'):
                                    # Remover chaves e dividir por vírgulas
                                    estrategias_raw = estrategias_data[1:-1]
                                    if estrategias_raw:  # Verificar se não está vazio
                                        # Dividir por vírgulas e tratar strings com aspas
                                        import re
                                        estrategias_list = re.findall(r'"([^"]*)"', estrategias_raw)
                                    else:
                                        estrategias_list = []
                                else:
                                    estrategias_list = []
                        elif isinstance(estrategias_data, list):
                            # Já é uma lista
                            estrategias_list = estrategias_data
                        else:
                            estrategias_list = []
                        
                        if estrategias_list and len(estrategias_list) > 0:
                            for i, estrategia in enumerate(estrategias_list):
                                if estrategia:  # Verifica se não está vazio
                                    st.markdown(f"**Estratégia {i+1}:**")
                                    st.write(estrategia)
                                    st.markdown("---")
                        else:
                            st.info("Não foram registradas estratégias para crescimento.")
                    
                    # Aba de comentários
                    with tabs[3]:
                        st.subheader("Comentários Recentes")
                        
                        recent_comments = ministry_data[
                            ['data_submissao', 'nome', 'comentarios']
                        ].sort_values('data_submissao', ascending=False).head(5)
                        
                        for _, row in recent_comments.iterrows():
                            if pd.notna(row['comentarios']) and row['comentarios'].strip():
                                st.markdown(f"""
                                **Data:** {row['data_submissao'].strftime('%d/%m/%Y')}  
                                **Nome:** {row['nome']}
                                
                                  
                                **Comentário:** {row['comentarios']}
                                ---
                                """)
                        
                        if recent_comments.empty or not any(pd.notna(row['comentarios']) for _, row in recent_comments.iterrows()):
                            st.info("Não há comentários registrados.")
                    
                    # Adicionar seletor de submissões anteriores
                    if len(ministry_data) > 1:
                        st.subheader("Histórico de Submissões")
                        
                        submissions_df = ministry_data[['data_submissao', 'nome', 'mes_referencia', 'ano_referencia']]
                        submissions_df['data_formatada'] = submissions_df['data_submissao'].dt.strftime('%d/%m/%Y %H:%M')
                        submissions_df = submissions_df.sort_values('data_submissao', ascending=False)
                        
                        st.dataframe(
                            submissions_df[['data_formatada', 'nome', 'mes_referencia', 'ano_referencia']].rename(
                                columns={
                                    'data_formatada': 'Data de Submissão',
                                    'nome': 'Nome',
                                    'mes_referencia': 'Mês',
                                    'ano_referencia': 'Ano'
                                }
                            ),
                            width=800
                        )
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
        finally:
            conn.close()
    else:
        st.error("Não foi possível conectar ao banco de dados.")

# Run the app
if __name__ == "__main__":
    main() 
