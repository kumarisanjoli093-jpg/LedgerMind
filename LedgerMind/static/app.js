
// ==================================================
// LEDGERMIND — FRONTEND APPLICATION
// ==================================================

const $ = (id) => document.getElementById(id);

// ==================================================
// UTILITIES
// ==================================================

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

function displayValue(value) {
    if (value === null || value === undefined || value === "") {
        return "Not available";
    }

    if (typeof value === "object") {
        return JSON.stringify(value);
    }

    return String(value);
}

function toast(message) {
    const element = $("toast");
    if (!element) return;

    element.textContent = message;
    element.classList.add("show");

    setTimeout(() => {
        element.classList.remove("show");
    }, 3500);
}

async function api(url, options = {}) {
    const response = await fetch(url, options);

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(
            data.detail || data.message || `Server error: ${response.status}`
        );
    }

    return data;
}

// ==================================================
// NAVIGATION
// ==================================================

function showView(view) {
    document.querySelectorAll(".view").forEach(section => {
        section.classList.toggle("active", section.id === view);
    });

    document.querySelectorAll(".nav-item").forEach(button => {
        button.classList.toggle(
            "active",
            button.dataset.view === view
        );
    });

    const titles = {
        overview: [
            "Overview",
            "Your financial intelligence workspace."
        ],
        invoices: [
            "Invoice intelligence",
            "Extract structured information from invoices."
        ],
        assistant: [
            "AI financial assistant",
            "Ask questions about your financial records."
        ],
        knowledge: [
            "Knowledge base",
            "Manage information available to your AI agent."
        ],
        memory: [
            "Vendor memory",
            "Persistent memory and integration status."
        ]
    };

    if (titles[view]) {
        $("pageTitle").textContent = titles[view][0];
        $("pageDescription").textContent = titles[view][1];
    }

    if (view === "memory") {
        checkStatus();
    }
}

document.querySelectorAll("[data-view]").forEach(button => {
    button.addEventListener("click", () => {
        showView(button.dataset.view);
    });
});

document.querySelectorAll("[data-go]").forEach(button => {
    button.addEventListener("click", () => {
        showView(button.dataset.go);
    });
});

// ==================================================
// BACKEND AND SERVICE STATUS
// ==================================================

async function checkStatus() {
    try {
        const data = await api("/api/ai/status");

        $("systemDot").className = "status-dot good";
        $("systemLabel").textContent = "Backend connected";
        $("connectionLabel").textContent = "Backend connected";

        $("hindsightStatus").textContent =
            data.hindsight_status || "Not reported";

        $("agentStatus").textContent =
            data.agent || "Not reported";

        $("ragStatus").textContent =
            data.rag_available ? "Available" : "Unavailable";

    } catch (error) {
        $("systemDot").className = "status-dot bad";
        $("systemLabel").textContent = "Backend unavailable";
        $("connectionLabel").textContent = "Connection error";

        $("hindsightStatus").textContent = "Unable to check";
        $("agentStatus").textContent = "Unable to check";
        $("ragStatus").textContent = "Unable to check";

        console.error("Status check failed:", error);
    }
}

$("refreshButton").addEventListener("click", checkStatus);
$("memoryRefresh").addEventListener("click", checkStatus);

// ==================================================
// INVOICE UPLOAD AND EXTRACTION
// ==================================================

$("invoiceFile").addEventListener("change", event => {
    const file = event.target.files[0];

    $("fileName").textContent = file
        ? `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`
        : "Click here to select a PDF or image";
});

