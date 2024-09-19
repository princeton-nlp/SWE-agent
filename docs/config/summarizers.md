# Summarizers Configuration

LMs perform best if given concise inputs; superfluous context can degrade performance while increasing costs. Because agents require LMs to process entire trajectories, compressing context is of particular importance.

We designed two summarizers to handle long output commands. The first, a ***simple summarizer***, saves the command output to a file if it exceeds a certain configurable line count. We show an indicative warning to the agent and tell it to open the saved command output using the built-in SWE-agent utility `open`.

The second, an ***LM summarizer***, integrates with the main agent to enhance its problem-solving efficacy and avoid exceeding input length limitations. It employs the same model (though can be configured differently) as the main agent; it receives a configurable prompt containing some context about the problem, the most recent action taken by the main agent, and any observations from that action exceeding a configurable line count threshold. The LM summarizer then generates a concise summary of the observation that is directly relevant to the ongoing problem. This summary is sent to the main agent, accompanied by a warning message indicating that the command output was summarized due to exceeding the line count limit.

The summarizer configuration is defined within the main [configuration](config.md) `.yaml` file, and has the following structure:

```yaml
summarizer_config:
  function: Reference to functionality of the summarizer. Can be one of SimpleSummarizer, LMSummarizer or Identity
  window_length: Threshold of the line count limit. Observation output exceeding these number, will be summarized.
  system_template: |-
    First `system` message shown to the LMSummarizer. 
    This has no effect in other summarizer functionalities.
  instance_template: |-
    Instance prompt, contains task instance-specific content, 
    the most recent action taken by the main agent, 
    and any observations from that action exceeding the line count threshold. 
    This has effect only for the LM Summarizer functionality.
  model: [Optional configuration of a different model, 
  if not configured the same model as the main agent model will be used. 
  This has effect only for the LM Summarizer functionality.]
    model_name: Name of the model to use
    per_instance_cost_limit: Cost limit for every instance (task)
    total_cost_limit: Total cost limit for summarizer only
    temperature: Sampling temperature
    top_p: Sampling top-p
    host_url: Host URL when using Ollama model
```
