const { spawn } = require("child_process");

export default function handler(req, res) {
    const {
        openai_api_key,
        github_api_key,
        github_issue_link,
        config_filename,
    } = req.body;

    const command = [
        `conda run -n swe-agent python run.py`,
        `--model_name gpt4`,
        github_issue_link ? `--data_path ${github_issue_link}` : null,
        config_filename ===
        `--instance_filter marshmallow-code__marshmallow-1359`
            ? `--instance_filter marshmallow-code__marshmallow-1359`
            : `--config_file ${config_filename}`,
        `--per_instance_cost_limit 2.00`,
    ]
        .filter((notFalsy) => !!notFalsy)
        .join(" ");

    const agent = spawn(command, {
        shell: true,
        cwd: "../",
        env: {
            ...process.env,
            OPENAI_API_KEY: openai_api_key,
            GITHUB_API_KEY: github_api_key,
        },
    });

    agent.stdout.pipe(res);
    agent.stderr.pipe(res);

    agent.on("close", (code) => {
        console.log(`Agent exited with code ${code}`);
        if (code !== 0) {
            res.status(500).send(`Agent exited with code ${code}`);
        } else {
            res.end();
        }
    });

    agent.on("error", (error) => {
        console.error(`Failed to start subprocess: ${error}`);
        res.status(500).send(`Failed to start subprocess: ${error}`);
    });
}
