import streamlit as st
import pandas as pd
import numpy as np
import psycopg2
from datetime import datetime
import re
import plotly.express as px
import json
import os

# Import configuration
try:
    from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, MINISTRY_LEADERS, ADMIN_USERNAME, ADMIN_PASSWORD
except ImportError:
    st.error("Configuration file not found. Please make sure config.py exists with the required variables.")
    # Default values for development (should be empty or placeholders in production)
    DB_HOST = "localhost"
    DB_PORT = "5432"
    DB_NAME = "postgres"
    DB_USER = "postgres"
    DB_PASSWORD = "postgres"
    MINISTRY_LEADERS = {}
    ADMIN_USERNAME = ""
    ADMIN_PASSWORD = ""

# Set page configuration
st.set_page_config(
    page_title="Premiação Anual dos Ministérios",
    page_icon="🏆",
    layout="wide"
)

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
                        
                        nomes_novos_membros TEXT,
                        nomes_membros_qualificacao TEXT,
                        
                        comentarios TEXT,
                        
                        data_submissao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        mes_referencia VARCHAR(20),
                        ano_referencia INTEGER,
                        semana_referencia INTEGER
                    )
                """)
                st.success("Banco de dados inicializado com sucesso!")
            else:
                # Verificar se a coluna semana_referencia existe
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'avaliacoes_ministerios' AND column_name = 'semana_referencia'
                    );
                """)
                semana_column_exists = cur.fetchone()[0]
                
                # Adicionar a coluna se não existir
                if not semana_column_exists:
                    cur.execute("""
                        ALTER TABLE avaliacoes_ministerios 
                        ADD COLUMN semana_referencia INTEGER;
                    """)
                
                # Verificar se as colunas para nomes de membros existem
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'avaliacoes_ministerios' AND column_name = 'nomes_novos_membros'
                    );
                """)
                novos_membros_column_exists = cur.fetchone()[0]
                
                # Adicionar as colunas se não existirem
                if not novos_membros_column_exists:
                    cur.execute("""
                        ALTER TABLE avaliacoes_ministerios 
                        ADD COLUMN nomes_novos_membros TEXT,
                        ADD COLUMN nomes_membros_qualificacao TEXT;
                    """)
                
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
            
            # Converter arrays para formato JSON
            treinamentos_json = json.dumps(treinamentos_clean)
            estrategias_json = json.dumps(estrategias_clean)
            
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
                    nomes_novos_membros, nomes_membros_qualificacao,
                    comentarios, mes_referencia, ano_referencia, semana_referencia
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                data["ministerio"], data["nome"], data["email"],
                data["pontualidade"], data["assiduidade_celebracoes"], data["assiduidade_reunioes"], data["trabalho_equipe"],
                data["consagracao_semana1"], data["consagracao_semana2"], data["consagracao_semana3"], data["consagracao_semana4"], data["consagracao_semana5"],
                data["preparo_tecnico_semana1"], data["preparo_tecnico_semana2"], data["preparo_tecnico_semana3"], data["preparo_tecnico_semana4"], data["preparo_tecnico_semana5"],
                data["reunioes_semana1"], data["reunioes_semana2"], data["reunioes_semana3"], data["reunioes_semana4"], data["reunioes_semana5"],
                treinamentos_json, estrategias_json,
                data["novos_membros"], data["membros_qualificacao"],
                data["nomes_novos_membros"], data["nomes_membros_qualificacao"],
                data["comentarios"], data["mes_referencia"], data["ano_referencia"], data["semana_referencia"]
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
    
    # Initialize session state for leader authentication
    if "leader_authenticated" not in st.session_state:
        st.session_state.leader_authenticated = False
    if "current_ministry" not in st.session_state:
        st.session_state.current_ministry = None
    
    # Sidebar for navigation
    st.sidebar.title("Navegação")
    page = st.sidebar.radio("Ir para:", ["Formulário de Avaliação", "Área da Gestora"])
    
    if page == "Formulário de Avaliação":
        # Check if leader is authenticated
        if st.session_state.leader_authenticated:
            show_evaluation_form()
        else:
            show_leader_login()
    else:
        show_admin_area()

# Leader login page
def show_leader_login():
    st.title("Login de Líder de Ministério")
    
    st.markdown("""
    Por favor, faça login para acessar o formulário de avaliação.
    """)
    
    with st.form("leader_login_form"):
        # Create a dropdown with ministry options
        ministerio = st.selectbox(
            "Ministério",
            list(MINISTRY_LEADERS.keys()),
            help="Selecione o seu ministério."
        )
        
        # Password field with a hint
        st.markdown("**Dica**: A senha é o nome do líder do ministério com a primeira letra maiúscula.")
        password = st.text_input("Senha", type="password")
        
        login_button = st.form_submit_button("Entrar")
        
        if login_button:
            # Check if the password matches the leader's name
            if password == MINISTRY_LEADERS[ministerio]:
                st.session_state.leader_authenticated = True
                st.session_state.current_ministry = ministerio
                st.success(f"Login bem-sucedido como líder do ministério {ministerio}!")
                st.rerun()
            else:
                st.error("Senha incorreta. Por favor, tente novamente.")

# Evaluation form page
def show_evaluation_form():
    st.title("PREMIAÇÃO ANUAL DOS MINISTÉRIOS")
    
    # Show who is logged in
    st.info(f"Logado como líder do ministério: {st.session_state.current_ministry}")
    
    # Logout button
    if st.button("Sair"):
        st.session_state.leader_authenticated = False
        st.session_state.current_ministry = None
        st.rerun()
    
    st.markdown("""
    Serão avaliados, podendo ficar em: **Primeiro**, **Segundo** ou **Terceiro**. 
    A avaliação será realizada **semanalmente** pelo **líder** ou **auxiliar** do ministério.
    
    *Preencha os dados com atenção para garantir uma análise precisa.*
    """)
    
    # Initialize all session state variables
    if "treinamento_count" not in st.session_state:
        st.session_state.treinamento_count = 1
    if "estrategia_count" not in st.session_state:
        st.session_state.estrategia_count = 1
    if "semana_atual" not in st.session_state:
        st.session_state.semana_atual = 1
    if "novos_membros_lista" not in st.session_state:
        st.session_state.novos_membros_lista = []
    if "membros_qualificacao_lista" not in st.session_state:
        st.session_state.membros_qualificacao_lista = []
    if "form_data" not in st.session_state:
        st.session_state.form_data = {}
    
    # SECTION: Basic Information - OUTSIDE FORM
    st.subheader("Informações Gerais")
    col1, col2 = st.columns(2)
    
    with col1:
        # Display the ministry from login (disabled)
        ministerio = st.selectbox(
            "Ministério *",
            [st.session_state.current_ministry],
            disabled=True,
            help="Ministério selecionado no login."
        )
    
    with col2:
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
    
    # Dropdown de semana FORA do formulário para permitir atualizações imediatas
    semana_referencia = st.selectbox(
        "Semana de Referência *",
        list(range(1, 6)),  # 5 semanas possíveis no mês
        key="semana_selecionada",
        help="Selecione a semana do mês à qual esta avaliação se refere."
    )
    
    # Atualiza a semana no session state quando alterada
    st.session_state.semana_atual = semana_referencia
    
    # Define os labels das semanas
    semana_label = {
        1: "Primeira Semana",
        2: "Segunda Semana",
        3: "Terceira Semana",
        4: "Quarta Semana",
        5: "Quinta Semana"
    }
    
    # Exemplos para cada tipo de seção
    exemplo_consagracao = {
        1: "(Ex.: A equipe realizou jejum na quarta-feira e oração coletiva antes do ensaio.)",
        2: "(Ex.: Oração individual diária, leitura bíblica em grupo)",
        3: "(Ex.: Tempo de louvor e adoração juntos)",
        4: "(Ex.: Vigília de oração, intercessão por necessidades específicas)",
        5: "(Ex.: Agradecimento e celebração, oração por frutos do trabalho)"
    }
    
    exemplo_preparo = {
        1: "(Ex: Estudo da documentação técnica, testes iniciais de equipamentos.)",
        2: "(Ex: Desenvolvimento de protótipos, simulações e análises de desempenho.)",
        3: "(Ex: Ajustes finais em equipamentos, preparação para testes de campo.)",
        4: "(Ex: Realização de testes de campo, coleta e análise de dados.)",
        5: "(Ex: Elaboração de relatório técnico, apresentação dos resultados.)"
    }
    
    exemplo_reunioes = {
        1: "(Ex: Reunião de planejamento inicial, definição de metas e cronograma.)",
        2: "(Ex: Reunião de acompanhamento do progresso, discussão de desafios e soluções.)",
        3: "(Ex: Reunião de revisão de testes, ajustes e preparação para apresentação.)",
        4: "(Ex: Reunião de avaliação dos resultados, feedback e planejamento para próximas etapas.)",
        5: "(Ex: Reunião de encerramento, avaliação final e definição de próximos passos.)"
    }
    
    # SECTION: FORM 1 - Personal info and weekly activities
    st.markdown("---")
    with st.form("form_part1"):
        # Informações pessoais
        st.subheader("Informações do Responsável")
        nome = st.text_input(
            "Nome de quem está preenchendo *",
            help="Digite o nome completo de quem está preenchendo este formulário."
        )
        
        email = st.text_input(
            "Email *",
            help="Digite seu email para contato."
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
        
        # Mostrar informações sobre a semana atual
        st.info(f"Preenchendo informações para: {semana_label[st.session_state.semana_atual]}")
        
        # Consagração (Jejum e Oração)
        st.subheader("Consagração (Jejum e Oração)")
        
        # Inicializar os campos de todas as semanas vazios
        consagracao_semana1 = consagracao_semana2 = consagracao_semana3 = consagracao_semana4 = consagracao_semana5 = ""
        
        # Mostrar apenas o campo da semana selecionada
        st.markdown(f"**{semana_label[st.session_state.semana_atual]}**: {exemplo_consagracao[st.session_state.semana_atual]}")
        if st.session_state.semana_atual == 1:
            consagracao_semana1 = st.text_area("Descrição da Consagração", key="consagracao1", help=f"Descreva as atividades de jejum e oração realizadas na {semana_label[st.session_state.semana_atual].lower()}.")
        elif st.session_state.semana_atual == 2:
            consagracao_semana2 = st.text_area("Descrição da Consagração", key="consagracao2", help=f"Descreva as atividades de jejum e oração realizadas na {semana_label[st.session_state.semana_atual].lower()}.")
        elif st.session_state.semana_atual == 3:
            consagracao_semana3 = st.text_area("Descrição da Consagração", key="consagracao3", help=f"Descreva as atividades de jejum e oração realizadas na {semana_label[st.session_state.semana_atual].lower()}.")
        elif st.session_state.semana_atual == 4:
            consagracao_semana4 = st.text_area("Descrição da Consagração", key="consagracao4", help=f"Descreva as atividades de jejum e oração realizadas na {semana_label[st.session_state.semana_atual].lower()}.")
        elif st.session_state.semana_atual == 5:
            consagracao_semana5 = st.text_area("Descrição da Consagração", key="consagracao5", help=f"Descreva as atividades de jejum e oração realizadas na {semana_label[st.session_state.semana_atual].lower()}.")

        # Preparo Técnico (Ensaio, preparo técnico e equipamentos)
        st.subheader("Preparo Técnico (Ensaio, preparo técnico e equipamentos)")

        # Inicializar os campos de todas as semanas vazios
        preparo_tecnico_semana1 = preparo_tecnico_semana2 = preparo_tecnico_semana3 = preparo_tecnico_semana4 = preparo_tecnico_semana5 = ""
        
        # Mostrar apenas o campo da semana selecionada
        st.markdown(f"**{semana_label[st.session_state.semana_atual]}**: {exemplo_preparo[st.session_state.semana_atual]}")
        if st.session_state.semana_atual == 1:
            preparo_tecnico_semana1 = st.text_area("Descrição do Preparo Técnico", key="preparo1", help=f"Descreva as atividades de preparo técnico realizadas na {semana_label[st.session_state.semana_atual].lower()}.")
        elif st.session_state.semana_atual == 2:
            preparo_tecnico_semana2 = st.text_area("Descrição do Preparo Técnico", key="preparo2", help=f"Descreva as atividades de preparo técnico realizadas na {semana_label[st.session_state.semana_atual].lower()}.")
        elif st.session_state.semana_atual == 3:
            preparo_tecnico_semana3 = st.text_area("Descrição do Preparo Técnico", key="preparo3", help=f"Descreva as atividades de preparo técnico realizadas na {semana_label[st.session_state.semana_atual].lower()}.")
        elif st.session_state.semana_atual == 4:
            preparo_tecnico_semana4 = st.text_area("Descrição do Preparo Técnico", key="preparo4", help=f"Descreva as atividades de preparo técnico realizadas na {semana_label[st.session_state.semana_atual].lower()}.")
        elif st.session_state.semana_atual == 5:
            preparo_tecnico_semana5 = st.text_area("Descrição do Preparo Técnico", key="preparo5", help=f"Descreva as atividades de preparo técnico realizadas na {semana_label[st.session_state.semana_atual].lower()}.")

        # Reuniões
        st.subheader("Reuniões")
        
        # Inicializar os campos de todas as semanas vazios
        reunioes_semana1 = reunioes_semana2 = reunioes_semana3 = reunioes_semana4 = reunioes_semana5 = ""
        
        # Mostrar apenas o campo da semana selecionada
        st.markdown(f"**{semana_label[st.session_state.semana_atual]}**: {exemplo_reunioes[st.session_state.semana_atual]}")
        if st.session_state.semana_atual == 1:
            reunioes_semana1 = st.text_area("Descrição das Reuniões", key="reunioes1", help=f"Descreva as reuniões realizadas na {semana_label[st.session_state.semana_atual].lower()}.")
        elif st.session_state.semana_atual == 2:
            reunioes_semana2 = st.text_area("Descrição das Reuniões", key="reunioes2", help=f"Descreva as reuniões realizadas na {semana_label[st.session_state.semana_atual].lower()}.")
        elif st.session_state.semana_atual == 3:
            reunioes_semana3 = st.text_area("Descrição das Reuniões", key="reunioes3", help=f"Descreva as reuniões realizadas na {semana_label[st.session_state.semana_atual].lower()}.")
        elif st.session_state.semana_atual == 4:
            reunioes_semana4 = st.text_area("Descrição das Reuniões", key="reunioes4", help=f"Descreva as reuniões realizadas na {semana_label[st.session_state.semana_atual].lower()}.")
        elif st.session_state.semana_atual == 5:
            reunioes_semana5 = st.text_area("Descrição das Reuniões", key="reunioes5", help=f"Descreva as reuniões realizadas na {semana_label[st.session_state.semana_atual].lower()}.")
        
        # Form submit button
        form1_submitted = st.form_submit_button("Salvar Informações Semanais")
        
        if form1_submitted:
            # Save form data to session state
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
            st.session_state.form_data["semana_referencia"] = st.session_state.semana_atual
            st.success("Informações semanais salvas com sucesso! Continue preenchendo as próximas seções.")
    
    # SECTION: Training & Strategies - NO FORM, just inputs and buttons
    st.markdown("---")
    st.subheader("Seção 3 - Treinamento e Capacitação")
    st.markdown("Relate quais treinamentos e capacitações foram realizados pela equipe do ministério esse mês.")
    
    # Training fields
    treinamentos = []
    for i in range(st.session_state.treinamento_count):
        key = f"treinamento_{i}"
        treinamento = st.text_area(
            f"Treinamento/Capacitação {i+1}",
            key=key,
            help="Descreva um treinamento ou capacitação realizado pela equipe."
        )
        treinamentos.append(treinamento)
    
    # Button to add more trainings
    if st.button("Adicionar Mais Treinamentos"):
        st.session_state.treinamento_count += 1
        st.rerun()
    
    # SECTION: Growth Strategies
    st.markdown("---")
    st.subheader("Seção 4 - Estratégias para Crescimento")
    st.markdown("Descreva as estratégias implementadas para o crescimento e desenvolvimento do ministério.")
    
    # Strategy fields
    estrategias = []
    for i in range(st.session_state.estrategia_count):
        key = f"estrategia_{i}"
        estrategia = st.text_area(
            f"Estratégia {i+1}",
            key=key,
            help="Descreva uma estratégia implementada para o crescimento do ministério."
        )
        estrategias.append(estrategia)
    
    # Button to add more strategies
    if st.button("Adicionar Mais Estratégias"):
        st.session_state.estrategia_count += 1
        st.rerun()
    
    # SECTION: New Members - NO FORM
    st.markdown("---")
    st.subheader("Seção 5 - Novos Membros")
    
    # New members and members in training
    col1, col2 = st.columns(2)
    
    # Column 1: New members
    with col1:
        st.markdown("### Novos Membros Incorporados")
        
        novo_membro = st.text_input("Nome do novo membro", key="novo_membro_input")
        
        if st.button("Adicionar Novo Membro"):
            if novo_membro.strip():
                st.session_state.novos_membros_lista.append(novo_membro.strip())
                st.rerun()
        
        if st.session_state.novos_membros_lista:
            st.markdown("**Novos membros adicionados:**")
            for i, membro in enumerate(st.session_state.novos_membros_lista):
                col1a, col1b = st.columns([4, 1])
                col1a.write(f"{i+1}. {membro}")
                if col1b.button("Remover", key=f"remove_novo_{i}"):
                    st.session_state.novos_membros_lista.pop(i)
                    st.rerun()
        
        st.metric("Total de novos membros", len(st.session_state.novos_membros_lista))
    
    # Column 2: Members in training
    with col2:
        st.markdown("### Membros em Qualificação")
        
        membro_qualificacao = st.text_input("Nome do membro em qualificação", key="membro_qualificacao_input")
        
        if st.button("Adicionar Membro em Qualificação"):
            if membro_qualificacao.strip():
                st.session_state.membros_qualificacao_lista.append(membro_qualificacao.strip())
                st.rerun()
        
        if st.session_state.membros_qualificacao_lista:
            st.markdown("**Membros em qualificação adicionados:**")
            for i, membro in enumerate(st.session_state.membros_qualificacao_lista):
                col2a, col2b = st.columns([4, 1])
                col2a.write(f"{i+1}. {membro}")
                if col2b.button("Remover", key=f"remove_qualif_{i}"):
                    st.session_state.membros_qualificacao_lista.pop(i)
                    st.rerun()
        
        st.metric("Total de membros em qualificação", len(st.session_state.membros_qualificacao_lista))
    
    # SECTION: Final form with comments and submit button
    st.markdown("---")
    with st.form("form_part2"):
        st.subheader("Seção 6 - Comentários e Finalização")
        
        comentarios = st.text_area(
            "Comentários e Sugestões",
            help="Informe pontos de melhoria, dificuldades encontradas ou elogios."
        )
        
        final_submitted = st.form_submit_button("Enviar Avaliação")
        
        if final_submitted:
            # Validations
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
                    "novos_membros": len(st.session_state.novos_membros_lista),
                    "membros_qualificacao": len(st.session_state.membros_qualificacao_lista),
                    "nomes_novos_membros": "\n".join(st.session_state.novos_membros_lista),
                    "nomes_membros_qualificacao": "\n".join(st.session_state.membros_qualificacao_lista),
                    "comentarios": comentarios,
                    "mes_referencia": mes_referencia,
                    "ano_referencia": ano_referencia,
                    "semana_referencia": st.session_state.semana_atual
                }
                
                # Save to database
                if save_evaluation(data):
                    st.success("Avaliação enviada com sucesso! Obrigado pela sua participação.")
                    # Reset form and member lists
                    st.session_state.treinamento_count = 1
                    st.session_state.estrategia_count = 1
                    st.session_state.novos_membros_lista = []
                    st.session_state.membros_qualificacao_lista = []
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
                if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
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
    col1, col2, col3 = st.columns(3)
    
    with col1:
        meses = ["Todos", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        mes_filtro = st.selectbox("Filtrar por Mês", meses)
    
    with col2:
        anos = ["Todos"]
        # Get list of years from database
        conn = connect_to_db()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT DISTINCT ano_referencia 
                    FROM avaliacoes_ministerios 
                    ORDER BY ano_referencia
                """)
                anos_db = [str(row[0]) for row in cur.fetchall()]
                anos.extend(anos_db)
            except Exception as e:
                st.error(f"Erro ao buscar anos: {e}")
            finally:
                cur.close()
                conn.close()
                
        ano_filtro = st.selectbox("Filtrar por Ano", anos)

    with col3:
        # Add option to analyze by week or month
        periodicidade = st.selectbox(
            "Periodicidade da Análise",
            ["Mensal", "Semanal"],
            help="Escolha se deseja ver análises por mês ou por semana."
        )
        
        if periodicidade == "Semanal":
            semana_filtro = st.selectbox(
                "Filtrar por Semana",
                ["Todas", "1", "2", "3", "4", "5"],
                help="Selecione a semana específica para análise."
            )
        else:
            semana_filtro = "Todas"  # Default value for monthly analysis
    
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
            
            # Add filter for week if weekly analysis is selected
            if periodicidade == "Semanal" and semana_filtro != "Todas":
                conditions.append("semana_referencia = %s")
                params.append(int(semana_filtro))
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            df = pd.read_sql_query(query, conn, params=params)
            
            if df.empty:
                st.warning("Não há dados disponíveis para o período selecionado.")
            else:
                # Add context about the analysis period
                if periodicidade == "Semanal":
                    period_text = f"Semana {semana_filtro}" if semana_filtro != "Todas" else "Todas as Semanas"
                    if mes_filtro != "Todos":
                        period_text += f" de {mes_filtro}"
                    if ano_filtro != "Todos":
                        period_text += f" de {ano_filtro}"
                else:
                    period_text = f"{mes_filtro}" if mes_filtro != "Todos" else "Todos os Meses"
                    if ano_filtro != "Todos":
                        period_text += f" de {ano_filtro}"
                
                st.subheader(f"Análise {periodicidade}: {period_text}")
                
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
                    
                    # If weekly analysis is selected, show weekly trends
                    if periodicidade == "Semanal" and mes_filtro != "Todos" and ano_filtro != "Todos":
                        st.subheader(f"Tendências Semanais - {mes_filtro} de {ano_filtro}")
                        
                        # Sort by week
                        weekly_data = ministry_data.sort_values('semana_referencia')
                        
                        # Create a time series for each metric
                        fig = px.line(
                            weekly_data,
                            x='semana_referencia',
                            y=['pontualidade', 'assiduidade_celebracoes', 'assiduidade_reunioes', 'trabalho_equipe'],
                            title=f"Progresso Semanal - {selected_ministry}",
                            labels={
                                'semana_referencia': 'Semana', 
                                'value': 'Pontuação', 
                                'variable': 'Métrica'
                            },
                            markers=True
                        )
                        st.plotly_chart(fig)
                        
                        # Calculate week-to-week changes
                        if len(weekly_data) >= 2:
                            st.subheader("Evolução Semanal")
                            metrics = ['pontualidade', 'assiduidade_celebracoes', 'assiduidade_reunioes', 'trabalho_equipe']
                            
                            for metric in metrics:
                                # Get first and last week values
                                first_value = weekly_data[metric].iloc[0]
                                last_value = weekly_data[metric].iloc[-1]
                                change = last_value - first_value
                                
                                # Display change with color
                                col1, col2 = st.columns([1, 3])
                                col1.metric(
                                    metric.replace('_', ' ').title(), 
                                    f"{last_value:.1f}",
                                    f"{change:+.1f}",
                                    delta_color="normal" if change >= 0 else "inverse"
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
                    
                    fig_radar = px.line_polar(
                        r=values,
                        theta=categories,
                        line_close=True,
                        range_r=[0, 10],
                        title=f"Perfil de Requisitos: {selected_ministry}"
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)
                    
                    # Display metrics for members
                    st.subheader("Métricas de Crescimento")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        total_new_members = ministry_data['novos_membros'].sum()
                        st.metric(
                            f"Total de Novos Membros ({periodicidade.lower().rstrip('l')})", 
                            total_new_members
                        )
                        
                        if total_new_members > 0:
                            # Coletar nomes de novos membros de todas as entradas no período
                            nomes_novos = []
                            for _, row in ministry_data.iterrows():
                                if pd.notna(row['nomes_novos_membros']) and row['nomes_novos_membros']:
                                    nomes_novos.extend([nome.strip() for nome in row['nomes_novos_membros'].split('\n') if nome.strip()])
                            
                            if nomes_novos:
                                st.markdown("**Nomes dos Novos Membros:**")
                                for nome in nomes_novos:
                                    st.markdown(f"- {nome}")
                    
                    with col2:
                        total_qualifying_members = ministry_data['membros_qualificacao'].sum()
                        st.metric(
                            f"Total de Membros em Qualificação ({periodicidade.lower().rstrip('l')})", 
                            total_qualifying_members
                        )
                        
                        if total_qualifying_members > 0:
                            # Coletar nomes de membros em qualificação de todas as entradas no período
                            nomes_qualificacao = []
                            for _, row in ministry_data.iterrows():
                                if pd.notna(row['nomes_membros_qualificacao']) and row['nomes_membros_qualificacao']:
                                    nomes_qualificacao.extend([nome.strip() for nome in row['nomes_membros_qualificacao'].split('\n') if nome.strip()])
                            
                            if nomes_qualificacao:
                                st.markdown("**Nomes dos Membros em Qualificação:**")
                                for nome in nomes_qualificacao:
                                    st.markdown(f"- {nome}")
                    
                    # Exibir detalhes da Seção 2, 3 e 4 para o ministério selecionado
                    st.subheader("Informações Detalhadas")
                    
                    # Obter a entrada mais recente para o ministério selecionado
                    latest_entry = ministry_data.sort_values('data_submissao', ascending=False).iloc[0]
                    
                    # Criar abas para cada seção
                    tabs = st.tabs(["Preparo da Equipe", "Treinamentos", "Estratégias", "Comentários"])
                    
                    # Seção 2: Preparo da Equipe para a Celebração
                    with tabs[0]:
                        st.subheader("Seção 2 - Preparo da Equipe para a Celebração")
                        
                        # Definir os rótulos das semanas
                        semana_label = {
                            1: "Primeira Semana",
                            2: "Segunda Semana",
                            3: "Terceira Semana",
                            4: "Quarta Semana",
                            5: "Quinta Semana"
                        }
                        
                        # Consagração (Jejum e Oração)
                        st.markdown("### Consagração (Jejum e Oração)")
                        
                        # Se estiver no modo semanal e uma semana específica estiver selecionada, mostrar apenas os dados dessa semana
                        if periodicidade == "Semanal" and semana_filtro != "Todas":
                            semana_num = int(semana_filtro)
                            semana_campos = {
                                1: 'consagracao_semana1',
                                2: 'consagracao_semana2',
                                3: 'consagracao_semana3',
                                4: 'consagracao_semana4',
                                5: 'consagracao_semana5'
                            }
                            
                            campo = semana_campos[semana_num]
                            if pd.notna(latest_entry[campo]) and latest_entry[campo]:
                                st.markdown(f"**{semana_label[semana_num]}:**")
                                st.write(latest_entry[campo])
                            
                            # Preparo Técnico (somente da semana selecionada)
                            st.markdown("### Preparo Técnico (Ensaio, preparo técnico e equipamentos)")
                            
                            campo = f'preparo_tecnico_semana{semana_num}'
                            if pd.notna(latest_entry[campo]) and latest_entry[campo]:
                                st.markdown(f"**{semana_label[semana_num]}:**")
                                st.write(latest_entry[campo])
                            
                            # Reuniões (somente da semana selecionada)
                            st.markdown("### Reuniões")
                            
                            campo = f'reunioes_semana{semana_num}'
                            if pd.notna(latest_entry[campo]) and latest_entry[campo]:
                                st.markdown(f"**{semana_label[semana_num]}:**")
                                st.write(latest_entry[campo])
                        else:
                            # Mostrar todas as semanas em modo mensal ou quando "Todas" as semanas estiverem selecionadas
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
