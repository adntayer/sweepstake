# uv run --with tiktoken python parse_opencode_session.py
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from collections import Counter

try:
    import tiktoken
except ImportError:
    tiktoken = None

def obter_sessoes_opencode():
    """Lista as sessões disponíveis gerando um arquivo temporário físico."""
    print("🔍 Buscando sessões ativas no OpenCode CLI...")
    temp_list = "opencode_list_temp.json"
    try:
        subprocess.run(
            f"opencode session list --format json > {temp_list}",
            shell=True,
            capture_output=True
        )
        if not os.path.exists(temp_list) or os.path.getsize(temp_list) == 0:
            subprocess.run(f"opencode export > {temp_list}", shell=True, capture_output=True)

        if not os.path.exists(temp_list) or os.path.getsize(temp_list) == 0:
            print("❌ Nenhuma sessão encontrada ou o OpenCode CLI não gerou dados.")
            if os.path.exists(temp_list): os.remove(temp_list)
            return None

        with open(temp_list, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()

        if os.path.exists(temp_list):
            os.remove(temp_list)

        if not conteudo.startswith('{') and '[' not in conteudo:
            inicio_json = conteudo.find('{') if '{' in conteudo else conteudo.find('[')
            if inicio_json != -1:
                conteudo = conteudo[inicio_json:]

        dados = json.loads(conteudo)
        return dados if isinstance(dados, list) else dados.get('sessions', [])
    except Exception as e:
        print(f"❌ Erro ao listar sessões do OpenCode: {e}")
        if os.path.exists(temp_list): os.remove(temp_list)
        return None

def baixar_json_sessao_seguro(session_id):
    """Garante o dump completo escrevendo direto no disco em modo silencioso."""
    print(f"📥 Baixando dados da sessão '{session_id}' via Dump Físico Seguro...")
    temp_file = "sessao_raw_temp.json"
    try:
        subprocess.run(f"opencode export {session_id} 2>nul > {temp_file}", shell=True)
        if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
            print("❌ Falha crítica: O arquivo de dump veio vazio.")
            return None
        with open(temp_file, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        os.remove(temp_file)

        if not conteudo.startswith('{') and '[' not in conteudo:
            inicio_json = conteudo.find('{') if '{' in conteudo else conteudo.find('[')
            if inicio_json != -1:
                conteudo = conteudo[inicio_json:]
        if conteudo.startswith('},'):
            conteudo = '{' + conteudo[2:]
        if not conteudo.endswith('}') and conteudo.startswith('{'):
            conteudo = conteudo + '}'
        return json.loads(conteudo)
    except Exception as e:
        print(f"❌ Erro crítico ao exportar sessão {session_id}: {e}")
        if os.path.exists(temp_file): os.remove(temp_file)
        return None

def menu_selecao_e_pipeline():
    sessoes = obter_sessoes_opencode()
    if not sessoes:
        print("Saindo do script."); return

    print("\n📋 === SESSÕES ENCONTRADAS NO SEU OPENCODE ===")
    for idx, sessao in enumerate(sessoes):
        s_id = sessao.get('id', 'N/A')
        s_title = sessao.get('title', 'Sem título')
        s_updated_raw = sessao.get('time', {}).get('updated', 0) or sessao.get('updatedAt', 0)
        s_date = f" ({datetime.fromtimestamp(int(s_updated_raw)/1000).strftime('%Y-%m-%d %H:%M')})" if s_updated_raw else ""
        print(f" [{idx + 1}] ID: {s_id} -> \"{s_title}\"{s_date}")

    try:
        escolha = input("\n👉 Digite o número da sessão que deseja processar: ").strip()
        indice = int(escolha) - 1
        if indice < 0 or indice >= len(sessoes):
            print("❌ Opção inválida."); return
    except ValueError:
        print("❌ Digite um número válido."); return

    dados = baixar_json_sessao_seguro(sessoes[indice].get('id'))
    if not dados: return

    try:
        info_sessao = dados.get('info', {})
        titulo_real = info_sessao.get('title', 'Contexto Essencial')
        session_id = info_sessao.get('id', 'sem_id')

        t_created = datetime.fromtimestamp(info_sessao.get('time', {}).get('created', 0) / 1000).strftime('%Y%m%d_%H%M')
        t_updated = datetime.fromtimestamp(info_sessao.get('time', {}).get('updated', 0) / 1000).strftime('%Y%m%d_%H%M')

        tok = info_sessao.get('tokens', {})
        frontmatter = (
            "---\n"
            f"title: \"{titulo_real}\"\n"
            f"session_id: \"{session_id}\"\n"
            f"slug: \"{info_sessao.get('slug', '')}\"\n"
            f"agent: \"{info_sessao.get('agent', '')}\"\n"
            f"model: \"{info_sessao.get('model', {}).get('id', '')}\"\n"
            f"cost: {info_sessao.get('cost', 0)}\n"
            f"time:\n  created: \"{t_created}\"\n  updated: \"{t_updated}\"\n"
            f"tokens:\n  input: {tok.get('input', 0)}\n  output: {tok.get('output', 0)}\n  reasoning: {tok.get('reasoning', 0)}\n  cache_read: {tok.get('cache', {}).get('read', 0)}\n"
            "---\n\n"
        )

        pasta_destino = os.path.join("sessions", f"{t_created}_{session_id}")
        os.makedirs(pasta_destino, exist_ok=True)

        nome_limpo = re.sub(r'[\s-]+', '_', re.sub(r'[^a-z0-9\s_-]', '', re.sub(r'[ç]', 'c', re.sub(r'[úùûü]', 'u', re.sub(r'[óòôõö]', 'o', re.sub(r'[íìîï]', 'i', re.sub(r'[éèêë]', 'e', re.sub(r'[áàâãä]', 'a', titulo_real.lower())))))))).strip('_')
        caminho_final_md = os.path.join(pasta_destino, f"{nome_limpo}.md")

        mensagens = dados.get('messages', [])
        contador_originais = Counter([p.get('type') for m in mensagens for p in m.get('parts', []) if 'type' in p])
        fluxo_final = []

        for index, msg in enumerate(mensagens):
            role = msg.get('info', {}).get('role', 'unknown').upper()
            parts = msg.get('parts', [])
            bloco_turno = []

            if role == 'USER':
                for part in parts:
                    if part.get('type') == 'text' and part.get('text'):
                        bloco_turno.append(f"### 👤 PROMPT DO USUÁRIO:\n{part['text']}")
            elif role == 'ASSISTANT':
                bloco_turno.append(f"### 🤖 AGENTE (Turno {index}):")
                for part in parts:
                    p_type = part.get('type')
                    if p_type == 'reasoning' and part.get('text'):
                        bloco_turno.append(f"💭 **PENSAMENTO DO AGENTE:**\n{part['text'].strip()}")
                    elif p_type == 'text' and part.get('text'):
                        bloco_turno.append(f"📄 **RESPOSTA DO AGENTE:**\n{part['text'].strip()}")
                    elif p_type == 'tool':
                        state = part.get('state', {})
                        input_data = state.get('input', {})
                        output_data = state.get('output', '')
                        alvo = input_data.get('filePath', input_data.get('pattern', input_data.get('prompt', input_data.get('description', str(input_data)))))

                        bloco_turno.append(f"🛠️ **AÇÃO DA FERRAMENTA [{part.get('tool', '').upper()}]**\n*Alvo/Parâmetro:* `{alvo}`")
                        if output_data:
                            str_output = str(output_data)
                            if '<content>' in str_output:
                                bloco_turno.append(f"```python\n{re.search(r'<content>(.*?)</content>', str_output, re.DOTALL).group(1).strip()}\n```")
                            elif 'diff' in str(input_data).lower():
                                bloco_turno.append(f"```diff\n{input_data.get('diff', str(input_data))}\n```")
                            else:
                                bloco_turno.append(f"```text\n{str_output.strip()}\n```")

            if bloco_turno:
                if len(bloco_turno) == 1 and f"### 🤖 AGENTE" in bloco_turno: continue
                fluxo_final.append("\n\n".join(bloco_turno))

        with open(caminho_final_md, 'w', encoding='utf-8') as f_out:
            f_out.write(frontmatter + f"# 📑 HISTÓRICO: {titulo_real}\n\n" + "\n\n---\n\n".join(fluxo_final))

        print(f"\n🎉 EXTRATOR EXECUTADO COM SUCESSO!\n📁 Arquivo salvo em: '{caminho_final_md}'")

        md_conteudo = open(caminho_final_md, 'r', encoding='utf-8').read()
        print("\n" + "="*50 + "\n📊 VERIFICAÇÃO DE COBERTURA MATEMÁTICA NO MD:")
        print(f"🔹 Prompts/Respostas salvos: {len(re.findall(r'### 👤|📄 \*\*RESPOSTA', md_conteudo))} de {contador_originais.get('text', 0)}")
        print(f"🔹 Pensamentos salvos: {md_conteudo.count('💭 **PENSAMENTO')} de {contador_originais.get('reasoning', 0)}")
        print(f"🔹 Ações de Ferramentas salvas: {md_conteudo.count('🛠️ **AÇÃO DA FERRAMENTA')} de {contador_originais.get('tool', 0)}")

        if tiktoken:
            print(f"\n🔥 TOTAL DE TOKENS (Markdown Limpo): {len(tiktoken.get_encoding('cl100k_base').encode(md_conteudo)):,} tokens.")
        print("="*50 + "\n")
    except Exception as e:
        print(f"❌ Erro crítico no processamento: {e}")

if __name__ == '__main__':
    menu_selecao_e_pipeline()
