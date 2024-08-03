from hackathon.evaluation.evaluate import run_and_catch_logs, run_swebench_evaluation
import time

def run_instance(model_name, instance_id, cost_limit, split):
    return run_and_catch_logs(model_name=model_name, instance=instance_id, cost_limit=cost_limit, split=split)


def check_mini_for_regressions(splits_to_check=["dev", "test"], model_name="gpt-4o-mini", cost_limit=1.00):
    t0 = time.time()
    from datasets import load_dataset
    d = load_dataset("princeton-nlp/SWE-bench_Lite")

    mini_successes = {
        "dev": [
            "pvlib__pvlib-python-1072",
            "pydicom__pydicom-1694"
        ],
        "test": ["astropy__astropy-14995", "django__django-11039", "django__django-11099", "django__django-11133", "django__django-12453", "django__django-12983", "django__django-13658", "django__django-14382", "django__django-14855"]
    }

    for split in splits_to_check:
        import multiprocessing

        num_cpus = multiprocessing.cpu_count()
        with multiprocessing.Pool(processes=num_cpus) as pool:
            pool.starmap(run_instance, [(model_name, instance_id, cost_limit, split) for instance_id in mini_successes[split]])
    t1 = time.time()
    for split in splits_to_check:
        success_ids,  failed_ids = run_swebench_evaluation(
            predictions_path_override=None,
            model_name=model_name,
            full_dataset_name="princeton-nlp/SWE-bench_Lite",
            cost_limit=cost_limit,
            temperature=0.00,
            top_p=0.95,
            run_id="test",
            split=split,
            max_workers=8,
            dev_ids = mini_successes[split],
            test_ids = mini_successes[split]
        )
        print("Newly failed ids: ", failed_ids, "In split: ", split)
    print("Time taken to run agent: ", t1 - t0)
    print("Time taken to run swebench evaluation: ", time.time() - t1)

if __name__ == "__main__":
    t0 = time.time()
    check_mini_for_regressions(
        splits_to_check=["test"],
        model_name="gpt4o",
        cost_limit=1.00
    )
    print("Time taken: ", time.time() - t0)
    #5 - 357.5591461658478 @ two workers
    #6 - 1722.5970497131348 @ 8 workers

    # 25 cent test - gpt-4o
    # agent time: 349.05855894088745
    # eval time: 9.075476884841919

    # 50 cent test - gpt-4o
    # agent time: 285.3860
    # eval time: 138.46

    # 50 cent test - gpt-4o
    # django__django-11099, django__django-11133, django__django-12453, django__django-13658, django__django-14855
    # 240s agent, 220 s eval
    # 
    pass

    
    
    