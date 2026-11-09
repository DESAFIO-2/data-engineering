# Fontes complementares: coleta, rastreabilidade e revisão

**Objetivo:** Registrar inventário, coleta, rastreabilidade, integração e revisão das fontes complementares.

Na inspeção de 06/11/2026, `data/manifests/fontes-complementares.json` registra
17 documentos com `status: downloaded`, hashes de conteúdo distintos e
`review_status: pending`. Com RENAME, REME-DF e Farmácia Popular, o recorte
reúne 20 fontes coletadas. **A meta de 20 documentos curados permanece pendente
de revisão humana.** Não contar páginas, chunks, cópias ou índices de links
como novas fontes; diferenças de hash não provam conteúdo independente.

O manifesto é a referência dos URLs originais/finais, títulos, datas, hashes,
paths, estado HTTP e resultado de extração de cada snapshot. Para evitar
divergência, não duplicar aqui valores de hash ou datas de atualização da fonte.

## 1. Inventário inspecionado

Todos os itens abaixo estão baixados e pendentes de revisão:

| ID | Documento/tema registrado |
|---|---|
| C01 | Farmácia Popular: acesso e representação |
| C02 | Farmácias das Unidades Básicas de Saúde |
| C03 | Farmácias da atenção secundária |
| C04 | Componente especializado no DF |
| C05 | CEAF: telecuidado farmacêutico |
| C06 | Farmácias ambulatoriais: orientações de acesso |
| C07 | Farmácias de alto custo: cadastro e retirada |
| C08 | CEAF: etapas para acesso aos medicamentos |
| C09 | CEAF: perguntas frequentes |
| C10 | Laudo para solicitação, avaliação e autorização de medicamentos (LME) |
| C11 | CEAF: da incorporação à disponibilização |
| C12 | CEAF: regulamentação e financiamento |
| C13 | Componente Básico da Assistência Farmacêutica |
| C14 | Componente Estratégico da Assistência Farmacêutica |
| C15 | Medicamentos da atenção básica e estratégicos: consulta ao elenco |
| C16 | Portaria 13/2020: formulário LME e instruções de preenchimento |
| C17 | Portaria GM/MS 12.091/2026: regras do Farmácia Popular |

Títulos descrevem o inventário; não atestam vigência normativa, aplicabilidade
a um cidadão ou ausência de atualizações posteriores. O material é um snapshot.
As fontes administrativas podem apoiar informação de acesso quando houver
instituição, programa e contexto explícitos; não autorizam orientação clínica.

## 2. Reprodução e arquivos

Na raiz do repositório:

```powershell
uv run python -m scripts.collect_sources --help
uv run python -m scripts.collect_sources --timeout 25 --retries 2 --workers 4
$sourceInventory = Get-Content data/manifests/fontes-complementares.json -Raw | ConvertFrom-Json
$sourceInventory.sources | Select-Object source_id,status,review_status,title
$sourceInventory.sources | Group-Object status | Select-Object Name,Count
($sourceInventory.sources | Where-Object status -eq 'downloaded' | Select-Object -ExpandProperty sha256 -Unique).Count
```

A execução requer rede e pode alterar o inventário atual. Timeout deve ser
positivo, retries 0–5 e workers 1–8. `data/raw/complementares` preserva bytes
HTML/PDF e texto extraído por hash; `runs/` mantém manifestos e chunks de cada
rodada. O manifesto atual e `chunks.jsonl` são atualizados pelo coletor.

| Estado | Significado operacional |
|---|---|
| `downloaded` | Bytes e texto extraídos; não significa revisão aprovada |
| `duplicate` | Texto duplicado detectado; não contar como nova fonte |
| `failed` | Falha de coleta/extração; examinar erro sem inferir conteúdo |
| `last_failed_attempt` | Tentativa falhou e snapshot anterior foi preservado |
| `review_status: pending` | Pertinência, aplicabilidade e curadoria ainda não aprovadas |

Saída 1 não significa que todos os downloads falharam; consultar os registros.
O coletor verifica formato PDF/HTML, texto mínimo e pertinência lexical básica,
e rejeita páginas de desafio reconhecidas. Essas verificações não substituem
conferência de conteúdo, qualidade de extração ou direitos de redistribuição.

## 3. Chunking e integração

O coletor divide texto em até 1.600 caracteres, preferindo quebra de linha ou
espaço na segunda metade da janela. Não há sobreposição nessa implementação.
PDF mantém página física; HTML usa `section` com offsets. O chunk contém ID,
texto, estado de revisão e fonte com URL, versão, hash e página/seção.
Não confundir essa configuração com o contrato 2.000/240 do novo corpus das listas.

O suplemento não é carregado implicitamente. Passar o mesmo argumento ao
indexar, consultar, gerar golden set e avaliar:

```powershell
uv run python app.py search "Quais informações sobre acesso ao CEAF constam no recorte?" --experimental --corpus data/corpus/experimental --supplement data/raw/complementares/chunks.jsonl --strategy lexical --documental --show-context
```

O loader inclui o hash do suplemento no fingerprint. Mudança do arquivo exige
índice compatível e reconciliação dos IDs de evidência do golden set.
Documentos recuperados permanecem candidatos enquanto a revisão estiver pendente.

## 4. Gate de curadoria

Para cada documento, registrar responsável, data, hash exato e IDs/escopo revisto.
Conferir autoria oficial, conteúdo substantivo distinto, pertinência, território,
programa, versão, contexto e qualidade da extração. Comparar texto e origem,
inclusive tabelas, títulos e trechos de navegação eventualmente preservados.
Revisar páginas que só apontam para outros documentos: um índice de links não
satisfaz a meta de fonte substantiva.

Registrar aceitação, rejeição, duplicidade ou pendência, sem propagar aprovação
antiga a novos snapshots. Se uma fonte for rejeitada, identificar substituta
oficial e repetir coleta/revisão; não aumentar a contagem por chunks. Antes de
distribuir o pacote, conferir direitos de redistribuição dos documentos.

Resultados finais de curadoria, cobertura e avaliação devem constar no relatório
da rodada. Este documento registra o inventário inspecionado, não uma declaração
de vigência, extração completa, aprovação final ou envio ao Teams.
