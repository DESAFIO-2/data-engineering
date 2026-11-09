import pytest
from sacrebleu.metrics.bleu import BLEU

from rag.metrics import PortugueseTokenizer, percentile, retrieval_metrics, text_metrics


def test_retrieval_duplicates_short_lists_and_cutoff() -> None:
    result = retrieval_metrics(["x", "a", "a", "b"], ["a", "b", "c"])
    assert result["hit@1"] == 0
    assert result["recall@3"] == pytest.approx(2 / 3)
    assert result["precision@5"] == pytest.approx(2 / 5)
    assert result["mrr@5"] == 0.5
    assert retrieval_metrics(["1", "2", "3", "4", "5", "a"], ["a"])["mrr"] == 0
    assert all(value is None for value in retrieval_metrics([], []).values())


def test_percentile_interpolation_and_invalid_samples() -> None:
    assert percentile([10, 20], 95) == 19.5
    assert percentile([10], 50) == 10
    assert percentile([], 50) is None
    with pytest.raises(ValueError):
        percentile([float("nan")], 50)


def test_unicode_rouge_precision_recall_and_citation_removal() -> None:
    assert PortugueseTokenizer().tokenize("AÇÃO ac\u0327a\u0303o órgãos") == [
        "ação",
        "ação",
        "órgãos",
    ]
    result = text_metrics(["Ação clínica [ev-abc] [1]."], ["ação clínica segura"])
    assert result["rouge1_precision"] == 1
    assert result["rouge1_recall"] == pytest.approx(2 / 3)
    assert result["rouge1_f1"] == pytest.approx(0.8)
    assert result["rougeL"] == result["rougeL_f1"]
    assert text_metrics(["ação"], ["acao"])["rouge1"] == 0


def test_bleu_is_corpus_not_mean_sentence_score() -> None:
    predictions = ["o serviço atende pessoas na unidade", "outro texto"]
    references = ["o serviço atende pessoas na unidade", "o serviço atende pessoas na unidade"]
    expected = (
        BLEU(tokenize="13a", smooth_method="exp", effective_order=False)
        .corpus_score(predictions, [references])
        .score
    )
    result = text_metrics(predictions, references)
    assert result["bleu"] == pytest.approx(expected)
    assert "tok:13a" in result["bleu_signature"]
    assert text_metrics([], [])["bleu"] is None
    with pytest.raises(ValueError):
        text_metrics(["a"], [])
