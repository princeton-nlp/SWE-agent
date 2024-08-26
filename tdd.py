import os
from pathlib import Path

# various configurable things.  Many these will go into computing the path for
# the trajectory directory that contains all_preds.jsonl after an inference run.
model_name = "claude-sonnet-3.5"
dataset_name = "princeton-nlp/SWE-bench_Verified"
split = "test"
config = "default"
temperature = 0
top_p = 0.95
per_instance_cost_limit = 2
install_env="install"

# a list of all instance id strings we'll be running inference on and evaluating.
instance_id_list: list[str] = [
    # a random sample of the 50 instances in the dataset.
    # seed = 1724428709 here
    'matplotlib__matplotlib-21568',
    'django__django-15957',
    'django__django-14170',
    'scikit-learn__scikit-learn-12682',
    'scikit-learn__scikit-learn-25931',
    'scikit-learn__scikit-learn-14629',
    'scikit-learn__scikit-learn-13328',
    'pytest-dev__pytest-6202',
    'sphinx-doc__sphinx-8035',
    'pytest-dev__pytest-5840',
    'pytest-dev__pytest-5631',
    'pytest-dev__pytest-5262',
    'sympy__sympy-23413',
    'pytest-dev__pytest-10051',
    'django__django-13821',
    'django__django-13786',
    'matplotlib__matplotlib-25775',
    'django__django-11206',
    'astropy__astropy-14096',
    'sphinx-doc__sphinx-8593',
    'django__django-14155',
    'sphinx-doc__sphinx-9698',
    'django__django-16560',
    'sympy__sympy-12481',
    'django__django-12276',
    'pylint-dev__pylint-7080',
    'django__django-13121',
    'sympy__sympy-18189',
    'django__django-17029',
    'sphinx-doc__sphinx-10614',
    'django__django-15572',
    'scikit-learn__scikit-learn-14710',
    'astropy__astropy-14309',
    'scikit-learn__scikit-learn-25232',
    'sympy__sympy-15976',
    'django__django-12858',
    'scikit-learn__scikit-learn-25973',
    'sympy__sympy-23534',
    'django__django-13569',
    'django__django-13925',
    'sphinx-doc__sphinx-7454',
    'matplotlib__matplotlib-22719',
    'django__django-16454',
    'django__django-14053',
    'psf__requests-1142',
    'scikit-learn__scikit-learn-14983',
    'django__django-13363',
    'scikit-learn__scikit-learn-14087',
    'django__django-13089',
    'django__django-11095',
]

def trajectory_dir():
    return f"trajectories/{os.getlogin()}/{model_name}__{Path(dataset_name).stem}__{config}__t-{temperature:.2f}__p-{top_p:.2f}__c-{per_instance_cost_limit:.2f}__{install_env}-1"

def run_python_cmd(cmd: str, args: dict[str, str]):
    # convert args to a string
    args_str = " ".join([f"--{k} {v}" for k, v in args.items()])
    # execute the command
    print(f"Running command: python {cmd} {args_str}")
    os.system(f"python {cmd} {args_str}")

def run_inference():
    print(f"Running inference:")
    run_python_cmd("run.py", {
        "model_name": model_name,
        "per_instance_cost_limit": 2.00,
        "config_file": f"./config/{config}.yaml",
        "data_path": dataset_name,
        "split": split,
        "instance_filter": f"\"{'|'.join(instance_id_list)}\"", # make sure we quote this because it contains a | symbol which the shell will want to interpret.
        "skip_existing": False, # causes inference to be re-run.  do we need/want this?
    })

def run_evaluation(predictions_path):
    print(f"Running evaluation:")
    run_python_cmd("-m swebench.harness.run_evaluation", {
        "run_id": "command_line_test",
        "dataset_name": dataset_name,
        "predictions_path": predictions_path,
#        "max_workers": 1,
        "split": split,
        "instance_ids": " ".join(instance_id_list),
    })


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()

    # parse command line arguments for "--inference" and "--evaluation" (both are store_true), and a --predictions_path argument for evaluation.
    parser.add_argument("--inference", action="store_true")
    parser.add_argument("--evaluation", action="store_true")
    parser.add_argument("--predictions_path", type=str)

    args = parser.parse_args()
    if args.inference:
        run_inference()

    if args.evaluation:
        predictions_path = args.predictions_path if args.predictions_path is not None else Path(trajectory_dir()) / "all_preds.jsonl"
        run_evaluation(predictions_path)
