const { spawn } = require("child_process");
export default function handler(req, res) {
    // Pass the configuration to the CLI interface
    const {
        openai_api_key,
        github_api_key,
        github_issue_link,
        config_filename,
    } = req.body;

    // Run the agent and stream the output back to the client
    const envVars = [
        `OPENAI_API_KEY=${openai_api_key}`,
        `GITHUB_API_KEY=${github_api_key}`,
    ];
    const args = [
        "run.py",
        "--model_name",
        "gpt4",
        "--data_path",
        github_issue_link,
        "--config_file",
        config_filename,
    ];
    const agent = spawn(`${envVars.join(" ")} python`, args);
    agent.stdout.pipe(res);
    agent.stderr.pipe(res);
    agent.on("close", (code) => {
        console.log(`Agent exited with code ${code}`);
    });
}
