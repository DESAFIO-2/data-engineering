# SPEC-10 — Endereço/CEP para UBS de referência no DF

**Estado:** descoberta e especificação; integração adiada até os gates documental, de recuperação e de estoque. Nenhum endpoint GeoServer foi validado neste repositório.

## Fato confirmado e objetivo

O [Busca Saúde UBS da SES/DF](https://info.saude.df.gov.br/busca-saude-ubs/) informa que endereço ou CEP residencial pode localizar a UBS de referência. A mesma página informa que farmácia básica, vacinação e urgência podem ser procuradas em qualquer UBS, independentemente da referência territorial. Portanto, a funcionalidade futura deve devolver **referência territorial** e **serviços disponíveis** como atributos distintos; referência não prova estoque nem elegibilidade.

## Descoberta obrigatória antes do código

Inspecionar a página oficial e o aplicativo incorporado, identificar os serviços realmente chamados, sua titularidade, URLs, métodos, parâmetros, esquemas, limites, data de observação e política de uso. Confirmar a origem da base de endereços/CEPs e a versão dos polígonos territoriais. Um endpoint observado publicamente não implica contrato de estabilidade nem autorização para uso ilimitado. Guardar exemplos reproduzíveis somente com **endereço público de teste**, sem residência real de usuário.

Se houver GeoServer, registrar `GetCapabilities`, camada, CRS, operação espacial, geometria e atributos retornados. Validar unidade, território e serviços contra o resultado do site oficial. Até completar essa etapa, nenhuma URL suposta entrará no contrato operacional.

## Fluxo previsto

1. Receber CEP ou endereço apenas para a consulta corrente. CEP genérico ou múltiplos endereços exige seleção explícita; não assumir o primeiro resultado.
2. Geocodificar o endereço escolhido e retornar coordenada com precisão/incerteza informada pelo provedor. Endereço sem ponto inequívoco pede esclarecimento.
3. Consultar o território oficial pela coordenada. Sem cobertura, fronteira ou sobreposição retornam estado explícito e orientação para consultar o site oficial; não escolher a UBS mais próxima silenciosamente.
4. Ligar território à unidade e serviços por identificador oficial estável, com versão/data da camada. Informar a UBS de referência como resultado territorial, não como confirmação de atendimento individual ou estoque.
5. Se qualquer serviço estiver indisponível, retornar erro temporário e link para o site oficial. Não reutilizar uma região de conversa anterior como resposta para um endereço novo.

Contrato proposto: entrada efêmera `{cep_or_address}`; saída `{status, selected_address_label?, territory_id?, ubs_id?, ubs_name?, services[], source_url, source_updated_at?, queried_at, ambiguity_options[]}`. `status` distingue `resolved`, `ambiguous_address`, `generic_cep`, `no_geocode`, `no_territory`, `overlapping_territories`, `service_unavailable`. Não retornar coordenadas completas ao modelo de linguagem nem registrá-las em logs.

## Privacidade e validação

CEP, endereço e coordenadas podem relacionar-se a pessoa identificável. Usar apenas os campos necessários, em memória e pelo tempo da requisição. Não gravar em banco, histórico de chat, cache, analytics, traces, exceções ou logs; aplicar redação de parâmetros inclusive em URLs e ferramentas de observabilidade. Antes da consulta, informar quais serviços externos receberão os dados. O texto “Usamos seu CEP ou endereço apenas para localizar sua UBS de referência. Não salvamos essas informações em nossos sistemas.” só poderá ser publicado após verificar esses controles e completar os destinatários externos efetivamente usados. Revisão de privacidade deve registrar finalidade, necessidade, transparência, segurança e base legal aplicável; ver [princípios da LGPD — Ministério da Saúde](https://www.gov.br/saude/pt-br/acesso-a-informacao/lgpd/principios/principios/).

Testes de aceite: endereço público com resultado igual ao site oficial, CEP genérico, endereços homônimos, fronteira e sobreposição, ausência de geocodificação, falha de cada provedor, ausência de vazamento de CEP/endereço/coordenadas em logs e histórico, e distinção entre referência territorial, serviços e estoque. Ativar somente após revisão de privacidade e dos provedores registrados.
