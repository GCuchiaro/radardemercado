import streamlit as st
import pandas as pd
import json
import os
import datetime
import pytz
import sys
import hashlib
import secrets
from dateutil import parser
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from google_news_searcher import GoogleNewsSearcher

# Configuração da página
st.set_page_config(
    page_title="Radar de Mercado",
    page_icon="📰",
    layout="wide"
)

# Configuração de autenticação
SENHA_PADRAO = "news2025"  # Senha padrão - você pode alterar para a senha desejada

# Função para verificar a senha
def verificar_senha(senha_informada):
    # Compara a senha informada com a senha padrão usando hash
    if not senha_informada:
        return False
        
    # Criar hash da senha informada
    senha_hash = hashlib.sha256(senha_informada.encode()).hexdigest()
    senha_padrao_hash = hashlib.sha256(SENHA_PADRAO.encode()).hexdigest()
    
    # Comparação segura usando tempo constante para evitar ataques de timing
    return secrets.compare_digest(senha_hash, senha_padrao_hash)

# Inicializar estado de autenticação
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    
# Inicializar nome de usuário
if 'username' not in st.session_state:
    st.session_state.username = ""

# Função para fazer login (mantida para compatibilidade)
def fazer_login(senha):
    username = st.session_state.get('username', '').strip()
    
    if not username:
        st.error("Por favor, informe seu nome de usuário.")
        return False
        
    if not senha:
        st.error("Por favor, informe a senha.")
        return False
        
    if not verificar_senha(senha):
        st.error("Senha incorreta. Tente novamente.")
        return False
    
    # Se chegou aqui, login está válido
    st.session_state.autenticado = True
    st.session_state.username = username  # Garantir que o username está na sessão
    
    try:
        # Carregar o histórico de consultas do usuário
        historico = load_user_history(username)
        if historico:
            st.session_state.historico_consultas = historico
            st.success(f"Bem-vindo, {username}! Seu histórico com {len(historico)} consultas foi carregado.")
        else:
            st.session_state.historico_consultas = []
            st.success(f"Bem-vindo, {username}! Nenhum histórico encontrado. Suas consultas serão salvas automaticamente.")
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")
        st.session_state.historico_consultas = []
    
    return True
# Função para atualizar o estado de relevância na edição
def update_relevance_state(consulta_id, indice):
    # Obter a chave do checkbox
    checkbox_key = f"edit_relevante_{consulta_id}_{indice}"
    # Obter o estado atual do checkbox
    is_relevant = st.session_state.get(checkbox_key, False)
    # Atualizar o estado de relevância
    st.session_state[f"edit_state_{consulta_id}"][str(indice)] = is_relevant

# Inicializar o searcher
@st.cache_resource
def get_searcher():
    return GoogleNewsSearcher()

searcher = get_searcher()

# Função para limpar o cache de notícias
def clear_news_cache():
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
    if os.path.exists(cache_dir):
        try:
            files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith('.pkl')]
            for file in files:
                os.remove(file)
            return len(files), True
        except Exception as e:
            st.error(f"Erro ao limpar cache: {e}")
            return 0, False
    return 0, False

# Função para garantir que os links tenham o formato correto
def format_link(link):
    """Formata um link para garantir que tenha o protocolo correto."""
    if not link:
        return ""
    if not isinstance(link, str):
        link = str(link)
    if not link.startswith(('http://', 'https://')):
        link = 'https://' + link.lstrip('/')
    return link

# Inicializar session_state para armazenar resultados e estado dos checkboxes
if 'all_results' not in st.session_state:
    st.session_state.all_results = []
    
if 'relevante_state' not in st.session_state:
    st.session_state.relevante_state = {}
    
# Variáveis para controle de feedback
if 'mostrar_feedback' not in st.session_state:
    st.session_state.mostrar_feedback = False
    
if 'noticias_salvas' not in st.session_state:
    st.session_state.noticias_salvas = 0
    
if 'noticias_ja_existentes' not in st.session_state:
    st.session_state.noticias_ja_existentes = 0
    
# Flag para rastrear quando o botão de busca foi clicado
if '_button_clicked' not in st.session_state:
    st.session_state._button_clicked = False
    
# Inicializar histórico de consultas
if 'historico_consultas' not in st.session_state:
    st.session_state.historico_consultas = []

