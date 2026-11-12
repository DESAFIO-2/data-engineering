# Preparação do DVC com Google Drive compartilhado

**Estado:** DVC 3.67.1 com suporte a Google Drive instalado e inicializado na raiz. Remoto `compartilhado` configurado para a pasta informada por Jhiovana (`gdrive://1tPvsMggxEE0UmyrdkqkP9VMoJ9Ow6mZn`). O release `corpus-consolidado-v7-aprovado-2026-11-11` foi adicionado com ponteiro `data/releases/corpus-consolidado-v7-aprovado-2026-11-11.dvc` (9 arquivos, 7.148.111 bytes, hash de diretório `26e95ea7c64da7b40704f9ce8a2ce8fc.dir`). Os 2.114 chunks v7 foram gerados e adicionados com ponteiro `data/derived/chunks/corpus-consolidado-v7-aprovado-2026-11-11.dvc` (2 arquivos, 2.033.273 bytes, hash de diretório `befa0a8039609a92cc39688fc97e5d99.dir`). **Jhiovana confirmou `dvc push` e `dvc status -c` sincronizados para o release e os chunks.** O Google bloqueou o aplicativo OAuth padrão do DVC; o projeto próprio `SUS-Cidadao-DVC` tem Drive API habilitada, cliente OAuth para computador e Jhiovana como usuária de teste. As credenciais ficam somente na configuração local ignorada pelo Git.

O projeto DVC ficará somente na raiz `engenharia-dados`; `Data-Science/` permanece repositório de referência. A pasta do Drive deve ser privada, compartilhada nominalmente com as contas que usarão Mac e Windows. Copie o ID da URL `https://drive.google.com/drive/folders/ID` após criá-la. Segundo a [documentação do DVC](https://s.dvc.org/user-guide/data-management/remote-storage/google-drive), pastas compartilhadas devem ser referenciadas pelo ID e o aplicativo OAuth padrão pode estar bloqueado; nesse caso, configurar cliente OAuth próprio antes do primeiro `push`.

Configuração já executada no Windows:

```powershell
uv add --group dev 'dvc[gdrive]'
uv add --group dev 'pyOpenSSL==24.2.1'
uv run dvc init
uv run dvc remote add -d compartilhado 'gdrive://1tPvsMggxEE0UmyrdkqkP9VMoJ9Ow6mZn'
uv run dvc add data/releases/corpus-consolidado-v7-aprovado-2026-11-11
uv run dvc status
uv run dvc push
```

`pyOpenSSL==24.2.1` resolve a incompatibilidade observada entre a versão 22.0.0 e `cryptography` 50 na autenticação do PyDrive2 (`GEN_EMAIL` ausente). O resolvedor escolheu `cryptography` 43.0.3. No sandbox Windows desta execução, o cache de site padrão do DVC em `C:\ProgramData\iterative` não era gravável; `core.site_cache_dir` foi definido **somente** em `.dvc/config.local` para uma pasta local ignorada pelo Git. Essa configuração é específica do Windows e não deve ser copiada para o Mac. A telemetria foi desativada nesta execução com `DVC_NO_ANALYTICS=1`.

O bloqueio do cliente padrão é [documentado pelo DVC](https://doc.dvc.org/user-guide/data-management/remote-storage/google-drive), que recomenda configurar um projeto Google Cloud e cliente OAuth próprio. Não contornar o aviso de segurança. No projeto exclusivo `SUS-Cidadao-DVC` foram habilitados a Google Drive API, o app externo em modo de teste, a conta de Jhiovana como usuária de teste e um cliente **Desktop app**. `gdrive_client_id` e `gdrive_client_secret` foram guardados em `.dvc/config.local` com `dvc remote modify --local`; esses valores e o token de usuário não entram no Git. A autorização OAuth será realizada pela própria titular da conta.

No **PowerShell local do Windows**, Jhiovana executou `uv run dvc push` e confirmou que `uv run dvc status -c` informou cache e remoto sincronizados após adicionar os chunks v7. Para futuras autorizações, abra a URL exibida pelo DVC em um navegador local (Chrome ou Edge do próprio Windows). O retorno `http://localhost:8080/` precisa alcançar o processo DVC no mesmo Windows; não compartilhe nem transcreva o código OAuth retornado.

O release `corpus-consolidado-v8-aprovado-2026-11-11` e seus 2.114 chunks têm ponteiros DVC separados. Após a aprovação da correção, Jhiovana confirmou `uv run dvc push` e `uv run dvc status -c` com cache e remoto sincronizados para a v8. O gate da recuperação v8 permanece fechado pelo [resultado do teste](reports/validacao-recuperacao-v8-test.md), independentemente da sincronização.

O release `corpus-consolidado-v9-aprovado-2026-11-12` e seus 2.114 chunks também têm ponteiros DVC separados. Em 12/11/2026, Jhiovana confirmou a execução de `uv run dvc push` e `uv run dvc status -c` no PowerShell autenticado, com cache e remoto sincronizados. O [relatório da correção](reports/auditoria-claritromicina-v9.md) registra a aprovação documental; a sincronização não altera o gate de desempenho da recuperação.

O índice Chroma será acrescentado por fingerprint/modelo após a vetorização e verificação de IDs. `dvc add` criará ponteiros `.dvc`; confirmar que Git inclui esses ponteiros e `.dvc/config`, nunca `.dvc/config.local`, tokens OAuth ou o cache. No Mac, clonar a **mesma revisão Git**, autenticar a conta com acesso à pasta, executar `dvc pull` e verificar hashes do manifesto, chunks e índice. Se o OAuth padrão falhar, registrar o bloqueio e configurar o cliente próprio sem publicar segredo no repositório. Não usar uma pasta `gdrive://root`, pois ela resolveria para Drives pessoais diferentes.

Não rastrear perguntas de usuários, CEP, endereço, coordenadas, histórico de conversa ou snapshots de estoque contendo dados não aprovados. O sucesso do fluxo Windows → Drive → Mac é um gate verificável, não uma consequência presumida da configuração.
