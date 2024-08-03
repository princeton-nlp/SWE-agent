from run import main,get_args_dev
import io
import sys
from contextlib import redirect_stdout
from run import main, get_args_dev

def run_and_catch_logs(model_name = "gpt-4o-mini", instance = "marshmallow-code__marshmallow-1359", cost_limit=0.05):
    output = io.StringIO()
    with redirect_stdout(output):
        main(get_args_dev(
            model_name=model_name,
            instance_to_filter_by=instance,
            per_instance_cost_limit=cost_limit
        ))
    
    captured_logs = output.getvalue()
    log_lines = captured_logs.splitlines()
    print(f"Captured {len(log_lines)} lines of logs")

#TODO: goal here is for us to be able to run swe-agent and then eval it with swe-bench to know correct/incorrect. 
# Then, to enable us to add scoring functions that parse through the logged lines and keep track of intermediate metrics
if __name__ == "__main__":
    from datasets import load_dataset

    # TODO: seems like in my local env I'm struggling with
    # types-pkg_resources
    d = load_dataset("princeton-nlp/SWE-bench_Lite")
    question_index = 0
    run_and_catch_logs(instance=d['dev'][question_index]['instance_id'])

    