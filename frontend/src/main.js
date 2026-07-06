// @ts-check
/* global __GIT_BRANCH__, __GIT_COMMIT__ */

// Dynamic Title based on Git Info
if (typeof __GIT_BRANCH__ !== 'undefined' && typeof __GIT_COMMIT__ !== 'undefined') {
  document.title = `FH6-Painter - ${__GIT_BRANCH__} (${__GIT_COMMIT__})`;

  // Also add it visually to the custom Tauri titlebar if present
  document.addEventListener('DOMContentLoaded', () => {
    const logoArea = document.querySelector('.logo-area');
    if (logoArea) {
      const gitBadge = document.createElement('span');
      gitBadge.className = 'badge git-badge';
      gitBadge.style.opacity = '0.7';
      gitBadge.style.fontSize = '0.7em';
      gitBadge.style.marginLeft = '8px';
      gitBadge.style.backgroundColor = 'var(--bg-glass)';
      gitBadge.style.border = '1px solid var(--glass-border)';
      gitBadge.textContent = `${__GIT_BRANCH__} (${__GIT_COMMIT__})`;
      logoArea.appendChild(gitBadge);
    }
  });
}

const wsUrl = "ws://localhost:8765";
let ws = null;
let currentShapes = [];
let currentCheckpoints = [];
let totalLayersLimit = 1000;
let isGenerating = false;
let currentLangDict = {};

// 全域狀態變數，用於支援多語言即時更新
let currentFileStatus = { type: null, path: "" }; // { type: "json" | "image" | "selected", path: "..." }
let currentRewindHint = { type: null, layer: 0 }; // { type: "loading" | "aligning" | "success" | "failed" | "scrubbing" | "rewinding", layer: 0 }
let currentProfileSettings = null; // 存放當前 profile 的 settings 物件

// ROI Selection State
let roiEnabled = false;
let roiSelection = null; // { x1, y1, x2, y2 } in original image pixels
let isRoiDragging = false;
let isRoiMoving = false;
let roiDragStart = null; // { x, y } in client space
let roiMoveStart = null; // { x, y } in image pixels

// UI Elements
const btnGenerate = document.getElementById("btn-generate");
const btnInject = document.getElementById("btn-inject");
const btnBrowseNative = document.getElementById("btn-browse-native");
const btnTextVinyl = document.getElementById("btn-text-vinyl");
const overlay = document.getElementById("connection-overlay");
const canvas = /** @type {HTMLCanvasElement} */ (document.getElementById("preview-canvas"));
const previewDisabledOverlay = document.getElementById("preview-disabled-overlay");
const ctx = canvas.getContext("2d");

// Header Buttons
const btnTogglePreview = document.getElementById("btn-toggle-preview");
const btnMarket = document.getElementById("btn-market");
const btnOutput = document.getElementById("btn-output");
const btnBenchmark = document.getElementById("btn-benchmark");
const btnShowLogs = document.getElementById("btn-show-logs");
const langSelect = document.getElementById("lang-select");
if (langSelect) {
  langSelect.addEventListener("change", (e) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: "get_lang", lang: e.target.value }));
    }
  });
}

// Modals
const modalTextVinyl = document.getElementById("modal-text-vinyl");
const modalLogs = document.getElementById("modal-logs");
const modalBenchmark = document.getElementById("modal-benchmark");
const closeBtns = document.querySelectorAll(".btn-close-modal");

// Modal Inputs
const textVinylInput = /** @type {HTMLInputElement} */ (document.getElementById("text-vinyl-input"));
const textVinylSize = /** @type {HTMLInputElement} */ (document.getElementById("text-vinyl-size"));
const btnGenerateText = document.getElementById("btn-generate-text");
const consoleLogs = document.getElementById("console-logs");
const btnClearLogs = document.getElementById("btn-clear-logs");
const btnStartBenchmark = document.getElementById("btn-start-benchmark");
const benchmarkStatus = document.getElementById("benchmark-status");
const consoleBenchmark = document.getElementById("console-benchmark");

let isPreviewEnabled = true;

const valLayers = document.getElementById("val-layers");
const valSpeed = document.getElementById("val-speed");
const valEta = document.getElementById("val-eta");
const engineSelect = /** @type {HTMLSelectElement} */ (document.getElementById("engine-select"));
const layersInput = /** @type {HTMLInputElement} */ (document.getElementById("layers-input"));
const filePathDisplay = document.getElementById("file-path-display");

// New UI Elements
const profileSelect = /** @type {HTMLSelectElement} */ (document.getElementById("profile-select"));
const profileDesc = document.getElementById("profile-desc");
const taichiSettingsPanel = document.getElementById("taichi-settings-panel");
const taichiArchSelect = /** @type {HTMLSelectElement} */ (document.getElementById("taichi-arch-select"));
const chkHybrid = /** @type {HTMLInputElement} */ (document.getElementById("chk-hybrid"));
const taichiDeviceSelect = /** @type {HTMLSelectElement} */ (document.getElementById("taichi-device-select"));
const chkOverride = /** @type {HTMLInputElement} */ (document.getElementById("chk-override"));
const overrideSettingsPanel = document.getElementById("override-settings-panel");
const candidatesInput = /** @type {HTMLInputElement} */ (document.getElementById("candidates-input"));
const stepsInput = /** @type {HTMLInputElement} */ (document.getElementById("steps-input"));

