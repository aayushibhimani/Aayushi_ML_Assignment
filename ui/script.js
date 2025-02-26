document.getElementById("generateBtn").addEventListener("click", async function() {
    const prompt = document.getElementById("prompt").value;
    const maxTokens = document.getElementById("max_tokens").value;
    const temperature = document.getElementById("temperature").value;
    
    if (!prompt) {
        alert("Please enter a prompt!");
        return;
    }

    // Prepare API request
    const requestData = {
        prompt: prompt,
        max_tokens: parseInt(maxTokens),
        temperature: parseFloat(temperature)
    };

    document.getElementById("response").textContent = "Generating...";
    document.getElementById("stats").textContent = "";

    try {
        // Send request to FastAPI backend
        const response = await fetch("http://localhost:8000/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            throw new Error(`Error: ${response.statusText}`);
        }

        const result = await response.json();

        document.getElementById("response").textContent = result.response;

        document.getElementById("stats").textContent = `
            Model Used: ${result.provider_used}
            Cost: $${result.cost}
            Tokens Used: ${result.total_tokens}
            Prompt Tokens: ${result.prompt_tokens}
            Completion Tokens: ${result.completion_tokens}
        `;

    } catch (error) {
        document.getElementById("response").textContent = "Error generating text.";
        document.getElementById("stats").textContent = error.message;
    }
});
