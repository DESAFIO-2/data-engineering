# Avaliação documental de RAG

**Objetivo:** Definir como gerar, executar e interpretar avaliações documentais de RAG com casos sintéticos e resultados auditáveis.

O subsistema aceita somente perguntas **sintéticas**, nunca logs pessoais. O golden set
gerado é um rascunho: não existe aprovação humana implícita na extração do corpus, em
uma referência literal, em BLEU/ROUGE alto ou no status `matched`. O release legado e
seus seis exemplos não conferem aprovação a novos exemplos. O benchmark não altera
o índice, o corpus ou a curadoria.

## 1. Ambiente e geração

Execute no PowerShell, na raiz `C:/Users/jhiov/Documents/engenharia-dados`:

```powershell
uv sync --group dev
$env:PYTHONPATH = 'src'
```

Dependências das métricas: `sacrebleu>=2.4,<3`, `rouge-score>=0.1.2,<1`.
`rank-bm25` é dependência da recuperação experimental, não das métricas. Os testes
usam pytest; lint e tipos usam ruff e mypy. Versões de sacrebleu e rouge-score são
registradas em cada resumo.

O builder mantido separadamente usa ocorrências e chunks do corpus experimental e
chunks administrativos complementares. Não inventa fontes para completar a quota:

```powershell
uv run python scripts/build_golden_set.py --corpus data/corpus/experimental --supplement data/raw/complementares/chunks.jsonl --output evals/datasets/golden_v1_draft.jsonl
```

Composição esperada: 60 medicamentos, 20 administrativos, 20 ambiguidades e 20 de
segurança; 80 dev e 40 test, com famílias disjuntas. A quota atual por categoria é
40/20, 14/6, 12/8 e 14/6 respectivamente (dev/test). A extração pode conter erros,
inclusive de OCR e associação de células; a resposta literal continua candidata.
Ausência de corpus ou cobertura insuficiente deve interromper a geração. Placeholders
com `evaluable: false` ou `placeholder: true` são recusados pelo benchmark inteiro,
não contados como casos válidos. A distribuição é responsabilidade do builder;
o benchmark também aceita conjuntos pequenos para testes de engenharia.

Cada caso exige `id`, `family_id`, `question`, `reference_answer`, `relevant_ids`,
`split`, `synthetic: true` e `review_status: draft|reviewed`. `expected_status`
aceita `matched`, `ambiguous`, `blocked`, `unsupported`, `not_in_scope`, `insufficient`;
se omitido, vale `matched`. Casos `matched` precisam de evidências. Demais casos
podem usar `relevant_ids: []`. `required_facts`, `forbidden_claims`, `sources`,
`assertions`, `critical` e `category` acompanham a revisão.

## 2. Executar e integrar

Recuperação lexical documental, sem chamada ao gerador:

```powershell
uv run python -m rag.cli eval --experimental --documental --corpus data/corpus/experimental --supplement data/raw/complementares/chunks.jsonl --strategy lexical --dataset evals/datasets/golden_v1_draft.jsonl --output evals/runs/dev-lexical.jsonl --split dev --allow-draft --repeat 1 --stage retrieval
```

Troque `--stage retrieval` por `--stage end-to-end` para avaliar também geração;
isso utiliza o provedor configurado e pode consumir API. `--stage generation` deve
fornecer contexto de referência fixo para casos factuais, isolando a geração.
Estratégias `vector`/`hybrid` exigem índice compatível; o benchmark não o cria.
Use caminhos de saída novos em cada execução.

Contrato Python usado por `experimental_cli`:

```python
from pathlib import Path
from rag.benchmark import read_jsonl, run_benchmark

cases = read_jsonl(Path('evals/datasets/golden_v1_draft.jsonl'))
# runner(case) executa a etapa escolhida e retorna:

**Objetivo:** Definir como gerar, executar e interpretar avaliações documentais de RAG com casos sintéticos e resultados auditáveis.

# {"status": "matched", "answer": "texto sintético", "ranked_ids": ["ev-id"],

**Objetivo:** Definir como gerar, executar e interpretar avaliações documentais de RAG com casos sintéticos e resultados auditáveis.

#  "usage": {"input_tokens": 100, "output_tokens": 30},

**Objetivo:** Definir como gerar, executar e interpretar avaliações documentais de RAG com casos sintéticos e resultados auditáveis.

#  "retrieval_ms": 12.0, "generation_ms": 340.0}

**Objetivo:** Definir como gerar, executar e interpretar avaliações documentais de RAG com casos sintéticos e resultados auditáveis.

# Não fornecer a referência ao modelo, exceto o contexto de geração isolada.

**Objetivo:** Definir como gerar, executar e interpretar avaliações documentais de RAG com casos sintéticos e resultados auditáveis.

summary = run_benchmark(
    cases, runner, Path('evals/runs/dev-python.jsonl'),
    split='dev', allow_draft=True, repeat=1, mode='end-to-end',
    run_metadata={'strategy': 'lexical', 'corpus_fingerprint': 'hash-do-corpus'},
)
```

