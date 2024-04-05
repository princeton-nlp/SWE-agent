import { OutputView } from "@/components/OutputView";
import { useState } from "react";

const LOCAL_API_RUN_AGENT_ENDPOINT = "/api/runAgent";

const reshapeFormDataFromEvent = async ({ formEvent }) => {
    const formData = new FormData(formEvent.target);
    const data = Object.fromEntries(formData.entries());
    return data;
};

const validateFormData = async ({ formData }) => {
    if (!formData["openai_api_key"]) {
        throw Error("OpenAI API Key is required");
    }
    if (!formData["github_api_key"]) {
        throw Error("Github API Key is required");
    }
    if (!formData["github_issue_link"]) {
        throw Error("Github Issue Link is required");
    }
    if (!formData["config_filename"]) {
        throw Error("Config is required");
    }
};

const makeRequest = async ({ formData }) => {
    // Make fetch request to backend
    const response = await fetch(LOCAL_API_RUN_AGENT_ENDPOINT, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
    });

    if (!response.ok || response.status >= 400) {
        throw Error(response.statusText);
    }

    const data = await response.json();
    return data;
};

export default function Home() {
    const [validationError, setValidationError] = useState(null);
    const handleSubmit = async (formEvent) => {
        try {
            formEvent.preventDefault();
            const formData = await reshapeFormDataFromEvent({ formEvent });
            await validateFormData({ formData });
            setValidationError(null);
            const response = await makeRequest({ formData });
        } catch (error) {
            // Show validation or toher error message to user
            console.error(error);
            if (error && typeof error === "string") {
                setValidationError(error);
            } else if (error && typeof error === "object" && error?.message) {
                setValidationError(error?.message);
            } else {
                setValidationError("An error occurred");
            }
        }
    };
    return (
        <main>
            {validationError && (
                <div className="rounded-md p-4 bg-red-200 border-red-400 my-4">
                    {validationError}
                </div>
            )}
            <form onSubmit={handleSubmit}>
                <h1>SWE-agent</h1>

                <h2>Config</h2>
                <>
                    <h3>Tokens</h3>
                    <input type="text" placeholder="OpenAI API Key" name="openai_api_key" />
                    <input type="text" placeholder="Gituhb API Key" name="github_api_key" />
                </>

                <>
                    <h3>Issue</h3>
                    <input type="text" placeholder="Github Issue Link" name="github_issue_link" />
                </>

                <>
                    <h3>Pre-configured settings</h3>
                    <select name="config_filename">
                        <option value="1">Config 1</option>
                        <option value="2">Config 2</option>
                        <option value="3">Config 3</option>
                    </select>
                </>

                <>
                    <h3>Tail Output</h3>
                    {/* <OutputView /> */}
                </>

                <button type="submit">Run</button>
            </form>
        </main>
    );
}
