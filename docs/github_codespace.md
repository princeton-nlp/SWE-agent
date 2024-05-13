# SWE-agent on GitHub Codespaces

## Running the web UI

Go to the terminal and enter

```bash
./start_web_ui.sh
```

After a while, you should see a popup offering you to forward port `3000`. Click `Open in Browser`.

![port 3000 forwarding popup](assets/open_port_default.png)


If you instead only see the offer to forward port `8000`, do not click it (this is the port that's being used by the backend).

Instead, click on the `Ports` tab, and click on the globe next to port `3000`:

![port 3000 forwarding manual](assets/open_port_in_browser.png)