// Optimizations UI
const optPyramid = /** @type {HTMLInputElement} */ (document.getElementById("opt-pyramid"));
const optFreeze = /** @type {HTMLInputElement} */ (document.getElementById("opt-freeze"));
const optImportance = /** @type {HTMLInputElement} */ (document.getElementById("opt-importance"));
const optWeight = /** @type {HTMLInputElement} */ (document.getElementById("opt-weight"));
const optAnnealing = /** @type {HTMLInputElement} */ (document.getElementById("opt-annealing"));
const optDecay = /** @type {HTMLInputElement} */ (document.getElementById("opt-decay"));
const chkEarlyConv = /** @type {HTMLInputElement} */ (document.getElementById("chk-early-conv"));
const optimizationsCard = document.getElementById("optimizations-card");

// ROI UI
const roiEnabledCheckbox = /** @type {HTMLInputElement} */ (document.getElementById("roi-enabled"));
const roiControls = document.getElementById("roi-controls");
const roiBoundsDisplay = document.getElementById("roi-bounds-display");
const rewindLayerInput = /** @type {HTMLInputElement} */ (document.getElementById("rewind-layer-input"));
const btnRewind = document.getElementById("btn-rewind");
const rewindHint = document.getElementById("rewind-hint");

// Timeline UI
const timelineSlider = /** @type {HTMLInputElement} */ (document.getElementById("timeline-slider"));
const checkpointsContainer = document.getElementById("checkpoints-container");
const timelineVal = document.getElementById("timeline-val");

let selectedFilePath = "";
let isAutoResumePending = false;
let isStopRewindPending = false;
let originalImageWidth = 600;
let originalImageHeight = 600;

function updateButtonStates() {
  const wsOpen = ws && ws.readyState === WebSocket.OPEN;
  
  if (wsOpen && selectedFilePath) {
    btnGenerate.classList.remove("disabled");
  } else {
    if (isGenerating && wsOpen) {
      btnGenerate.classList.remove("disabled");
    } else {
      btnGenerate.classList.add("disabled");
    }
  }
  
  if (wsOpen && selectedFilePath && !isGenerating) {
    btnInject.classList.remove("disabled");
  } else {
    btnInject.classList.add("disabled");
  }
}

// Initialize WebSocket
function connectWebSocket() {
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log("Connected to Python backend");
    overlay.classList.add("hidden");
    updateButtonStates();
    
    // Fetch initial configuration listings
    ws.send(JSON.stringify({ action: "get_engines" }));
    ws.send(JSON.stringify({ action: "get_profiles" }));
    ws.send(JSON.stringify({ action: "get_gpus" }));
    ws.send(JSON.stringify({ action: "get_lang", lang: langSelect ? langSelect.value : "en-us" }));
  };

  ws.onclose = () => {
    console.log("Disconnected from Python backend. Reconnecting...");
    overlay.classList.remove("hidden");
    overlay.innerHTML = `<h3>${currentLangDict["label.connection_lost"] || "CONNECTION LOST. RECONNECTING..."}</h3>`;
    updateButtonStates();
    setTimeout(connectWebSocket, 2000);
  };

  ws.onerror = (err) => {
    console.error("WebSocket error", err);
  };

  ws.onmessage = (event) => {
    if (typeof event.data === "string") {
      const msg = JSON.parse(event.data);
      handleBackendMessage(msg);
    }
  };
}

function updateCanvasSize(newWidth, newHeight) {
  if (newWidth && newHeight) {
    if (roiSelection && originalImageWidth && originalImageHeight) {
      if (originalImageWidth !== newWidth || originalImageHeight !== newHeight) {
        const scaleX = newWidth / originalImageWidth;
        const scaleY = newHeight / originalImageHeight;
        roiSelection.x1 *= scaleX;
        roiSelection.y1 *= scaleY;
        roiSelection.x2 *= scaleX;
        roiSelection.y2 *= scaleY;
      }
    }
    canvas.width = newWidth;
    canvas.height = newHeight;
    originalImageWidth = newWidth;
    originalImageHeight = newHeight;
  }
}

