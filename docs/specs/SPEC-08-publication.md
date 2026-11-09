# Revisão e publicação do corpus ampliado

**Objetivo:** Documentar o fluxo de revisão humana e publicação do corpus ampliado.

## 1. Exportar candidatos para revisão

O fluxo está implementado; aprovação humana real continua pendente. Nenhum comando
aprova automaticamente. O release original permanece separado e não é alterado.

```powershell
uv run python scripts/curate_corpus.py export --corpus data/corpus/experimental --supplement data/raw/complementares/chunks.jsonl --output revisao.json
uv run python scripts/curate_corpus.py publish --review revisao.json --output data/releases/curado-v2-001
```

O export inclui todas as evidências: 2.620 chunks de linhas/páginas e 108
complementares na versão atual (2.728). Não há limite fixo de quantidade.
Se a pasta do corpus já contém os 2.728 chunks consolidados, omitir
`--supplement` para não duplicar as evidências complementares.
O arquivo de saída deve ser novo. Cada entrada contém o chunk completo, origem
exata, hash e `decision: pending`. O documento também vincula o fingerprint do
corpus e as ocorrências estruturadas. Os caminhos de entrada ficam absolutos.

## 2. Registrar decisões de revisão

O revisor confere texto, contexto, campos da ocorrência, versão e página/seção da
fonte. Altera somente `decision` para `approve` ou `reject`, preenchendo `reviewer`
(identidade declarada), `date` (YYYY-MM-DD, não futura) e `reason` (justificativa).
Pendências permanecem `pending`. Não modificar texto, origem, hashes ou IDs para
contornar uma divergência: corrigir o candidato e exportar uma nova revisão.
Uma rejeição exclui o chunk mesmo que conserve metadados de aprovação anteriores.

## 3. Publicar e carregar release

A publicação compara toda a revisão com as entradas atuais verificadas por hash.
Cada chunk aprovado é incluído; uma ocorrência só entra quando TODOS os seus
chunks de linha estão aprovados, e seus vínculos publicados contêm apenas essas
linhas. Aprovar página não aprova linhas nem ocorrências. Chunks de linha aprovados
podem existir sem ocorrência publicada enquanto outra parte permanece pendente.
Páginas gerais e fontes complementares são decisões independentes. Uma revisão
inteiramente pendente não publica nada e permanece intacta.

O destino deve ser uma pasta inexistente, com pai existente. Não há atualização
ou sobrescrita de releases: mudanças exigem outra pasta. O manifesto é escrito por
último com `status: approved`, `schema_version: 2` e hashes de `review.json`,
`chunks.jsonl` e `occurrences.jsonl`. Uma falha intermediária pode deixar uma pasta
incompleta, que não é carregável. Imutabilidade é uma regra do publicador, não uma
proteção de sistema de arquivos contra edição externa.

Integração: `from rag.curation import load_approved`; chamar
`load_approved(Path("data/releases/curado-v2-001")) -> Corpus`.
O leitor verifica hashes, decisões, metadados e correspondência exata entre a
revisão arquivada e o subconjunto publicado; não precisa dos candidatos originais.
Seu fingerprint inclui o manifesto da publicação, isolando revisões/subconjuntos.
Symlinks, junctions, escapes de caminho, IDs duplicados/desconhecidos e metadados
incompletos são recusados. Identificadores de fonte podem ser URLs.

## 4. Limites de integridade e verificação

Hashes detectam inconsistência, mas não são assinatura digital: alguém capaz de
reescrever todos os arquivos e hashes pode fabricar uma revisão. A identidade do
revisor é registrada, sem autenticação externa. A validação usa os snapshots e
metadados de origem locais; não consulta URLs para verificar mudanças remotas.
Os testes usam somente texto fictício e decisões sintéticas em diretórios temporários.

```powershell
uv run pytest tests/unit/test_curation.py
uv run ruff check src/rag/curation.py scripts/curate_corpus.py tests/unit/test_curation.py
uv run mypy --follow-imports=silent src/rag/curation.py scripts/curate_corpus.py
```
