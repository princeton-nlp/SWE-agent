# Changelog

## 0.4.0 (2024-05-09)

[All new commits](https://github.com/princeton-nlp/SWE-agent/compare/v0.3.0...v0.4.0)

### Added

We’re excited to launch the SWE-agent web UI! Specify a bug, press start and watch SWE-agent do the magic.

## 0.3.0 (2024-05-02)

### Added

* Run SWE-agent in the cloud using GitHub Codespaces
* Add GPT4-turbo model by @zgrannan in https://github.com/princeton-nlp/SWE-agent/pull/252
* feat: Amazon Bedrock support (Claude models) by @JGalego in https://github.com/princeton-nlp/SWE-agent/pull/207

### Fixed 

* Better error handling for --open_pr by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/239
* Fixed a potential error by @DanjieTang in https://github.com/princeton-nlp/SWE-agent/pull/242
* fix: TARGETARCH not set on some OS/docker setups by @mspronesti in https://github.com/princeton-nlp/SWE-agent/pull/249
* Pass Python version to get_environment_yml by @waterson in https://github.com/princeton-nlp/SWE-agent/pull/271
* Fix Together model validation error by @mikanfactory in https://github.com/princeton-nlp/SWE-agent/pull/236
* Doc: Avoid invalid github token by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/292

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