function translateUI() {
  if (!currentLangDict) return;

  // 1. Static i18n attributes
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (currentLangDict[key]) {
      if (el.children.length === 0) {
        el.textContent = currentLangDict[key];
      } else {
        Array.from(el.childNodes).forEach(node => {
          if (node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0) {
            node.textContent = currentLangDict[key];
          }
        });
      }
    }
  });

  document.querySelectorAll("[data-i18n-title]").forEach(el => {
    const key = el.getAttribute("data-i18n-title");
    if (currentLangDict[key]) {
      el.setAttribute("title", currentLangDict[key]);
    }
  });

  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (currentLangDict[key]) {
      el.setAttribute("placeholder", currentLangDict[key]);
    }
  });

  // 2. Button states and dynamic controls
  if (btnTogglePreview) {
    if (isPreviewEnabled) {
      btnTogglePreview.textContent = currentLangDict["header.disable_preview"] || "Disable Preview";
    } else {
      btnTogglePreview.textContent = currentLangDict["header.enable_preview"] || "Enable Preview";
    }
  }

  if (btnGenerate) {
    if (isGenerating) {
      btnGenerate.textContent = currentLangDict["action.stop_generation"] || "STOP GENERATION";
    } else {
      btnGenerate.textContent = currentLangDict["action.start_generation"] || "START GENERATION";
    }
  }
  
  if (btnInject) {
    if (btnInject.textContent.includes("INJECTING") || btnInject.textContent.includes("注入")) {
      btnInject.textContent = currentLangDict["action.injecting"] || "INJECTING...";
    } else {
      btnInject.textContent = currentLangDict["action.inject"] || "INJECT TO GAME";
    }
  }

  // 3. Engine translation
  if (engineSelect) {
    Array.from(engineSelect.options).forEach(option => {
      option.textContent = currentLangDict["engine." + option.value] || option.getAttribute("data-raw-name") || option.textContent;
    });
  }

  // 4. Profile translation
  if (profileSelect) {
    Array.from(profileSelect.options).forEach(option => {
      option.textContent = currentLangDict["profile." + option.value] || option.getAttribute("data-raw-name") || option.textContent;
    });
  }

  // 5. Profile Description translation
  if (profileDesc) {
    if (currentProfileSettings && currentProfileSettings.description) {
      profileDesc.textContent = currentLangDict["profile.desc." + currentProfileSettings.description] || currentProfileSettings.description;
    } else {
      profileDesc.textContent = currentLangDict["label.no_description"] || "No description available.";
    }
  }

  // 6. Taichi Device Default Option Translation
  if (taichiDeviceSelect) {
    Array.from(taichiDeviceSelect.options).forEach(option => {
      if (option.value === "0" && (option.textContent.includes("Default Device") || option.textContent.includes("預設裝置") || option.textContent.includes("デフォルトデバイス"))) {
        option.textContent = currentLangDict["label.default_device"] || "(0) Default Device";
      }
    });
  }

  // 7. ROI display translation
  if (roiBoundsDisplay) {
    if (!roiSelection) {
      roiBoundsDisplay.textContent = currentLangDict["label.none"] || "None";
    } else {
      const xMin = Math.min(roiSelection.x1, roiSelection.x2);
      const xMax = Math.max(roiSelection.x1, roiSelection.x2);
      const yMin = Math.min(roiSelection.y1, roiSelection.y2);
      const yMax = Math.max(roiSelection.y1, roiSelection.y2);
      roiBoundsDisplay.textContent = (currentLangDict["label.roi_bounds_format"] || "({xMin}, {yMin}) to ({xMax}, {yMax})")
        .replace("{xMin}", xMin.toString())
        .replace("{yMin}", yMin.toString())
        .replace("{xMax}", xMax.toString())
        .replace("{yMax}", yMax.toString());
    }
  }

  // 8. Benchmark Status translation
  if (benchmarkStatus) {
    const rawStatus = benchmarkStatus.getAttribute("data-raw-status") || "READY";
    const statusKey = "status." + rawStatus.toLowerCase().replace("...", "");
    benchmarkStatus.textContent = currentLangDict[statusKey] || rawStatus;
  }

  // 9. File path status translation
  if (filePathDisplay) {
    if (currentFileStatus.type) {
      const type = currentFileStatus.type;
      const path = currentFileStatus.path;
      if (type === "json") {
        filePathDisplay.textContent = (currentLangDict["hint.loaded_json"] || "Loaded JSON: {path}").replace("{path}", path);
      } else if (type === "image") {
        filePathDisplay.textContent = (currentLangDict["hint.loaded_image"] || "Loaded Image: {path}").replace("{path}", path);
      } else if (type === "selected") {
        filePathDisplay.textContent = (currentLangDict["hint.selected_file"] || "Selected: {path}").replace("{path}", path);
      }
    }
  }

  // 10. Rewind hint translation
  if (rewindHint) {
    if (currentRewindHint.type) {
      const { type, layer } = currentRewindHint;
      if (type === "loading") {
        rewindHint.textContent = (currentLangDict["hint.loading_resume_state"] || "Loading resume state at layer {layer}...").replace("{layer}", layer.toString());
        rewindHint.style.color = "var(--secondary-color)";
      } else if (type === "aligning") {
        rewindHint.textContent = (currentLangDict["hint.aligning_resume_state"] || "Aligning resume state at layer {layer}...").replace("{layer}", layer.toString());
        rewindHint.style.color = "var(--secondary-color)";
      } else if (type === "success") {
        rewindHint.textContent = (currentLangDict["hint.rewind_success"] || "Successfully rewound to layer {layer}").replace("{layer}", layer.toString());
        rewindHint.style.color = "var(--primary-color)";
      } else if (type === "failed") {
        rewindHint.textContent = currentLangDict["hint.rewind_failed"] || "Rewind failed";
        rewindHint.style.color = "#D32F2F";
      } else if (type === "scrubbing") {
        rewindHint.textContent = (currentLangDict["hint.scrubbing_layer"] || "Scrubbing to layer {layer}...").replace("{layer}", layer.toString());
        rewindHint.style.color = "var(--secondary-color)";
      } else if (type === "rewinding") {
        rewindHint.textContent = (currentLangDict["hint.rewinding_layer"] || "Rewinding to layer {layer}...").replace("{layer}", layer.toString());
        rewindHint.style.color = "var(--secondary-color)";
      }
    }
  }

  // 11. Checkpoint track marker titles (re-render checkpoints to update tooltip titles)
  renderCheckpointsTrack();
}

