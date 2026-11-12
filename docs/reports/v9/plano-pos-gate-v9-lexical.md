# Plano pós-gate v9 — RAG lexical e respostas

**Decisão em 12/11/2026:** manter recuperação lexical como estratégia de produção desta etapa. A nova rodada do gate sobre o release consolidado v9 passou com Hit@5 e MRR@5 de 1,00 nas estratégias exata e lexical, zero confusões críticas e 26/26 citações verificáveis por estratégia. Ver [resultado por caso](validacao-recuperacao-v9-next-test.md). O teste oficial v9 anterior continua reprovado em seu registro histórico. Não construir índice vetorial, não gerar embeddings e não fazer benchmark híbrido nesta etapa.

## 1. Fechar o caminho lexical do chat

- Fazer `chat` e `ask` do release v9 usarem `lexical` como padrão explícito, inclusive na mensagem de ajuda, sem tentar abrir índice vetorial nem chamar provedor de embeddings. Preservar `exact` para avaliação e diagnóstico.
- Manter separados os caminhos documental e de estoque. A resposta documental afirma apenas presença na lista, com fonte, versão, página e ID da evidência; não infere estoque, elegibilidade, indicação, dose individual ou equivalência terapêutica.
- Testar consultas com apresentação exata, fonte específica, forma ou dose incompatível, ambiguidade, ausência na lista, seguimento de conversa e indisponibilidade do gerador. A resposta documental continua disponível quando o modelo falhar.

**Entrega:** código e instruções de uso consistentes com a escolha lexical; testes unitários e suíte completa aprovados.

## 2. Avaliar respostas completas

- Criar um conjunto de avaliação de respostas distinto do `test` de recuperação v9: perguntas naturais com positivos e negativos F01/F03/F04, ambiguidade, perguntas com duas fontes e pedidos que devem ser recusados ou esclarecidos. Reservar famílias de desenvolvimento e de teste; registrar reutilização inevitável em F04.
- Para cada caso, registrar fatos autorizados, evidências admissíveis, status esperado, informação que não pode ser afirmada e critérios de resposta. Conferir o gabarito nos PDFs e obter revisão humana antes da avaliação final.
- Avaliar primeiro a saída documental determinística. Depois, se a síntese por modelo for usada no produto, avaliar a resposta gerada com modelo, parâmetros, prompt, hashes, custo, erros e política de repetição fixados. Não usar o `test` de recuperação anterior para escolher ajustes.
- Medir por caso e por fonte: resposta correta, fidelidade factual às evidências, citação que sustenta cada afirmação, abstenção/esclarecimento correto, ausência de alegações indevidas sobre estoque e segurança nas perguntas clínicas. RAGAS pode ser um sinal complementar; a aprovação factual vem de critérios verificáveis e revisão humana. Reportar também taxa de falha do gerador e comportamento do fallback.

**Gate:** 100% das afirmações factuais emitidas apoiadas por evidência verificável, zero afirmações críticas indevidas sobre estoque/uso clínico, 100% de citações válidas e nenhum erro de identidade de apresentação. Definir antes do teste final o limiar mínimo de utilidade da resposta e a tolerância a falhas do provedor; publicar resultados por caso e fonte. Se falhar, corrigir usando apenas desenvolvimento e preparar outro teste independente.

## 3. Preparar o contrato de estoque do agente

- Inspecionar os vínculos já validados entre apresentação do catálogo v9 e códigos UBS/CEAF em `src/rag/consolidated_live.py`, sem presumir que presença em RENAME, REME-DF ou Farmácia Popular implique saldo.
- Definir entrada explícita: `medicine_id` ou apresentação resolvida, fonte/canal de estoque e região. Para identidade incompleta ou múltiplos produtos possíveis, pedir esclarecimento antes da consulta.
- Definir saída estruturada: produto/código consultado, unidade e região, saldo ou status conforme o painel, horário de consulta, data da posição do painel, origem, estado de erro/ausência e aviso de desatualização. Não transformar dado ausente em “sem estoque”.
- Testar com fixtures e snapshots: produto sem vínculo, código divergente, saldo zero, data ausente ou antiga, API indisponível, mudança de região e pergunta que mistura Farmácia Popular com estoque UBS. Só integrar ao agente depois de validar o contrato e a apresentação ao usuário.

## Sequência e limites

1. Fechar o caminho lexical do chat.
2. Preparar e revisar o gabarito de respostas; congelar código e parâmetros; executar a avaliação final uma vez; publicar o parecer.
3. Se o gate de respostas passar, concluir e integrar o contrato de estoque.
4. Tratar CEP → UBS em frente separada, após validar o serviço territorial e os controles de privacidade.

O release consolidado v9 e os resultados oficiais de recuperação permanecem imutáveis. Este plano não autoriza afirmações de disponibilidade atual a partir do corpus documental.