# Função para carregar as palavras-chave do usuário
def load_keywords(username=None):
    # Se não for especificado um usuário, carrega as palavras-chave globais
    if username is None or not username.strip():
        if os.path.exists(searcher.config_file):
            try:
                with open(searcher.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    keywords = data.get('keywords', [])
                    # Verificar se keywords é realmente uma lista
                    if not isinstance(keywords, list):
                        st.warning("O formato das palavras-chave no arquivo de configuração é inválido. Inicializando com lista vazia.")
                        return []
                    return keywords
            except json.JSONDecodeError:
                st.error("Erro ao decodificar o arquivo de palavras-chave. O arquivo pode estar corrompido.")
                return []
            except Exception as e:
                st.error(f"Erro ao carregar palavras-chave: {e}")
                return []
        return []
    
    # Se for especificado um usuário, carrega as palavras-chave específicas do usuário
    user_keywords_file = get_user_keywords_file(username)
    if os.path.exists(user_keywords_file):
        try:
            with open(user_keywords_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                keywords = data.get('keywords', [])
                # Verificar se keywords é realmente uma lista
                if not isinstance(keywords, list):
                    st.warning(f"O formato das palavras-chave do usuário {username} é inválido. Inicializando com lista vazia.")
                    return []
                return keywords
        except json.JSONDecodeError:
            st.error(f"Erro ao decodificar o arquivo de palavras-chave do usuário {username}. O arquivo pode estar corrompido.")
            return []
        except Exception as e:
            st.error(f"Erro ao carregar palavras-chave do usuário {username}: {e}")
            return []
    else:
        # Criar o diretório e arquivo se não existir
        try:
            os.makedirs(os.path.dirname(user_keywords_file), exist_ok=True)
            with open(user_keywords_file, 'w', encoding='utf-8') as f:
                json.dump({'keywords': []}, f, ensure_ascii=False, indent=2)
            return []
        except Exception as e:
            st.error(f"Erro ao criar arquivo de palavras-chave para o usuário {username}: {e}")
            return []
    return []

# Função para salvar as palavras-chave
def save_keywords(keywords, username=None):
    # Validar entrada
    if not isinstance(keywords, list):
        st.error("Erro: As palavras-chave devem estar em formato de lista.")
        return False
        
    # Se não for especificado um usuário, salva as palavras-chave globais
    if username is None or not username.strip():
        try:
            with open(searcher.config_file, 'w', encoding='utf-8') as f:
                json.dump({'keywords': keywords}, f, ensure_ascii=False, indent=2)
            st.success("Palavras-chave salvas com sucesso!")
            return True
        except PermissionError as e:
            st.error(f"Erro de permissão ao salvar palavras-chave: {e}")
            return False
        except Exception as e:
            st.error(f"Erro ao salvar palavras-chave: {e}")
            return False
    
    # Se for especificado um usuário, salva as palavras-chave específicas do usuário
    try:
        user_keywords_file = get_user_keywords_file(username)
        os.makedirs(os.path.dirname(user_keywords_file), exist_ok=True)
        with open(user_keywords_file, 'w', encoding='utf-8') as f:
            json.dump({'keywords': keywords}, f, ensure_ascii=False, indent=2)
        st.success(f"Palavras-chave do usuário {username} salvas com sucesso!")
        return True
    except PermissionError as e:
        st.error(f"Erro de permissão ao salvar palavras-chave do usuário {username}: {e}")
        return False
    except Exception as e:
        st.error(f"Erro ao salvar palavras-chave do usuário {username}: {e}")
        return False
        
# Funções para gerenciar o histórico de consultas por usuário
def get_user_history_file(username):
    # Verificar se o nome de usuário não está vazio
    if not username or not username.strip():
        raise ValueError("Nome de usuário não pode ser vazio")
        
    # Criar um nome de arquivo seguro baseado no nome do usuário
    safe_username = ''.join(c if c.isalnum() else '_' for c in username.lower().strip())
    return os.path.join(os.path.dirname(searcher.config_file), f"historico_{safe_username}.json")

# Função para obter o arquivo de palavras-chave do usuário
def get_user_keywords_file(username):
    # Verificar se o nome de usuário não está vazio
    if not username or not username.strip():
        raise ValueError("Nome de usuário não pode ser vazio")
        
    # Criar um nome de arquivo seguro baseado no nome do usuário
    safe_username = ''.join(c if c.isalnum() else '_' for c in username.lower().strip())
    return os.path.join(os.path.dirname(searcher.config_file), f"keywords_{safe_username}.json")

def save_user_history(username, historico):
    try:
        if not username or not username.strip():
            st.error("Erro: Nome de usuário vazio. Histórico não será salvo.")
            print("Tentativa de salvar histórico com nome de usuário vazio.")
            return False
            
        if not isinstance(historico, (list, dict)):
            st.error("Erro: Histórico deve ser uma lista ou dicionário.")
            print(f"Histórico inválido para {username}: {type(historico)}")
            return False
            
        if not historico:
            print(f"Nenhum histórico para salvar para o usuário {username}")
            return True
            
        history_file = get_user_history_file(username)
        if not isinstance(history_file, str) or not history_file.strip():
            st.error("Erro: Caminho do arquivo de histórico inválido.")
            print(f"Caminho inválido para {username}: {history_file}")
            return False
        
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        
        def json_serializable(obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return str(obj)

        # Verificar se o histórico contém dados válidos antes de salvar
        historico_validado = []
        for consulta in historico:
            if not isinstance(consulta, dict) or 'resultados' not in consulta or 'relevante_state' not in consulta:
                print(f"Ignorando consulta inválida ao salvar histórico")
                continue
            historico_validado.append(consulta)
            
        print(f"Salvando {len(historico_validado)} consultas válidas para o usuário {username}")
            
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(historico_validado, f, ensure_ascii=False, indent=2, default=json_serializable)
            
        print(f"Histórico salvo com sucesso para o usuário {username} em {history_file}")
        return True
    except PermissionError as e:
        st.error(f"Erro de permissão ao salvar histórico: {e}")
        print(f"Erro de permissão para {username}: {e}")
        return False
    except (TypeError, ValueError) as e:
        st.error(f"Erro ao serializar histórico em JSON: {e}")
        print(f"Erro de serialização para {username}: {e}")
        return False
    except Exception as e:
        st.error(f"Erro inesperado ao salvar histórico: {e}")
        print(f"Erro inesperado para {username}: {e}")
        return False

# Função para limpar o histórico de notícias do usuário
def clear_user_history(username):
    try:
        if not username or not username.strip():
            st.error("Erro: Nome de usuário vazio. Não é possível limpar o histórico.")
            print("Tentativa de limpar histórico com nome de usuário vazio.")
            return False
            
        # Obter o caminho do arquivo de histórico
        try:
            history_file = get_user_history_file(username)
        except Exception as e:
            st.error("Erro: Caminho do arquivo de histórico inválido.")
            print(f"Erro ao obter caminho do arquivo para limpar histórico: {e}")
            return False
            
        # Verificar se o arquivo existe
        if os.path.exists(history_file):
            try:
                # Salvar um histórico vazio (lista vazia)
                with open(history_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                print(f"Histórico limpo com sucesso para o usuário {username}")
                return True
            except PermissionError as e:
                st.error(f"Erro de permissão ao limpar histórico: {e}")
                return False
            except Exception as e:
                st.error(f"Erro inesperado ao limpar histórico: {e}")
                return False
        else:
            # Se o arquivo não existe, consideramos que o histórico já está limpo
            print(f"Arquivo de histórico não encontrado para o usuário {username}. Nada a limpar.")
            return True
    except Exception as e:
        st.error(f"Erro ao limpar histórico: {e}")
        return False

def load_user_history(username):
    try:
        if not username or not username.strip():
            print(f"Tentativa de carregar histórico com nome de usuário vazio.")
            return []
            
        history_file = get_user_history_file(username)
        print(f"Tentando carregar histórico de: {history_file}")
        
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                try:
                    historico = json.load(f)
                    print(f"Histórico carregado com {len(historico)} consultas")
                    
                    # Garantir que todas as consultas tenham a estrutura correta
                    historico_validado = []
                    for consulta in historico:
                        # Verificar se todos os campos necessários existem
                        if not isinstance(consulta, dict) or 'resultados' not in consulta or 'relevante_state' not in consulta:
                            print(f"Consulta inválida encontrada e ignorada")
                            continue
                            
                        # Garantir que o usuário está correto
                        consulta['usuario'] = username
                        
                        # Garantir que relevante_state use chaves como strings
                        if consulta['relevante_state'] and not isinstance(next(iter(consulta['relevante_state'])), str):
                            consulta['relevante_state'] = {str(k): v for k, v in consulta['relevante_state'].items()}
                            
                        historico_validado.append(consulta)
                    
                    print(f"Histórico validado com {len(historico_validado)} consultas")
                    return historico_validado
                except json.JSONDecodeError as e:
                    print(f"Erro ao decodificar JSON do histórico: {e}")
                    return []
        else:
            print(f"Arquivo de histórico não encontrado: {history_file}")
            return []
    except Exception as e:
        print(f"Erro ao carregar histórico: {e}")
        st.error(f"Erro ao carregar histórico: {e}")
        return []

# Container principal para o aplicativo
main_container = st.container()

# Inicializar variável de autenticação se não existir
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# Tela de login (exibida apenas se não estiver autenticado)
if not st.session_state.autenticado:
    with main_container:
        st.title("📰 Radar de Mercado - Login")
        st.markdown("Por favor, informe seu nome e a senha para acessar o aplicativo.")
        
        # Inicializar variáveis de sessão para controle do formulário
        if 'login_submitted' not in st.session_state:
            st.session_state.login_submitted = False
        
        # Função para processar o login apenas quando o formulário for enviado
        def process_login():
            if not st.session_state.login_submitted:
                return
                
            username = st.session_state.username_input.strip() if 'username_input' in st.session_state else ""
            senha = st.session_state.senha_input if 'senha_input' in st.session_state else ""
            
            # Verificar se os campos estão preenchidos
            if not username:
                st.error("Por favor, informe seu nome de usuário.")
                st.session_state.login_submitted = False
                return
                
            if not senha:
                st.error("Por favor, informe a senha.")
                st.session_state.login_submitted = False
                return
            
            # Atualizar username na sessão
            st.session_state.username = username
            
            # Tentar fazer login
            if verificar_senha(senha):
                st.session_state.autenticado = True
                st.session_state.username = username
                
                try:
                    # Carregar o histórico de consultas do usuário
                    historico = load_user_history(username)
                    if historico:
                        st.session_state.historico_consultas = historico
                        st.success(f"Bem-vindo, {username}! Seu histórico com {len(historico)} consultas foi carregado.")
                    else:
                        st.session_state.historico_consultas = []
                        st.success(f"Bem-vindo, {username}! Nenhum histórico encontrado. Suas consultas serão salvas automaticamente.")
                except Exception as e:
                    st.error(f"Erro ao carregar histórico: {e}")
                    st.session_state.historico_consultas = []
                
                main_container.empty()
                st.rerun()
            else:
                st.error("Senha incorreta. Tente novamente.")
                st.session_state.login_submitted = False
        
        # Formulário para evitar recarregamento com Enter
        with st.form(key="login_form"):
            # Campo para nome de usuário
            username = st.text_input(
                "Nome de usuário", 
                value=st.session_state.get('username', ''), 
                placeholder="Digite seu nome",
                key="username_input"
            ).strip()
            
            # Campo de senha
            senha = st.text_input(
                "Senha", 
                type="password", 
                key="senha_input"
            )
            
            # Botão de login dentro do formulário
            submit_button = st.form_submit_button("Entrar")
            if submit_button:
                st.session_state.login_submitted = True
                process_login()
        
        # Mensagem de rodapé
        st.markdown("---")
        st.markdown("*Este é um aplicativo restrito. Apenas usuários autorizados podem acessar.*")
        st.stop()

# Título principal (visível apenas após login)
st.title("📰 Radar de Mercado")

# Criação de abas (disponíveis para todos, mas conteúdo protegido)
tab1, tab2, tab3, tab4 = st.tabs(["Buscar Notícias", "Histórico de Consultas", "Gerenciar Palavras-chave", "Estatísticas"])

# Conteúdo principal do aplicativo (exibido apenas se estiver autenticado)
if st.session_state.autenticado:
    st.markdown("Busque notícias relacionadas às suas palavras-chave de interesse no Google News.")
    
    # Exibir informações do usuário logado na barra lateral
    st.sidebar.write(f"Usuário: **{st.session_state.username}**")
    
    # Opções de otimização no sidebar
    with st.sidebar.expander("Opções de Otimização"):
        if st.button("🔄 Limpar Cache de Notícias", help="Remove arquivos de cache para liberar espaço e forçar novas consultas"):
            num_files, success = clear_news_cache()
            if success:
                st.success(f"Cache limpo com sucesso! {num_files} arquivos removidos.")
            else:
                st.error("Não foi possível limpar o cache.")
    
    # Seção Sobre no sidebar
    with st.sidebar.expander("Sobre o Radar de Mercado"):
        st.markdown("""
        ### Descrição
        O Radar de Mercado é uma aplicação que monitora notícias do Google News relacionadas 
        a palavras-chave específicas, facilitando a análise de informações relevantes para o 
        mercado financeiro.

        ### Funcionalidades
        - Busca de notícias em PT/EN
        - Cadastro de palavras-chave
        - Filtragem por período
        - Marcação de relevância
        - Exportação para CSV
        - Histórico de consultas
        
        ### Como usar
        1. Faça login com a senha fornecida
        2. Cadastre suas palavras-chave de interesse na aba "Gerenciar Palavras-chave"
        3. Na aba "Buscar Notícias", selecione as palavras-chave, idiomas e período desejado
        4. Clique em "Buscar Notícias" para obter os resultados
        5. Marque as notícias relevantes usando os checkboxes na tabela
        6. Baixe os resultados em formato CSV para análise detalhada
        7. Acesse suas consultas anteriores na aba "Histórico de Consultas"
        
        """)
    
    # Botão de logout
    if st.sidebar.button("Sair"):
        try:
            # Obter o nome do usuário atual
            username = st.session_state.get('username', '').strip()
            if not username:
                st.sidebar.error("Erro: Nome de usuário não encontrado na sessão.")
            else:
                # Salvar o histórico do usuário antes de fazer logout
                if st.session_state.get('historico_consultas', []):
                    if save_user_history(username, st.session_state.historico_consultas):
                        st.sidebar.success(f"Histórico de {username} salvo com sucesso!")
                        print(f"Histórico salvo com sucesso para {username} durante logout")
                    else:
                        st.sidebar.error(f"Não foi possível salvar o histórico de {username}.")
                        print(f"Falha ao salvar histórico para {username} durante logout")
        except Exception as e:
            st.sidebar.error(f"Erro ao salvar histórico durante logout: {e}")
            print(f"Erro durante logout: {e}")
        finally:
            # Limpar todas as variáveis de sessão
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            # Reinicializar variáveis essenciais
            st.session_state.autenticado = False
            st.session_state.username = ""
            st.session_state.historico_consultas = []
            
            # Forçar atualização da página
            st.rerun()
        if 'historico_consultas' in st.session_state:
            del st.session_state.historico_consultas
        st.rerun()

# Aba 1: Buscar Notícias
with tab1:
    if st.session_state.autenticado:
        st.header("Buscar Notícias")
        
        # Carregar palavras-chave específicas do usuário
        keywords = load_keywords(st.session_state.username)
        
        if not keywords:
            st.warning("Nenhuma palavra-chave cadastrada. Vá para a aba 'Gerenciar Palavras-chave' para adicionar.")
        else:
                # Seleção de palavras-chave
            st.subheader("Selecione as palavras-chave")
            selected_keywords = []
            
            # Opção para selecionar todas
            if st.checkbox("Selecionar todas as palavras-chave"):
                selected_keywords = keywords
            else:
                # Mostrar as palavras-chave como checkboxes
                for keyword in keywords:
                    if st.checkbox(keyword):
                        selected_keywords.append(keyword)
            
            # Seleção de idioma
            st.subheader("Selecione o idioma")
            language_option = st.radio(
                "Idioma para busca:",
                ["Português", "Inglês", "Ambos"],
                horizontal=True,
                help="Escolha o idioma das notícias que deseja buscar"
            )
        
            language_map = {
                "Português": ["pt"],
                "Inglês": ["en"],
                "Ambos": ["pt", "en"]
            }
            
            selected_languages = language_map[language_option]
            
            # Seleção de período
            st.subheader("Selecione o período de busca")
            period_option = st.radio(
                "Período:",
                ["Últimas 24 horas", "Última semana", "Último mês", "Período personalizado"],
                horizontal=True,
                help="Escolha o período de tempo para buscar notícias"
            )
        
            # Definir datas com base no período selecionado (fuso horário brasileiro)
            fuso_brasil = pytz.timezone('America/Sao_Paulo')
            today = datetime.datetime.now(fuso_brasil)
            
            if period_option == "Últimas 24 horas":
                start_date = (today - datetime.timedelta(days=1)).strftime('%d/%m/%Y')
                end_date = today.strftime('%d/%m/%Y')
            elif period_option == "Última semana":
                start_date = (today - datetime.timedelta(days=7)).strftime('%d/%m/%Y')
                end_date = today.strftime('%d/%m/%Y')
            elif period_option == "Último mês":
                start_date = (today - datetime.timedelta(days=30)).strftime('%d/%m/%Y')
                end_date = today.strftime('%d/%m/%Y')
            else:  # Período personalizado
                col1, col2 = st.columns(2)
                with col1:
                    start_date_dt = st.date_input("Data inicial", 
                                               value=(today - datetime.timedelta(days=7)).date(),
                                               max_value=today)
                    start_date = start_date_dt.strftime('%d/%m/%Y')
                with col2:
                    end_date_dt = st.date_input("Data final", 
                                             value=today.date(),
                                             max_value=today)
                    end_date = end_date_dt.strftime('%d/%m/%Y')
        
            # Função para realizar a busca e atualizar a session_state
            def realizar_busca():
                # Removido o spinner duplicado
                all_results = []
                
                # Mostrar mensagem de carregamento
                with st.spinner('Buscando notícias... Por favor, aguarde...'):
                    # Buscar para cada palavra-chave e idioma sequencialmente
                    # Isso é mais seguro com o Streamlit que não suporta bem atualizações de threads paralelas
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Calcular o total de consultas a serem feitas
                    total_queries = len(selected_keywords) * len(selected_languages)
                    completed = 0
                    
                    # Criar lista de tarefas (pares keyword-language)
                    tasks = [(k, l) for k in selected_keywords for l in selected_languages]
                    
                    # Processar cada tarefa sequencialmente, mas com feedback visual
                    for idx, (keyword, language) in enumerate(tasks):
                        # Atualizar texto de status
                        status_text.text(f"Buscando: '{keyword}' em {language}... ({idx+1}/{total_queries})")
                        
                        # As datas já foram convertidas e validadas anteriormente
                        
                        try:
                            # Buscar notícias
                            results = searcher._fetch_news(
                                keyword, 
                                start_date_obj, 
                                end_date_obj, 
                                language
                            )
                            
                            if results:
                                all_results.extend(results)
                        except Exception as e:
                            st.error(f"Erro ao buscar notícias para '{keyword}' em {language}: {e}")
                        
                        # Atualizar barra de progresso
                        progress_bar.progress((idx + 1) / total_queries)
                    
                    # Limpar elementos temporários
                    status_text.empty()
                
                # Ordenar por data (mais recentes primeiro) se houver resultados
                if all_results:
                    all_results.sort(key=lambda x: parser.parse(x['published']), reverse=True)
                    
                    # Armazenar resultados na session_state
                    st.session_state.all_results = all_results
                    
                    # Inicializar checkboxes para novos resultados
                    for i in range(len(all_results)):
                        if i not in st.session_state.relevante_state:
                            st.session_state.relevante_state[i] = False
                else:
                    # Limpar resultados anteriores se a nova busca não retornou nada
                    st.session_state.all_results = []
                    st.warning("Nenhuma notícia encontrada para os critérios selecionados.")
            # Botão para buscar usando formulário para evitar problemas com Enter
            with st.form(key="search_form"):
                submit_button = st.form_submit_button("🔍 Buscar Notícias", type="primary", help="Clique para buscar notícias com os filtros selecionados")
                if submit_button:
                    st.session_state._button_clicked = True
                    # Verificar se os campos obrigatórios estão preenchidos
                    if not selected_keywords or not selected_languages or not start_date or not end_date:
                        st.error("Por favor, selecione pelo menos uma palavra-chave, um idioma e o período de busca.")
                    else:
                        # Verificar se a data inicial é menor que a data final
                        try:
                            start_date_obj = datetime.datetime.strptime(start_date, '%d/%m/%Y')
                            end_date_obj = datetime.datetime.strptime(end_date, '%d/%m/%Y')
                            if start_date_obj > end_date_obj:
                                st.error("A data inicial não pode ser maior que a data final.")
                            else:
                                realizar_busca()
                                if not st.session_state.all_results:
                                    st.warning("⚠️ Nenhuma notícia encontrada para os critérios selecionados. Tente ajustar os filtros.")
                        except Exception as e:
                            st.error(f"Erro ao processar datas: {e}")
            
            # Função de callback para atualizar o estado do checkbox
            def update_checkbox_state(i):
                checkbox_key = f"relevante_{i}_{hash(st.session_state.all_results[i]['title'])}"
                st.session_state.relevante_state[i] = st.session_state[checkbox_key]
                print(f"Checkbox {i} atualizado para {st.session_state.relevante_state[i]}")
                
            # Função para salvar notícias relevantes marcadas
            def salvar_noticias_relevantes():
                print("Função salvar_noticias_relevantes chamada")
                print(f"Estado atual de relevante_state: {st.session_state.relevante_state}")
                
                # Garantir que temos o histórico carregado
                if not hasattr(st.session_state, 'historico_consultas') or st.session_state.historico_consultas is None:
                    st.session_state.historico_consultas = load_user_history(st.session_state.username)
                    print(f"Histórico carregado: {len(st.session_state.historico_consultas)} entradas")
                
                noticias_salvas = 0
                noticias_ja_existentes = 0
                
                # Verificar se existem notícias marcadas como relevantes
                if not any(st.session_state.relevante_state.get(i, False) for i in range(len(st.session_state.all_results))):
                    st.warning("Nenhuma notícia foi marcada como relevante.")
                    return
                
                # Lista para armazenar notícias a serem salvas
                noticias_para_salvar = []
                
                # Identificar notícias marcadas como relevantes
                for i, resultado in enumerate(st.session_state.all_results):
                    if st.session_state.relevante_state.get(i, False):
                        noticia_atual = st.session_state.all_results[i].copy()  # Fazer uma cópia para evitar problemas de referência
                        print(f"Processando notícia {i}: {noticia_atual['title']}")
                        noticias_para_salvar.append(noticia_atual)
                
                # Processar cada notícia marcada como relevante
                for noticia_atual in noticias_para_salvar:
                    consulta_id = datetime.datetime.now(fuso_brasil).strftime('%Y%m%d_%H%M%S')
                    relevante_state = {"0": True}  # Sempre usar índice 0 para a notícia única
                    consulta = {
                        'id': consulta_id,
                        'data_hora': datetime.datetime.now(fuso_brasil).strftime('%d/%m/%Y %H:%M'),
                        'usuario': st.session_state.username,
                        'parametros': {
                            'keywords': st.session_state.get('last_keywords', []),
                            'languages': st.session_state.get('last_languages', []),
                            'start_date': st.session_state.get('last_start_date', ''),
                            'end_date': st.session_state.get('last_end_date', '')
                        },
                        'resultados': [noticia_atual],
                        'relevante_state': relevante_state
                    }
                    
                    # Verificar se a notícia já existe no histórico
                    noticia_existente = False
                    for c in st.session_state.historico_consultas:
                        if 'resultados' in c and len(c['resultados']) > 0:
                            if noticia_atual['title'] == c['resultados'][0]['title']:
                                noticia_existente = True
                                noticias_ja_existentes += 1
                                print(f"Notícia já existe no histórico: {noticia_atual['title']}")
                                break
                    
                    if not noticia_existente:
                        st.session_state.historico_consultas.append(consulta)
                        noticias_salvas += 1
                        print(f"Notícia '{noticia_atual['title']}' adicionada para salvar no histórico.")
                
                # Salvar o histórico atualizado se houver notícias novas
                if noticias_salvas > 0:
                    save_user_history(st.session_state.username, st.session_state.historico_consultas)
                    print(f"Histórico salvo com {noticias_salvas} novas notícias.")
                
                # Definir variáveis de feedback para exibir na próxima renderização
                st.session_state.noticias_salvas = noticias_salvas
                st.session_state.noticias_ja_existentes = noticias_ja_existentes
                st.session_state.mostrar_feedback = True
                
                # Limpar os checkboxes após salvar
                st.session_state.relevante_state = {}

            # Botão para salvar notícias relevantes será exibido após os resultados
            
            # Verificar se há feedback para exibir
            if st.session_state.get('mostrar_feedback', False):
                noticias_salvas = st.session_state.get('noticias_salvas', 0)
                noticias_ja_existentes = st.session_state.get('noticias_ja_existentes', 0)
                
                if noticias_salvas > 0:
                    st.success(f"{noticias_salvas} notícia(s) relevante(s) salva(s) no histórico!")
                    if noticias_ja_existentes > 0:
                        st.info(f"{noticias_ja_existentes} notícia(s) já existiam no histórico.")
                elif noticias_ja_existentes > 0:
                    st.info(f"Todas as {noticias_ja_existentes} notícia(s) já existiam no histórico.")
                
                # Limpar as variáveis de feedback
                st.session_state.mostrar_feedback = False
                st.session_state.noticias_salvas = 0
                st.session_state.noticias_ja_existentes = 0
            
            # Exibir resultados se existirem na session_state
            if st.session_state.all_results:
                # Exibir tabela de resultados
                st.subheader(f"Resultados da Busca ({len(st.session_state.all_results)} notícias)")
                
                # Botões de ação no final da tabela
                st.markdown("---")
                col1, col2 = st.columns(2)
                
                # Criar cabeçalho da tabela
                header_cols = st.columns([0.05, 0.15, 0.35, 0.2, 0.1, 0.15])
                header_cols[0].write("**Índice**")
                header_cols[1].write("**Palavra-chave**")
                header_cols[2].write("**Título**")
                header_cols[3].write("**Data/Hora**")
                header_cols[4].write("**Link**")
                header_cols[5].write("**Relevante**")
                
                # Exibir cada linha da tabela
                for i, result in enumerate(st.session_state.all_results):
                    # Criar colunas para cada linha
                    row_cols = st.columns([0.05, 0.15, 0.35, 0.2, 0.1, 0.15])
                    
                    # Formatar a data para exibição
                    data_publicacao = parser.parse(result['published'])
                    data_formatada = data_publicacao.strftime('%d/%m/%Y %H:%M')
                    
                    # Dados da notícia
                    row_cols[0].write(str(i))
                    row_cols[1].write(result['keyword'])
                    row_cols[2].write(result['title'])
                    row_cols[3].write(data_formatada)
                                        # Formatar o link usando a função auxiliar
                    link = format_link(result['link'])
                    # Usar o componente de link do Streamlit para melhor compatibilidade
                    row_cols[4].markdown(f"<a href='{link}' target='_blank' style='display: inline-block; padding: 5px 10px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px;'>Abrir</a>", unsafe_allow_html=True)
                    
                    # Checkbox para marcar como relevante
                    checkbox_key = f"relevante_{i}_{hash(result['title'])}"
                    row_cols[5].checkbox(
                        "", 
                        key=checkbox_key,
                        value=st.session_state.relevante_state.get(i, False),
                        on_change=update_checkbox_state,
                        args=(i,)
                    )
                
                # Preparar CSV para download incluindo a coluna de relevância
                # Formatar as datas para o padrão brasileiro
                datas_formatadas = []
                for i, result in enumerate(st.session_state.all_results):
                    data_publicacao = parser.parse(result['published'])
                    datas_formatadas.append(data_publicacao.strftime('%d/%m/%Y %H:%M'))
                
                csv_data = pd.DataFrame({
                    'Relevante': [st.session_state.relevante_state.get(i, False) for i in range(len(st.session_state.all_results))],
                    'Índice': list(range(len(st.session_state.all_results))),
                    'Palavra-chave': [result['keyword'] for result in st.session_state.all_results],
                    'Título': [result['title'] for result in st.session_state.all_results],
                    'Fonte': [result['source'] for result in st.session_state.all_results],
                    'Data/Hora': datas_formatadas,
                    'Idioma': [result['language'] for result in st.session_state.all_results],
                    'Link': [result['link'] for result in st.session_state.all_results]
                })
                
                # Converter para CSV
                csv = csv_data.to_csv(index=False)
                
                # Adicionar botão para salvar notícias relevantes após a tabela
                st.markdown("---")
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn2:
                    # Botão para salvar notícias relevantes com chave fixa
                    if st.button("Salvar Notícias Relevantes", type="primary", key="btn_salvar_noticias_fixo"):
                        salvar_noticias_relevantes()
                
                with col1:
                    # Botão para download direto em CSV
                    st.download_button(
                        label="⬇️ Baixar Resultados (CSV)",
                        data=csv,
                        file_name=f"noticias_{datetime.datetime.now(fuso_brasil).strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        help="Baixe os resultados da busca em formato CSV para abrir em Excel ou outro programa de planilhas"
                    )
            else:
                if st.session_state.get('_button_clicked', False):
                    st.error("Nenhuma notícia encontrada para os critérios selecionados.")
            
            if not selected_keywords:
                st.error("Selecione pelo menos uma palavra-chave para buscar.")

def export_all_history_to_csv(historico_consultas):
    if not historico_consultas:
        return None
        
    # Lista para armazenar todas as notícias relevantes
    todas_noticias = []
    
    # Processar cada consulta
    for consulta in historico_consultas:
        # Filtrar notícias relevantes
        noticias_relevantes = [result for j, result in enumerate(consulta['resultados']) 
                              if consulta['relevante_state'].get(str(j), False)]
        
        # Adicionar informações da consulta para cada notícia
        for noticia in noticias_relevantes:
            data_publicacao = parser.parse(noticia['published'])
            data_formatada = data_publicacao.strftime('%d/%m/%Y %H:%M')
            
            todas_noticias.append({
                'Data da Consulta': consulta.get('data_hora', ''),
                'ID da Consulta': consulta.get('id', ''),
                'Palavra-chave': noticia['keyword'],
                'Título': noticia['title'],
                'Fonte': noticia['source'],
                'Data de Publicação': data_formatada,
                'Idioma': noticia['language'],
                'Link': noticia['link']
            })
    
    if not todas_noticias:
        return None
        
    # Criar DataFrame
    return pd.DataFrame(todas_noticias)

# Aba 2: Histórico de Consultas
with tab2:
    if st.session_state.autenticado:
        st.header("Histórico de Consultas")
        
        if not st.session_state.historico_consultas:
            st.info("Nenhuma consulta salva no histórico. Realize buscas na aba 'Buscar Notícias' para salvá-las aqui.")
        else:
            # Informações gerais e resumo
            st.write(f"Total de consultas: **{len(st.session_state.historico_consultas)}**")
            
            # Contar o total de notícias relevantes em todas as consultas
            total_noticias_relevantes = 0
            for consulta in st.session_state.historico_consultas:
                noticias_relevantes = [result for j, result in enumerate(consulta['resultados']) 
                                      if consulta['relevante_state'].get(str(j), False)]
                total_noticias_relevantes += len(noticias_relevantes)
            
            st.write(f"Total de notícias relevantes: **{total_noticias_relevantes}**")
            
            # Seção de botões de exportação e gerenciamento
            st.subheader("Opções de Exportação e Gerenciamento")
            
            # Criar três colunas para os botões
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Botão para exportar todo o histórico
                df_historico = export_all_history_to_csv(st.session_state.historico_consultas)
                if df_historico is not None:
                    csv = df_historico.to_csv(index=False)
                    st.download_button(
                        label="📥 Exportar Todo o Histórico (CSV)",
                        data=csv,
                        file_name=f"historico_completo_{st.session_state.username}_{datetime.datetime.now(fuso_brasil).strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        help="Baixe todas as notícias relevantes em um único arquivo CSV"
                    )
                else:
                    st.info("Não há notícias relevantes no histórico para exportar.")

            with col3:
                # Botão para limpar o histórico
                if st.button("🗑️ Limpar Histórico", type="secondary", help="Excluir todo o histórico de notícias salvas"):
                    # Confirmação antes de limpar o histórico
                    if st.session_state.get('confirmar_exclusao', False):
                        # Limpar o histórico
                        if clear_user_history(st.session_state.username):
                            # Limpar o histórico na sessão
                            st.session_state.historico_consultas = []
                            st.session_state.confirmar_exclusao = False
                            st.success("Histórico de notícias excluído com sucesso!")
                            # Recarregar a página para atualizar a interface
                            st.rerun()
                        else:
                            st.error("Não foi possível excluir o histórico. Tente novamente.")
                            st.session_state.confirmar_exclusao = False
                    else:
                        # Solicitar confirmação
                        st.session_state.confirmar_exclusao = True
                        st.warning("Tem certeza que deseja excluir todo o histórico de notícias? Esta ação não pode ser desfeita. Clique novamente para confirmar.")
            
            # Coletar todas as notícias relevantes de todas as consultas
            col_header, col_refresh = st.columns([5, 1])
            with col_header:
                st.subheader("Todas as Notícias Relevantes")
            with col_refresh:
                # Definir flag para recarregar o histórico
                if 'recarregar_historico' not in st.session_state:
                    st.session_state.recarregar_historico = False
                    
                if st.button("🔄 Atualizar", help="Atualizar a tabela de notícias relevantes", key="btn_atualizar_historico"):
                    # Definir flag para recarregar o histórico
                    st.session_state.recarregar_historico = True
                    st.rerun()
                    
                # Verificar se é necessário recarregar o histórico
                if st.session_state.recarregar_historico:
                    # Limpar o cache de notícias adicionadas
                    if 'noticias_adicionadas' in st.session_state:
                        del st.session_state.noticias_adicionadas
                    
                    # Recarregar o histórico do usuário
                    st.session_state.historico_consultas = load_user_history(st.session_state.username)
                    print(f"Histórico recarregado via botão de atualização: {len(st.session_state.historico_consultas)} consultas")
                    st.success("Histórico atualizado com sucesso!")
                    
                    # Limpar a flag
                    st.session_state.recarregar_historico = False
            
            # Preparar dados para a tabela de notícias
            todas_noticias = []
            # Dicionário para rastrear notícias já adicionadas e evitar duplicação
            if 'noticias_adicionadas' not in st.session_state:
                st.session_state.noticias_adicionadas = {}
            noticias_adicionadas = st.session_state.noticias_adicionadas.copy()  # Usar uma cópia para evitar modificações durante a iteração
            
            # Limpar o dicionário de notícias adicionadas se estiver muito grande
            if len(noticias_adicionadas) > 1000:
                st.session_state.noticias_adicionadas = {}
                noticias_adicionadas = {}
            
            # Garantir que o histórico está carregado
            if 'historico_consultas' not in st.session_state or not st.session_state.historico_consultas:
                st.session_state.historico_consultas = load_user_history(st.session_state.username)
                print(f"Recarregado histórico com {len(st.session_state.historico_consultas)} consultas")
                
            # Exibir informações de debug sobre o histórico
            print(f"Processando {len(st.session_state.historico_consultas)} consultas no histórico")
            
            for i, consulta in enumerate(st.session_state.historico_consultas):
                # Verificar se a consulta tem a estrutura correta
                if not isinstance(consulta, dict) or 'resultados' not in consulta or 'relevante_state' not in consulta:
                    continue
                    
                # Filtrar apenas notícias relevantes
                noticias_relevantes = []
                for j, result in enumerate(consulta['resultados']):
                    # Verificar se a notícia é relevante
                    if consulta['relevante_state'].get(str(j), False):
                        # Adicionar informações de debug
                        print(f"Notícia relevante encontrada: {result.get('title', 'Sem título')}")
                        # Verificar se a notícia tem os campos necessários antes de adicionar
                        if isinstance(result, dict) and 'title' in result and 'link' in result:
                            noticias_relevantes.append(result)
                
                # Adicionar cada notícia relevante à lista
                for result in noticias_relevantes:
                    # Verificar se a notícia tem os campos necessários
                    if not isinstance(result, dict) or 'title' not in result or 'link' not in result:
                        print(f"Notícia ignorada por falta de campos obrigatórios")
                        continue
                        
                    print(f"Processando notícia: {result.get('title', 'Sem título')}")
                    try:
                        # Formatar a data para exibição
                        if 'published' in result:
                            data_publicacao = parser.parse(result['published'])
                            data_formatada = data_publicacao.strftime('%d/%m/%Y %H:%M')
                        else:
                            data_formatada = "N/A"
                        
                        # Adicionar dados da notícia
                        todas_noticias.append({
                            'Data da Consulta': consulta.get('data_hora', 'N/A'),
                            'Palavra-chave': result.get('keyword', 'N/A'),
                            'Título': result.get('title', 'N/A'),
                            'Fonte': result.get('source', 'N/A'),
                            'Data de Publicação': data_formatada,
                            'Idioma': result.get('language', 'N/A'),
                            'Link': result.get('link', '')
                        })
                        
                        print(f"Notícia adicionada à tabela: {result.get('title', 'Sem título')}")
                    except Exception as e:
                        print(f"Erro ao processar notícia: {e}")
            
            if not todas_noticias:
                st.info("Nenhuma notícia foi marcada como relevante em suas consultas.")
            else:
                # Criar DataFrame para a tabela de notícias
                # Verificar se há notícias para exibir
                print(f"Total de notícias relevantes encontradas: {len(todas_noticias)}")
                
                # Formatar os links antes de criar o DataFrame
                for noticia in todas_noticias:
                    if 'Link' in noticia and noticia['Link']:
                        noticia['Link'] = format_link(noticia['Link'])
                
                # Criar DataFrame apenas se houver notícias
                df_todas_noticias = pd.DataFrame(todas_noticias) if todas_noticias else pd.DataFrame(columns=[
                    'Data da Consulta', 'Palavra-chave', 'Título', 'Fonte', 
                    'Data de Publicação', 'Idioma', 'Link'
                ])
                
                # Exibir resultados
                total_noticias = len(todas_noticias)

                if total_noticias > 0:
                    st.write(f"Exibindo **{total_noticias}** notícias relevantes")
                    
                    # Exibir tabela de notícias
                    st.dataframe(
                        df_todas_noticias,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            'Link': st.column_config.LinkColumn(display_text="Abrir"),
                            'Data de Publicação': st.column_config.DatetimeColumn("Data de Publicação", format="DD/MM/YYYY HH:mm")
                        }
                    )
                else:
                    st.info("Nenhuma notícia foi marcada como relevante em suas consultas.")

                # Atualizar dados para exportação
                if not df_todas_noticias.empty:
                    st.session_state.tem_noticias_filtradas = True
                    st.session_state.csv_filtrado = df_todas_noticias.to_csv(index=False)
                    st.session_state.total_noticias_filtradas = len(df_todas_noticias)
                else:
                    st.session_state.tem_noticias_filtradas = False

                # Verificar se já temos notícias filtradas no session_state
                if not st.session_state.get('tem_noticias_filtradas', False):
                    st.info("Nenhuma notícia foi marcada como relevante em suas consultas.")
                
            # Removido o expander "Detalhes das Consultas" conforme solicitado
                    


# Aba 3: Gerenciar Palavras-chave
with tab3:
    if st.session_state.autenticado:
        st.header("Gerenciar Palavras-chave")
        
        # Carregar palavras-chave existentes do usuário
        username = st.session_state.username
        keywords = load_keywords(username)
        
        # Exibir informação sobre palavras-chave por usuário
        st.info(f"Você está gerenciando palavras-chave para o usuário: **{username}**")
        
        # Exibir palavras-chave existentes
        if keywords:
            st.subheader("Palavras-chave cadastradas")
            for i, keyword in enumerate(keywords, 1):
                st.text(f"{i}. {keyword}")
        else:
            st.info("Nenhuma palavra-chave cadastrada para este usuário.")
        
        # Adicionar nova palavra-chave usando formulário para evitar problemas com Enter
        st.subheader("Adicionar nova palavra-chave")
        
        with st.form(key="add_keyword_form"):
            new_keyword = st.text_input("Digite a nova palavra-chave:")
            submit_button = st.form_submit_button("Adicionar")
            
            if submit_button:
                if not new_keyword:
                    st.error("Por favor, digite uma palavra-chave antes de adicionar.")
                elif new_keyword in keywords:
                    st.warning(f"A palavra-chave '{new_keyword}' já está cadastrada.")
                else:
                    keywords.append(new_keyword)
                    save_keywords(keywords, username)
                    st.success(f"Palavra-chave '{new_keyword}' adicionada com sucesso!")
                    st.rerun()
        
        # Remover palavra-chave usando formulário para evitar problemas com Enter
        if keywords:
            st.subheader("Remover palavra-chave")
            
            with st.form(key="remove_keyword_form"):
                keyword_to_remove = st.selectbox("Selecione a palavra-chave para remover:", keywords)
                submit_button = st.form_submit_button("Remover")
                
                if submit_button:
                    keywords.remove(keyword_to_remove)
                    save_keywords(keywords, username)
                    st.success(f"Palavra-chave '{keyword_to_remove}' removida com sucesso!")
                    st.rerun()

# Aba 4: Estatísticas
with tab4:
    if st.session_state.autenticado:
        st.header("Estatísticas de Notícias Relevantes")
        
        # Botão para atualizar estatísticas
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("🔄 Atualizar", help="Recarregar dados para estatísticas"):
                st.rerun()
        with col2:
            st.write("Clique no botão para atualizar as estatísticas com os dados mais recentes.")
            
        if not st.session_state.historico_consultas:
            st.info("Nenhuma consulta salva no histórico. Realize buscas na aba 'Buscar Notícias' para gerar estatísticas.")
        else:
            # Função para processar os dados do histórico e gerar estatísticas
            def gerar_estatisticas_por_palavra_chave():
                # Dicionário para armazenar a contagem de notícias por palavra-chave
                contagem_por_palavra = {}
                total_noticias = 0
                
                # Processar cada consulta no histórico
                for consulta in st.session_state.historico_consultas:
                    # Filtrar apenas notícias relevantes
                    noticias_relevantes = [result for j, result in enumerate(consulta['resultados']) 
                                          if consulta['relevante_state'].get(str(j), False)]
                    
                    # Contar notícias por palavra-chave
                    for noticia in noticias_relevantes:
                        keyword = noticia['keyword']
                        if keyword in contagem_por_palavra:
                            contagem_por_palavra[keyword] += 1
                        else:
                            contagem_por_palavra[keyword] = 1
                        total_noticias += 1
                
                # Ordenar por contagem (do maior para o menor)
                contagem_ordenada = dict(sorted(contagem_por_palavra.items(), key=lambda x: x[1], reverse=True))
                
                return contagem_ordenada, total_noticias
            
            # Gerar estatísticas
            contagem_por_palavra, total_noticias = gerar_estatisticas_por_palavra_chave()
            
            if not contagem_por_palavra:
                st.warning("Nenhuma notícia relevante encontrada no histórico.")
            else:
                # Exibir resumo
                st.subheader("Resumo")
                st.write(f"Total de notícias relevantes: **{total_noticias}**")
                st.write(f"Número de palavras-chave diferentes: **{len(contagem_por_palavra)}**")
                
                # Exibir estatísticas em formato de texto
                st.subheader("Notícias por Palavra-chave")
                
                # Criar uma tabela com as contagens
                data = {
                    'Palavra-chave': list(contagem_por_palavra.keys()),
                    'Quantidade de Notícias': list(contagem_por_palavra.values()),
                    'Porcentagem': [f"{(count/total_noticias)*100:.1f}%" for count in contagem_por_palavra.values()]
                }
                
                df_estatisticas = pd.DataFrame(data)
                st.dataframe(df_estatisticas, use_container_width=True)
                
                # Exibir gráfico de barras
                st.subheader("Gráfico de Notícias por Palavra-chave")
                
                # Criar dataframe para o gráfico
                df_grafico = pd.DataFrame({
                    'Palavra-chave': list(contagem_por_palavra.keys()),
                    'Quantidade': list(contagem_por_palavra.values())
                })
                
                # Limitar a 15 palavras-chave para melhor visualização
                if len(df_grafico) > 15:
                    df_grafico = df_grafico.head(15)
                    st.info("Mostrando apenas as 15 palavras-chave mais frequentes no gráfico.")
                
                # Criar gráfico com Altair
                import altair as alt
                
                chart = alt.Chart(df_grafico).mark_bar().encode(
                    x=alt.X('Quantidade:Q', title='Quantidade de Notícias'),
                    y=alt.Y('Palavra-chave:N', sort='-x', title='Palavra-chave'),
                    tooltip=['Palavra-chave', 'Quantidade']
                ).properties(
                    title='Notícias Relevantes por Palavra-chave',
                    width=600,
                    height=400
                ).configure_axis(
                    labelFontSize=12,
                    titleFontSize=14
                )
                
                st.altair_chart(chart, use_container_width=True)
                
                # Opção para exportar os dados
                csv = df_estatisticas.to_csv(index=False)
                st.download_button(
                    label="⬇️ Baixar Estatísticas (CSV)",
                    data=csv,
                    file_name=f"estatisticas_palavras_chave_{datetime.datetime.now(fuso_brasil).strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    help="Baixe as estatísticas em formato CSV para análise detalhada"
                )


# Rodapé - visível para todos, mesmo sem autenticação
st.markdown("---")
st.markdown("📰 Radar de Mercado | Desenvolvido por Giovanni Cuchiaro com a ajuda do Streamlit")
