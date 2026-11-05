# RAG híbrido com ChromaDB

## Decisão e fluxo

O índice local persistente usa ChromaDB via `langchain-chroma`. O release JSONL aprovado é a fonte de verdade; o índice é derivado e separado por hash do release e modelo de embeddings. `Release.load` confere status, aprovação humana, hashes, contagens e referências. A busca exata exige princípio ativo, concentração e forma; o Chroma recebe filtro por `medicine_id`. O CLI anexa as fontes a partir do release, sem depender de citações geradas pelo modelo.

## Configuração

O arquivo `.env.example` documenta a chave Google, modelos de conversa e embeddings, caminhos e `top_k`. Use `.env` local, ignorado pelo Git. `index` publica 18 evidências, `eval` mede match exato e Hit@5 sobre seis perguntas em `evals/datasets/retrieval_lote1.jsonl`, `search` inspeciona recuperação, `ask` responde uma pergunta e `chat` abre a conversa no terminal.

## Limites

Este lote cobre somente seis apresentações aprovadas em F01, F03 e F04. Presença em lista não comprova estoque. O ramo de estoque UBS e localização usa um snapshot público separado do InfoSaúde-DF, descrito em [infosaude-live-rag.md](infosaude-live-rag.md), com horário e fonte explícitos. Não há sustentação para documentos, elegibilidade individual, exames, dose, diagnóstico ou substituição terapêutica. Perguntas fora da cobertura recebem limite explícito. Use apenas perguntas fictícias no protótipo; o provedor de modelo recebe o texto das perguntas documentais.