$("extractButton").addEventListener("click", async () => {
    const file = $("invoiceFile").files[0];

    if (!file) {
        toast("Please select an invoice first.");
        return;
    }

    const allowedTypes = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp"
    ];

    if (!allowedTypes.includes(file.type)) {
        toast("Upload a PDF, JPG, PNG or WEBP file.");
        return;
    }

    if (file.size > 15 * 1024 * 1024) {
        toast("Maximum file size is 15 MB.");
        return;
    }

    const button = $("extractButton");

    button.disabled = true;
    button.textContent = "Processing...";

    $("invoiceLoading").classList.remove("hidden");
    $("invoiceResult").innerHTML = "";

    try {
        const formData = new FormData();
        formData.append("file", file);

        const data = await api("/api/ai/extract-invoice", {
            method: "POST",
            body: formData
        });

        const invoice = data.invoice || {};

        $("invoiceResult").innerHTML = `
            <div class="result-card">
                <div class="success-text">
                    ${escapeHTML(data.message || "Invoice processed.")}
                </div>

                <h3 style="margin-top:16px">
                    Extracted invoice information
                </h3>

                <div class="result-grid">
                    ${Object.entries(invoice).map(([key, value]) => `
                        <div class="result-field">
                            <small>
                                ${escapeHTML(key.replaceAll("_", " "))}
                            </small>
                            <strong>
                                ${escapeHTML(displayValue(value))}
                            </strong>
                        </div>
                    `).join("")}
                </div>

                <p class="form-note">
                    Document ID:
                    ${escapeHTML(data.document_id || "Not provided")}
                </p>

                <p class="form-note">
                    RAG chunks added:
                    ${escapeHTML(data.rag_chunks_added ?? "Not reported")}
                </p>
            </div>
        `;

        toast("Invoice extraction completed.");

    } catch (error) {
        $("invoiceResult").innerHTML = `
            <div class="error-text">
                ${escapeHTML(error.message)}
            </div>
        `;

        toast("Invoice extraction failed.");
        console.error(error);

    } finally {
        button.disabled = false;
        button.textContent = "Extract invoice data";
        $("invoiceLoading").classList.add("hidden");
    }
});

// ==================================================
// AI FINANCIAL ASSISTANT
// ==================================================

function addMessage(message, type) {
    const element = document.createElement("div");

    element.className = `chat-message ${type}`;
    element.textContent = message;

    $("chatOutput").appendChild(element);

    $("chatOutput").scrollTop =
        $("chatOutput").scrollHeight;
}

document.querySelectorAll(".suggestion").forEach(button => {
    button.addEventListener("click", () => {
        $("questionInput").value = button.textContent.trim();
        $("questionInput").focus();
    });
});

$("askForm").addEventListener("submit", async event => {
    event.preventDefault();

    const question = $("questionInput").value.trim();

    if (!question) return;

    addMessage(question, "user");

    $("questionInput").value = "";

    const button = $("askButton");

    button.disabled = true;
    button.textContent = "Thinking...";

    try {
        const data = await api("/api/ai/ask", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question,
                top_k: 5
            })
        });

        const answer =
            typeof data === "string"
                ? data
                : data.answer ||
                  data.response ||
                  data.message ||
                  JSON.stringify(data, null, 2);

        addMessage(answer, "bot");

    } catch (error) {
        addMessage(
            "Unable to process your question: " + error.message,
            "bot"
        );

        console.error(error);

    } finally {
        button.disabled = false;
        button.textContent = "Send ↑";
    }
});

// ==================================================
// KNOWLEDGE BASE AND RAG INGESTION
// ==================================================

$("ingestForm").addEventListener("submit", async event => {
    event.preventDefault();

    const text = $("documentInput").value.trim();

    if (!text) {
        toast("Please enter document content.");
        return;
    }

    const button = $("ingestButton");

    button.disabled = true;
    button.textContent = "Adding document...";

    $("ingestResult").innerHTML = "";

    try {
        const data = await api("/api/ai/ingest-text", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                text: text,
                source:
                    $("sourceInput").value.trim() ||
                    "financial-reference",
                vendor:
                    $("vendorInput").value.trim() || null
            })
        });

        $("ingestResult").innerHTML = `
            <div class="success-text">
                ${escapeHTML(data.message || "Document added.")}

                <br>
                Chunks added:
                ${escapeHTML(data.chunks_added ?? "Not reported")}
            </div>
        `;

        $("documentInput").value = "";

        toast("Knowledge base updated.");

    } catch (error) {
        $("ingestResult").innerHTML = `
            <div class="error-text">
                ${escapeHTML(error.message)}
            </div>
        `;

        console.error(error);

    } finally {
        button.disabled = false;
        button.textContent = "Add to knowledge base";
    }
});

// ==================================================
// INITIALIZE APPLICATION
// ==================================================

document.addEventListener("DOMContentLoaded", () => {
    checkStatus();
});
