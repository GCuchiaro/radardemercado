#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Patch for feedparser in Python 3.13 where cgi module is removed
import sys
import html

# Create a mock CGIModule with required functions
class CGIModule:
    @staticmethod
    def escape(s):
        return html.escape(s)
    
    @staticmethod
    def parse_header(line):
        # Simple implementation of parse_header
        if not line:
            return '', {}
        parts = line.split(';')
        key = parts[0].strip()
        params = {}
        for param in parts[1:]:
            if '=' in param:
                name, value = param.split('=', 1)
                name = name.strip()
                value = value.strip().strip('"')
                params[name] = value
        return key, params

# Replace the removed cgi module with our mock
sys.modules['cgi'] = CGIModule

import feedparser
import datetime
import time
from dateutil import parser
from dateutil.relativedelta import relativedelta
import os
import json
import urllib.parse
import requests

class GoogleNewsSearcher:
    def __init__(self):
        self.keywords = []
        self.config_file = "keywords.json"
        # Configurações de idioma para as buscas
        self.language_configs = {
            'pt': {'hl': 'pt-BR', 'gl': 'BR', 'ceid': 'BR:pt-419', 'name': 'Português'},
            'en': {'hl': 'en-US', 'gl': 'US', 'ceid': 'US:en', 'name': 'Inglês'}
        }
        self.load_keywords()
        
    def load_keywords(self):
        """Load saved keywords from file if it exists"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.keywords = json.load(f)
                print(f"Palavras-chave carregadas: {', '.join(self.keywords)}")
            except Exception as e:
                print(f"Erro ao carregar palavras-chave: {e}")
                self.keywords = []
    
    def save_keywords(self):
        """Save keywords to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.keywords, f, ensure_ascii=False)
            print("Palavras-chave salvas com sucesso!")
        except Exception as e:
            print(f"Erro ao salvar palavras-chave: {e}")
    
    def add_keywords(self):
        """Add new keywords to the list"""
        print("\n=== Adicionar Palavras-chave ===")
        while True:
            keyword = input("Digite uma palavra-chave (ou deixe em branco para terminar): ").strip()
            if not keyword:
                break
            
            if keyword in self.keywords:
                print(f"A palavra-chave '{keyword}' já existe na lista.")
            else:
                self.keywords.append(keyword)
                print(f"Palavra-chave '{keyword}' adicionada com sucesso!")
        
        self.save_keywords()
    
    def remove_keywords(self):
        """Remove keywords from the list"""
        if not self.keywords:
            print("Não há palavras-chave para remover.")
            return
            
        print("\n=== Remover Palavras-chave ===")
        for i, keyword in enumerate(self.keywords, 1):
            print(f"{i}. {keyword}")
        
        while True:
            choice = input("\nDigite o número da palavra-chave a remover (ou deixe em branco para terminar): ").strip()
            if not choice:
                break
                
            try:
                index = int(choice) - 1
                if 0 <= index < len(self.keywords):
                    removed = self.keywords.pop(index)
                    print(f"Palavra-chave '{removed}' removida com sucesso!")
                else:
                    print("Número inválido.")
            except ValueError:
                print("Por favor, digite um número válido.")
        
        self.save_keywords()
    
    def view_keywords(self):
        """Display all saved keywords"""
        print("\n=== Palavras-chave Cadastradas ===")
        if not self.keywords:
            print("Nenhuma palavra-chave cadastrada.")
            return
            
        for i, keyword in enumerate(self.keywords, 1):
            print(f"{i}. {keyword}")
    
    def search_news(self):
        """Search for news based on keywords and time period"""
        if not self.keywords:
            print("Não há palavras-chave cadastradas. Por favor, adicione algumas palavras-chave primeiro.")
            return []
        
        print("\n=== Buscar Notícias ===")
        print("Palavras-chave disponíveis:")
        for i, keyword in enumerate(self.keywords, 1):
            print(f"{i}. {keyword}")
        
        # Select keywords to search
        while True:
            choice = input("\nDigite os números das palavras-chave separados por vírgula (ou 'todas' para todas): ").strip().lower()
            if not choice:
                return
                
            if choice == 'todas':
                selected_keywords = self.keywords.copy()
                break
                
            try:
                indices = [int(idx.strip()) - 1 for idx in choice.split(',')]
                selected_keywords = [self.keywords[idx] for idx in indices if 0 <= idx < len(self.keywords)]
                if selected_keywords:
                    break
                else:
                    print("Nenhuma palavra-chave válida selecionada.")
            except ValueError:
                print("Por favor, digite números válidos separados por vírgula.")
        
        # Selecionar idiomas para busca
        print("\nIdiomas disponíveis para busca:")
        print("1. Português")
        print("2. Inglês")
        print("3. Ambos")
        
        while True:
            lang_choice = input("Escolha uma opção (1-3): ").strip()
            
            if lang_choice == '1':
                selected_languages = ['pt']
                break
            elif lang_choice == '2':
                selected_languages = ['en']
                break
            elif lang_choice == '3':
                selected_languages = ['pt', 'en']
                break
            else:
                print("Opção inválida. Por favor, escolha entre 1 e 3.")
        
        # Get time period
        print("\nPeríodo de busca:")
        print("1. Últimas 24 horas")
        print("2. Última semana")
        print("3. Último mês")
        print("4. Período personalizado")
        
        while True:
            period_choice = input("Escolha uma opção (1-4): ").strip()
            
            if period_choice == '1':
                start_date = datetime.datetime.now() - datetime.timedelta(days=1)
                end_date = datetime.datetime.now()
                break
            elif period_choice == '2':
                start_date = datetime.datetime.now() - datetime.timedelta(days=7)
                end_date = datetime.datetime.now()
                break
            elif period_choice == '3':
                start_date = datetime.datetime.now() - relativedelta(months=1)
                end_date = datetime.datetime.now()
                break
            elif period_choice == '4':
                try:
                    start_date_str = input("Data inicial (DD/MM/AAAA): ").strip()
                    start_date = datetime.datetime.strptime(start_date_str, "%d/%m/%Y")
                    
                    end_date_str = input("Data final (DD/MM/AAAA): ").strip()
                    end_date = datetime.datetime.strptime(end_date_str, "%d/%m/%Y") + datetime.timedelta(days=1, seconds=-1)
                    break
                except ValueError:
                    print("Formato de data inválido. Use DD/MM/AAAA.")
            else:
                print("Opção inválida. Por favor, escolha entre 1 e 4.")
        
        # Perform search for each keyword
        print(f"\nBuscando notícias de {start_date.strftime('%d/%m/%Y')} até {end_date.strftime('%d/%m/%Y')}...")
        
        all_results = []
        for keyword in selected_keywords:
            for lang in selected_languages:
                lang_name = self.language_configs[lang]['name']
                print(f"\nBuscando por: '{keyword}' em {lang_name}")
                results = self._fetch_news(keyword, start_date, end_date, lang)
                
                if results:
                    all_results.extend(results)
                    print(f"Encontradas {len(results)} notícias para '{keyword}' em {lang_name}")
                else:
                    print(f"Nenhuma notícia encontrada para '{keyword}' em {lang_name}")
        
        # Display results
        if all_results:
            self._display_results(all_results)
            
            # Option to save results
            save_option = input("\nDeseja salvar os resultados? (s/n): ").strip().lower()
            if save_option == 's':
                filename = input("Nome do arquivo (sem extensão): ").strip()
                if not filename:
                    filename = f"noticias_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                self._save_results(all_results, filename)
            
            return all_results
        else:
            print("\nNenhuma notícia encontrada para as palavras-chave e período especificados.")
            return []
    
    def _fetch_news(self, keyword, start_date, end_date, language='pt'):
        """Fetch news from Google News RSS feed for a specific keyword"""
        # URL encode the keyword
        encoded_keyword = urllib.parse.quote(keyword)
        
        # Get language configuration
        lang_config = self.language_configs[language]
        
        # Google News RSS URL
        url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl={lang_config['hl']}&gl={lang_config['gl']}&ceid={lang_config['ceid']}"
        
        try:
            # Parse the RSS feed
            feed = feedparser.parse(url)
            
            results = []
            for entry in feed.entries:
                # Parse the publication date
                try:
                    pub_date = parser.parse(entry.published)
                    
                    # Convert aware datetime to naive datetime for comparison
                    if pub_date.tzinfo is not None:
                        # Convert to UTC and then remove timezone info
                        pub_date = pub_date.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                    
                    # Check if the publication date is within the specified range
                    if start_date <= pub_date <= end_date:
                        # Criar um dicionário com os dados básicos da notícia
                        news_item = {
                            'title': entry.title,
                            'link': entry.link,
                            'published': pub_date.strftime('%d/%m/%Y %H:%M'),
                            'source': entry.source.title if hasattr(entry, 'source') else "Google News",
                            'keyword': keyword,
                            'language': self.language_configs[language]['name']
                        }
                        
                        results.append(news_item)
                except Exception as e:
                    print(f"Erro ao processar data de publicação: {e}")
                    continue
            
            return results
        except Exception as e:
            print(f"Erro ao buscar notícias: {e}")
            return []
    

    
    def _display_results(self, results):
        """Display search results in a formatted way"""
        # Sort results by date (newest first)
        results.sort(key=lambda x: parser.parse(x['published']), reverse=True)
        
        print(f"\n=== Resultados da Busca ({len(results)} notícias) ===")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['title']}")
            print(f"   Fonte: {result['source']}")
            print(f"   Data: {result['published']}")
            print(f"   Palavra-chave: {result['keyword']}")
            print(f"   Idioma: {result['language']}")
            print(f"   Link: {result['link']}")
    

    
    def _save_results(self, results, filename):
        """Save search results to a file"""
        try:
            # Sort results by date (newest first)
            results.sort(key=lambda x: parser.parse(x['published']), reverse=True)
            
            # Save as text file
            with open(f"{filename}.txt", 'w', encoding='utf-8') as f:
                f.write(f"=== Resultados da Busca ({len(results)} notícias) ===\n\n")
                for i, result in enumerate(results, 1):
                    f.write(f"{i}. {result['title']}\n")
                    f.write(f"   Fonte: {result['source']}\n")
                    f.write(f"   Data: {result['published']}\n")
                    f.write(f"   Palavra-chave: {result['keyword']}\n")
                    f.write(f"   Idioma: {result['language']}\n")
                    f.write(f"   Link: {result['link']}\n\n")
            
            # Save as JSON for potential future use
            with open(f"{filename}.json", 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"\nResultados salvos em '{filename}.txt' e '{filename}.json'")
        except Exception as e:
            print(f"Erro ao salvar resultados: {e}")

def main():
    searcher = GoogleNewsSearcher()
    last_results = []
    
    while True:
        print("\n=== Google News Searcher ===")
        print("1. Adicionar palavras-chave")
        print("2. Remover palavras-chave")
        print("3. Ver palavras-chave cadastradas")
        print("4. Buscar notícias")
        print("5. Sair")
        
        choice = input("\nEscolha uma opção (1-5): ").strip()
        
        if choice == '1':
            searcher.add_keywords()
        elif choice == '2':
            searcher.remove_keywords()
        elif choice == '3':
            searcher.view_keywords()
        elif choice == '4':
            results = searcher.search_news()
            if results:
                last_results = results
        elif choice == '5':
            print("Obrigado por usar o Google News Searcher!")
            break
        else:
            print("Opção inválida. Por favor, escolha entre 1 e 5.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nPrograma interrompido pelo usuário.")
        sys.exit(0)
