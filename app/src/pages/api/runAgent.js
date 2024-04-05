const { spawn } = require("child_process");

export default function handler(req, res) {
    const {
        openai_api_key,
        github_api_key,
        github_issue_link,
        config_filename,
    } = req.body;

    // Construct the command to run your Python script within the Conda environment
    // Note: Adjust 'myenv' to your Conda environment's name
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

    // Use spawn with shell=true to execute the command in a shell, allowing for Conda environment usage
    const agent = spawn(command, {
        shell: true,
        cwd: "../",
        env: {
            ...process.env, // Include existing environment variables
            OPENAI_API_KEY: openai_api_key, // Pass additional variables
            GITHUB_API_KEY: github_api_key,
        },
    });

    // Directly stream stdout and stderr to the HTTP response
    agent.stdout.pipe(res);
    agent.stderr.pipe(res); // You might want to handle stderr differently depending on your needs

    agent.on("close", (code) => {
        console.log(`Agent exited with code ${code}`);
        if (code !== 0) {
            // Optionally, handle non-zero exit codes explicitly
            // For example, you could end the response with a specific error message
            res.status(500).send(`Agent exited with code ${code}`);
        } else {
            // Ensure the response is properly closed when the process ends successfully
            res.end();
        }
    });

    agent.on("error", (error) => {
        console.error(`Failed to start subprocess: ${error}`);
        res.status(500).send(`Failed to start subprocess: ${error}`);
    });
}