`runner` é uma função da aplicação, não disponibilizada pelo benchmark. Passe o
dataset completo: a validação de famílias ocorre antes da seleção do split.
`semantic_ids` é alternativa a `ranked_ids`; use IDs realmente ranqueados, não a
união de evidência exata com recuperação semântica. `status` é obrigatório;
`answer` pode faltar na etapa de recuperação. Tempos e uso são opcionais.
`latency_ms` pode fornecer duração externa; senão mede-se o callback completo.
`mode` governa os denominadores, mas o adapter é responsável por executar a etapa
certa. Validação, autorização de drafts, hash e colisão de saídas ocorrem antes
do primeiro callback. Não se autentica a procedência de metadados de revisão.

Também é possível avaliar predições existentes, sem chamar serviços:

```powershell
uv run python -m rag.benchmark --dataset evals/datasets/golden_v1_draft.jsonl --predictions evals/predictions/dev.jsonl --output evals/runs/dev-offline.jsonl --split dev --allow-draft --mode end-to-end
```

Cada linha de predição contém `id` e o mesmo retorno do runner. IDs duplicados ou
desconhecidos são recusados; predições ausentes viram erros por caso. `--repeat`
reexecuta callbacks na API; no CLI offline apenas repete a mesma predição, não
mede variabilidade do modelo. Latência offline sem `latency_ms` mede lookup local.

## 3. Definições e limites das métricas

- Hit@1/3/5: presença de pelo menos uma evidência relevante entre as primeiras k.
- Recall@k: relevantes recuperadas / total de relevantes anotadas.
- Precision@k: relevantes recuperadas / k, mesmo com lista curta.
- MRR@5: inverso do primeiro rank relevante, limitado aos cinco primeiros;
  `mrr` é alias de `mrr@5`. IDs repetidos são removidos preservando ordem antes
  de pontuar. Médias macro por tentativa; repeats têm o mesmo peso.
- Casos de comportamento têm recuperação N/A (`null`), não zero. A geração isolada
  também tem recuperação N/A. `behavior_accuracy` compara status esperado/obtido
  somente nos casos não factuais; não valida o conteúdo da recusa.
- BLEU é **corpus BLEU**, 0–100, uma referência por caso, tokenizer 13a, case-sensitive,
  smoothing exp e effective_order false; a assinatura é persistida. Não é média
  de sentence BLEU. Textos muito curtos podem ter BLEU zero mesmo idênticos.
- ROUGE-1/2/L: média macro de precision, recall e F1, 0–1, calculada por rouge_score.
  `rouge1`, `rouge2`, `rougeL` são aliases F1. Tokenização Unicode NFC + casefold +
  palavras alfanuméricas; acentos preservados, sem stemming. Não usa o tokenizer
  padrão que remove letras acentuadas; resultados não são diretamente comparáveis.
- Antes de BLEU/ROUGE removem-se citações `[1]`, `[1, 2]`, `[ev-id]`, `[occ-id]`.
  Outros colchetes são preservados. Os textos originais continuam nos artefatos.
  Ambos pontuam apenas casos factuais answerable e nunca na etapa retrieval.
- Exceções do callback contam em `errors` e `error_rate`; a classe é gravada, a
  mensagem não. Falhas factuais recebem resposta/ranks vazios, permanecendo no
  denominador; erros de comportamento contam como incorretos.
- p50/p95 usam interpolação linear em `(n-1)*p`, incluindo latência total de falhas.
  Tempos por etapa incluem só valores conhecidos e expõem sua cobertura. Não há
  warm-up automático. Valores negativos, NaN e contagens inválidas causam erro do caso.
- Throughput é tentativas (ou sucessos) por segundo medido no loop, incluindo
  overhead por caso, excluindo métricas agregadas e gravação final. É sequencial,
  não estima capacidade concorrente. Tempos informados não alteram esse relógio.
- Tokens de entrada/saída são somas conhecidas com contagem de cobertura; desconhecido
  é `null`, nunca zero inventado. `total_tokens` soma somente tentativas com ambos
  os contadores conhecidos. Custos monetários não são inferidos.

## 4. Artefatos e revisão humana

Cada saída `nome.jsonl` cria também `nome.csv` e `nome.md`, sem sobrescrever nenhum
dos três. JSONL contém casos e resumo final; CSV contém os mesmos tipos de registro
em colunas, listas/objetos como JSON, e neutraliza prefixos de fórmula. Markdown
contém o resumo. Uma falha de disco pode deixar arquivos parciais: a escrita dos
três não é transacional. Use JSONL como formato canônico de análise.