function handleBackendMessage(msg) {
  switch (msg.action) {
    case "lang_data":
      currentLangDict = msg.data;
      translateUI();
      break;

    case "engines_list":
      engineSelect.innerHTML = "";
      msg.data.forEach(engine => {
        const option = document.createElement("option");
        option.value = engine.code;
        option.setAttribute("data-raw-name", engine.name);
        option.textContent = currentLangDict["engine." + engine.code] || engine.name;
        if (!engine.available) option.disabled = true;
        engineSelect.appendChild(option);
      });
      break;

    case "profiles_list":
      profileSelect.innerHTML = "";
      msg.data.forEach(p => {
        const option = document.createElement("option");
        option.value = p.name;
        option.setAttribute("data-raw-name", p.name);
        option.textContent = currentLangDict["profile." + p.name] || p.name;
        profileSelect.appendChild(option);
      });
      // Select first profile and load settings
      if (msg.data.length > 0) {
        profileSelect.value = msg.data[0].name;
        fetchProfileSettings(msg.data[0].name);
      }
      break;

    case "gpus_list":
      taichiDeviceSelect.innerHTML = "";
      if (msg.data && msg.data.length > 0) {
        msg.data.forEach((gpu, idx) => {
          const option = document.createElement("option");
          option.value = idx.toString();
          option.textContent = `(${idx}) ${gpu}`;
          taichiDeviceSelect.appendChild(option);
        });
      } else {
        const option = document.createElement("option");
        option.value = "0";
        option.textContent = currentLangDict["label.default_device"] || "(0) Default Device";
        taichiDeviceSelect.appendChild(option);
      }
      break;

    case "profile_settings":
      if (msg.settings) {
        currentProfileSettings = msg.settings;
        layersInput.value = msg.settings.stopAt;
        candidatesInput.value = msg.settings.randomSamples;
        stepsInput.value = msg.settings.mutatedSamples;
        translateUI();
      }
      break;

    case "checkpoints_list":
      currentCheckpoints = msg.checkpoints || [];
      renderCheckpointsTrack();
      
      // Auto-resume logic: if checkpoints exist and we are idle, prep the latest checkpoint
      if (isAutoResumePending && currentCheckpoints.length > 0 && !isGenerating) {
        isAutoResumePending = false;
        let maxLayer = 0;
        let maxPath = "";
        currentCheckpoints.forEach(cp => {
          if (cp.layer > maxLayer) {
            maxLayer = cp.layer;
            maxPath = cp.path;
          }
        });
        
        if (maxLayer > 0) {
          rewindLayerInput.value = maxLayer.toString();
          
          // If the selected path is not already a checkpoint/resume JSON,
          // automatically trigger rewind to it so the next generation resumes from this state.
          if (!selectedFilePath.toLowerCase().endsWith("_temp_resume.json") && 
              !selectedFilePath.toLowerCase().endsWith(".json")) {
            console.log(`Auto-resuming from the latest checkpoint at layer ${maxLayer}`);
            currentRewindHint = { type: "loading", layer: maxLayer };
            translateUI();
            ws.send(JSON.stringify({
              action: "rewind_checkpoint",
              path: maxPath,
              layer: maxLayer
            }));
          }
        }
      } else {
        isAutoResumePending = false;
      }

      // Auto-sync rewind after manual stop to ensure frontend and backend session state variables are fully synchronized
      if (isStopRewindPending) {
        isStopRewindPending = false;
        const targetLayer = parseInt(rewindLayerInput.value);
        if (!isNaN(targetLayer) && targetLayer >= 1) {
          let bestCp = null;
          for (let i = 0; i < currentCheckpoints.length; i++) {
            const cp = currentCheckpoints[i];
            if (cp.layer >= targetLayer) {
              bestCp = cp;
              break;
            }
          }
          if (!bestCp && currentCheckpoints.length > 0) {
            bestCp = currentCheckpoints[currentCheckpoints.length - 1];
          }
          
          if (bestCp) {
            console.log(`Auto-rewinding after stop to layer ${targetLayer} using checkpoint ${bestCp.path}`);
            currentRewindHint = { type: "aligning", layer: targetLayer };
            translateUI();
            ws.send(JSON.stringify({
              action: "rewind_checkpoint",
              path: bestCp.path,
              layer: targetLayer
            }));
          } else {
            canvas.width = originalImageWidth;
            canvas.height = originalImageHeight;
            renderShapes();
          }
        } else {
          canvas.width = originalImageWidth;
          canvas.height = originalImageHeight;
          renderShapes();
        }
      }
      break;

    case "text_vinyl_success":
      if (msg.path) {
        modalTextVinyl.classList.add("hidden");
        ws.send(JSON.stringify({ action: "load_json_file", path: msg.path }));
      }
      break;

    case "log":
      if (msg.text) {
        consoleLogs.textContent += msg.text;
        consoleLogs.scrollTop = consoleLogs.scrollHeight;
      }
      break;

    case "benchmark_log":
      if (msg.text) {
        consoleBenchmark.textContent += msg.text;
        consoleBenchmark.scrollTop = consoleBenchmark.scrollHeight;
      }
      break;

    case "benchmark_done":
      benchmarkStatus.setAttribute("data-raw-status", msg.status || "DONE");
      translateUI();
      if (msg.status === "PASSED") {
        benchmarkStatus.style.color = "var(--primary-color)";
      } else {
        benchmarkStatus.style.color = "#D32F2F";
      }
      btnStartBenchmark.disabled = false;
      break;

    case "rewind_success":
      selectedFilePath = msg.temp_path;
      valLayers.textContent = `${msg.layer} / ${layersInput.value}`;
      timelineSlider.value = msg.layer;
      timelineVal.textContent = `${Math.round((msg.layer / parseInt(layersInput.value)) * 100)}%`;
      rewindLayerInput.value = msg.layer.toString();
      
      if (msg.width && msg.height) {
        updateCanvasSize(msg.width, msg.height);
      }
      if (msg.preview_base64) {
        canvas.style.backgroundImage = `url(data:image/jpeg;base64,${msg.preview_base64})`;
        canvas.style.backgroundSize = "contain";
        canvas.style.backgroundPosition = "center";
        canvas.style.backgroundRepeat = "no-repeat";
      }
      if (msg.shapes) {
        currentShapes = msg.shapes;
        renderShapes();
      }
      currentRewindHint = { type: "success", layer: msg.layer };
      translateUI();
      updateButtonStates();
      break;

    case "rewind_failed":
      alert((currentLangDict["alert.rewind_failed"] || "Rewind failed: ") + msg.error);
      currentRewindHint = { type: "failed", layer: 0 };
      translateUI();
      break;

    case "load_json_success":
      selectedFilePath = msg.path;
      currentFileStatus = { type: "json", path: msg.path };
      translateUI();
      if (msg.width && msg.height) {
        updateCanvasSize(msg.width, msg.height);
      }
      if (msg.preview_base64) {
        canvas.style.backgroundImage = `url(data:image/jpeg;base64,${msg.preview_base64})`;
        canvas.style.backgroundSize = "contain";
        canvas.style.backgroundPosition = "center";
        canvas.style.backgroundRepeat = "no-repeat";
      }
      if (msg.shapes) {
        currentShapes = msg.shapes;
        const layerCount = Math.max(0, currentShapes.length - 1);
        valLayers.textContent = `${layerCount} / ${layersInput.value}`;
        timelineSlider.disabled = false;
        timelineSlider.max = layersInput.value;
        timelineSlider.value = layerCount;
        timelineVal.textContent = `${Math.round((layerCount / parseInt(layersInput.value)) * 100)}%`;
        renderShapes();
      }
      updateButtonStates();
      // Scan checkpoints for new project context
      ws.send(JSON.stringify({ action: "get_checkpoints", img_path: msg.path }));
      break;

    case "load_json_failed":
      alert((currentLangDict["alert.load_json_failed"] || "Failed to load JSON file: ") + msg.error);
      break;

    case "load_image_success":
      selectedFilePath = msg.path;
      currentFileStatus = { type: "image", path: msg.path };
      translateUI();
      if (msg.width && msg.height) {
        updateCanvasSize(msg.width, msg.height);
      }
      if (msg.preview_base64) {
        canvas.style.backgroundImage = `url(data:image/jpeg;base64,${msg.preview_base64})`;
        canvas.style.backgroundSize = "contain";
        canvas.style.backgroundPosition = "center";
        canvas.style.backgroundRepeat = "no-repeat";
      }
      currentShapes = [];
      renderShapes();
      updateButtonStates();
      isAutoResumePending = true;
      ws.send(JSON.stringify({ action: "get_checkpoints", img_path: msg.path }));
      break;

    case "load_image_failed":
      alert((currentLangDict["alert.load_image_failed"] || "Failed to load image file: ") + msg.error);
      break;

    case "file_selected":
      if (msg.path) {
        selectedFilePath = msg.path;
        currentFileStatus = { type: "selected", path: msg.path };
        translateUI();
        
        if (msg.path.toLowerCase().endsWith(".json")) {
          // Send request to load the JSON geometry file
          ws.send(JSON.stringify({ action: "load_json_file", path: msg.path }));
        } else {
          // Send request to load the image file details and preview
          ws.send(JSON.stringify({ action: "load_image_file", path: msg.path }));
        }
      }
      break;

    case "generation_status":
      if (msg.status === "started") {
        isGenerating = true;
        btnGenerate.textContent = currentLangDict["action.stop_generation"] || "STOP GENERATION";
        btnGenerate.style.background = "#D32F2F";
        btnGenerate.style.boxShadow = "0 0 15px rgba(211, 47, 47, 0.4)";
        timelineSlider.disabled = true;
        
        canvas.style.backgroundImage = "none";
        currentShapes = [];
        if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
      } else {
        isGenerating = false;
        btnGenerate.textContent = currentLangDict["action.start_generation"] || "START GENERATION";
        btnGenerate.style.background = "var(--primary-color)";
        btnGenerate.style.boxShadow = "0 0 15px var(--glow-primary)";
        timelineSlider.disabled = false;
        
        // Default rewindLayerInput value to actual generated layers count if stopped, or max layers on success
        if (msg.status === "stopped") {
          rewindLayerInput.value = timelineSlider.value;
          isStopRewindPending = true;
        } else {
          rewindLayerInput.value = layersInput.value;
          isStopRewindPending = true;
        }
        
        // Refresh checkpoints when generation completes
        ws.send(JSON.stringify({ action: "get_checkpoints", img_path: selectedFilePath }));
      }
      updateButtonStates();
      break;

    case "metrics":
      valLayers.textContent = `${msg.curr} / ${msg.total}`;
      valSpeed.textContent = `${msg.speed.toFixed(1)} L/s`;
      valEta.textContent = `${msg.eta.toFixed(0)}s`;
      
      // Update timeline progress
      timelineSlider.max = msg.total.toString();
      timelineSlider.value = msg.curr.toString();
      timelineVal.textContent = `${Math.round((msg.curr / msg.total) * 100)}%`;
      
      if (msg.width && msg.height) {
        updateCanvasSize(msg.width, msg.height);
      }
      
      if (msg.shapes) {
        if (msg.shapes.length > 0) {
          currentShapes = msg.shapes;
          renderShapes();
        } else {
          currentShapes = [];
          if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
      }
      break;

    case "pixel_preview":
      if (msg.image_base64) {
        canvas.style.backgroundImage = `url(data:image/jpeg;base64,${msg.image_base64})`;
        canvas.style.backgroundSize = "contain";
        canvas.style.backgroundPosition = "center";
        canvas.style.backgroundRepeat = "no-repeat";
      }
      break;

    case "injection_status":
      if (msg.status === "started") {
        btnInject.textContent = currentLangDict["action.injecting"] || "INJECTING...";
        btnInject.classList.add("disabled");
      } else {
        btnInject.textContent = currentLangDict["action.inject"] || "INJECT TO GAME";
        btnInject.classList.remove("disabled");
        if (msg.status === "failed") {
          alert((currentLangDict["alert.inject_failed"] || "Injection failed: ") + msg.error);
        } else {
          alert(currentLangDict["alert.inject_success"] || "Injection completed successfully!");
        }
      }
      break;

    case "clear_roi":
      roiSelection = null;
      roiBoundsDisplay.textContent = "None";
      if (ctx) {
        renderShapes();
      }
      console.log("[Region Painting] ROI cleared due to early convergence restart.");
      break;
  }
}

function fetchProfileSettings(name) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: "get_profile_settings", profile_name: name }));
  }
}

