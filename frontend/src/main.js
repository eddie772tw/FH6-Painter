// @ts-check

const wsUrl = "ws://localhost:8765";
let ws = null;
let currentShapes = [];

// UI Elements
const btnGenerate = document.getElementById("btn-generate");
const btnInject = document.getElementById("btn-inject");
const overlay = document.getElementById("connection-overlay");
const canvas = /** @type {HTMLCanvasElement} */ (document.getElementById("preview-canvas"));
const ctx = canvas.getContext("2d");

const valLayers = document.getElementById("val-layers");
const valSpeed = document.getElementById("val-speed");
const valEta = document.getElementById("val-eta");
const engineSelect = document.getElementById("engine-select");
const layersInput = document.getElementById("layers-input");
const fileInput = document.getElementById("file-input");
const filePathDisplay = document.getElementById("file-path-display");
const uploadZone = document.getElementById("upload-zone");

let selectedFilePath = "";

// Initialize WebSocket
function connectWebSocket() {
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log("Connected to Python backend");
    overlay.classList.add("hidden");
    btnGenerate.classList.remove("disabled");
    ws.send(JSON.stringify({ action: "get_engines" }));
  };

  ws.onclose = () => {
    console.log("Disconnected from Python backend. Reconnecting...");
    overlay.classList.remove("hidden");
    overlay.innerHTML = "<h3>CONNECTION LOST. RECONNECTING...</h3>";
    btnGenerate.classList.add("disabled");
    btnInject.classList.add("disabled");
    setTimeout(connectWebSocket, 2000);
  };

  ws.onerror = (err) => {
    console.error("WebSocket error", err);
  };

  ws.onmessage = (event) => {
    // If it's a string, parse as JSON. If Blob/ArrayBuffer, handle binary.
    if (typeof event.data === "string") {
      const msg = JSON.parse(event.data);
      handleBackendMessage(msg);
    } else {
      handleBinaryStream(event.data);
    }
  };
}

function handleBackendMessage(msg) {
  switch (msg.action) {
    case "engines_list":
      engineSelect.innerHTML = "";
      msg.data.forEach(engine => {
        const option = document.createElement("option");
        option.value = engine.code;
        option.textContent = engine.name;
        if (!engine.available) option.disabled = true;
        engineSelect.appendChild(option);
      });
      break;

    case "generation_status":
      if (msg.status === "started") {
        btnGenerate.textContent = "STOP GENERATION";
        btnGenerate.style.background = "#D32F2F";
        btnGenerate.style.boxShadow = "0 0 15px rgba(211, 47, 47, 0.4)";
        btnInject.classList.add("disabled");
      } else {
        btnGenerate.textContent = "START GENERATION";
        btnGenerate.style.background = "var(--primary-color)";
        btnGenerate.style.boxShadow = "0 0 15px var(--glow-primary)";
        btnInject.classList.remove("disabled");
      }
      break;

    case "metrics":
      valLayers.textContent = `${msg.curr} / ${msg.total}`;
      valSpeed.textContent = `${msg.speed.toFixed(1)} L/s`;
      valEta.textContent = `${msg.eta.toFixed(0)}s`;
      
      if (msg.shapes) {
        currentShapes = msg.shapes;
        renderShapes();
      }
      break;

    case "injection_status":
      if (msg.status === "started") {
        btnInject.textContent = "INJECTING...";
        btnInject.classList.add("disabled");
      } else {
        btnInject.textContent = "INJECT TO GAME";
        btnInject.classList.remove("disabled");
        if (msg.status === "failed") {
          alert("Injection failed: " + msg.error);
        } else {
          alert("Injection completed successfully!");
        }
      }
      break;
  }
}

async function handleBinaryStream(blob) {
  // Useful for raw pixel buffers (Error map, original image preview)
  const arrayBuffer = await blob.arrayBuffer();
  // Decode logic... 
}

// Vector Render Engine
function renderShapes() {
  if (!ctx) return;
  
  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  // Base background (Optional: can be driven by a header shape)
  ctx.fillStyle = "#808080";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Render each shape
  currentShapes.forEach(shape => {
    if (shape.type === 32 || shape.type === 16) {
      const [x, y, rx, ry, angleDeg] = shape.data;
      const [r, g, b, a] = shape.color;
      
      ctx.beginPath();
      const angleRad = angleDeg * (Math.PI / 180);
      ctx.ellipse(x, y, rx, ry, angleRad, 0, 2 * Math.PI);
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${a / 255.0})`;
      ctx.fill();
    }
  });
}

// UI Event Listeners
btnGenerate.addEventListener("click", () => {
  if (btnGenerate.classList.contains("disabled")) return;
  
  if (btnGenerate.textContent === "STOP GENERATION") {
    ws.send(JSON.stringify({ action: "stop_generation" }));
  } else {
    ws.send(JSON.stringify({
      action: "start_generation",
      config: {
        img_path: selectedFilePath,
        layers: parseInt(layersInput.value),
        engine_code: engineSelect.value
      }
    }));
  }
});

btnInject.addEventListener("click", () => {
  if (btnInject.classList.contains("disabled")) return;
  ws.send(JSON.stringify({
    action: "inject_geometry",
    config: {
      json_path: selectedFilePath,
      layers: parseInt(layersInput.value)
    }
  }));
});

// Drag and Drop (Native HTML5 fallback, since we might not run inside Tauri yet)
uploadZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadZone.style.borderColor = "var(--primary-color)";
});

uploadZone.addEventListener("dragleave", () => {
  uploadZone.style.borderColor = "var(--glass-border)";
});

uploadZone.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadZone.style.borderColor = "var(--glass-border)";
  if (e.dataTransfer.files.length > 0) {
    const file = e.dataTransfer.files[0];
    handleFileSelect(file);
  }
});

uploadZone.addEventListener("click", () => {
  fileInput.click();
});

fileInput.addEventListener("change", (e) => {
  if (e.target.files.length > 0) {
    handleFileSelect(e.target.files[0]);
  }
});

function handleFileSelect(file) {
  // In a real Tauri app, we'd use @tauri-apps/plugin-dialog to get the absolute path
  // For standard web, we can only get the file name or a blob URL
  selectedFilePath = file.name; // Placeholder for absolute path
  filePathDisplay.textContent = `Selected: ${file.name}`;
  
  // If it's an image, draw it temporarily to the canvas
  if (file.type.startsWith("image/")) {
    const img = new Image();
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);
    };
    img.src = URL.createObjectURL(file);
  }
}

// Start
connectWebSocket();
