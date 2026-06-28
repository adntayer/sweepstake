# sweepstake

[repo wc2026](https://github.com/rezarahiminia/worldcup2026)

[codeburn](https://github.com/getagentseal/codeburn)


# Get all World Cup 2026 matches (no auth needed for demo)
curl https://worldcup26.ir/get/games

# Get group standings
curl https://worldcup26.ir/get/groups

# Get all 48 teams
curl https://worldcup26.ir/get/teams

# Get all 16 stadiums
curl https://worldcup26.ir/get/stadiums




```terminal
$ uv venv
$ .venv\Scripts\activate
$ uv sync --all-extras
$ uv pip install -e .
$ uv run pytest tests/ -v
```

ruff check --fix
ruff format


llama-server -m "C:\Users\adnta\.cache\huggingface\hub\models--unsloth--gpt-oss-20b-GGUF\snapshots\d449b42d93e1c2c7bda5312f5c25c8fb91dfa9b4\gpt-oss-20b-Q4_0.gguf" --port 8080 -ngl 0 -c 8192



llama-server -hf Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q5_K_M -ngl 99 -c 8192 -fa on --no-mmap


llama-server -hf Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q5_K_M -ngl 99 -c 32768 -fa on --cache-type-k q4_0 --cache-type-v q4_0



llama-server -hf Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q5_K_M -ngl 24 -c 8192 -fa on --cache-type-k q4_0 --cache-type-v q4_0 --no-mmap



llama-server -hf Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:Q5_K_M -ngl 24 -c 16384 -fa on --cache-type-k q4_0 --cache-type-v q4_0 --no-mmap



llama-server -hf bartowski/gemma-2-9b-it-GGUF:Q5_K_M -ngl 28 -c 8192 -fa on --cache-type-k q4_0 --cache-type-v q4_0 --temp 0.3


ficou legal
llama-server -hf unsloth/gemma-4-E2B-it-GGUF:Q6_K -ngl 99 -c 20480 -fa on --cache-type-k q4_0 --cache-type-v q4_0


=======

llama-server -hf unsloth/gemma-4-E2B-it-GGUF:Q6_K -ngl 99 -c 65536 -fa on --cache-type-k q4_0 --cache-type-v q4_0 -b 4096 -ub 1024 --prio 3


O argumento -hf unsloth/gemma-4-E2B-it-GGUF:Q6_K indica ao servidor o repositório e o arquivo específico a ser carregado diretamente do Hugging Face. O sufixo :Q6_K é crucial, pois define uma quantização de 6 bits, que preserva quase toda a inteligência do modelo original, mas reduz o tamanho do arquivo para que ele caiba confortavelmente na sua memória.O parâmetro -ngl 99 (Number of GPU Layers) determina quantas camadas do modelo serão processadas pela placa de vídeo. Ao definir 99, você garante que todas as camadas do Gemma-4 (que possui bem menos que isso) sejam enviadas para a GPU, o que elimina a dependência da CPU e eleva a velocidade de resposta para o patamar máximo de frames e tokens.O comando -c 65536 estabelece o tamanho da janela de contexto (memória de trabalho) em 64k tokens. Essa configuração é o que permite ao modelo "ler" e manter na memória arquivos de código extensos, como o seu script de futebol, garantindo que ele não esqueça as instruções iniciais ou a estrutura do projeto durante a conversa.A flag -fa on ativa o Flash Attention, uma otimização de algoritmo que acelera drasticamente o cálculo de atenção em contextos longos. Para a sua arquitetura de GPU, isso é vital para evitar que o modelo fique progressivamente mais lento conforme o chat acumula milhares de tokens, mantendo a latência baixa.O argumento --cache-type-k q4_0 aplica uma compressão de 4 bits ao cache das "chaves" (Keys) do modelo dentro da VRAM. Essa técnica de economia de memória é o que permite que um contexto gigante de 64k ocupe apenas uma fração do espaço que ocuparia normalmente, sendo fundamental para não estourar os seus 6GB de vídeo.De forma complementar, o --cache-type-v q4_0 faz a mesma compressão de 4 bits para os "valores" (Values) do cache. Juntos, esses dois comandos de quantized cache são os responsáveis por permitir que você utilize modelos inteligentes com janelas de contexto profissionais em uma placa de vídeo voltada para o mercado de entrada/intermediário.O parâmetro -b 4096 define o tamanho do lote de processamento (Batch Size). Ele dita quantos tokens o modelo tenta processar simultaneamente durante a fase de leitura; um valor alto como 4096 é o que gera aquela velocidade impressionante de mais de 200 tokens por segundo quando você cola um novo script no chat.O argumento -ub 1024 (Universal Batch) serve como um limitador físico para o tamanho do lote, garantindo que, embora o modelo queira processar 4096 tokens, ele o faça em sub-blocos de 1024. Isso evita picos de consumo de energia e memória que poderiam causar o fechamento repentino do driver da NVIDIA ou do servidor.A flag --prio 3 ajusta a prioridade do processo llama-server dentro do Windows para o nível "Acima do Normal". Isso garante que o sistema operacional priorize os cálculos da IA em vez de outros processos de segundo plano, evitando que o modelo "engasgue" enquanto você navega no VS Code ou no navegador.Por fim, embora não seja um argumento direto de performance, o uso implícito do vulkan ou backend similar (visto nos seus logs) é o que amarra todos esses parâmetros, permitindo que a comunicação entre o software e o hardware da sua RTX 3050 ocorra sem gargalos de compatibilidade.



llama-server -hf unsloth/gemma-4-E2B-it-GGUF:Q6_K -ngl 99 -c 98304 -fa on --cache-type-k q4_0 --cache-type-v q4_0 -b 4096 -ub 1024 --prio 3




===================
===================

#dv
llama-server -hf unsloth/gemma-4-E2B-it-GGUF:Q6_K -ngl 60 -c 32768 -fa on --cache-type-k q4_0 --cache-type-v q4_0 -b 512 -ub 256 -t 4 --prio 2
Por que esse comando encaixa no seu projeto?-t 4: Deixa mais núcleos de CPU livres para o multithreading do seu to_dv.py.-c 32768: Libera RAM para o DuckDB operar em alta velocidade.-ngl 60: Mantém a GPU ativa para você tirar dúvidas com o Pi Agent sobre a modelagem de Hubs e Links enquanto o script roda










# Tente com 16k ou 32k primeiro
llama-server -hf unsloth/gemma-4-E4B-it-GGUF:UD-Q6_K_XL -ngl 99 -c 16384 -fa on --cache-type-k q4_0 --cache-type-v q4_0 -b 1024 -ub 512 --prio 3


llama-server -hf unsloth/gemma-4-E4B-it-GGUF:UD-Q4_K_XL -ngl 35 -c 32768 -fa on --cache-type-k q4_0 --cache-type-v q4_0 -b 512 -ub 256 -fit off


rmdir /s /q "%USERPROFILE%\.local\share\opencode"
rmdir /s /q "%USERPROFILE%\.cache\opencode"



llama-server -hf unsloth/gemma-4-E2B-it-GGUF:Q6_K -ngl 99 -c 32768 -fa on --cache-type-k q4_0 --cache-type-v q4_0 -b 1024 -ub 512 --prio 3




llama-server -hf Qwen/Qwen2.5-Coder-3B-Instruct-GGUF:Q8_0 -ngl 99 -c 16384 -fa on --cache-type-k q4_0 --cache-type-v q4_0 -b 1024 -ub 512 --prio 3


---

llama-server -hf unsloth/gemma-4-E4B-it-GGUF:UD-Q6_K_XL -ngl 99 -c 16384 -fa on --cache-type-k q4_0 --cache-type-v q4_0 -b 1024 -ub 512 --prio 3 --no-warmup --no-mmproj-offload



----------------------------
----------------------------
----------------------------
llama-server -hf unsloth/gemma-4-E4B-it-GGUF:UD-Q6_K_XL -ngl 99 -c 32768 -fa on --cache-type-k q4_0 --cache-type-v q4_0 -b 1024 -ub 512 --prio 3 --no-warmup --no-mmproj-offload


llama-server -hf unsloth/gemma-4-E4B-it-GGUF:UD-Q6_K_XL -ngl 99 -c 65536 -fa on --cache-type-k q4_0 --cache-type-v q4_0 -b 1024 -ub 512 --prio 3 --no-warmup --no-mmproj-offload



----------------------------
----------------------------
----------------------------

llama-server -hf bartowski/deepreinforce-ai_Ornith-1.0-9B-GGUF:Q4_K_M -ngl 24 -c 16384 -fa on --cache-type-k q4_0 --cache-type-v q4_0 -b 512 -ub 256 --prio 3 --no-warmup
