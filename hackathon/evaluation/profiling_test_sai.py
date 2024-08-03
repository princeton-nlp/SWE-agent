from hackathon.evaluation.evaluate import run_swebench_evaluation
if __name__ == "__main__":
    import time
    model_name = "gpt-4o-mini"
    cost_limit = 0.05
    t0 = time.time()
    splits = ["dev", "test"]
    for split in splits:
        print("Running evaluation for split: ", split)
        run_swebench_evaluation(
            predictions_path_override=None,
            model_name=model_name,
            full_dataset_name="princeton-nlp/SWE-bench_Lite",
            cost_limit=cost_limit,
            temperature=0.00,
            top_p=0.95,
            run_id="test",
            split=split,
            max_workers=2,
        )
    print("Time taken: ", time.time() - t0)