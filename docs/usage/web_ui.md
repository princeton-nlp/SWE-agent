# Using the web interface

Our graphical web interface is optimized for using SWE-agent as a developer tool, fixing single GitHub issues or working in local repositories. 
However, it is still missing some of the options of the [command line interface](cl_tutorial.md).

## Quickstart

To start our web UI, simply run

```bash
./start_web_ui.sh
```

from the root of the repository.

!!! tip "Opening the webpage"
    If the user interface doesn't automatically open in your browser, please open it at `http://localhost:3000`. 
    Running from GitHub codespaces? More tips [here](../installation/codespaces.md#running-the-web-ui).

## Manually starting frontend and backend

The web UI consists of a frontend written in [react][] (showing the pretty control elements) and a backend written with [flask][]. 
The `./start_web_ui.sh` starts both of them in the background.
However, this might not be best for development and debugging.
This section explains how to start both parts separately.

[react]: https://react.dev/
[flask]: https://flask.palletsprojects.com/

First, let's start the backend:

```bash
python sweagent/api/server.py
```

You should see output similar to the following:

```
 * Serving Flask app 'server'
 * Debug mode: on
2024-05-23 11:30:45,436 - werkzeug - INFO - WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:8000
2024-05-23 11:30:45,437 - werkzeug - INFO - Press CTRL+C to quit
2024-05-23 11:30:45,437 - werkzeug - INFO -  * Restarting with watchdog (fsevents)
2024-05-23 11:30:46,484 - werkzeug - WARNING -  * Debugger is active!
2024-05-23 11:30:46,492 - werkzeug - INFO -  * Debugger PIN: 123-594-933
```

!!! tip "Port availability"
    If see an error about port 8000 not being available, 
    please first close any application that occupies it. 
    The frontend currently expects the `flask` server on port 8000, so choosing 
    a different port won't work.

Now, open a new terminal tab and navigate to the `frontend` directory:

```bash
cd sweagent/frontend
```

First, let's install the react dependencies:

```bash
npm install
```

And start the server:

```bash
npm start
```

This should also open the corresponding page in your browser. 
If not, check with the tips above. 
The default port that is being served is port 3000.

!!! tip "Possible errors"
    If you see errors

    ```
    Proxy error: Could not proxy request /socket.io/?EIO=4&transport=polling&t=O-c5kv9 from localhost:3000 to http://localhost:8000.
    See https://nodejs.org/api/errors.html#errors_common_system_errors for more information (ECONNREFUSED).
    ```

    something went wrong with the backend part.

{% include-markdown "../_footer.md" %}