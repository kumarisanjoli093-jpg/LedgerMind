
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
        return JSON.stringify(value, null, 2);
    }

    return String(value);
}

function toast(message) {
    const element = $("toast");
    if (!element) return;

    element.textContent = message;
    element.classList.add("show");

    setTimeout(() => element.classList.remove("show"), 3500);
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

function setText(id, value) {
    const element = $(id);
    if (element) element.textContent = displayValue(value);
}

function setHTML(id, value) {
    const element = $(id);
    if (element) element.innerHTML = value;
}

// ==================================================
// NAVIGATION
// ==================================================

const pageDetails = {
    overview: [
        "Overview",
        "Your financial intelligence workspace."
    ],
    invoices: [
        "Invoice intelligence",
        "Extract structured information from your invoices."
    ],
    knowledge: [
        "Knowledge base",
        "Manage information available to your AI agent."
    ],
    assistant: [
        "AI financial assistant",
        "Ask questions about your financial records."
    ],
    memory: [
        "Vendor memory",
        "Monitor persistent memory and connected services."
    ],
    activity: [
        "Activity",
        "Review the available system and service information."
    ],
    integrations: [
        "Integrations",
        "Check the status of connected services."
    ]
};

function showView(view) {
    if (!pageDetails[view]) return;

    document.querySelectorAll(".view").forEach(section => {
        section.classList.toggle("active", section.id === view);
    });

    document.querySelectorAll(".nav-item").forEach(button => {
        button.classList.toggle(
            "active",
            button.dataset.view === view
        );
    });

    setText("pageTitle", pageDetails[view][0]);
    setText("pageDescription", pageDetails[view][1]);

    const sidebar = document.querySelector(".sidebar");
    if (sidebar) sidebar.classList.remove("open");

    if (view === "memory" || view === "integrations") {
        checkStatus();
    }
}

document.querySelectorAll("[data-view]").forEach(button => {
    button.addEventListener("click", () => {
        showView(button.dataset.view);
    });
});

document.querySelectorAll("[data-go]").forEach(button => {
    button.addEventListener("click", event => {
        event.preventDefault();
        showView(button.dataset.go);
    });
});

// Mobile sidebar
const menuToggle = $("menuToggle");

if (menuToggle) {
    menuToggle.addEventListener("click", () => {
        document.querySelector(".sidebar")?.classList.toggle("open");
    });
}

// ==================================================
// BACKEND AND SERVICE STATUS
// ==================================================

function updateStatusElement(id, value, state) {
    const element = $(id);
    if (!element) return;

    element.textContent = value;

    if (state) {
        element.dataset.status = state;
    }
}

async function checkStatus() {
    try {
        const data = await api("/api/ai/status");

        const backendReady = data.success !== false;

        const dot = $("systemDot");
        if (dot) {
            dot.className = backendReady
                ? "status-dot good"
                : "status-dot bad";
        }

        setText(
            "systemLabel",
            backendReady ? "Backend connected" : "Backend unavailable"
        );

        const hindsight = data.hindsight_status || "Not reported";
        const agent = data.agent || "Not reported";
        const rag = data.rag_available ? "Available" : "Unavailable";

        updateStatusElement("hindsightStatus", hindsight);
        updateStatusElement("agentStatus", agent);
        updateStatusElement("ragStatus", rag);

        updateStatusElement("integrationBackend", "Connected");
        updateStatusElement("integrationAgent", agent);
        updateStatusElement("integrationRag", rag);
        updateStatusElement("integrationMemory", hindsight);

        updateStatusElement(
            "overviewMemory",
            hindsight
        );

    } catch (error) {
        const dot = $("systemDot");
        if (dot) dot.className = "status-dot bad";

        setText("systemLabel", "Backend unavailable");

        [
            "hindsightStatus",
            "agentStatus",
            "ragStatus",
            "integrationBackend",
            "integrationAgent",
            "integrationRag",
            "integrationMemory"
        ].forEach(id => {
            setText(id, "Unable to check");
        });

        setText("overviewMemory", "Unable to check");

        console.error("Status check failed:", error);
    }
}

["refreshButton", "memoryRefresh", "integrationRefresh"].forEach(id => {
    const button = $(id);
    if (button) button.addEventListener("click", checkStatus);
});

// ==================================================
// INVOICE UPLOAD AND EXTRACTION
// ==================================================

const invoiceFile = $("invoiceFile");

if (invoiceFile) {
    invoiceFile.addEventListener("change", event => {
        const file = event.target.files?.[0];

        setText(
            "fileName",
            file
                ? `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`
                : "Click here to select a PDF or image"
        );
    });
}

const extractButton = $("extractButton");

if (extractButton) {
    extractButton.addEventListener("click", async () => {
        const file = $("invoiceFile")?.files?.[0];

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

        extractButton.disabled = true;
        extractButton.textContent = "Processing...";

        $("invoiceLoading")?.classList.remove("hidden");
        setHTML("invoiceResult", "");

        try {
            const formData = new FormData();
            formData.append("file", file);

            const data = await api("/api/ai/extract-invoice", {
                method: "POST",
                body: formData
            });

            const invoice = data.invoice || {};

            const fields = Object.entries(invoice).map(([key, value]) => `
                <div class="result-field">
                    <small>${escapeHTML(key.replaceAll("_", " "))}</small>
                    <strong>${escapeHTML(displayValue(value))}</strong>
                </div>
            `).join("");

            setHTML("invoiceResult", `
                <div class="result-card">
                    <div class="success-text">
                        ${escapeHTML(data.message || "Invoice processed.")}
                    </div>

                    <h3 style="margin-top:16px">
                        Extracted invoice information
                    </h3>

                    <div class="result-grid">
                        ${fields || "<p>No structured invoice fields were returned.</p>"}
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
            `);

            toast("Invoice extraction completed.");

        } catch (error) {
            setHTML("invoiceResult", `
                <div class="error-text">
                    ${escapeHTML(error.message)}
                </div>
            `);

            toast("Invoice extraction failed.");
            console.error("Invoice extraction:", error);

        } finally {
            extractButton.disabled = false;
            extractButton.textContent = "Extract invoice data";
            $("invoiceLoading")?.classList.add("hidden");
        }
    });
}

// ==================================================
// AI FINANCIAL ASSISTANT
// ==================================================

function addMessage(message, type) {
    const output = $("chatOutput");
    if (!output) return;

    const element = document.createElement("div");
    element.className = `chat-message ${type}`;
    element.textContent = message;

    output.appendChild(element);
    output.scrollTop = output.scrollHeight;
}

document.querySelectorAll(".suggestion").forEach(button => {
    button.addEventListener("click", () => {
        const input = $("questionInput");
        if (!input) return;

        input.value = button.textContent.trim();
        input.focus();
    });
});

const askForm = $("askForm");

if (askForm) {
    askForm.addEventListener("submit", async event => {
        event.preventDefault();

        const input = $("questionInput");
        const button = $("askButton");

        const question = input?.value.trim();
        if (!question || !button) return;

        addMessage(question, "user");
        input.value = "";

        button.disabled = true;
        button.textContent = "Thinking...";

        try {
            const data = await api("/api/ai/ask", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    question,
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

            console.error("Assistant error:", error);

        } finally {
            button.disabled = false;
            button.textContent = "Send ↑";
        }
    });
}

// ==================================================
// KNOWLEDGE BASE AND RAG INGESTION
// ==================================================

const ingestForm = $("ingestForm");

if (ingestForm) {
    ingestForm.addEventListener("submit", async event => {
        event.preventDefault();

        const text = $("documentInput")?.value.trim();
        const button = $("ingestButton");

        if (!text) {
            toast("Please enter document content.");
            return;
        }

        if (!button) return;

        button.disabled = true;
        button.textContent = "Adding document...";
        setHTML("ingestResult", "");

        try {
            const data = await api("/api/ai/ingest-text", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    text,
                    source:
                        $("sourceInput")?.value.trim() ||
                        "financial-reference",
                    vendor:
                        $("vendorInput")?.value.trim() || null
                })
            });

            setHTML("ingestResult", `
                <div class="success-text">
                    ${escapeHTML(data.message || "Document added.")}
                    <p>
                        Chunks added:
                        ${escapeHTML(data.chunks_added ?? "Not reported")}
                    </p>
                </div>
            `);

            $("documentInput").value = "";
            toast("Knowledge base updated.");

        } catch (error) {
            setHTML("ingestResult", `
                <div class="error-text">
                    ${escapeHTML(error.message)}
                </div>
            `);

            console.error("Knowledge ingestion:", error);

        } finally {
            button.disabled = false;
            button.textContent = "Add to knowledge base";
        }
    });
}

// ==================================================
// INITIALIZE APPLICATION
// ==================================================

function initializeApp() {
    showView("overview");
    checkStatus();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeApp);
} else {
    initializeApp();
}
