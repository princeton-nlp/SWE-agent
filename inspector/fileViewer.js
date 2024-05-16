let currentFileName = null; // Store the current file name
let trajectoryDirectory = ""; // Global variable to store the directory
let timeoutIds = []; // Store timeout IDs for pending operations

function getBaseUrl() {
  const protocol = window.location.protocol;
  const host = window.location.hostname;
  const port = window.location.port;

  // Use the default port if the port number is empty (for standard HTTP/HTTPS)
  const defaultPort =
    protocol === "http:" && !port
      ? "80"
      : protocol === "https:" && !port
        ? "443"
        : port;

  return `${protocol}//${host}:${defaultPort}`;
}

function fetchFiles() {
  const baseUrl = getBaseUrl();
  fetch(`${baseUrl}/files`)
    .then((response) => response.json())
    .then((files) => {
      const fileList = document.getElementById("fileList");
      fileList.innerHTML = "";
      files.forEach((file) => {
        const fileElement = document.createElement("li");
        fileElement.textContent = file;
        fileElement.onclick = () => viewFile(file.split(" ")[0]);
        fileList.appendChild(fileElement);
      });
    });
}

// translate item.role to what we show the user
const roleMap = {
  user: "Environment",
  assistant: "SWE-Agent",
  subroutine: "SWE-Agent subroutine",
  default: "Default",
  system: "System",
  demo: "Demonstration",
};

function getRoleText(role) {
  return roleMap[role] || role;
}

function viewFile(fileName) {
  // Clear any pending message loading from previous files
  timeoutIds.forEach((timeoutId) => clearTimeout(timeoutId));
  timeoutIds = []; // Reset the list of timeout IDs

  const baseUrl = getBaseUrl();
  fetch(`${baseUrl}/trajectory/${fileName}`)
    .then((response) => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    })
    .then((content) => {
      const container = document.getElementById("fileContent");
      container.innerHTML = ""; // Clear existing content

      if (content.history && Array.isArray(content.history)) {
        let delay = 200; // Initial delay
        const delayIncrement = 50; // Delay between each message, in milliseconds

        content.history.forEach((item, index) => {
          const timeoutId = setTimeout(() => {
            const contentText = item.content
              ? item.content.replace(/</g, "&lt;").replace(/>/g, "&gt;")
              : "";
            let roleClass =
              item.agent && item.agent !== "primary"
                ? "subroutine"
                : item.role
                  ? item.role.toLowerCase().replaceAll(" ", "-")
                  : "default";
            const elementId = "historyItem" + index;
            const historyItem = document.createElement("div");
            historyItem.className = `history-item ${roleClass} fade-in`;
            historyItem.id = elementId;
            if (contentText.includes("--- DEMONSTRATION ---")) {
              item.role = "demo";
            } else if ("is_demo" in item && item.is_demo === true) {
              item.role += "[demo]";
            }
            historyItem.innerHTML = `
                            <div class="role-bar ${roleClass}">
                                <strong>
                                    <span>${getRoleText(item.role)}</span>
                                </strong>
                            </div>
                            <div class="content-container">
                                <pre>${contentText}</pre>
                            </div>
                            <div class="shadow"></div>
                        `;
            container.appendChild(historyItem);
          }, delay);

          delay += delayIncrement; // Increment delay for the next message
          timeoutIds.push(timeoutId); // Store the timeout ID
        });
      } else {
        container.textContent = "No history content found.";
      }
    })
    .catch((error) => {
      console.error("Error fetching file:", error);
      document.getElementById("fileContent").textContent =
        "Error loading content. " + error;
    });

  // Highlight the selected file in the list
  document.querySelectorAll("#fileList li").forEach((li) => {
    li.classList.remove("selected");
    if (li.textContent.split(" ")[0] === fileName) {
      li.classList.add("selected");
    }
  });
}

function refreshCurrentFile() {
  if (currentFileName) {
    const currentScrollPosition =
      document.documentElement.scrollTop || document.body.scrollTop;
    viewFile(currentFileName.split(" ")[0]); // Reload the current file
    // Restore the scroll position after the content is loaded
    setTimeout(() => {
      window.scrollTo(0, currentScrollPosition);
    }, 100);
  }
}

function fetchDirectoryInfo() {
  const baseUrl = getBaseUrl();
  fetch(`${baseUrl}/directory_info`)
    .then((response) => response.json())
    .then((data) => {
      if (data.directory) {
        trajectoryDirectory = data.directory; // Store the directory
        document.title = `Trajectory Viewer: ${data.directory}`;
        document.querySelector("h1").textContent =
          `Trajectory Viewer: ${data.directory}`;
      }
    })
    .catch((error) => console.error("Error fetching directory info:", error));
}

window.onload = function () {
  fetchFiles();
  fetchDirectoryInfo();
};
