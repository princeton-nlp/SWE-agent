
if [ -z "$(docker images -q sweagent/swe-agent 2> /dev/null)" ]; then
  echo "⚠️ Please wait for the postCreateCommand to start and finish (a new window will appear shortly) ⚠️"
fi

echo "Here's an example SWE-agent command to try out:"
echo "python run.py --model_name gpt4 --data_path https://github.com/pvlib/pvlib-python/issues/1603 --config_file config/default_from_url.yaml"
echo "Alternatively, start the web UI with "
echo "./start_web_ui.sh"