function renderCheckpointsTrack() {
  checkpointsContainer.innerHTML = "";
  const totalVal = parseInt(layersInput.value) || 1000;
  
  currentCheckpoints.forEach(cp => {
    const pct = (cp.layer / totalVal) * 100;
    if (pct >= 0 && pct <= 100) {
      const marker = document.createElement("div");
      marker.className = "checkpoint-marker";
      marker.style.left = `${pct}%`;
      marker.title = `Checkpoint at Layer ${cp.layer}`;
      checkpointsContainer.appendChild(marker);
    }
  });
}

// Vector Render Engine
function renderShapes() {
  if (!ctx) return;
  
  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  // Base background (gray placeholder if no background image)
  if (!canvas.style.backgroundImage || canvas.style.backgroundImage === "none") {
    ctx.fillStyle = "#808080";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  } else {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

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
  
  // Draw ROI region boundary overlay if enabled
  if (roiEnabled && roiSelection) {
    ctx.save();
    ctx.strokeStyle = "#FF3333";
    ctx.lineWidth = Math.max(1.5, canvas.width / 400);
    ctx.setLineDash([6, 4]);
    
    const { x1, y1, x2, y2 } = roiSelection;
    const shapeMode = /** @type {HTMLInputElement} */ (document.querySelector('input[name="roi-shape"]:checked')).value;
    
    if (shapeMode === "ellipse") {
      const rx = Math.abs(x2 - x1) / 2;
      const ry = Math.abs(y2 - y1) / 2;
      const cx = (x1 + x2) / 2;
      const cy = (y1 + y2) / 2;
      ctx.beginPath();
      ctx.ellipse(cx, cy, rx, ry, 0, 0, 2 * Math.PI);
      ctx.stroke();
    } else {
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
    }
    ctx.restore();
  }
}

// ROI Mouse Helpers
// Translate client mouse coordinate to canvas original image pixel coordinates
function getCanvasImageCoords(e) {
  const rect = canvas.getBoundingClientRect();
  const clientX = e.clientX - rect.left;
  const clientY = e.clientY - rect.top;
  
  // Calculate letterboxing offsets due to object-fit: contain
  const intrinsicRatio = canvas.width / canvas.height;
  const rectRatio = rect.width / rect.height;
  
  let renderWidth = rect.width;
  let renderHeight = rect.height;
  let offsetX = 0;
  let offsetY = 0;
  
  if (intrinsicRatio > rectRatio) {
    // Width is constrained, height is letterboxed
    renderHeight = rect.width / intrinsicRatio;
    offsetY = (rect.height - renderHeight) / 2;
  } else {
    // Height is constrained, width is letterboxed
    renderWidth = rect.height * intrinsicRatio;
    offsetX = (rect.width - renderWidth) / 2;
  }
  
  // Coordinates relative to the actual rendered image
  const imageX = clientX - offsetX;
  const imageY = clientY - offsetY;
  
  const scaleX = canvas.width / renderWidth;
  const scaleY = canvas.height / renderHeight;
  
  return {
    x: Math.max(0, Math.min(canvas.width - 1, Math.round(imageX * scaleX))),
    y: Math.max(0, Math.min(canvas.height - 1, Math.round(imageY * scaleY)))
  };
}

function isPointInRoi(x, y) {
  if (!roiSelection) return false;
  const minX = Math.min(roiSelection.x1, roiSelection.x2);
  const maxX = Math.max(roiSelection.x1, roiSelection.x2);
  const minY = Math.min(roiSelection.y1, roiSelection.y2);
  const maxY = Math.max(roiSelection.y1, roiSelection.y2);
  
  return x >= minX && x <= maxX && y >= minY && y <= maxY;
}

// UI Event Listeners
btnGenerate.addEventListener("click", () => {
  if (btnGenerate.classList.contains("disabled")) return;
  
  if (isGenerating) {
    ws.send(JSON.stringify({ action: "stop_generation" }));
  } else {
    // Collect all dynamic options
    const opt_settings = {
      image_pyramid: { enabled: optPyramid.checked },
      importance_sampling: { enabled: optImportance.checked },
      simulated_annealing: { enabled: optAnnealing.checked },
      dynamic_freeze: { enabled: optFreeze.checked },
      error_weighting: { enabled: optWeight.checked },
      decaying_shape: { enabled: optDecay.checked }
    };
    
    const startConfig = {
      img_path: selectedFilePath,
      profile_name: profileSelect.value,
      layers: parseInt(layersInput.value),
      engine_code: engineSelect.value,
      opt_settings: opt_settings,
      early_convergence: chkEarlyConv.checked,
      
      // Taichi
      taichi_arch: taichiArchSelect.value,
      use_pure_gpu: !chkHybrid.checked,
      taichi_device_id: parseInt(taichiDeviceSelect.value),
      
      // ROI
      roi: {
        enabled: roiEnabled && roiSelection !== null,
        shape: /** @type {HTMLInputElement} */ (document.querySelector('input[name="roi-shape"]:checked')).value,
        min_layers: parseInt(/** @type {HTMLInputElement} */ (document.getElementById("roi-min-layers")).value) || 500,
        x1: roiSelection ? Math.min(roiSelection.x1, roiSelection.x2) : 0,
        y1: roiSelection ? Math.min(roiSelection.y1, roiSelection.y2) : 0,
        x2: roiSelection ? Math.max(roiSelection.x1, roiSelection.x2) : 0,
        y2: roiSelection ? Math.max(roiSelection.y1, roiSelection.y2) : 0,
        canvas_w: canvas.width,
        canvas_h: canvas.height
      }
    };
    
    // Add overrides if checked
    if (chkOverride.checked) {
      startConfig.candidates_limit = parseInt(candidatesInput.value);
      startConfig.steps_limit = parseInt(stepsInput.value);
    }
    
    ws.send(JSON.stringify({
      action: "start_generation",
      config: startConfig
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

btnBrowseNative.addEventListener("click", () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: "browse_file" }));
  }
});

// Dropdowns and Panels Toggles
profileSelect.addEventListener("change", (e) => {
  const target = /** @type {HTMLSelectElement} */ (e.target);
  fetchProfileSettings(target.value);
});

engineSelect.addEventListener("change", () => {
  if (engineSelect.value === "TAICHI") {
    taichiSettingsPanel.classList.remove("hidden");
  } else {
    taichiSettingsPanel.classList.add("hidden");
  }
  
  if (engineSelect.value === "GO_OPENCL") {
    optimizationsCard.style.display = "none";
    roiEnabledCheckbox.checked = false;
    roiEnabledCheckbox.disabled = true;
    roiEnabled = false;
    roiControls.classList.add("hidden");
    roiSelection = null;
    renderShapes();
  } else {
    optimizationsCard.style.display = "";
    roiEnabledCheckbox.disabled = false;
  }
});

chkOverride.addEventListener("change", () => {
  if (chkOverride.checked) {
    overrideSettingsPanel.classList.remove("hidden");
  } else {
    overrideSettingsPanel.classList.add("hidden");
  }
});

roiEnabledCheckbox.addEventListener("change", () => {
  roiEnabled = roiEnabledCheckbox.checked;
  if (roiEnabled) {
    roiControls.classList.remove("hidden");
  } else {
    roiControls.classList.add("hidden");
    roiSelection = null;
    roiBoundsDisplay.textContent = "None";
    renderShapes();
  }
});

document.querySelectorAll('input[name="roi-shape"]').forEach(radio => {
  radio.addEventListener("change", () => {
    if (roiSelection) renderShapes();
  });
});

// Timeline Scrubbing Event
timelineSlider.addEventListener("change", () => {
  const targetLayer = parseInt(timelineSlider.value);
  if (!currentCheckpoints || currentCheckpoints.length === 0) return;
  
  rewindLayerInput.value = targetLayer.toString();
  
  // Find the checkpoint that represents the closest upper bound layer
  let bestCp = null;
  for (let i = 0; i < currentCheckpoints.length; i++) {
    const cp = currentCheckpoints[i];
    if (cp.layer >= targetLayer) {
      bestCp = cp;
      break;
    }
  }
  if (!bestCp && currentCheckpoints.length > 0) {
    bestCp = currentCheckpoints[currentCheckpoints.length - 1];
  }
  
  if (bestCp) {
    currentRewindHint = { type: "scrubbing", layer: targetLayer };
    translateUI();
    ws.send(JSON.stringify({
      action: "rewind_checkpoint",
      path: bestCp.path,
      layer: targetLayer
    }));
  }
});

btnRewind.addEventListener("click", () => {
  const targetLayer = parseInt(rewindLayerInput.value);
  if (isNaN(targetLayer) || targetLayer < 1) {
    alert(currentLangDict["alert.invalid_layer"] || "Please enter a valid layer number");
    return;
  }
  
  // Find closest checkpoint path
  let bestCp = null;
  for (let i = 0; i < currentCheckpoints.length; i++) {
    const cp = currentCheckpoints[i];
    if (cp.layer >= targetLayer) {
      bestCp = cp;
      break;
    }
  }
  if (!bestCp && currentCheckpoints.length > 0) {
    bestCp = currentCheckpoints[currentCheckpoints.length - 1];
  }
  
  if (bestCp) {
    currentRewindHint = { type: "rewinding", layer: targetLayer };
    translateUI();
    ws.send(JSON.stringify({
      action: "rewind_checkpoint",
      path: bestCp.path,
      layer: targetLayer
    }));
  } else {
    alert(currentLangDict["alert.no_checkpoints"] || "No checkpoints available to rewind");
  }
});

// Canvas Mouse Listeners for ROI Painting
canvas.addEventListener("mousedown", (e) => {
  if (!roiEnabled || isGenerating) return;
  
  const coords = getCanvasImageCoords(e);
  
  // Left Click
  if (e.button === 0) {
    // If clicking inside existing selection, start moving it
    if (roiSelection && isPointInRoi(coords.x, coords.y)) {
      isRoiMoving = true;
      roiMoveStart = {
        x: coords.x,
        y: coords.y,
        origX1: roiSelection.x1,
        origY1: roiSelection.y1,
        origX2: roiSelection.x2,
        origY2: roiSelection.y2
      };
    } else {
      // Start a brand new selection box
      isRoiDragging = true;
      roiDragStart = { x: coords.x, y: coords.y };
      roiSelection = {
        x1: coords.x,
        y1: coords.y,
        x2: coords.x,
        y2: coords.y
      };
    }
  }
});

canvas.addEventListener("mousemove", (e) => {
  if (!roiEnabled || isGenerating) return;
  
  const coords = getCanvasImageCoords(e);
  
  if (isRoiDragging && roiDragStart) {
    roiSelection.x2 = coords.x;
    roiSelection.y2 = coords.y;
    
    // Bounds string
    const xMin = Math.min(roiSelection.x1, roiSelection.x2);
    const xMax = Math.max(roiSelection.x1, roiSelection.x2);
    const yMin = Math.min(roiSelection.y1, roiSelection.y2);
    const yMax = Math.max(roiSelection.y1, roiSelection.y2);
    roiBoundsDisplay.textContent = `(${xMin}, ${yMin}) to (${xMax}, ${yMax})`;
    renderShapes();
  } else if (isRoiMoving && roiMoveStart) {
    const dx = coords.x - roiMoveStart.x;
    const dy = coords.y - roiMoveStart.y;
    
    roiSelection.x1 = roiMoveStart.origX1 + dx;
    roiSelection.y1 = roiMoveStart.origY1 + dy;
    roiSelection.x2 = roiMoveStart.origX2 + dx;
    roiSelection.y2 = roiMoveStart.origY2 + dy;
    
    // Bounds string
    const xMin = Math.min(roiSelection.x1, roiSelection.x2);
    const xMax = Math.max(roiSelection.x1, roiSelection.x2);
    const yMin = Math.min(roiSelection.y1, roiSelection.y2);
    const yMax = Math.max(roiSelection.y1, roiSelection.y2);
    roiBoundsDisplay.textContent = `(${xMin}, ${yMin}) to (${xMax}, ${yMax})`;
    renderShapes();
  }
});

canvas.addEventListener("mouseup", (e) => {
  if (!roiEnabled || isGenerating) return;
  
  if (e.button === 0) {
    isRoiDragging = false;
    isRoiMoving = false;
    
    // Validate selection size
    if (roiSelection) {
      const w = Math.abs(roiSelection.x2 - roiSelection.x1);
      const h = Math.abs(roiSelection.y2 - roiSelection.y1);
      if (w < 5 || h < 5) {
        roiSelection = null;
        roiBoundsDisplay.textContent = "None";
        renderShapes();
      }
    }
  }
});

canvas.addEventListener("contextmenu", (e) => {
  if (!roiEnabled) return;
  e.preventDefault(); // suppress native menu
  
  roiSelection = null;
  roiBoundsDisplay.textContent = "None";
  renderShapes();
});

// Modals Logic
closeBtns.forEach(btn => {
  btn.addEventListener("click", () => {
    const targetId = btn.getAttribute("data-target");
    if (targetId) document.getElementById(targetId).classList.add("hidden");
  });
});

btnTextVinyl.addEventListener("click", () => {
  modalTextVinyl.classList.remove("hidden");
  textVinylInput.focus();
});

btnGenerateText.addEventListener("click", () => {
  const text = textVinylInput.value.trim();
  const size = parseInt(textVinylSize.value) || 72;
  if (!text) return;
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      action: "generate_text_vinyl",
      text: text,
      font_size: size
    }));
    btnGenerateText.textContent = currentLangDict["action.generating"] || "Generating...";
    setTimeout(() => { btnGenerateText.textContent = currentLangDict["action.generate_json"] || "Generate JSON"; }, 1000);
  }
});

