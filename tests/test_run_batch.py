from pathlib import Path

import pytest

from sweagent.run.run import main


@pytest.mark.slow
def test_expert_instances(test_data_sources_path: Path, tmp_path: Path):
    ds_path = test_data_sources_path / "expert_instances.yaml"
    assert ds_path.exists()
    cmd = [
        "run-batch",
        "--agent.model.name",
        "instant_empty_submit",
        "--instances.type",
        "expert_file",
        "--instances.path",
        str(ds_path),
        "--output_dir",
        str(tmp_path),
        "--raise_exceptions",
    ]
    main(cmd)
    for _id in ["simple_test_problem", "simple_test_problem_2"]:
        assert (tmp_path / f"{_id}.traj").exists(), list(tmp_path.iterdir())


@pytest.mark.slow
def test_simple_instances(test_data_sources_path: Path, tmp_path: Path):
    ds_path = test_data_sources_path / "simple_instances.yaml"
    assert ds_path.exists()
    cmd = [
        "run-batch",
        "--agent.model.name",
        "instant_empty_submit",
        "--instances.path",
        str(ds_path),
        "--output_dir",
        str(tmp_path),
        "--raise_exceptions",
    ]
    main(cmd)
    assert (tmp_path / "simple_test_problem.traj").exists(), list(tmp_path.iterdir())


def test_empty_instances_simple(test_data_sources_path: Path, tmp_path: Path):
    ds_path = test_data_sources_path / "simple_instances.yaml"
    assert ds_path.exists()
    cmd = [
        "run-batch",
        "--agent.model.name",
        "instant_empty_submit",
        "--instances.path",
        str(ds_path),
        "--output_dir",
        str(tmp_path),
        "--raise_exceptions",
        "--instances.filter",
        "doesnotmatch",
    ]
    with pytest.raises(ValueError, match="No instances to run"):
        main(cmd)


def test_empty_instances_expert(test_data_sources_path: Path, tmp_path: Path):
    ds_path = test_data_sources_path / "expert_instances.yaml"
    assert ds_path.exists()
    cmd = [
        "run-batch",
        "--agent.model.name",
        "instant_empty_submit",
        "--instances.path",
        str(ds_path),
        "--instances.type",
        "expert_file",
        "--output_dir",
        str(tmp_path),
        "--raise_exceptions",
        "--instances.filter",
        "doesnotmatch",
    ]
    with pytest.raises(ValueError, match="No instances to run"):
        main(cmd)


# This doesn't work because we need to retrieve environment variables from the environment
# in order to format our templates.
# def test_run_batch_swe_bench_instances(tmp_path: Path):
#     cmd = [
#         "run-batch",
#         "--agent.model.name",
#         "instant_empty_submit",
#         "--instances.subset",
#         "lite",
#         "--instances.split",
#         "test",
#         "--instances.slice",
#         "0:1",
#         "--output_dir",
#         str(tmp_path),
#         "--raise_exceptions",
#         "--instances.deployment.type",
#         "dummy",
#     ]
#     main(cmd)
