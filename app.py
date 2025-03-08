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

# Importações removidas - não estamos mais usando AgGrid

# Configuração da página
st.set_page_config(
    page_title="Google News Searcher",
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

# Função para fazer login
def fazer_login():
    if verificar_senha(st.session_state.senha):
        st.session_state.autenticado = True
    else:
        st.error("Senha incorreta. Tente novamente.")

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

# Tela de login (exibida apenas se não estiver autenticado)
if not st.session_state.autenticado:
    st.title("📰 Radar de Mercado IBBA - Login")
    st.markdown("Por favor, insira a senha para acessar o aplicativo.")
    
    # Campo de senha
    st.text_input("Senha", type="password", key="senha", on_change=fazer_login)
    
    # Botão de login
    if st.button("Entrar"):
        fazer_login()
        
    # Mensagem de rodapé
    st.markdown("---")
    st.markdown("*Este é um aplicativo restrito. Apenas usuários autorizados podem acessar.*")

# Título principal e abas (visíveis para todos)
st.title("📰 Radar de Mercado IBBA")

# Criação de abas (disponíveis para todos, mas conteúdo protegido)
tab1, tab2, tab3 = st.tabs(["Buscar Notícias", "Gerenciar Palavras-chave", "Sobre"])

# Conteúdo principal do aplicativo (exibido apenas se estiver autenticado)
if st.session_state.autenticado:
    st.markdown("Busque notícias relacionadas às suas palavras-chave de interesse no Google News.")
    
    # Botão de logout
    if st.sidebar.button("Sair"):
        # Limpar todas as variáveis de sessão relevantes
        st.session_state.autenticado = False
        if 'all_results' in st.session_state:
            del st.session_state.all_results
        if 'relevante_state' in st.session_state:
            del st.session_state.relevante_state
        if 'busca_realizada' in st.session_state:
            del st.session_state.busca_realizada
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
                horizontal=True
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
                horizontal=True
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
            if st.button("Buscar Notícias", type="primary", disabled=not selected_keywords):
                st.session_state._button_clicked = True
                if selected_keywords:
                    realizar_busca()
            
            # Função de callback para atualizar o estado do checkbox
            def update_checkbox_state(i):
                checkbox_key = f"relevante_{i}_{hash(st.session_state.all_results[i]['title'])}"
                st.session_state.relevante_state[i] = st.session_state[checkbox_key]
        
            # Exibir resultados se existirem na session_state
            if st.session_state.all_results:
                # Exibir tabela de resultados
                st.subheader(f"Resultados da Busca ({len(st.session_state.all_results)} notícias)")
                
                # Criar cabeçalho da tabela
                header_cols = st.columns([0.05, 0.15, 0.3, 0.2, 0.1, 0.2])
                header_cols[0].write("**Índice**")
                header_cols[1].write("**Palavra-chave**")
                header_cols[2].write("**Título**")
                header_cols[3].write("**Data/Hora**")
                header_cols[4].write("**Link**")
                header_cols[5].write("**Relevante**")
                
                # Exibir cada linha da tabela
                for i, result in enumerate(st.session_state.all_results):
                    # Criar colunas para cada linha
                    row_cols = st.columns([0.05, 0.15, 0.3, 0.2, 0.1, 0.2])
                    
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
                    
                    # Checkbox para marcar como relevante (no final da linha)
                    # Usando uma chave única baseada no índice e título para evitar conflitos
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
                for result in st.session_state.all_results:
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
                
                # Botão para download direto em CSV
                st.download_button(
                    label="Baixar Resultados (CSV)",
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

# Aba 2: Gerenciar Palavras-chave
with tab2:
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

# Aba 3: Sobre
with tab3:
    if st.session_state.autenticado:
        st.header("Sobre o Radar de Mercado IBBA")
        st.markdown("""
        ### Descrição
        O Radar de Mercado IBBA é uma aplicação que permite buscar notícias relacionadas a palavras-chave específicas no feed RSS do Google News.
        
        ### Funcionalidades
        - Cadastro de palavras-chave de interesse
        - Busca de notícias em português e inglês
        - Filtragem por período de tempo
        - Salvamento dos resultados em formato texto e JSON
        
        ### Como usar
        1. Cadastre suas palavras-chave na aba "Gerenciar Palavras-chave"
        2. Vá para a aba "Buscar Notícias"
        3. Selecione as palavras-chave, idioma e período de busca
        4. Clique em "Buscar Notícias"
        5. Visualize os resultados e salve-os se desejar
    
        ### Desenvolvido por
        Esta aplicação foi desenvolvida como um projeto para busca de notícias utilizando o feed RSS do Google News.
        """)

# Rodapé - visível para todos, mesmo sem autenticação
st.markdown("---")
st.markdown("📰 Radar de Mercado IBBA | Desenvolvido com Streamlit")