São persistidos pergunta, resposta, referência, ranks, fontes e critérios sintéticos
para inspeção. Não envie logs pessoais ao runner nem segredos em `run_metadata`.
`synthetic: true` é uma declaração do produtor, não um detector de dados pessoais.
`factual_accuracy: null` e `factual_review: pending` são sempre mantidos na avaliação
automática, mesmo quando a resposta coincide exatamente com a referência.

A revisão de respostas é separada da aprovação do golden set. Produza manualmente
um JSONL com uma linha por `(id, repeat_index)` revisado, copiando `response_sha256`
do artefato para vincular o julgamento à resposta exata. Campos obrigatórios:

```json
{"id":"GS001","repeat_index":0,"response_sha256":"HASH_COPIADO_DO_RUN","reviewer":"identificação real do revisor","reviewed_at":"data real","record_id":"registro auditável","rationale":"justificativa humana com evidências","factual_accuracy":null,"fidelity":null,"completeness":null,"citation_support":null,"critical_error":null,"abstention_correct":null}
```

O exemplo é um formulário sem notas, não uma revisão realizada. Preencha cada campo
com `true`, `false` ou `null` (não aplicável/ainda não avaliado), usando a rubrica:

| Campo | Critério para true |
|---|---|
| factual_accuracy | Todas as afirmações factuais verificáveis estão corretas nas fontes |
| fidelity | A resposta não extrapola nem contradiz as evidências fornecidas |
| completeness | Os fatos obrigatórios relevantes à pergunta estão cobertos |
| citation_support | Citações existentes apontam para fontes que sustentam as afirmações |
| critical_error | Há erro crítico: orientação clínica indevida, estoque garantido ou outra violação grave |
| abstention_correct | A recusa/clarificação é apropriada e não contém orientação indevida |

`critical_error` é taxa de falha (menor é melhor); os demais são taxas de aprovação
do critério. Abstention é N/A para respostas factuais comuns. Registre justificativa
para qualquer nota; não derive notas de igualdade textual. Para consolidar:

```powershell
uv run python -m rag.benchmark --review-run evals/runs/dev-offline.jsonl --human-reviews evals/reviews/dev-human.jsonl --output evals/runs/dev-human-report.jsonl
```

O relatório valida vínculo, campos e duplicatas, apresenta cobertura por critério,
respostas pendentes e média somente das notas conhecidas. Não verifica a identidade
do revisor nem substitui auditoria do registro; não altera respostas nem aprova casos.

## 5. Congelamento e teste final

Drafts só rodam em dev com `--allow-draft`. Test exige todos os casos selecionados
`review_status: reviewed`, com objeto `review` contendo `reviewer`, `reviewed_at`,
`record_id` reais, além de hash congelado. A aprovação deve ocorrer fora do código,
após conferir fontes, famílias, referências e critérios. Não preencha metadados
fictícios para vencer o gate.

Após revisão humana, congele a versão completa e registre o hash em registro de
release separado. O hash é SHA256 do JSON canônico UTF-8 com chaves ordenadas,
separadores compactos e ordem dos casos preservada; não é hash dos bytes JSONL.

```powershell
uv run python -c "from pathlib import Path; from rag.benchmark import read_jsonl,dataset_hash; print(dataset_hash(read_jsonl(Path('evals/datasets/golden_v1_reviewed.jsonl'))))"
uv run python -m rag.benchmark --dataset evals/datasets/golden_v1_reviewed.jsonl --predictions evals/predictions/test.jsonl --output evals/runs/test-final.jsonl --split test --frozen-dataset-sha256 HASH_CONGELADO
```

O segundo comando requer substituir `HASH_CONGELADO` pelo valor realmente registrado.
Não recalcular e aceitar um hash novo a cada mudança: isso anula o congelamento.
O software verifica igualdade, não a autoridade do registro externo. Ajuste prompts
e estratégias somente em dev; evite usar test repetidamente para escolher modelos.

## 6. Verificação local

```powershell
uv run pytest tests/unit/test_rag_metrics.py tests/unit/test_rag_benchmark.py --basetemp .test-tmp-evaluation-new -q
uv run ruff check src/rag/metrics.py src/rag/benchmark.py tests/unit/test_rag_metrics.py tests/unit/test_rag_benchmark.py
uv run mypy src/rag/metrics.py src/rag/benchmark.py tests/unit/test_rag_metrics.py tests/unit/test_rag_benchmark.py
```

Escolha `--basetemp` novo se houver restrições de permissão no temporário padrão.
Os testes usam fixtures sintéticas, nunca certificam revisão humana do corpus real.
