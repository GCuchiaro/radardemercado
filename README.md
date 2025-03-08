# Google News RSS Searcher

Este aplicativo permite que você cadastre palavras-chave e busque notícias relacionadas a essas palavras-chave no feed RSS do Google News dentro de um período específico.

## Funcionalidades

- Cadastro de palavras-chave
- Remoção de palavras-chave
- Visualização de palavras-chave cadastradas
- Busca de notícias por palavras-chave em períodos específicos:
  - Últimas 24 horas
  - Última semana
  - Último mês
  - Período personalizado
- Salvamento dos resultados em formatos TXT e JSON

## Requisitos

- Python 3.6 ou superior
- Bibliotecas: feedparser, python-dateutil, requests

## Instalação

1. Clone ou baixe este repositório
2. Instale as dependências:

```
pip install -r requirements.txt
```

## Como usar

1. Execute o script principal:

```
python google_news_searcher.py
```

2. Siga as instruções no menu para:
   - Adicionar palavras-chave
   - Remover palavras-chave
   - Ver palavras-chave cadastradas
   - Buscar notícias
   - Sair do programa

## Armazenamento de dados

As palavras-chave são salvas no arquivo `keywords.json` no mesmo diretório do script.
Os resultados das buscas podem ser salvos em arquivos TXT e JSON com o nome especificado pelo usuário.
