# Guia Rápido e Prático — DVC com Google Drive

Este guia mostra como **baixar**, **verificar** e **publicar** releases e chunks do `data-engineering/` usando DVC + Google Drive compartilhado (`gdrive://1tPvsMggxEE0UmyrdkqkP9VMoJ9Ow6mZn`).

> [!NOTE]
> **Você precisa de DVC agora?**
> - **Só quer rodar o chat ou testes unitários sem Drive?** Não precisa de `dvc pull`. Use `uv run pytest -m "not dvc"` e o release local `data/releases/corpus-consolidado-v5-aprovado-2026-11-10` (veja o [Guia de desenvolvimento e testes](guia-desenvolvimento-e-testes.md)).
> - **Quer usar `v7`, `v8` ou `v9` aprovados ou rodar a suíte completa?** Siga o fluxo abaixo.

---

## 1. Fluxo Rápido (Escolha seu Cenário)

### Cenário A — Acabei de clonar o repo e quero baixar os dados (`dvc pull`)

1. Garanta que sua conta Google tem acesso à pasta privada do Drive compartilhado.
2. Instale o ambiente e puxe os ponteiros `.dvc`:
   ```bash
   uv sync --frozen --python 3.12
   uv run dvc pull
   ```
3. Confirme que os artefatos locais estão sincronizados:
   ```bash
   uv run dvc status -c
   ```
4. Rode a suíte completa (incluindo testes `v7`/`v8`/`v9`):
   ```bash
   uv run pytest
   ```

> [!TIP]
> **No Windows ou Mac pela primeira vez?** O aplicativo OAuth padrão do DVC costuma ser bloqueado pelo Google. Se aparecer erro de autorização OAuth, configure o cliente próprio do projeto `SUS-Cidadao-DVC` na seção **2** abaixo.

---

### Cenário B — Quero publicar um novo release ou chunks (`dvc add` + `dvc push`)

1. Adicione a pasta do release ou de chunks derivada:
   ```bash
   uv run dvc add data/releases/<novo-release-aprovado>
   uv run dvc add data/derived/chunks/<novo-release-aprovado>
   ```
2. Envie os dados para o remoto e confirme sincronização:
   ```bash
   uv run dvc push
   uv run dvc status -c
   ```
3. No **Git**, versione **apenas** os arquivos `.dvc` e `.gitignore` gerados (nunca `.dvc/config.local`, tokens OAuth ou cache):
   ```bash
   git add data/releases/<novo-release-aprovado>.dvc data/derived/chunks/<novo-release-aprovado>.dvc
   ```

---

## 2. Configuração OAuth Própria (Quando o Padrão do DVC Bloqueia)

O Google bloqueia o app OAuth padrão do PyDrive2/DVC. O projeto já possui o projeto Google Cloud **`SUS-Cidadao-DVC`** com:
- **Google Drive API** habilitada;
- App externo em **modo de teste** com as contas da equipe cadastradas como usuárias de teste;
- Cliente OAuth do tipo **Desktop app**.

Configure as credenciais **somente localmente** (nunca no Git):

```bash
uv run dvc remote modify --local compartilhado gdrive_client_id "SEU_CLIENT_ID"
uv run dvc remote modify --local compartilhado gdrive_client_secret "SEU_CLIENT_SECRET"
```

Na primeira execução de `uv run dvc pull` ou `dvc push`:
1. Copie a URL exibida pelo DVC e abra no navegador local da própria máquina (Chrome/Edge).
2. Autorize a conta com acesso à pasta do Drive.
3. O callback `http://localhost:8080/` precisa alcançar o processo DVC na mesma máquina.

> [!WARNING]
> **Segurança:** nunca compartilhe nem cole em chat/capturas o código OAuth retornado, nem versione `.dvc/config.local` ou arquivos de cache de credencial.

---

## 3. Ponteiros DVC Versionados Atualmente

| Versão | Release (`data/releases/*.dvc`) | Chunks (`data/derived/chunks/*.dvc`) | Estado |
|---|---|---|---|
| **v7** | `corpus-consolidado-v7-aprovado-2026-11-11.dvc` (9 arq., 7,15 MB) | `corpus-consolidado-v7-aprovado-2026-11-11.dvc` (2 arq., 2,03 MB) | Sincronizado |
| **v8** | `corpus-consolidado-v8-aprovado-2026-11-11.dvc` | `corpus-consolidado-v8-aprovado-2026-11-11.dvc` | Sincronizado |
| **v9** | `corpus-consolidado-v9-aprovado-2026-11-12.dvc` (9 arq., 7,15 MB) | `corpus-consolidado-v9-aprovado-2026-11-12.dvc` (2 arq., 2,03 MB) | Sincronizado |

- **Remoto configurado em `.dvc/config`:** `compartilhado` → `gdrive://1tPvsMggxEE0UmyrdkqkP9VMoJ9Ow6mZn` (ID fixo da pasta compartilhada; **não** usar `gdrive://root`, pois resolve para Drives diferentes por usuário).
- **Índices Chroma:** quando adicionados, devem ser isolados por fingerprint/modelo após verificação de IDs, contagem e dimensão.

---

## 4. Troubleshooting Rápido

| Sintoma | Causa provável | Solução |
|---|---|---|
| Erro `GEN_EMAIL` no PyDrive2 / OpenSSL | Incompatibilidade entre `pyOpenSSL` 22 e `cryptography` 50 | O `pyproject.toml` já fixa `pyopenssl==24.2.1` (com `cryptography` 43.0.3 no lockfile). Rode `uv sync --frozen`. |
| Erro de permissão em `C:\ProgramData\iterative` (Windows) | Cache de site padrão não gravável | Defina `core.site_cache_dir` **apenas** em `.dvc/config.local` apontando para uma pasta ignorada pelo Git (não copie para o Mac). |
| `dvc pull` funciona no Windows, mas falha no Mac | Revisão Git diferente ou conta sem acesso à pasta | Confira `git rev-parse HEAD` idêntico, confirme compartilhamento nominal da pasta no Drive e refaça a autorização OAuth local. |
| Desativar telemetria do DVC | — | Exporte `DVC_NO_ANALYTICS=1` no shell antes dos comandos `dvc`. |

---

## 5. O Que NUNCA Entra no DVC

- Perguntas de usuários, CEP, endereço, coordenadas ou histórico de conversa.
- Snapshots de estoque contendo dados não aprovados.
- `.env`, `.dvc/config.local` e tokens OAuth.
