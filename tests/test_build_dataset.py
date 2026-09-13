from pathlib import Path

from medassist.data.build_dataset import _exemplos_templates, build_dataset

TEMPLATES_DIR = Path("data/synthetic/templates")


def test_templates_viram_exemplos_de_treino():
    """O enunciado exige laudos/receitas/procedimentos no fine-tuning."""
    exemplos = _exemplos_templates(TEMPLATES_DIR)
    assert len(exemplos) >= 12

    doc_ids = {"TPL-001", "TPL-002", "TPL-003"}
    citados = {
        doc_id
        for ex in exemplos
        for doc_id in doc_ids
        if doc_id in ex["messages"][2]["content"]
    }
    assert citados == doc_ids


def test_exemplos_de_template_citam_a_secao():
    exemplos = _exemplos_templates(TEMPLATES_DIR)
    com_secao = [e for e in exemplos if "§" in e["messages"][2]["content"]]
    assert len(com_secao) >= 9


def test_build_dataset_inclui_as_tres_fatias(tmp_path):
    stats = build_dataset(out_dir=str(tmp_path))
    treino = (tmp_path / "train.jsonl").read_text(encoding="utf-8")
    val = (tmp_path / "val.jsonl").read_text(encoding="utf-8")

    assert stats["n_exemplos"] == stats["n_treino"] + stats["n_val"]
    assert "PROT-" in treino
    assert "TPL-" in treino + val
