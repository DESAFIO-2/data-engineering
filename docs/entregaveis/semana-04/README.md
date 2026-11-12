# Semana 4 — Primeiro sistema multiagentes

**Objetivo:** estruturar e documentar a arquitetura de sistema multiagentes do **SUS Cidadão**, separando responsabilidades entre triagem/esclarecimento, recuperação documental, consulta de dados vivos e verificação de segurança/evidências.

**Foco no roadmap:** Sistema multiagentes · **Estado:** Planejado.

## 1. Escopo previsto

- Definir papéis, ferramentas, contratos de comunicação e políticas de abstenção entre agentes especializados (ex.: roteamento de intenção, consulta ao corpus consolidado, consulta ao InfoSaúde-DF, validação de apresentação/citações).
- Avaliar a integração com a frente de privacidade e localização ([SPEC-10: CEP → UBS e privacidade](../../specs/SPEC-10-cep-ubs-privacidade.md)), mantendo a regra de não persistir dados pessoais.

## 2. Pré-requisitos e entregáveis esperados

- **Pré-requisito:** fechamento da revisão factual da Semana 3 e definição da estratégia padrão de recuperação/síntese.
- **Entregáveis previstos:** especificação da topologia multiagentes, implementação inicial, testes de roteamento/abstenção e relatório de validação nesta pasta.
