from __future__ import annotations

import time

from hackathon.evaluation.evaluate import get_runnable_problems, run_agents_and_catch_logs, run_swebench_evaluation

if __name__ == "__main__":
    from datasets import load_dataset

    d = load_dataset("princeton-nlp/SWE-bench_Lite")

    mode = ["mini", "sonnet", "L3.1-70b-Together", "L3.1-405b-Baseten", "L3.1-70b-Groq"][0]
    if mode == "mini":
        model_name = "gpt-4o-mini"
        cost_limit = 0.20
    elif mode == "sonnet":
        model_name = "claude-3-5-sonnet-20240620"
        cost_limit = 1.5
    elif mode == "L3.1-70b-Together":
        model_name = "L3.1-70b-Together"
        cost_limit = 0.50
    elif mode == "L3.1-405b-Baseten":
        model_name = "L3.1-405b-BaseTen"
        cost_limit = 1.0
    elif mode == "L3.1-70b-Groq":
        model_name = "L3.1-70b-Groq"
        cost_limit = 1.0
    run_agent = True
    evaluate_agent = True
    split = "dev"
    first_question_index = 5
    last_question_index = 20

    runnable_problems_by_split = get_runnable_problems(
        f"trajectories/jp/{model_name}__SWE-bench_Lite__default__t-0.00__p-0.95__c-{cost_limit:.2f}__install-1"
    )
    print("Model name: ", model_name)
    print("Split: ", split)
    print({k: len(v) for k, v in runnable_problems_by_split.items()})
    t0_agent = time.time()
    if run_agent:
        question_ids = [
            d[split][question_index]["instance_id"]
            for question_index in range(first_question_index, last_question_index)
        ]
        run_agents_and_catch_logs(
            model_name=model_name, instance_ids=question_ids, instance_cost_limit=cost_limit, split=split
        )
    print("Time taken to run agent: ", time.time() - t0_agent)
    if evaluate_agent:
        import time

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
                full_dataset=d,
            )
        print("Time taken to evaluate runs: ", time.time() - t0)
