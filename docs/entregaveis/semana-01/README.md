# Semana 1 — Definições do projeto

**Objetivo:** documentar o problema, os stakeholders, os riscos, as restrições, as regras de negócio e as métricas de aceite do **SUS Cidadão** no contexto do **Challenge 2 — Big Idea: Qualidade de Vida**.

**Foco no roadmap:** Problema, stakeholders, riscos e métricas · **Estado:** Concluído (base normativa registrada).

## 1. Big Idea e problema

- **Big Idea:** *"Empoderando pessoas com IA para compreender melhor, decidir melhor e viver melhor."*
- **Challenge Statement:** projetar e desenvolver uma solução baseada em IA capaz de apoiar a tomada de decisão em um contexto relacionado à qualidade de vida, com entendimento prévio do problema, decisões técnicas justificadas, explicitação de riscos/limitações, validação por métricas objetivas e uso de evidências confiáveis.
- **Problema no recorte do Distrito Federal:** cidadãos e cuidadores têm dificuldade para localizar informação oficial sobre medicamentos (RENAME, REME-DF, Farmácia Popular), canais de dispensação, documentos exigidos e preparo de exames, cuja aplicabilidade depende de lista, versão, programa, serviço e instituição.
- **Valor esperado:** melhorar a compreensão do próximo passo documentado, com proveniência verificável e tratamento explícito de ambiguidades — sem confundir presença em lista com estoque, elegibilidade individual ou orientação clínica.

## 2. Stakeholders e atores

| Ator / Stakeholder | Papel no sistema |
|---|---|
| Cidadão / Cuidador | Consulta informações e esclarece ambiguidades de apresentação, canal ou preparo |
| Revisor | Compara fontes oficiais e registra decisões de curadoria e validação |
| Responsável pelos dados | Define recorte, controla versões, proveniência e publicação de releases |
| Avaliador | Executa protocolos de avaliação e documenta métricas e limitações |
| Equipe / Instrutor | Confirma escopo, recursos e critérios acadêmicos do Challenge 2 |

## 3. Escopo, regras de negócio e riscos

- **Regras de negócio (RN01–RN10):** presença em lista, canal de acesso, elegibilidade e estoque são distintos (`RN01`); correspondência exige identidade e apresentação compatíveis sem fundir sais, concentrações, formas ou dispositivos (`RN02`); ausência de informação não significa dispensa de documento ou ausência no SUS (`RN04`); orientação crítica sem evidência suficiente exige esclarecimento ou abstenção (`RN08`).
- **Fora do escopo:** diagnóstico/triagem, prescrição ou alteração de dose, substituição terapêutica, garantia de estoque, prontuário/histórico real, armazenamento permanente de receitas/imagens pessoais e validação clínica institucional.
- **Riscos e limitações:** confusão entre apresentações próximas (ex.: liberação imediata vs. prolongada, concentrações distintas), desatualização de painéis públicos de estoque, uso de fontes sem verificação de vigência/território e alucinação sem evidência recuperada.

## 4. Artefatos de referência

| Artefato | Descrição |
|---|---|
| [Especificação funcional do MVP](../../specs/SPEC-02-functional-mvp.md) | Problema, atores, histórias de usuário (HU01–HU08), regras RN01–RN10, fora de escopo e critérios de aceite |
| [Arquitetura da Engenharia de Dados](../../specs/SPEC-00-architecture.md) | Camadas Bronze/Silver/Gold, proveniência, hashes e independência da camada de dados |
| [Ingestão de dados vivos](../../specs/SPEC-01-eda-and-sync.md) | Contratos técnicos de ingestão e armazenamento temporal |
| [Levantamento inicial de fontes](../../fontes/levantamento-fontes.md) | Mapeamento inicial das fontes públicas |
| [Fontes complementares](../../fontes/fontes-complementares.md) | Inventário de fontes complementares coletadas |
