# Avaliação RAG sintética

Métricas automáticas não constituem aprovação factual humana.

| Medida | Valor |
|---|---|
| record_type | "summary" |
| schema_version | 1 |
| synthetic | true |
| review_status | "draft" |
| split | "dev" |
| mode | "end-to-end" |
| total | 80 |
| unique_cases | 80 |
| repeat | 1 |
| elapsed_seconds | 391.177290600026 |
| throughput_cases_per_second | 0.20451084948537826 |
| successful_cases_per_second | 0.12270650969122697 |
| errors | 32 |
| dataset_sha256 | "364261c4b83f3c4bd34e842bc2ebb666d02c43fe32192aa182f4c846cb1ec976" |
| frozen_dataset_sha256 | null |
| metadata | {"strategy": "lexical", "corpus_fingerprint": "3b320bf22363827d2899035a7101484394c6edf943cb72522fbfb3ff7a67a57c", "chat_model": "gemini-3.5-flash", "embedding_model": "models/gemini-embedding-2"} |
| text_scored_cases | 54 |
| retrieval_scored_cases | 54 |
| behavior_scored_cases | 26 |
| behavior_accuracy | 1.0 |
| factual_accuracy | null |
| factual_review | "pending" |
| dependencies | {"sacrebleu": "2.6.0", "rouge-score": "0.1.2"} |
| bleu | 6.690391056650933 |
| bleu_signature | "nrefs:1\|case:mixed\|eff:no\|tok:13a\|smooth:exp\|version:2.6.0" |
| rouge1 | 0.12973642705449245 |
| rouge2 | 0.059627213042306164 |
| rougeL | 0.08569493713016642 |
| rouge1_precision | 0.0927625546643835 |
| rouge1_recall | 0.23447742344801167 |
| rouge1_f1 | 0.12973642705449245 |
| rouge2_precision | 0.042007592343904804 |
| rouge2_recall | 0.11288640020365166 |
| rouge2_f1 | 0.059627213042306164 |
| rougeL_precision | 0.06183662604775414 |
| rougeL_recall | 0.15065258409556656 |
| rougeL_f1 | 0.08569493713016642 |
| rouge_tokenizer | "unicode_nfc_casefold_alphanumeric_no_stemming" |
| error_rate | 0.4 |
| hit@1 | 0.37037037037037035 |
| hit@3 | 0.37037037037037035 |
| hit@5 | 0.37037037037037035 |
| recall@1 | 0.37037037037037035 |
| recall@3 | 0.37037037037037035 |
| recall@5 | 0.37037037037037035 |
| precision@1 | 0.37037037037037035 |
| precision@3 | 0.12345679012345678 |
| precision@5 | 0.07407407407407407 |
| mrr | 0.37037037037037035 |
| mrr@5 | 0.37037037037037035 |
| latency_p50_ms | 2158.5689000203274 |
| latency_p95_ms | 15491.36257996141 |
| latency_ms_known_cases | 80 |
| retrieval_p50_ms | 145.57224998134188 |
| retrieval_p95_ms | 257.3251049907413 |
| retrieval_ms_known_cases | 20 |
| generation_p50_ms | 0.0 |
| generation_p95_ms | 25355.11641499178 |
| generation_ms_known_cases | 48 |
| input_tokens | 6321 |
| input_tokens_known_cases | 20 |
| output_tokens | 19732 |
| output_tokens_known_cases | 20 |
| total_tokens_known_cases | 20 |
| total_tokens | 26053 |
