import streamlit as st
import pandas as pd
import json
import os
import datetime
import pytz
import sys
import hashlib
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
    # Compara a senha informada com a senha padrão
    return senha_informada == SENHA_PADRAO

# Inicializar estado de autenticação
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    
# Inicializar nome de usuário
if 'username' not in st.session_state:
    st.session_state.username = ""

# Função para fazer login
def fazer_login(senha):
    username = st.session_state.get('username', '').strip()
    
    if not username:
        st.error("Por favor, informe seu nome de usuário.")
        return
        
    if not senha:
        st.error("Por favor, informe a senha.")
        return
        
    if not verificar_senha(senha):
        st.error("Senha incorreta. Tente novamente.")
        return
    
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

# Inicializar session_state para armazenar resultados e estado dos checkboxes
if 'all_results' not in st.session_state:
    st.session_state.all_results = []
    
if 'relevante_state' not in st.session_state:
    st.session_state.relevante_state = {}
    
# Flag para rastrear quando o botão de busca foi clicado
if '_button_clicked' not in st.session_state:
    st.session_state._button_clicked = False
    
# Inicializar histórico de consultas
if 'historico_consultas' not in st.session_state:
    st.session_state.historico_consultas = []

# Função para carregar as palavras-chave
def load_keywords():
    if os.path.exists(searcher.config_file):
        try:
            with open(searcher.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('keywords', [])
        except Exception as e:
            st.error(f"Erro ao carregar palavras-chave: {e}")
            return []
    return []

# Função para salvar as palavras-chave
def save_keywords(keywords):
    try:
        with open(searcher.config_file, 'w', encoding='utf-8') as f:
            json.dump({'keywords': keywords}, f, ensure_ascii=False, indent=2)
        st.success("Palavras-chave salvas com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar palavras-chave: {e}")
        
# Funções para gerenciar o histórico de consultas por usuário
def get_user_history_file(username):
    # Verificar se o nome de usuário não está vazio
    if not username or not username.strip():
        raise ValueError("Nome de usuário não pode ser vazio")
        
    # Criar um nome de arquivo seguro baseado no nome do usuário
    safe_username = ''.join(c if c.isalnum() else '_' for c in username.lower().strip())
    return os.path.join(os.path.dirname(searcher.config_file), f"historico_{safe_username}.json")

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

        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(historico, f, ensure_ascii=False, indent=2, default=json_serializable)
            
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

def load_user_history(username):
    try:
        if not username or not username.strip():
            print(f"Tentativa de carregar histórico com nome de usuário vazio.")
            return []
            
        history_file = get_user_history_file(username)
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                historico = json.load(f)
                # Garantir que todas as consultas tenham a estrutura correta
                historico_validado = []
                for consulta in historico:
                    # Verificar se todos os campos necessários existem
                    if 'resultados' not in consulta or 'relevante_state' not in consulta:
                        continue
                        
                    # Garantir que o usuário está correto
                    consulta['usuario'] = username
                    
                    # Garantir que relevante_state use chaves como strings
                    if not isinstance(next(iter(consulta['relevante_state'] or {"0": False})), str):
                        consulta['relevante_state'] = {str(k): v for k, v in consulta['relevante_state'].items()}
                        
                    historico_validado.append(consulta)
                return historico_validado
        return []
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")
        return []

# Container principal para o aplicativo
main_container = st.container()

# Tela de login (exibida apenas se não estiver autenticado)
if not st.session_state.autenticado:
    with main_container:
        st.title("📰 Radar de Mercado IBBA - Login")
        st.markdown("Por favor, informe seu nome e a senha para acessar o aplicativo.")
        
        # Campo para nome de usuário
        username = st.text_input("Nome de usuário", value=st.session_state.get('username', ''), placeholder="Digite seu nome").strip()
        
        # Campo de senha
        senha = st.text_input("Senha", type="password", key="senha")
        
        # Botão de login
        if st.button("Entrar"):
            # Atualizar username e verificar login
            st.session_state.username = username
            if fazer_login(senha):
                main_container.empty()
                st.experimental_rerun()
        
        # Mensagem de rodapé
        st.markdown("---")
        st.markdown("*Este é um aplicativo restrito. Apenas usuários autorizados podem acessar.*")
        st.stop()

# Título principal (visível apenas após login)
st.title("📰 Radar de Mercado IBBA")

# Criação de abas (disponíveis para todos, mas conteúdo protegido)
tab1, tab2, tab3, tab4 = st.tabs(["Buscar Notícias", "Histórico de Consultas", "Gerenciar Palavras-chave", "Sobre"])

# Conteúdo principal do aplicativo (exibido apenas se estiver autenticado)
if st.session_state.autenticado:
    st.markdown("Busque notícias relacionadas às suas palavras-chave de interesse no Google News.")
    
    # Exibir informações do usuário logado na barra lateral
    st.sidebar.write(f"Usuário: **{st.session_state.username}**")
    
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
        
        # Carregar palavras-chave
        keywords = load_keywords()
        
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
                with st.spinner("Buscando notícias para todas as palavras-chave e idiomas selecionados..."):
                    all_results = []
                    
                    # Buscar para cada palavra-chave e idioma sem mostrar status parcial
                    for keyword in selected_keywords:
                        for language in selected_languages:
                            # Converter datas para o formato esperado pelo método _fetch_news
                            start_date_obj = datetime.datetime.strptime(start_date, '%d/%m/%Y')
                            end_date_obj = datetime.datetime.strptime(end_date, '%d/%m/%Y')
                            
                            results = searcher._fetch_news(
                                keyword, 
                                start_date_obj, 
                                end_date_obj, 
                                language
                            )
                            
                            if results:
                                all_results.extend(results)
                    
                    # Ordenar por data (mais recentes primeiro) se houver resultados
                    if all_results:
                        from dateutil import parser
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
            # Botão para buscar
            if st.button("🔍 Buscar Notícias", type="primary", help="Clique para buscar notícias com os filtros selecionados"):
                st.session_state._button_clicked = True
                with st.spinner('🔄 Buscando notícias... Por favor, aguarde...'):
                    realizar_busca()
                    if not st.session_state.all_results:
                        st.warning("⚠️ Nenhuma notícia encontrada para os critérios selecionados. Tente ajustar os filtros.")
            
            # Função de callback para atualizar o estado do checkbox
            def update_checkbox_state(i):
                checkbox_key = f"relevante_{i}_{hash(st.session_state.all_results[i]['title'])}"
                st.session_state.relevante_state[i] = st.session_state[checkbox_key]
        
            # Exibir resultados se existirem na session_state
            if st.session_state.all_results:
                # Exibir tabela de resultados
                st.subheader(f"Resultados da Busca ({len(st.session_state.all_results)} notícias)")
                
                # Botões de ação no final da tabela
                st.markdown("---")
                col1, col2 = st.columns(2)
                
                with col2:
                    # Botão para salvar notícias relevantes
                    if st.button("💾 Salvar Notícias Relevantes", type="primary", help="Salvar as notícias marcadas como relevantes no histórico"):
                        # Filtrar apenas as notícias marcadas como relevantes
                        noticias_relevantes = []
                        for i, result in enumerate(st.session_state.all_results):
                            if st.session_state.relevante_state.get(i, False):
                                noticias_relevantes.append(result)
                    
                        if not noticias_relevantes:
                            st.warning("Nenhuma notícia foi marcada como relevante.")
                        else:
                            # Criar um ID único para a consulta baseado na data/hora
                            consulta_id = datetime.datetime.now(fuso_brasil).strftime('%Y%m%d_%H%M%S')
                            
                            # Criar dicionário de relevância apenas para as notícias relevantes
                            relevante_state = {str(i): True for i in range(len(noticias_relevantes))}
                            
                            # Salvar parâmetros e resultados da consulta
                            consulta = {
                                'id': consulta_id,
                                'data_hora': datetime.datetime.now(fuso_brasil).strftime('%d/%m/%Y %H:%M'),
                                'usuario': st.session_state.username,
                                'parametros': {
                                    'keywords': selected_keywords,
                                    'languages': selected_languages,
                                    'period': period_option,
                                    'start_date': start_date,
                                    'end_date': end_date
                                },
                                'resultados': noticias_relevantes,
                                'relevante_state': relevante_state
                            }
                            
                            # Garantir que o histórico existe na sessão
                            if 'historico_consultas' not in st.session_state:
                                st.session_state.historico_consultas = []
                            
                            # Adicionar ao histórico (no início da lista para mostrar mais recentes primeiro)
                            st.session_state.historico_consultas.insert(0, consulta)
                            
                            try:
                                # Salvar o histórico do usuário
                                if save_user_history(st.session_state.username, st.session_state.historico_consultas):
                                    st.success(f"{len(noticias_relevantes)} notícias relevantes salvas no histórico!")
                                else:
                                    st.error("Não foi possível salvar as notícias no histórico.")
                            except Exception as e:
                                st.error(f"Erro ao salvar notícias no histórico: {e}")
                
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
                    from dateutil import parser
                    data_publicacao = parser.parse(result['published'])
                    data_formatada = data_publicacao.strftime('%d/%m/%Y %H:%M')
                    
                    # Dados da notícia
                    row_cols[0].write(str(i))
                    row_cols[1].write(result['keyword'])
                    row_cols[2].write(result['title'])
                    row_cols[3].write(data_formatada)
                    row_cols[4].markdown(f"[Abrir]({result['link']})")
                    
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
            col1, col2 = st.columns([0.7, 0.3])
            with col1:
                st.write(f"Total de consultas salvas: {len(st.session_state.historico_consultas)}")
            
            with col2:
                # Botão para exportar todo o histórico
                if st.button("📥 Exportar Todo o Histórico", help="Baixe todas as notícias relevantes em um único arquivo CSV"):
                    df_historico = export_all_history_to_csv(st.session_state.historico_consultas)
                    if df_historico is not None:
                        csv = df_historico.to_csv(index=False)
                        st.download_button(
                            label="⬇️ Baixar CSV",
                            data=csv,
                            file_name=f"historico_completo_{st.session_state.username}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            help="Clique para baixar o arquivo CSV com todo o histórico de notícias relevantes"
                        )
                    else:
                        st.info("Não há notícias relevantes no histórico para exportar.")
            
            # Exibir consultas em formato de acordeão
            for i, consulta in enumerate(st.session_state.historico_consultas):
                with st.expander(f"Consulta {i+1} - {consulta['data_hora']}"):
                    # Exibir parâmetros da consulta
                    st.subheader("Parâmetros da Consulta")
                    st.write(f"**Palavras-chave:** {', '.join(consulta['parametros']['keywords'])}")
                    st.write(f"**Idiomas:** {', '.join(consulta['parametros']['languages'])}")
                    st.write(f"**Período:** {consulta['parametros']['period']}")
                    st.write(f"**Data inicial:** {consulta['parametros']['start_date']}")
                    st.write(f"**Data final:** {consulta['parametros']['end_date']}")
                    
                    # Filtrar apenas notícias relevantes
                    noticias_relevantes = [result for j, result in enumerate(consulta['resultados']) if consulta['relevante_state'].get(str(j), False)]
                    
                    # Exibir resultados da consulta
                    st.subheader(f"Notícias Relevantes ({len(noticias_relevantes)} notícias)")
                    
                    if not noticias_relevantes:
                        st.info("Nenhuma notícia foi marcada como relevante nesta consulta.")
                    
                    if noticias_relevantes:
                        # Criar tabela de resultados
                        header_cols = st.columns([0.05, 0.15, 0.35, 0.25, 0.2])
                        header_cols[0].write("**Índice**")
                        header_cols[1].write("**Palavra-chave**")
                        header_cols[2].write("**Título**")
                        header_cols[3].write("**Data/Hora**")
                        header_cols[4].write("**Link**")
                        
                        # Exibir cada linha da tabela
                        for j, result in enumerate(noticias_relevantes):
                            # Criar colunas para cada linha
                            row_cols = st.columns([0.05, 0.15, 0.35, 0.25, 0.2])
                            
                            # Formatar a data para exibição
                            from dateutil import parser
                            data_publicacao = parser.parse(result['published'])
                            data_formatada = data_publicacao.strftime('%d/%m/%Y %H:%M')
                            
                            # Dados da notícia
                            row_cols[0].write(str(j))
                            row_cols[1].write(result['keyword'])
                            row_cols[2].write(result['title'])
                            row_cols[3].write(data_formatada)
                            row_cols[4].markdown(f"[Abrir]({result['link']})")
                    
                    if noticias_relevantes:
                        # Preparar CSV para download
                        datas_formatadas = []
                        for result in noticias_relevantes:
                            data_publicacao = parser.parse(result['published'])
                            datas_formatadas.append(data_publicacao.strftime('%d/%m/%Y %H:%M'))
                        
                        csv_data = pd.DataFrame({
                            'Índice': list(range(len(noticias_relevantes))),
                            'Palavra-chave': [result['keyword'] for result in noticias_relevantes],
                            'Título': [result['title'] for result in noticias_relevantes],
                            'Fonte': [result['source'] for result in noticias_relevantes],
                            'Data/Hora': datas_formatadas,
                            'Idioma': [result['language'] for result in noticias_relevantes],
                            'Link': [result['link'] for result in noticias_relevantes]
                        })
                        
                        # Converter para CSV
                        csv = csv_data.to_csv(index=False)
                        
                        # Botão para download direto em CSV
                        st.download_button(
                            label="Baixar Notícias Relevantes (CSV)",
                            data=csv,
                            file_name=f"noticias_relevantes_{consulta['id']}.csv",
                            mime="text/csv",
                            help="Baixe as notícias relevantes em formato CSV para abrir em Excel ou outro programa de planilhas"
                        )
                    


# Aba 3: Gerenciar Palavras-chave
with tab3:
    if st.session_state.autenticado:
        st.header("Gerenciar Palavras-chave")
        
        # Carregar palavras-chave existentes
        keywords = load_keywords()
        
        # Exibir palavras-chave existentes
        if keywords:
            st.subheader("Palavras-chave cadastradas")
            for i, keyword in enumerate(keywords, 1):
                st.text(f"{i}. {keyword}")
        else:
            st.info("Nenhuma palavra-chave cadastrada.")
        
        # Adicionar nova palavra-chave
        st.subheader("Adicionar nova palavra-chave")
        new_keyword = st.text_input("Digite a nova palavra-chave:")
        
        if st.button("Adicionar", disabled=not new_keyword):
            if new_keyword and new_keyword not in keywords:
                keywords.append(new_keyword)
                save_keywords(keywords)
                st.experimental_rerun()
            elif new_keyword in keywords:
                st.warning(f"A palavra-chave '{new_keyword}' já está cadastrada.")
        
        # Remover palavra-chave
        if keywords:
            st.subheader("Remover palavra-chave")
            keyword_to_remove = st.selectbox("Selecione a palavra-chave para remover:", keywords)
            
            if st.button("Remover"):
                keywords.remove(keyword_to_remove)
                save_keywords(keywords)
                st.experimental_rerun()

# Aba 4: Sobre
with tab4:
    if st.session_state.autenticado:
        st.header("Sobre o Radar de Mercado IBBA")
        st.markdown("""
        ### Descrição
        O Radar de Mercado IBBA é uma aplicação segura e eficiente que permite monitorar notícias relacionadas a palavras-chave específicas no feed RSS do Google News, facilitando a análise de informações relevantes para o mercado financeiro e corporativo.
        
        ### Funcionalidades
        - Sistema de autenticação com senha para acesso seguro
        - Cadastro e gerenciamento de palavras-chave de interesse
        - Busca de notícias em português e inglês com fuso horário brasileiro
        - Filtragem por período de tempo (24h, 7 dias ou período personalizado)
        - Marcação de notícias relevantes para análise posterior
        - Exportação dos resultados em formato CSV para análise em Excel
        - Histórico de consultas com acesso a buscas anteriores
        
        ### Como usar
        1. Faça login com a senha fornecida pelo administrador
        2. Cadastre suas palavras-chave de interesse na aba "Gerenciar Palavras-chave"
        3. Na aba "Buscar Notícias", selecione as palavras-chave, idiomas e período desejado
        4. Clique em "Buscar Notícias" para obter os resultados
        5. Marque as notícias relevantes usando os checkboxes na tabela
        6. Baixe os resultados em formato CSV para análise detalhada
        7. Acesse suas consultas anteriores na aba "Histórico de Consultas"
    
        ### Desenvolvido para
        Esta aplicação foi desenvolvida exclusivamente para o IBBA como ferramenta de monitoramento de notícias e informações de mercado.
        """)

# Rodapé - visível para todos, mesmo sem autenticação
st.markdown("---")
st.markdown("📰 Radar de Mercado IBBA | Desenvolvido por Giovanni Cuchiaro com a ajuda do Streamlit")
