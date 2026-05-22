"""Script d'évaluation RAGAS — faithfulness, answer_relevancy, context_recall.

Prérequis :
  pip install -r backend/requirements-eval.txt

Usage :
  # Évaluer toutes les questions
  python tests/evaluate_ragas.py --api-url http://localhost:8000 --token <admin_token>

  # Évaluer une collection spécifique
  python tests/evaluate_ragas.py --collection rh --token <token>

  # Évaluer les N premières questions
  python tests/evaluate_ragas.py --limit 5 --token <token>

Output :
  results_<timestamp>.json  — scores par question
  Console                   — résumé faithfulness / answer_relevancy / context_recall
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
API_QUERY_URL = "{api_url}/api/query"


def run_query(api_url: str, question: str, collection: str, token: str | None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.post(
        API_QUERY_URL.format(api_url=api_url),
        json={"question": question, "collection": collection, "stream": False},
        headers=headers,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def evaluate_with_ragas(samples: list[dict], llm_model: str) -> dict:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, context_recall, faithfulness
    from langchain_openai import ChatOpenAI

    dataset = Dataset.from_list(samples)
    llm = ChatOpenAI(model=llm_model)

    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_recall],
        llm=llm,
    )
    return result


def main():
    parser = argparse.ArgumentParser(description="Évaluation RAGAS du pipeline RAG")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--token", default=None, help="Bearer token (admin pour collections protégées)")
    parser.add_argument("--collection", default=None, help="Filtrer par collection")
    parser.add_argument("--limit", type=int, default=None, help="Limiter le nombre de questions")
    parser.add_argument("--llm-model", default="gpt-4o-mini", help="Modèle RAGAS pour l'évaluation")
    parser.add_argument("--skip-ragas", action="store_true", help="Collecter les réponses sans évaluer")
    args = parser.parse_args()

    dataset = json.loads(DATASET_PATH.read_text())
    questions = dataset["questions"]

    # Filtres
    if args.collection:
        questions = [q for q in questions if q["collection"] == args.collection]
    questions = [q for q in questions if q.get("reference_answer") != "TODO"]
    if args.limit:
        questions = questions[:args.limit]

    if not questions:
        print("Aucune question avec reference_answer remplie. Éditer tests/golden_dataset.json d'abord.")
        return

    print(f"Évaluation de {len(questions)} questions...")
    samples = []
    errors = []

    for i, q in enumerate(questions, 1):
        print(f"  [{i}/{len(questions)}] {q['id']} — {q['question'][:60]}...")
        try:
            result = run_query(args.api_url, q["question"], q["collection"], args.token)
            answer = result.get("answer", "")
            contexts = [s["content_excerpt"] for s in result.get("sources", [])]

            samples.append({
                "question": q["question"],
                "answer": answer,
                "contexts": contexts,
                "ground_truth": q["reference_answer"],
                "question_id": q["id"],
            })
        except Exception as exc:
            print(f"    ERREUR: {exc}")
            errors.append({"id": q["id"], "error": str(exc)})

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"results_{timestamp}.json")

    if args.skip_ragas or not samples:
        output_path.write_text(json.dumps({"samples": samples, "errors": errors}, indent=2, ensure_ascii=False))
        print(f"\nRéponses collectées → {output_path}")
        return

    print("\nÉvaluation RAGAS en cours...")
    t0 = time.perf_counter()
    scores = evaluate_with_ragas(samples, args.llm_model)
    elapsed = time.perf_counter() - t0

    output = {
        "timestamp": timestamp,
        "questions_evaluated": len(samples),
        "errors": errors,
        "scores": {
            "faithfulness": float(scores["faithfulness"]),
            "answer_relevancy": float(scores["answer_relevancy"]),
            "context_recall": float(scores["context_recall"]),
        },
        "samples": samples,
        "elapsed_seconds": round(elapsed, 1),
    }

    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    print(f"\n{'─' * 50}")
    print(f"  Faithfulness      : {output['scores']['faithfulness']:.3f}  (cible > 0.80)")
    print(f"  Answer Relevancy  : {output['scores']['answer_relevancy']:.3f}  (cible > 0.75)")
    print(f"  Context Recall    : {output['scores']['context_recall']:.3f}  (cible > 0.70)")
    print(f"{'─' * 50}")
    print(f"  Résultats détaillés → {output_path}")
    print(f"  Durée : {elapsed:.1f}s")


if __name__ == "__main__":
    main()
