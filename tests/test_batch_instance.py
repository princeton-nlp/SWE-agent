import json

import pytest

from sweagent.environment.config.deployment import DockerDeploymentConfig
from sweagent.environment.config.problem_statement import TextProblemStatement
from sweagent.environment.config.repo import PreExistingRepo
from sweagent.run.batch_instances import BatchInstance, SimpleBatchInstance, SWEBenchInstances, _slice_spec_to_slice


def test_simple_batch_from_swe_bench_to_full_batch_instance(test_data_sources_path):
    sb_instance = json.loads((test_data_sources_path / "swe-bench-dev-easy.json").read_text())[0]
    instance = SimpleBatchInstance.from_swe_bench(sb_instance).to_full_batch_instance(DockerDeploymentConfig())
    assert isinstance(instance.env.repo, PreExistingRepo)
    assert instance.env.repo.repo_name == "testbed"
    assert isinstance(instance.env.deployment, DockerDeploymentConfig)
    assert instance.env.deployment.image == "swebench/sweb.eval.x86_64.pydicom_1776_pydicom-1458:v1"
    assert isinstance(instance.problem_statement, TextProblemStatement)
    assert instance.problem_statement.text == sb_instance["problem_statement"]
    assert instance.problem_statement.id == "pydicom__pydicom-1458"


def test_slice_spec_to_slice():
    assert _slice_spec_to_slice("10") == slice(10)
    assert _slice_spec_to_slice("10:20") == slice(10, 20)
    assert _slice_spec_to_slice("10:20:3") == slice(10, 20, 3)
    with pytest.raises(ValueError):
        _slice_spec_to_slice("10:20:3:4")


@pytest.mark.slow
def test_get_swe_bench_instances():
    for flavor in ["lite", "verified", "full"]:
        for split in ["dev", "test"]:
            if flavor == "verified" and split == "dev":
                continue
            print(flavor, split)
            instance_config = SWEBenchInstances(flavor=flavor, split=split)  # type: ignore
            instances = instance_config.get_instance_configs()
            assert len(instances) > 0
            assert all(isinstance(instance, BatchInstance) for instance in instances)
