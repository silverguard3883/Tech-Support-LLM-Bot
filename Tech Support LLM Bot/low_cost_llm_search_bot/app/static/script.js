const apiKeyBox = document.getElementById("apiKey");
const modeBox = document.getElementById("mode");
const useLiveWebBox = document.getElementById("useLiveWeb");
const seedUrlsBox = document.getElementById("seedUrls");
const questionBox = document.getElementById("question");
const askButton = document.getElementById("askButton");
const statusBox = document.getElementById("status");
const answerBox = document.getElementById("answer");
const sourcesBox = document.getElementById("sources");

apiKeyBox.value = localStorage.getItem("rag_api_key") || "";

askButton.addEventListener("click", async () => {
    const apiKey = apiKeyBox.value.trim();
    const question = questionBox.value.trim();
    const seedUrls = seedUrlsBox.value
        .split("\n")
        .map(item => item.trim())
        .filter(Boolean);

    localStorage.setItem("rag_api_key", apiKey);

    if (!question) {
        statusBox.textContent = "Enter a question.";
        return;
    }

    askButton.disabled = true;
    statusBox.textContent = "Processing...";
    answerBox.textContent = "";
    sourcesBox.innerHTML = "";

    try {
        const response = await fetch("/api/query", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": apiKey
            },
            body: JSON.stringify({
                question,
                mode: modeBox.value,
                use_live_web: useLiveWebBox.checked,
                seed_urls: seedUrls
            })
        });

        if (!response.ok) {
            throw new Error(await response.text());
        }

        const data = await response.json();
        statusBox.textContent = data.insufficient_evidence ? "Insufficient evidence" : "Done";
        answerBox.textContent = data.answer;
        renderSources(data.sources || []);
    } catch (error) {
        statusBox.textContent = "Request failed.";
        answerBox.textContent = error.message;
    } finally {
        askButton.disabled = false;
    }
});

function renderSources(sources) {
    sourcesBox.innerHTML = "";
    if (!sources.length) {
        return;
    }

    const heading = document.createElement("h2");
    heading.textContent = "Sources";
    sourcesBox.appendChild(heading);

    for (const source of sources) {
        const item = document.createElement("div");
        item.className = "source";
        item.textContent = `${source.label}: ${source.title} (${source.source_type}, chunk ${source.chunk_index}, similarity ${source.similarity})`;
        sourcesBox.appendChild(item);
    }
}
