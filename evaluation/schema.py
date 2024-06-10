import pydantic
import eval_type_backport


class Args(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra='ignore')
    swe_bench_tasks: str


class Report(pydantic.BaseModel):
    no_generation: list[str] = []
    generated: list[str] = []
    with_logs: list[str] = []
    install_fail: list[str] = []
    reset_failed: list[str] = []
    no_apply: list[str] = []
    applied: list[str] = []
    test_errored: list[str] = []
    test_timeout: list[str] = []
    resolved: list[str] = []


class AllPreds(pydantic.BaseModel):
    model_name_or_path: str
    instance_id: str
    model_patch: str


class DataPoint(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra='ignore')
    instance_id: str
    patch: str
