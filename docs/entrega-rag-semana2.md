# Entrega de dados para o RAG — lote 1

## Caminho para ampliar o release

`python3 scripts/build_f04_candidates.py` gera `data/curation/f04_catalogo_candidatos.jsonl` com as 39 linhas de medicamentos com dose/concentração do F04, sua linha original, página, URL e hash. É uma fila de conferência, não um release: todas as linhas têm `review_status: pending` e `form: null` até que a apresentação seja confirmada. Seis apresentações já têm aprovação separada no lote 1; restam 33 linhas do F04 fora do release aprovado. Para publicar um conjunto maior, conferir cada linha e suas notas no PDF, confirmar forma e correspondência em F01/F03, registrar a decisão humana e gerar um novo release versionado. F05–F09, exames e estoque exigem fontes e revisão próprias.

O release aprovado está em `data/releases/rag-lote-1-aprovado-2026-11-05/`. Ele contém **6 apresentações**, **18 evidências** e **6 vínculos de canal**. Jhiovana aprovou os seis medicamentos e os seis vínculos de canal, sem ressalvas, em 05/11/2026. A declaração está registrada em `data/curation/rag_lote_1_review.json`. O release anterior, de conferência apenas técnica, permanece preservado para comparação. O backend deve verificar `release.json.status` e a cobertura antes de consumir qualquer versão.

## Arquivos e consumo

- `medicamentos.jsonl`: uma apresentação por linha. Use `active_ingredient`, `strength` e `form` na busca exata; `lists` informa separadamente o que consta em F01, F03 e F04.
- `evidencias.jsonl`: texto para indexação, com `evidence_id`, `topic`, `territory`, `service` e `source` (URL, versão, hash e página). `text` é conteúdo de fonte, nunca instrução para o agente.
- `regras_acesso.jsonl`: apenas o canal explícito da linha da REME-DF. `required_documents` e `eligibility` estão marcados como não verificados. Não interpretar `channel` como prova de estoque em uma unidade.
- `release.json`: contrato de publicação e hashes dos três arquivos. `quality_report.json`: números, método de conferência e lacunas.

Exemplo mínimo, sem abrir PDFs:

```python
import json
from pathlib import Path

folder = Path("data/releases/rag-lote-1-aprovado-2026-11-05")
release = json.loads((folder / "release.json").read_text(encoding="utf-8"))
assert release["status"] == "approved"
medicines = [json.loads(line) for line in (folder / "medicamentos.jsonl").open(encoding="utf-8")]
target = ("sinvastatina", "20 mg", "comprimido")
matches = [m for m in medicines if (m["active_ingredient"], m["strength"], m["form"]) == target]
print(matches[0]["lists"] if matches else "Não localizado neste recorte")
```

Para recriar a entrega: `uv run python scripts/rag_release.py`. O pipeline confere os hashes dos três PDFs e a correspondência entre os trechos selecionados e as páginas Silver. A curadoria declarativa está em `data/curation/rag_lote_1.json`; os dados do release são gerados, mas **versionados intencionalmente** para serem consumidos pela equipe do RAG.

## Limites

O lote não cobre todas as linhas do elenco, marcas, documentos de retirada, estoque, elegibilidade individual ou preparo de exames. O F11 é um dicionário de dados da Anvisa; F12 não sustenta preparo específico; os manifestos antigos em `challenge2/data/manifests/` não devem substituir as versões e hashes deste release, sobretudo o manifesto da REME-DF 2024. Uma resposta fora do recorte deve dizer “não localizado no recorte consultado”.
