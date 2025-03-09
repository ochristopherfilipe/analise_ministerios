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
            
            # Primeiro, verifica se já existe uma entrada para este ministério, semana, mês e ano
            cur.execute("""
                SELECT id, nomes_novos_membros, nomes_membros_qualificacao 
                FROM avaliacoes_ministerios 
                WHERE ministerio = %s 
                AND semana_referencia = %s 
                AND mes_referencia = %s 
                AND ano_referencia = %s
            """, (data["ministerio"], data["semana_referencia"], data["mes_referencia"], data["ano_referencia"]))
            
            result = cur.fetchone()
            
            # Filtrar apenas os arrays não vazios
            treinamentos_clean = [t for t in data["treinamentos"] if t and t.strip()]
            estrategias_clean = [e for e in data["estrategias"] if e and e.strip()]
            
            # Converter arrays para formato JSON
            treinamentos_json = json.dumps(treinamentos_clean)
            estrategias_json = json.dumps(estrategias_clean)
            
            if result:
                # Se já existe, atualiza a entrada
                entry_id = result[0]
                
                # Atualiza o registro existente
                cur.execute("""
                    UPDATE avaliacoes_ministerios SET
                        nome = %s,
                        email = %s,
                        pontualidade = %s,
                        assiduidade_celebracoes = %s,
                        assiduidade_reunioes = %s,
                        trabalho_equipe = %s,
                        consagracao_semana1 = %s,
                        consagracao_semana2 = %s,
                        consagracao_semana3 = %s,
                        consagracao_semana4 = %s,
                        consagracao_semana5 = %s,
                        preparo_tecnico_semana1 = %s,
                        preparo_tecnico_semana2 = %s,
                        preparo_tecnico_semana3 = %s,
                        preparo_tecnico_semana4 = %s,
                        preparo_tecnico_semana5 = %s,
                        reunioes_semana1 = %s,
                        reunioes_semana2 = %s,
                        reunioes_semana3 = %s,
                        reunioes_semana4 = %s,
                        reunioes_semana5 = %s,
                        treinamentos = %s,
                        estrategias = %s,
                        novos_membros = %s,
                        membros_qualificacao = %s,
                        nomes_novos_membros = %s,
                        nomes_membros_qualificacao = %s,
                        comentarios = %s,
                        data_submissao = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (
                    data["nome"], data["email"],
                    data["pontualidade"], data["assiduidade_celebracoes"], data["assiduidade_reunioes"], data["trabalho_equipe"],
                    data["consagracao_semana1"], data["consagracao_semana2"], data["consagracao_semana3"], data["consagracao_semana4"], data["consagracao_semana5"],
                    data["preparo_tecnico_semana1"], data["preparo_tecnico_semana2"], data["preparo_tecnico_semana3"], data["preparo_tecnico_semana4"], data["preparo_tecnico_semana5"],
                    data["reunioes_semana1"], data["reunioes_semana2"], data["reunioes_semana3"], data["reunioes_semana4"], data["reunioes_semana5"],
                    treinamentos_json, estrategias_json,
                    data["novos_membros"], data["membros_qualificacao"],
                    data["nomes_novos_membros"], data["nomes_membros_qualificacao"],
                    data["comentarios"], entry_id
                ))
            else:
                # Se não existe, insere uma nova entrada
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

# Function to clear member-related session state
def clear_member_session_state():
    """Reset all member-related session state variables to ensure a clean state."""
    st.session_state.novos_membros_lista = []
    st.session_state.membros_qualificacao_lista = []
    if "last_ministry" in st.session_state:
        st.session_state.last_ministry = None

# Leader login page
def show_leader_login():
    st.title("Login de Líder de Ministério")
    
    st.markdown("""
    Por favor, faça login para acessar o formulário de avaliação.
    """)
    
    # Add a clear session button for troubleshooting
    #if st.button("Limpar Sessão (Resolver Problemas)"):
    #    clear_member_session_state()
    #    st.success("Sessão limpa com sucesso!")
    #    st.rerun()
    
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
            clear_member_session_state()
            # Check if the password matches the leader's name
            if password == MINISTRY_LEADERS[ministerio]:
                # Clear any existing member lists
                clear_member_session_state()
                
                # Set authentication and ministry
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
        # Clear member lists when logging out
        clear_member_session_state()
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
    
    # Track the last ministry used to manage member lists
    if "last_ministry" not in st.session_state:
        st.session_state.last_ministry = None
    
    # Check if ministry has changed since last access - if so, reset member lists
    if st.session_state.last_ministry != st.session_state.current_ministry:
        st.session_state.novos_membros_lista = []
        st.session_state.membros_qualificacao_lista = []
        st.session_state.last_ministry = st.session_state.current_ministry
    
    # Initialize member lists if they don't exist
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
        form1_submitted = st.form_submit_button("Salvar Informações Semanais*")
        
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
    
    # Only load members if the lists are empty - ensures we don't mix members from different ministries
    if len(st.session_state.novos_membros_lista) == 0 and len(st.session_state.membros_qualificacao_lista) == 0:
        # Log the current ministry for debugging
        st.write(f"Carregando membros para: {st.session_state.current_ministry}")
        
        # Fetch existing members from database for the current ministry/month/year
        existing_novos_membros, existing_membros_qualificacao = get_existing_members(
            st.session_state.current_ministry, 
            mes_referencia, 
            ano_referencia
        )
        
        # Only populate the lists if we got results AND the current ministry matches
        if existing_novos_membros:
            st.session_state.novos_membros_lista = existing_novos_membros.copy()
            st.write(f"Carregados {len(existing_novos_membros)} novos membros")
        
        if existing_membros_qualificacao:
            st.session_state.membros_qualificacao_lista = existing_membros_qualificacao.copy()
            st.write(f"Carregados {len(existing_membros_qualificacao)} membros em qualificação")
    
    # New members and members in training
    col1, col2 = st.columns(2)
    
    # Column 1: New members
    with col1:
        st.markdown("### Novos Membros Incorporados")
        
        # Show the ministry name for clarity
        st.info(f"Exibindo membros do ministério: {st.session_state.current_ministry}")
        
        novo_membro = st.text_input("Nome do novo membro", key="novo_membro_input")
        
        if st.button("Adicionar Novo Membro"):
            if novo_membro.strip():
                # Avoid duplicates
                if novo_membro.strip() not in st.session_state.novos_membros_lista:
                    st.session_state.novos_membros_lista.append(novo_membro.strip())
                    st.rerun()
                else:
                    st.warning("Este membro já está na lista de novos membros.")
        
        # Display existing members with options
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
                # Avoid duplicates
                if membro_qualificacao.strip() not in st.session_state.membros_qualificacao_lista:
                    st.session_state.membros_qualificacao_lista.append(membro_qualificacao.strip())
                    st.rerun()
                else:
                    st.warning("Este membro já está na lista de membros em qualificação.")
        
        # Display existing qualification members with options
        if st.session_state.membros_qualificacao_lista:
            st.markdown("**Membros em qualificação adicionados:**")
            for i, membro in enumerate(st.session_state.membros_qualificacao_lista):
                col2a, col2b, col2c = st.columns([3, 1, 1])
                col2a.write(f"{i+1}. {membro}")
                
                # Add promotion button
                if col2b.button("Promover", key=f"promote_{i}"):
                    # Move member to new members list
                    if membro not in st.session_state.novos_membros_lista:
                        st.session_state.novos_membros_lista.append(membro)
                    # Remove from qualification list
                    st.session_state.membros_qualificacao_lista.pop(i)
                    
                    # Update the database to reflect this change for all entries of the month
                    promote_member_in_database(
                        st.session_state.current_ministry, 
                        mes_referencia, 
                        ano_referencia, 
                        membro
                    )
                    
                    st.success(f"Membro '{membro}' promovido com sucesso!")
                    st.rerun()
                
                # Add remove button
                if col2c.button("Remover", key=f"remove_qualif_{i}"):
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
            # Validations - use the ministry from session state since it's defined outside the form
            if not st.session_state.current_ministry or not nome or not email:
                st.error("Por favor, preencha todos os campos obrigatórios marcados com *.")
            elif not is_valid_email(email):
                st.error("Por favor, insira um email válido.")
            else:
                # Prepare data - use current_ministry from session state
                data = {
                    "ministerio": st.session_state.current_ministry,
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
                        # Get the total new members from the latest entries
                        total_new_members = ministry_data['novos_membros'].sum()
                        
                        # Get unique new member names
                        novos_membros_unique = []
                        
                        # To avoid duplicates, we'll use the latest entries first
                        for _, row in ministry_data.sort_values('data_submissao', ascending=False).iterrows():
                            if pd.notna(row['nomes_novos_membros']) and row['nomes_novos_membros']:
                                current_members = [nome.strip() for nome in row['nomes_novos_membros'].split('\n') if nome.strip()]
                                for membro in current_members:
                                    if membro not in novos_membros_unique:
                                        novos_membros_unique.append(membro)
                        
                        st.metric(
                            f"Total de Novos Membros ({periodicidade.lower().rstrip('l')})", 
                            len(novos_membros_unique)
                        )
                        
                        if novos_membros_unique:
                            st.markdown("**Nomes dos Novos Membros:**")
                            for nome in novos_membros_unique:
                                st.markdown(f"- {nome}")
                    
                    with col2:
                        # Get the total members in qualification from the latest entries
                        total_qualifying_members = ministry_data['membros_qualificacao'].sum()
                        
                        # Get unique members in qualification
                        membros_qualificacao_unique = []
                        
                        # To avoid duplicates, we'll use the latest entries first
                        for _, row in ministry_data.sort_values('data_submissao', ascending=False).iterrows():
                            if pd.notna(row['nomes_membros_qualificacao']) and row['nomes_membros_qualificacao']:
                                current_members = [nome.strip() for nome in row['nomes_membros_qualificacao'].split('\n') if nome.strip()]
                                for membro in current_members:
                                    if membro not in membros_qualificacao_unique and membro not in novos_membros_unique:
                                        membros_qualificacao_unique.append(membro)
                        
                        st.metric(
                            f"Total de Membros em Qualificação ({periodicidade.lower().rstrip('l')})", 
                            len(membros_qualificacao_unique)
                        )
                        
                        if membros_qualificacao_unique:
                            st.markdown("**Nomes dos Membros em Qualificação:**")
                            for nome in membros_qualificacao_unique:
                                st.markdown(f"- {nome}")
                    
                    # Exibir detalhes da Seção 2, 3 e 4 para o ministério selecionado
                    st.subheader("Informações Detalhadas")
                    
                    # Definir os rótulos das semanas
                    semana_label = {
                        1: "Primeira Semana",
                        2: "Segunda Semana",
                        3: "Terceira Semana",
                        4: "Quarta Semana",
                        5: "Quinta Semana"
                    }
                    
                    # Criar abas para cada seção
                    tabs = st.tabs(["Preparo da Equipe", "Treinamentos", "Estratégias", "Comentários"])
                    
                    # Seção 2: Preparo da Equipe para a Celebração
                    with tabs[0]:
                        st.subheader("Seção 2 - Preparo da Equipe para a Celebração")
                        
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
                            if pd.notna(ministry_data[campo].iloc[0]) and ministry_data[campo].iloc[0]:
                                st.markdown(f"**{semana_label[semana_num]}:**")
                                st.write(ministry_data[campo].iloc[0])
                            
                            # Preparo Técnico (somente da semana selecionada)
                            st.markdown("### Preparo Técnico (Ensaio, preparo técnico e equipamentos)")
                            
                            campo = f'preparo_tecnico_semana{semana_num}'
                            if pd.notna(ministry_data[campo].iloc[0]) and ministry_data[campo].iloc[0]:
                                st.markdown(f"**{semana_label[semana_num]}:**")
                                st.write(ministry_data[campo].iloc[0])
                            
                            # Reuniões (somente da semana selecionada)
                            st.markdown("### Reuniões")
                            
                            campo = f'reunioes_semana{semana_num}'
                            if pd.notna(ministry_data[campo].iloc[0]) and ministry_data[campo].iloc[0]:
                                st.markdown(f"**{semana_label[semana_num]}:**")
                                st.write(ministry_data[campo].iloc[0])
                        else:
                            # Mostrar TODAS as semanas em modo mensal ou quando "Todas" as semanas estiverem selecionadas
                            # Agrupar entradas por semana para obter dados de todas as semanas do mês
                            semanas_data = {}
                            
                            # Processar todas as entradas do ministério no período selecionado
                            for _, row in ministry_data.iterrows():
                                semana = row['semana_referencia']
                                if semana not in semanas_data:
                                    semanas_data[semana] = row
                            
                            # Ordenar semanas
                            semanas_ordenadas = sorted(semanas_data.keys())
                            
                            # Mostrar dados de cada semana
                            for semana in semanas_ordenadas:
                                entry = semanas_data[semana]
                                
                                # Consagração
                                campo_consagracao = f'consagracao_semana{semana}'
                                if pd.notna(entry[campo_consagracao]) and entry[campo_consagracao]:
                                    st.markdown(f"**{semana_label[semana]}:**")
                                    st.write(entry[campo_consagracao])
                            
                            # Preparo Técnico para todas as semanas
                            st.markdown("### Preparo Técnico (Ensaio, preparo técnico e equipamentos)")
                            
                            for semana in semanas_ordenadas:
                                entry = semanas_data[semana]
                                campo_preparo = f'preparo_tecnico_semana{semana}'
                                if pd.notna(entry[campo_preparo]) and entry[campo_preparo]:
                                    st.markdown(f"**{semana_label[semana]}:**")
                                    st.write(entry[campo_preparo])
                            
                            # Reuniões para todas as semanas
                            st.markdown("### Reuniões")
                            
                            for semana in semanas_ordenadas:
                                entry = semanas_data[semana]
                                campo_reunioes = f'reunioes_semana{semana}'
                                if pd.notna(entry[campo_reunioes]) and entry[campo_reunioes]:
                                    st.markdown(f"**{semana_label[semana]}:**")
                                    st.write(entry[campo_reunioes])
                    
                    # Seção 3: Treinamento e Capacitação
                    with tabs[1]:
                        st.subheader("Seção 3 - Treinamento e Capacitação")
                        
                        # Aggregating all training data from the selected period
                        all_treinamentos = []
                        
                        # Process each entry
                        for _, row in ministry_data.iterrows():
                            treinamentos_data = row['treinamentos']
                            
                            # Try to interpret as JSON if it's a string
                            if isinstance(treinamentos_data, str):
                                try:
                                    treinamentos_data = json.loads(treinamentos_data)
                                except json.JSONDecodeError:
                                    treinamentos_data = []
                            
                            # Ensure we have an iterable
                            if isinstance(treinamentos_data, list):
                                for item in treinamentos_data:
                                    if item and item not in all_treinamentos:  # Avoid duplicates
                                        all_treinamentos.append(item)
                        
                        # Display all trainings
                        if all_treinamentos:
                            for i, treinamento in enumerate(all_treinamentos):
                                st.markdown(f"**{i+1}.** {treinamento}")
                        else:
                            st.info("Nenhum treinamento registrado para este período.")
                    
                    # Seção 4: Estratégias para Crescimento
                    with tabs[2]:
                        st.subheader("Seção 4 - Estratégias para Crescimento")
                        
                        # Aggregating all strategies data from the selected period
                        all_estrategias = []
                        
                        # Process each entry
                        for _, row in ministry_data.iterrows():
                            estrategias_data = row['estrategias']
                            
                            # Try to interpret as JSON if it's a string
                            if isinstance(estrategias_data, str):
                                try:
                                    estrategias_data = json.loads(estrategias_data)
                                except json.JSONDecodeError:
                                    estrategias_data = []
                            
                            # Ensure we have an iterable
                            if isinstance(estrategias_data, list):
                                for item in estrategias_data:
                                    if item and item not in all_estrategias:  # Avoid duplicates
                                        all_estrategias.append(item)
                        
                        # Display all strategies
                        if all_estrategias:
                            for i, estrategia in enumerate(all_estrategias):
                                st.markdown(f"**{i+1}.** {estrategia}")
                        else:
                            st.info("Nenhuma estratégia registrada para este período.")
                    
                    # Seção 6: Comentários
                    with tabs[3]:
                        st.subheader("Seção 6 - Comentários e Sugestões")
                        
                        # Display comments from all entries in the period
                        if not ministry_data.empty:
                            for i, row in ministry_data.iterrows():
                                if pd.notna(row['comentarios']) and row['comentarios'].strip():
                                    semana = row['semana_referencia']
                                    st.markdown(f"**Comentários da {semana_label[semana]}:**")
                                    st.write(row['comentarios'])
                    
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

# Get members from database for the current month
def get_existing_members(ministerio, mes, ano):
    """Fetch existing members data for the specified ministry, month and year."""
    conn = connect_to_db()
    if conn:
        try:
            cur = conn.cursor()
            
            # Query to get latest members data for the specific ministry, month and year
            # Ensure we're strictly filtering by ministry to avoid cross-ministry data
            cur.execute("""
                SELECT 
                    nomes_novos_membros, 
                    nomes_membros_qualificacao 
                FROM 
                    avaliacoes_ministerios 
                WHERE 
                    ministerio = %s AND 
                    mes_referencia = %s AND 
                    ano_referencia = %s
                ORDER BY
                    data_submissao DESC
                LIMIT 1
            """, (ministerio, mes, ano))
            
            result = cur.fetchone()
            
            # Initialize lists for members
            novos_membros = []
            membros_qualificacao = []
            
            # Process the results only if we have data for the specified ministry
            if result:
                st.write(f"Encontrados dados para {ministerio}")
                # Add new members from the latest entry
                if result[0] and result[0].strip():
                    novos_membros = [m.strip() for m in result[0].split('\n') if m.strip()]
                
                # Add members in qualification from the latest entry
                if result[1] and result[1].strip():
                    membros_qualificacao = [m.strip() for m in result[1].split('\n') if m.strip()]
            
            return novos_membros, membros_qualificacao
            
        except Exception as e:
            st.error(f"Erro ao buscar membros do banco de dados: {e}")
            return [], []
        finally:
            cur.close()
            conn.close()
    
    return [], []

# Function to promote a member from qualification to new member in the database
def promote_member_in_database(ministerio, mes, ano, membro):
    """Update all records for the current month to move a member from qualification to new member list."""
    conn = connect_to_db()
    if conn:
        try:
            cur = conn.cursor()
            
            # Get all entries for this ministry, month and year
            cur.execute("""
                SELECT id, nomes_novos_membros, nomes_membros_qualificacao 
                FROM avaliacoes_ministerios 
                WHERE ministerio = %s 
                AND mes_referencia = %s 
                AND ano_referencia = %s
            """, (ministerio, mes, ano))
            
            entries = cur.fetchall()
            
            for entry in entries:
                entry_id = entry[0]
                novos_membros_text = entry[1] or ""
                membros_qualificacao_text = entry[2] or ""
                
                # Parse member lists
                novos_membros = [m.strip() for m in novos_membros_text.split('\n') if m.strip()]
                membros_qualificacao = [m.strip() for m in membros_qualificacao_text.split('\n') if m.strip()]
                
                # Check if the member is in qualification list
                if membro in membros_qualificacao:
                    # Remove from qualification
                    membros_qualificacao = [m for m in membros_qualificacao if m != membro]
                    
                    # Add to new members if not already there
                    if membro not in novos_membros:
                        novos_membros.append(membro)
                    
                    # Update counts
                    novos_membros_count = len(novos_membros)
                    membros_qualificacao_count = len(membros_qualificacao)
                    
                    # Update database
                    cur.execute("""
                        UPDATE avaliacoes_ministerios SET
                            nomes_novos_membros = %s,
                            nomes_membros_qualificacao = %s,
                            novos_membros = %s,
                            membros_qualificacao = %s
                        WHERE id = %s
                    """, (
                        '\n'.join(novos_membros),
                        '\n'.join(membros_qualificacao),
                        novos_membros_count,
                        membros_qualificacao_count,
                        entry_id
                    ))
            
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Erro ao promover membro no banco de dados: {e}")
            return False
        finally:
            cur.close()
            conn.close()
    return False

# Run the app
if __name__ == "__main__":
    main() 
