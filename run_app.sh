#!/bin/bash

# Cores para melhorar a visualização
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Google News Searcher - Script de Inicialização ===${NC}"

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python 3 não encontrado. Por favor, instale o Python 3 para continuar.${NC}"
    exit 1
fi

# Diretório do script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Verificar se o ambiente virtual existe
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Ambiente virtual não encontrado. Criando...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}Erro ao criar o ambiente virtual. Tentando instalar venv...${NC}"
        pip3 install virtualenv
        python3 -m venv venv
        if [ $? -ne 0 ]; then
            echo -e "${YELLOW}Falha ao criar ambiente virtual. Tentando executar sem ambiente virtual...${NC}"
            pip3 install --break-system-packages -r requirements.txt
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}Dependências instaladas globalmente com sucesso.${NC}"
                streamlit run app.py
                exit 0
            else
                echo -e "${YELLOW}Falha ao instalar dependências. Verifique sua instalação do Python.${NC}"
                exit 1
            fi
        fi
    fi
fi

# Ativar o ambiente virtual e instalar dependências
echo -e "${BLUE}Ativando ambiente virtual...${NC}"
source venv/bin/activate

# Verificar se as dependências estão instaladas
if ! python -c "import streamlit" &> /dev/null; then
    echo -e "${YELLOW}Instalando dependências...${NC}"
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}Erro ao instalar dependências. Tentando com --break-system-packages...${NC}"
        pip install --break-system-packages -r requirements.txt
        if [ $? -ne 0 ]; then
            echo -e "${YELLOW}Falha ao instalar dependências. Verifique sua instalação do Python.${NC}"
            exit 1
        fi
    fi
fi

# Executar o aplicativo
echo -e "${GREEN}Iniciando o aplicativo Google News Searcher...${NC}"
echo -e "${BLUE}O aplicativo será aberto no seu navegador em alguns instantes.${NC}"
echo -e "${BLUE}Para encerrar o aplicativo, pressione Ctrl+C neste terminal.${NC}"
streamlit run app.py

# Desativar o ambiente virtual ao sair
deactivate