btnShowLogs.addEventListener("click", () => {
  modalLogs.classList.remove("hidden");
});

btnClearLogs.addEventListener("click", () => {
  consoleLogs.textContent = "";
});

btnBenchmark.addEventListener("click", () => {
  modalBenchmark.classList.remove("hidden");
});

btnStartBenchmark.addEventListener("click", () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    consoleBenchmark.textContent = "";
    benchmarkStatus.setAttribute("data-raw-status", "RUNNING...");
    translateUI();
    benchmarkStatus.style.color = "var(--secondary-color)";
    btnStartBenchmark.disabled = true;
    ws.send(JSON.stringify({ action: "start_benchmark" }));
  }
});

btnMarket.addEventListener("click", () => {
  // Delegate URL opening to the backend Python server for 100% reliability
  // across both Tauri native windows and standard browsers.
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: "open_url", url: "https://painter6.com" }));
  } else {
    window.open("https://painter6.com", "_blank");
  }
});

btnOutput.addEventListener("click", () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: "open_output" }));
  }
});

btnTogglePreview.addEventListener("click", () => {
  isPreviewEnabled = !isPreviewEnabled;
  if (isPreviewEnabled) {
    btnTogglePreview.textContent = currentLangDict["header.disable_preview"] || "Disable Preview";
    btnTogglePreview.classList.add("text-green");
    previewDisabledOverlay.classList.add("hidden");
  } else {
    btnTogglePreview.textContent = currentLangDict["header.enable_preview"] || "Enable Preview";
    btnTogglePreview.classList.remove("text-green");
    previewDisabledOverlay.classList.remove("hidden");
  }
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: "set_preview", enabled: isPreviewEnabled }));
  }
});


// Tauri Native File Drop Listener
if (window.__TAURI__) {
  const { listen } = window.__TAURI__.event;
  listen('tauri://file-drop', (event) => {
    const paths = event.payload;
    if (paths && paths.length > 0) {
      const path = paths[0];
      selectedFilePath = path;
      filePathDisplay.textContent = `Selected: ${path}`;
      if (path.toLowerCase().endsWith(".json")) {
        ws.send(JSON.stringify({ action: "load_json_file", path: path }));
      } else {
        ws.send(JSON.stringify({ action: "load_image_file", path: path }));
      }
    }
  });
}

// Start
connectWebSocket();
