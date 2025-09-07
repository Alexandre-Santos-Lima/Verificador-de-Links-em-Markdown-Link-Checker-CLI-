# -*- coding: utf-8 -*-

# ---
# Projeto: Verificador de Links em Markdown (Link-Checker CLI)
# Descrição: Uma ferramenta de linha de comando que lê um arquivo Markdown, encontra
#            todos os URLs e verifica se eles estão ativos (retornam um status 2xx)
#            ou quebrados. As requisições são feitas de forma concorrente para
#            melhorar a performance.
#
# Bibliotecas necessárias:
#   - requests: Para fazer as requisições HTTP.
#   Instale com: pip install requests
#
# Como executar:
#   python main.py /caminho/para/seu/arquivo.md
#
# Exemplo de uso:
#   python main.py README.md
# ---

import sys
import re
import argparse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Constantes de Cores para o Terminal ---
class Colors:
    """Classe para armazenar códigos de cores ANSI para o terminal."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

# --- Funções Core ---

def extract_urls_from_file(filepath):
    """
    Lê um arquivo e extrai todos os URLs absolutos (http/https) usando expressões regulares.
    Retorna uma lista de URLs únicos.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # Regex para encontrar URLs http e https
            url_pattern = re.compile(r'https?://[^\s)\]]+')
            urls = url_pattern.findall(content)
            # Retorna apenas URLs únicos para evitar verificações duplicadas
            return sorted(list(set(urls)))
    except FileNotFoundError:
        print(f"{Colors.RED}Erro: O arquivo '{filepath}' não foi encontrado.{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}Erro ao ler o arquivo: {e}{Colors.RESET}")
        sys.exit(1)

def check_url_status(url, timeout=10):
    """
    Verifica o status de um único URL fazendo uma requisição HEAD.
    Retorna uma tupla contendo (url, status_code, status_text).
    """
    try:
        # Usamos uma requisição HEAD para ser mais rápido, pois não baixamos o corpo da página.
        # allow_redirects=True garante que seguimos redirecionamentos.
        response = requests.head(url, timeout=timeout, allow_redirects=True, headers={'User-Agent': 'MarkdownLinkChecker/1.0'})
        status_code = response.status_code
        # Para códigos de sucesso (2xx), pegamos o 'reason' (ex: 'OK')
        status_text = response.reason if 200 <= status_code < 300 else f"Client/Server Error"
    except requests.Timeout:
        status_code = 408
        status_text = "Timeout"
    except requests.RequestException as e:
        # Captura outras exceções de requisição (ex: erro de DNS, conexão recusada)
        status_code = 0  # Usamos 0 para erros de conexão
        status_text = f"Connection Error: {str(e)[:50]}..."
    
    return url, status_code, status_text

def print_result(url, status_code, status_text):
    """Formata e imprime o resultado da verificação do URL com cores."""
    if 200 <= status_code < 300:
        status_colored = f"{Colors.GREEN}[{status_code} {status_text}]{Colors.RESET}"
    elif 400 <= status_code < 500 or status_code == 408:
        status_colored = f"{Colors.YELLOW}[{status_code} {status_text}]{Colors.RESET}"
    else:
        status_colored = f"{Colors.RED}[{status_code} {status_text}]{Colors.RESET}"

    print(f"{status_colored} {url}")

# --- Função Principal de Execução ---

def main():
    """
    Ponto de entrada do script. Orquestra a extração, verificação e
    apresentação dos resultados.
    """
    parser = argparse.ArgumentParser(
        description="Verificador de Links em Arquivos Markdown.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("filepath", help="O caminho para o arquivo .md a ser verificado.")
    parser.add_argument("-w", "--workers", type=int, default=10, help="Número de workers concorrentes para verificar os links.")
    
    args = parser.parse_args()
    
    print(f"{Colors.BLUE}--- Iniciando Verificação de Links para '{args.filepath}' ---\n{Colors.RESET}")
    
    urls = extract_urls_from_file(args.filepath)
    
    if not urls:
        print(f"{Colors.YELLOW}Nenhum URL encontrado no arquivo.{Colors.RESET}")
        sys.exit(0)

    print(f"Encontrados {len(urls)} URLs únicos. Verificando...\n")

    summary = {
        'good': 0,
        'bad': 0,
        'error': 0
    }

    # Usando ThreadPoolExecutor para verificar os links em paralelo
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Cria um futuro para cada verificação de URL
        future_to_url = {executor.submit(check_url_status, url): url for url in urls}
        
        # Processa os resultados à medida que são concluídos
        for future in as_completed(future_to_url):
            try:
                url, status_code, status_text = future.result()
                print_result(url, status_code, status_text)
                
                # Atualiza o resumo
                if 200 <= status_code < 300:
                    summary['good'] += 1
                elif status_code > 0:
                    summary['bad'] += 1
                else: # Erros de conexão
                    summary['error'] += 1

            except Exception as e:
                url = future_to_url[future]
                print(f"{Colors.RED}[ERRO] Exceção inesperada ao verificar {url}: {e}{Colors.RESET}")
                summary['error'] += 1

    # Imprime o resumo final
    print(f"\n{Colors.BLUE}--- Resumo da Verificação ---{Colors.RESET}")
    print(f"Total de links verificados: {len(urls)}")
    print(f"{Colors.GREEN}Links bons: {summary['good']}{Colors.RESET}")
    print(f"{Colors.YELLOW}Links quebrados/redirecionados: {summary['bad']}{Colors.RESET}")
    print(f"{Colors.RED}Erros de conexão: {summary['error']}{Colors.RESET}")
    print(f"{Colors.BLUE}-----------------------------{Colors.RESET}")

if __name__ == "__main__":
    main()
