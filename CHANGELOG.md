# Changelog

## 0.2.0 (2024-04-15)

[All new commits](https://github.com/princeton-nlp/SWE-agent/compare/v0.1.2...v0.2.0)

### Added

* Allow to run on local repos (new flag: `--repo_path`) in https://github.com/princeton-nlp/SWE-agent/pull/193
* Patch files are now saved separately to a patch directory in https://github.com/princeton-nlp/SWE-agent/pull/126
* Allow to supply custom installation commands when running on gh issues or locally (`--environment_setup`) in https://github.com/princeton-nlp/SWE-agent/pull/153
* Allow to specify openapi base url in `keys.cfg` in https://github.com/princeton-nlp/SWE-agent/pull/118

### Improved

* Improve error handling of docker issues in https://github.com/princeton-nlp/SWE-agent/pull/165
* Make github token fully optional in https://github.com/princeton-nlp/SWE-agent/pull/189

### Fixed

* Fix opening PR from fork in https://github.com/princeton-nlp/SWE-agent/pull/229
* Fix: Choosing TogetherAI models in https://github.com/princeton-nlp/SWE-agent/pull/130
