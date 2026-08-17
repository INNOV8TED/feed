/**
 * IN-NO-V8 // Clickbait Production Hub
 * Client-Side JavaScript Engine (app.js)
 * 
 * ponytail: Designed serverless, self-contained, using native API fetches with zero dependencies.
 */

// Application State
const STATE = {
  // Active API Keys
  geminiKey: localStorage.getItem('GEMINI_API_KEY') || '',
  nanoKey: localStorage.getItem('NANO_BANANA_KEY') || '',

  // Tab State
  activeTab: 'character', // Start on Character Setup

  // Active Toggle Modes
  charMode: 'char-img', // char-img, char-txt, char-prem
  envMode: 'env-txt',   // env-txt, env-img, env-prem
  prodMode: 'prod-img',  // prod-img, prod-txt, prod-prem

  // Anchored URLs / Data
  CHARACTER_SHEET_URL: '',
  SET_SHEET_URL: '',
  PRODUCT_SHEET_URL: '',

  // Uploaded Files (Base64 data / names)
  files: {
    char: null,
    env: null,
    prodFront: null,
    prodBack: null
  },

  // Final compiled campaign timeline data
  campaignScenes: []
};

// DOM Elements
const DOM = {
  settingsToggle: document.getElementById('settings-toggle-btn'),
  settingsPanel: document.getElementById('settings-panel'),
  geminiKeyInput: document.getElementById('gemini-key-input'),
  nanoKeyInput: document.getElementById('nano-key-input'),
  saveSettingsBtn: document.getElementById('save-settings-btn'),
  
  tabBtns: document.querySelectorAll('.tab-btn'),
  tabContents: document.querySelectorAll('.tab-content'),

  // Character Setup
  charToggles: document.querySelectorAll('[data-toggle-mode^="char-"]'),
  charInputImg: document.getElementById('char-input-img'),
  charInputTxt: document.getElementById('char-input-txt'),
  charInputPrem: document.getElementById('char-input-prem'),
  charFileInput: document.getElementById('char-file'),
  charFileName: document.getElementById('char-file-name'),
  charPromptText: document.getElementById('char-prompt-text'),
  charUrlInput: document.getElementById('char-url-input'),
  charRefinement: document.getElementById('char-refinement'),
  genCharBtn: document.getElementById('gen-char-btn'),
  charSpinner: document.getElementById('char-spinner'),
  charPreviewCard: document.getElementById('char-preview-card'),
  charPlaceholder: document.getElementById('char-placeholder'),
  charLoadedImg: document.getElementById('char-loaded-img'),
  charStatusText: document.getElementById('char-status-text'),
  charCopyUrlBtn: document.getElementById('char-copy-url-btn'),
  charDownloadBtn: document.getElementById('char-download-btn'),

  // Environment Set
  envToggles: document.querySelectorAll('[data-toggle-mode^="env-"]'),
  envInputTxt: document.getElementById('env-input-txt'),
  envInputImg: document.getElementById('env-input-img'),
  envInputPrem: document.getElementById('env-input-prem'),
  envFileInput: document.getElementById('env-file'),
  envFileName: document.getElementById('env-file-name'),
  envPromptText: document.getElementById('env-prompt-text'),
  envUrlInput: document.getElementById('env-url-input'),
  envRefinement: document.getElementById('env-refinement'),
  genEnvBtn: document.getElementById('gen-env-btn'),
  envSpinner: document.getElementById('env-spinner'),
  envPreviewCard: document.getElementById('env-preview-card'),
  envPlaceholder: document.getElementById('env-placeholder'),
  envLoadedImg: document.getElementById('env-loaded-img'),
  envStatusText: document.getElementById('env-status-text'),
  envCopyUrlBtn: document.getElementById('env-copy-url-btn'),
  envDownloadBtn: document.getElementById('env-download-btn'),

  // Product Design
  prodToggles: document.querySelectorAll('[data-toggle-mode^="prod-"]'),
  prodInputImg: document.getElementById('prod-input-img'),
  prodInputTxt: document.getElementById('prod-input-txt'),
  prodInputPrem: document.getElementById('prod-input-prem'),
  prodFileFront: document.getElementById('prod-file-front'),
  prodFileBack: document.getElementById('prod-file-back'),
  prodFrontName: document.getElementById('prod-front-name'),
  prodBackName: document.getElementById('prod-back-name'),
  prodPromptText: document.getElementById('prod-prompt-text'),
  prodUrlInput: document.getElementById('prod-url-input'),
  prodRefinement: document.getElementById('prod-refinement'),
  genProdBtn: document.getElementById('gen-prod-btn'),
  prodSpinner: document.getElementById('prod-spinner'),
  prodPreviewCard: document.getElementById('prod-preview-card'),
  prodPlaceholder: document.getElementById('prod-placeholder'),
  prodLoadedImg: document.getElementById('prod-loaded-img'),
  prodStatusText: document.getElementById('prod-status-text'),
  prodCopyUrlBtn: document.getElementById('prod-copy-url-btn'),
  prodDownloadBtn: document.getElementById('prod-download-btn'),

  // Production Hub
  notionBriefInput: document.getElementById('notion-brief-input'),
  briefFileInput: document.getElementById('brief-file-input'),
  outputLayoutSelect: document.getElementById('output-layout-select'),
  compileCampaignBtn: document.getElementById('compile-campaign-btn'),
  compileSpinner: document.getElementById('compile-spinner'),
  sceneCounter: document.getElementById('scene-counter'),
  timelineContainer: document.getElementById('timeline-container'),
  timelinePlaceholder: document.getElementById('timeline-placeholder'),
  exportJsonBtn: document.getElementById('export-json-btn'),
  exportScriptBtn: document.getElementById('export-script-btn'),

  // Footer / Global UI
  footerCharStatus: document.getElementById('footer-char-status'),
  footerEnvStatus: document.getElementById('footer-env-status'),
  footerProdStatus: document.getElementById('footer-prod-status'),
  toast: document.getElementById('toast-notification'),
  toastMsg: document.getElementById('toast-message')
};

// Initialize App
function init() {
  // Load Keys into Inputs
  DOM.geminiKeyInput.value = STATE.geminiKey;
  DOM.nanoKeyInput.value = STATE.nanoKey;

  setupEventListeners();
  switchTab(STATE.activeTab);
  updateFooterIndicators();

  // Restore application session state if saved in LocalStorage
  restoreApplicationState();
}

// Event Listeners Routing
function setupEventListeners() {
  // Settings gear toggle
  DOM.settingsToggle.addEventListener('click', () => {
    DOM.settingsPanel.classList.toggle('hidden');
  });

  // Save Settings
  DOM.saveSettingsBtn.addEventListener('click', () => {
    STATE.geminiKey = DOM.geminiKeyInput.value.trim();
    STATE.nanoKey = DOM.nanoKeyInput.value.trim();
    localStorage.setItem('GEMINI_API_KEY', STATE.geminiKey);
    localStorage.setItem('NANO_BANANA_KEY', STATE.nanoKey);
    DOM.settingsPanel.classList.add('hidden');
    showToast('Credentials updated and saved locally.');
  });

  // Close dropdown on click outside
  document.addEventListener('click', (e) => {
    if (!DOM.settingsToggle.contains(e.target) && !DOM.settingsPanel.contains(e.target)) {
      DOM.settingsPanel.classList.add('hidden');
    }
  });

  // Tabs navigation
  DOM.tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.getAttribute('data-tab');
      switchTab(tabId);
    });
  });

  // Toggle buttons logic for Character, Environment, Product
  setupToggleHandlers(DOM.charToggles, 'charMode', {
    'char-img': DOM.charInputImg,
    'char-txt': DOM.charInputTxt,
    'char-prem': DOM.charInputPrem
  });

  setupToggleHandlers(DOM.envToggles, 'envMode', {
    'env-txt': DOM.envInputTxt,
    'env-img': DOM.envInputImg,
    'env-prem': DOM.envInputPrem
  });

  setupToggleHandlers(DOM.prodToggles, 'prodMode', {
    'prod-img': DOM.prodInputImg,
    'prod-txt': DOM.prodInputTxt,
    'prod-prem': DOM.prodInputPrem
  });

  // File upload change handlers
  DOM.charFileInput.addEventListener('change', (e) => handleFileUpload(e, 'char', DOM.charFileName));
  DOM.envFileInput.addEventListener('change', (e) => handleFileUpload(e, 'env', DOM.envFileName));
  DOM.prodFileFront.addEventListener('change', (e) => handleFileUpload(e, 'prodFront', DOM.prodFrontName));
  DOM.prodFileBack.addEventListener('change', (e) => handleFileUpload(e, 'prodBack', DOM.prodBackName));
  DOM.briefFileInput.addEventListener('change', handleBriefFileImport);

  // Action Buttons
  DOM.genCharBtn.addEventListener('click', generateCharacterSheet);
  DOM.genEnvBtn.addEventListener('click', generateEnvironmentSheet);
  DOM.genProdBtn.addEventListener('click', generateProductSheet);
  DOM.compileCampaignBtn.addEventListener('click', compileProductionCampaign);
  DOM.exportJsonBtn.addEventListener('click', exportCampaignJSON);
  DOM.exportScriptBtn.addEventListener('click', exportMasterScript);

  // Copy button URLs
  DOM.charCopyUrlBtn.addEventListener('click', () => copyToClipboard(STATE.CHARACTER_SHEET_URL, 'Character URL copied'));
  DOM.envCopyUrlBtn.addEventListener('click', () => copyToClipboard(STATE.SET_SHEET_URL, 'Environment URL copied'));
  DOM.prodCopyUrlBtn.addEventListener('click', () => copyToClipboard(STATE.PRODUCT_SHEET_URL, 'Product URL copied'));

  // Download buttons
  DOM.charDownloadBtn.addEventListener('click', () => downloadAsset(STATE.CHARACTER_SHEET_URL, 'character_sheet.png'));
  DOM.envDownloadBtn.addEventListener('click', () => downloadAsset(STATE.SET_SHEET_URL, 'environment_sheet.png'));
  DOM.prodDownloadBtn.addEventListener('click', () => downloadAsset(STATE.PRODUCT_SHEET_URL, 'product_sheet.png'));

  // Autoload persistence hooks
  DOM.notionBriefInput.addEventListener('input', saveApplicationState);
  DOM.charRefinement.addEventListener('input', saveApplicationState);
  DOM.envRefinement.addEventListener('input', saveApplicationState);
  DOM.prodRefinement.addEventListener('input', saveApplicationState);
  DOM.outputLayoutSelect.addEventListener('change', saveApplicationState);
}

// Switch navigation tabs
function switchTab(tabId) {
  STATE.activeTab = tabId;
  DOM.tabBtns.forEach(btn => {
    if (btn.getAttribute('data-tab') === tabId) {
      btn.classList.add('active-tab', 'border-cyber-accent');
      btn.classList.remove('text-slate-400');
      btn.classList.add('text-white');
    } else {
      btn.classList.remove('active-tab', 'border-cyber-accent');
      btn.classList.add('text-slate-400');
      btn.classList.remove('text-white');
    }
  });

  DOM.tabContents.forEach(content => {
    if (content.id === `tab-${tabId}`) {
      content.classList.remove('hidden');
    } else {
      content.classList.add('hidden');
    }
  });
}

// 3-way toggle controllers
function setupToggleHandlers(buttons, stateKey, displayMap) {
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      const mode = btn.getAttribute('data-toggle-mode');
      STATE[stateKey] = mode;
      
      buttons.forEach(b => {
        b.className = "mode-toggle-btn py-2 text-xs font-mono rounded-md transition-all duration-200 text-slate-400 hover:text-white";
      });

      // Highlight active
      if (stateKey === 'prodMode') {
        btn.className = "mode-toggle-btn py-2 text-xs font-mono rounded-md transition-all duration-200 bg-cyber-neonGreen text-cyber-black font-bold";
      } else if (stateKey === 'envMode') {
        btn.className = "mode-toggle-btn py-2 text-xs font-mono rounded-md transition-all duration-200 bg-cyber-neonBlue text-white font-semibold";
      } else {
        btn.className = "mode-toggle-btn py-2 text-xs font-mono rounded-md transition-all duration-200 bg-cyber-accent text-white font-semibold";
      }

      // Toggle form contents
      Object.keys(displayMap).forEach(key => {
        if (key === mode) {
          displayMap[key].classList.remove('hidden');
        } else {
          displayMap[key].classList.add('hidden');
        }
      });

      saveApplicationState();
    });
  });
}

// Base64 File Loader
function handleFileUpload(event, stateKey, nameEl) {
  const file = event.target.files[0];
  if (!file) return;

  nameEl.textContent = `Attached: ${file.name}`;
  nameEl.classList.remove('hidden');

  const reader = new FileReader();
  reader.onload = function(e) {
    STATE.files[stateKey] = {
      name: file.name,
      mimeType: file.type,
      base64: e.target.result.split(',')[1] // Get base64 string
    };
  };
  reader.readAsDataURL(file);
}

// MD and CSV Brief Import Helper (Appends content to allow multiple file parts)
function handleBriefFileImport(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(evt) {
    let importedText = evt.target.result;
    if (file.name.toLowerCase().endsWith('.csv')) {
      importedText = parseCSVToMarkdown(importedText);
    }
    const currentVal = DOM.notionBriefInput.value.trim();
    const separator = currentVal ? `\n\n--- Imported: ${file.name} ---\n` : "";
    DOM.notionBriefInput.value = currentVal + separator + importedText;
    showToast(`Brief file '${file.name}' appended successfully.`);
    e.target.value = "";
    saveApplicationState();
  };
  reader.onerror = function() {
    showToast("Failed to read the imported brief file.");
  };
  reader.readAsText(file);
}

// Robust client-side CSV to Markdown converter
function parseCSVToMarkdown(csvText) {
  const lines = [];
  let row = [];
  let currentValue = "";
  let inQuotes = false;
  const text = csvText.replace(/\r\n/g, '\n');

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    const nextChar = text[i + 1];

    if (char === '"') {
      if (inQuotes && nextChar === '"') {
        currentValue += '"'; // Escaped double quotes
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      row.push(currentValue.trim());
      currentValue = "";
    } else if (char === '\n' && !inQuotes) {
      row.push(currentValue.trim());
      lines.push(row);
      row = [];
      currentValue = "";
    } else {
      currentValue += char;
    }
  }

  if (currentValue || row.length > 0) {
    row.push(currentValue.trim());
    lines.push(row);
  }

  const validLines = lines.filter(r => r.some(cell => cell !== ""));
  if (validLines.length === 0) return "";

  const colCount = Math.max(...validLines.map(r => r.length));
  
  const markdownRows = validLines.map(r => {
    const filledRow = [...r, ...Array(colCount - r.length).fill("")];
    return "| " + filledRow.join(" | ") + " |";
  });

  const separator = "| " + Array(colCount).fill("---").join(" | ") + " |";
  if (markdownRows.length > 1) {
    markdownRows.splice(1, 0, separator);
  } else {
    markdownRows.push(separator);
  }

  return markdownRows.join("\n");
}

// Copy prompt clipboard function
function copyToClipboard(text, msg) {
  navigator.clipboard.writeText(text).then(() => {
    showToast(msg || 'Copied to clipboard');
  }).catch(() => {
    showToast('Failed to copy. Permission denied.');
  });
}

// Download Helper
function downloadAsset(url, filename) {
  if (!url) return;
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// Show active Toast Notifications
function showToast(message) {
  DOM.toastMsg.textContent = message;
  DOM.toast.classList.remove('translate-y-20', 'opacity-0');
  DOM.toast.classList.add('translate-y-0', 'opacity-100');
  
  setTimeout(() => {
    DOM.toast.classList.add('translate-y-20', 'opacity-0');
    DOM.toast.classList.remove('translate-y-0', 'opacity-100');
  }, 3000);
}

// Update UI Indicators
function updateFooterIndicators() {
  DOM.footerCharStatus.textContent = STATE.CHARACTER_SHEET_URL ? 'anchored' : 'empty';
  DOM.footerCharStatus.className = STATE.CHARACTER_SHEET_URL ? 'text-cyber-accent' : 'text-slate-500';

  DOM.footerEnvStatus.textContent = STATE.SET_SHEET_URL ? 'anchored' : 'empty';
  DOM.footerEnvStatus.className = STATE.SET_SHEET_URL ? 'text-cyber-neonBlue' : 'text-slate-500';

  DOM.footerProdStatus.textContent = STATE.PRODUCT_SHEET_URL ? 'anchored' : 'empty';
  DOM.footerProdStatus.className = STATE.PRODUCT_SHEET_URL ? 'text-cyber-neonGreen' : 'text-slate-500';
}

// -------------------------------------------------------------
// ENGINE API ACTIONS
// -------------------------------------------------------------

// Helper API Fetcher for Gemini Images
async function generateAssetImage(promptText, fileData = null, customConfig = {}) {
  if (!STATE.geminiKey) {
    console.warn("No GEMINI_API_KEY found, returning local styled canvas placeholder");
    return generateLocalFallbackCanvasUrl(promptText);
  }

  try {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=${STATE.geminiKey}`;
    
    const parts = [
      { text: promptText }
    ];

    if (fileData) {
      parts.push({
        inlineData: {
          mimeType: fileData.mimeType,
          data: fileData.base64
        }
      });
    }

    const gConfig = {
      response_modalities: ["TEXT", "IMAGE"]
    };

    const ratio = customConfig.aspectRatio || customConfig.aspect_ratio;
    if (ratio) {
      gConfig.imageConfig = {
        aspectRatio: ratio
      };
    }

    // Merge other custom configs if any
    for (const key in customConfig) {
      if (key !== 'aspectRatio' && key !== 'aspect_ratio') {
        gConfig[key] = customConfig[key];
      }
    }

    const payload = {
      contents: [{
        parts: parts
      }],
      generationConfig: gConfig
    };

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error: ${response.status} - ${errorText}`);
    }

    const data = await response.json();
    if (data.candidates && data.candidates[0] && data.candidates[0].content && data.candidates[0].content.parts) {
      const respParts = data.candidates[0].content.parts;
      for (const part of respParts) {
        if (part.inlineData) {
          const mime = part.inlineData.mimeType || 'image/png';
          return `data:${mime};base64,${part.inlineData.data}`;
        }
      }
    }
    throw new Error("No inline image returned from Gemini.");
  } catch (error) {
    console.error("Gemini native image generation failed:", error);
    showToast(`Generation failed: ${error.message}`);
    throw error;
  }
}

// Helper local canvas fallback generator
function generateLocalFallbackCanvasUrl(text) {
  const canvas = document.createElement('canvas');
  canvas.width = 960;
  canvas.height = 540;
  const ctx = canvas.getContext('2d');

  // Cool cool slate-gray background (HEX #6F7478)
  ctx.fillStyle = '#6F7478';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Add subtle grid overlay lines
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
  ctx.lineWidth = 2;
  // Divide Left 40% vs Right 60%
  const boundary = canvas.width * 0.4;
  ctx.beginPath();
  ctx.moveTo(boundary, 0);
  ctx.lineTo(boundary, canvas.height);
  ctx.stroke();

  // Draw 2x2 portrait lines on left
  ctx.beginPath();
  ctx.moveTo(0, canvas.height / 2);
  ctx.lineTo(boundary, canvas.height / 2);
  ctx.moveTo(boundary / 2, 0);
  ctx.lineTo(boundary / 2, canvas.height);
  ctx.stroke();

  // Draw 2 vertical body dividers on right
  ctx.beginPath();
  ctx.moveTo(boundary + (canvas.width - boundary) / 2, 0);
  ctx.lineTo(boundary + (canvas.width - boundary) / 2, canvas.height);
  ctx.stroke();

  // Add premium design branding text
  ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
  ctx.font = 'bold 24px monospace';
  ctx.fillText('IN-NO-V8 PRODUCTION ASSET', 50, 50);

  ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
  ctx.font = '16px monospace';
  // Wrap and print descriptive text
  const words = text.split(' ');
  let line = '';
  let y = 120;
  for (let n = 0; n < words.length; n++) {
    let testLine = line + words[n] + ' ';
    let metrics = ctx.measureText(testLine);
    if (metrics.width > 280 && n > 0) {
      ctx.fillText(line, 50, y);
      line = words[n] + ' ';
      y += 24;
    } else {
      line = testLine;
    }
  }
  ctx.fillText(line, 50, y);

  return canvas.toDataURL('image/jpeg');
}

// TAB 1: Character Sheet Anchor Pipeline
async function generateCharacterSheet() {
  DOM.genCharBtn.disabled = true;
  DOM.charSpinner.classList.remove('hidden');
  DOM.charStatusText.textContent = "GENERATING...";

  let prompt = '';
  let fileToUpload = null;

  // Refinement overwriting logic (reads fresh on click, sets empty if input is empty)
  const refinement = DOM.charRefinement.value.trim();
  const refinementPart = refinement ? ` [ADDITIONAL REFINEMENTS]: ${refinement}` : '';

  if (STATE.charMode === 'char-img') {
    fileToUpload = STATE.files.char;
    const basePrompts = [
      "A portrait from the shoulders up, strict 0-degree direct front view face, centered, isolated cutout on a completely flat solid uniform white background HEX #FFFFFF.",
      "A portrait from the shoulders up, strict 90-degree side profile view facing completely right, centered, showing full profile contour of the nose, eyes, and lips, isolated cutout on a completely flat solid uniform white background HEX #FFFFFF.",
      "A portrait from the shoulders up, strict 180-degree view of the back of the head and hair, centered, isolated cutout on a completely flat solid uniform white background HEX #FFFFFF.",
      "A portrait from the shoulders up, strict 270-degree side profile view facing completely left, centered, showing full profile contour of the nose, eyes, and lips, isolated cutout on a completely flat solid uniform white background HEX #FFFFFF.",
      "Full length full-body shot, standing facing directly forward, complete outfit visible with all gear and skirts, centered, isolated cutout on a completely flat solid uniform white background HEX #FFFFFF.",
      "Full length full-body shot, standing facing directly backward, complete back outfit and back of head visible, centered, isolated cutout on a completely flat solid uniform white background HEX #FFFFFF."
    ];

    try {
      // Execute 6 parallel image generations using gemini-2.5-flash-image
      const imagePromises = basePrompts.map(bp => {
        const identityConstraint = " Replicate the uploaded photo's clothing, skirt, armor, and facial traits with 100% exact styling continuity.";
        const finalPromptText = bp + identityConstraint + (refinementPart ? ` [ADDITIONAL REFINEMENTS]: ${refinementPart}` : '');
        return generateAssetImage(finalPromptText, fileToUpload);
      });

      const imageUrls = await Promise.all(imagePromises);

      // Load all images asynchronously
      const loadImage = (url) => new Promise((resolve, reject) => {
        const img = new Image();
        img.crossOrigin = "anonymous";
        img.onload = () => resolve(img);
        img.onerror = (e) => reject(new Error("Failed to load generated panel image."));
        img.src = url;
      });

      // Helper function to remove background from loaded image (chroma keying/thresholding)
      const removeImageBackground = (img) => {
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = img.width;
        tempCanvas.height = img.height;
        const tempCtx = tempCanvas.getContext('2d');
        tempCtx.drawImage(img, 0, 0);

        const imgData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
        const pixelData = imgData.data;

        // Key out near-white pixels (R, G, B all very high)
        for (let i = 0; i < pixelData.length; i += 4) {
          const r = pixelData[i];
          const g = pixelData[i + 1];
          const b = pixelData[i + 2];

          if (r > 240 && g > 240 && b > 240) {
            pixelData[i + 3] = 0; // Set Alpha to transparent
          }
        }
        tempCtx.putImageData(imgData, 0, 0);
        return tempCanvas;
      };

      const loadedImages = await Promise.all(imageUrls.map(loadImage));
      const processedImages = loadedImages.map(removeImageBackground);

      // Ensure the master canvas is a crisp, locked resolution
      const canvas = document.createElement('canvas');
      canvas.width = 1920;
      canvas.height = 1080;
      const ctx = canvas.getContext('2d');

      // 1. Fill base solid gray studio background
      ctx.fillStyle = '#6F7478';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Helper function to draw square close-ups with perfect center-cropping (Cover style)
      function drawSquareCrop(img, x, y, size) {
          const srcSize = Math.min(img.width, img.height);
          const srcX = (img.width - srcSize) / 2;
          const srcY = (img.height - srcSize) / 2;
          ctx.drawImage(img, srcX, srcY, srcSize, srcSize, x, y, size, size);
      }

      // Helper function to draw full-body panels without squashing (Zoomed & Clipped style)
      function drawFullBody(img, targetX, targetY, targetW, targetH) {
          // Zoom factor to crop out excess empty background space around the figure
          const zoom = 2.2; 
          
          const imgRatio = img.width / img.height;
          const targetRatio = targetW / targetH;
          
          let renderW, renderH;
          if (imgRatio > targetRatio) {
              // Image is wider than slot
              renderW = targetW * zoom;
              renderH = (targetW / imgRatio) * zoom;
          } else {
              // Image is taller than slot
              renderH = targetH * zoom;
              renderW = (targetH * imgRatio) * zoom;
          }
          
          // Center the zoomed image inside the target slot boundaries
          let renderX = targetX - (renderW - targetW) / 2;
          let renderY = targetY - (renderH - targetH) / 2;

          // Clip the drawing bounds strictly to the designated slot
          ctx.save();
          ctx.beginPath();
          ctx.rect(targetX, targetY, targetW, targetH);
          ctx.clip();
          
          ctx.drawImage(img, renderX, renderY, renderW, renderH);
          ctx.restore();
      }

      // Map processed cutouts to image variables
      const imgFrontHead = processedImages[0];
      const imgRightProfile = processedImages[1];
      const imgBackHead = processedImages[2];
      const imgLeftProfile = processedImages[3];
      const imgBodyFront = processedImages[4];
      const imgBodyBack = processedImages[5];

      // 2. Map the 4 Close-Up Portraits (Left 40% of Canvas)
      // Left area width = 768px (1920 * 0.40). Each square box = 360x360px with 32px padding margins.
      drawSquareCrop(imgFrontHead, 32, 160, 360);       // Top-Left Panel
      drawSquareCrop(imgLeftProfile, 412, 160, 360);    // Top-Right Panel
      drawSquareCrop(imgBackHead, 32, 560, 360);        // Bottom-Left Panel
      drawSquareCrop(imgRightProfile, 412, 560, 360);   // Bottom-Right Panel

      // 3. Map the 2 Full-Body Turnarounds (Right 60% of Canvas)
      // Right area width = 1152px (1920 * 0.60), starting at X = 768. 
      // Each tall slot = 544x960px with a 32px spacing gap.
      drawFullBody(imgBodyFront, 800, 60, 544, 960);    // Full Body Front
      drawFullBody(imgBodyBack, 1376, 60, 544, 960);    // Full Body Back

      const finalDataUrl = canvas.toDataURL('image/png');
      STATE.CHARACTER_SHEET_URL = finalDataUrl;
      mountCharacterImage(finalDataUrl);
      showToast('Character asset sheet compiled successfully.');
    } catch (err) {
      console.error("Canvas compilation failed:", err);
      showToast(`Canvas generation failed: ${err.message}`);
      DOM.charStatusText.textContent = "GENERATION FAILED";
      DOM.charStatusText.className = "text-red-500 uppercase font-bold";
    } finally {
      DOM.genCharBtn.disabled = false;
      DOM.charSpinner.classList.add('hidden');
    }
    return;
  }

  if (STATE.charMode === 'char-txt') {
    const userText = DOM.charPromptText.value.trim() || 'Hero character';
    prompt = `A professional character design sheet of ${userText}, 16:9 horizontal layout. The entire sheet sits on a single, continuous, solid flat neutral studio background (HEX #6F7478) with zero internal borders, zero separate panels, no outlines, no text, and no framing lines.
- Left 40% of canvas: 4 distinct isolated headshot portraits (Top-Left: 0-degree front, Top-Right: 90-degree side profile looking completely left, Bottom-Left: 180-degree back of head, Bottom-Right: 270-degree side profile looking completely right).
- Right 60% of canvas: 2 isolated full-body turnaround views side-by-side (Full front view, Full back view). Maintain absolute continuity across all views on the sheet.${refinementPart}`;
  } else {
    // Pre-made Asset Mode
    const url = DOM.charUrlInput.value.trim();
    if (!url) {
      showToast('Please insert a valid Pre-made URL.');
      DOM.genCharBtn.disabled = false;
      DOM.charSpinner.classList.add('hidden');
      DOM.charStatusText.textContent = "UNMOUNTED";
      return;
    }
    STATE.CHARACTER_SHEET_URL = url;
    mountCharacterImage(url);
    showToast('Pre-made character sheet anchored.');
    DOM.genCharBtn.disabled = false;
    DOM.charSpinner.classList.add('hidden');
    return;
  }

  try {
    const generatedUrl = await generateAssetImage(prompt, fileToUpload);
    STATE.CHARACTER_SHEET_URL = generatedUrl;
    mountCharacterImage(generatedUrl);
    showToast('Character asset sheet successfully anchored.');
  } catch (err) {
    console.error("Character generation failed:", err);
    showToast(`Generation failed: ${err.message}`);
    DOM.charStatusText.textContent = "GENERATION FAILED";
    DOM.charStatusText.className = "text-red-500 uppercase font-bold";
  } finally {
    DOM.genCharBtn.disabled = false;
    DOM.charSpinner.classList.add('hidden');
  }
}

function mountCharacterImage(url) {
  DOM.charPlaceholder.classList.add('hidden');
  DOM.charLoadedImg.src = url;
  DOM.charLoadedImg.classList.remove('hidden');
  DOM.charStatusText.textContent = "ANCHORED & ONLINE";
  DOM.charStatusText.className = "text-cyber-neonGreen uppercase font-bold";
  DOM.charCopyUrlBtn.classList.remove('hidden');
  DOM.charCopyUrlBtn.classList.add('flex');
  DOM.charDownloadBtn.classList.remove('hidden');
  DOM.charDownloadBtn.classList.add('flex');
  updateFooterIndicators();
  saveApplicationState();
}

// TAB 2: Environment Anchor Pipeline
async function generateEnvironmentSheet() {
  DOM.genEnvBtn.disabled = true;
  DOM.envSpinner.classList.remove('hidden');
  DOM.envStatusText.textContent = "GENERATING...";

  let prompt = '';
  let fileToUpload = null;

  if (STATE.envMode === 'env-txt') {
    const userText = DOM.envPromptText.value.trim() || 'Futuristic chamber';
    prompt = `[LAYOUT]: A clean 16:9 horizontal location concept master sheet containing exactly 4 separate environmental panels arranged in a balanced 2x2 grid. Empty set, no characters. [GRID DIVISION]: Top-Left: Wide Master Shot. Top-Right: Medium Composition Anchor. Bottom-Left: Reverse Angle View. Bottom-Right: Close-Up Texture Detail. [SET DESIGN]: ${userText}.`;
  } else if (STATE.envMode === 'env-img') {
    fileToUpload = STATE.files.env;
    prompt = `[LAYOUT]: A clean 16:9 horizontal location concept master sheet containing exactly 4 separate environmental panels arranged in a balanced 2x2 grid. Empty set, no characters. [GRID DIVISION]: Top-Left: Wide Master Shot. Top-Right: Medium Composition Anchor. Bottom-Left: Reverse Angle View. Bottom-Right: Close-Up Texture Detail. Replicate style, geometry, and tone from the uploaded reference image.`;
  } else {
    // Pre-made
    const url = DOM.envUrlInput.value.trim();
    if (!url) {
      showToast('Please insert a valid Pre-made URL.');
      DOM.genEnvBtn.disabled = false;
      DOM.envSpinner.classList.add('hidden');
      DOM.envStatusText.textContent = "UNMOUNTED";
      return;
    }
    STATE.SET_SHEET_URL = url;
    mountEnvironmentImage(url);
    showToast('Pre-made environment sheet anchored.');
    DOM.genEnvBtn.disabled = false;
    DOM.envSpinner.classList.add('hidden');
    return;
  }

  const refinement = DOM.envRefinement.value.trim();
  if (refinement) {
    prompt += ` [ADDITIONAL REFINEMENTS]: ${refinement}`;
  }

  try {
    const generatedUrl = await generateAssetImage(prompt, fileToUpload, { aspectRatio: "16:9" });
    STATE.SET_SHEET_URL = generatedUrl;
    mountEnvironmentImage(generatedUrl);
    showToast('Environment asset sheet successfully anchored.');
  } catch (err) {
    console.error("Environment generation failed:", err);
    showToast(`Generation failed: ${err.message}`);
    DOM.envStatusText.textContent = "GENERATION FAILED";
    DOM.envStatusText.className = "text-red-500 uppercase font-bold";
  } finally {
    DOM.genEnvBtn.disabled = false;
    DOM.envSpinner.classList.add('hidden');
  }
}

function mountEnvironmentImage(url) {
  DOM.envPlaceholder.classList.add('hidden');
  DOM.envLoadedImg.src = url;
  DOM.envLoadedImg.classList.remove('hidden');
  DOM.envStatusText.textContent = "ANCHORED & ONLINE";
  DOM.envStatusText.className = "text-cyber-neonBlue uppercase font-bold";
  DOM.envCopyUrlBtn.classList.remove('hidden');
  DOM.envCopyUrlBtn.classList.add('flex');
  DOM.envDownloadBtn.classList.remove('hidden');
  DOM.envDownloadBtn.classList.add('flex');
  updateFooterIndicators();
  saveApplicationState();
}

// TAB 3: Product Anchor Pipeline
async function generateProductSheet() {
  DOM.genProdBtn.disabled = true;
  DOM.prodSpinner.classList.remove('hidden');
  DOM.prodStatusText.textContent = "GENERATING...";

  if (STATE.prodMode === 'prod-img') {
    if (!STATE.files.prodFront || !STATE.files.prodBack) {
      showToast('Please upload both Front and Back Packaging Layouts.');
      DOM.genProdBtn.disabled = false;
      DOM.prodSpinner.classList.add('hidden');
      DOM.prodStatusText.textContent = "UNMOUNTED";
      return;
    }

    try {
      const loadImg = (fileObj) => new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error("Failed to load product file"));
        img.src = `data:${fileObj.mimeType};base64,${fileObj.base64}`;
      });

      const [imgFront, imgBack] = await Promise.all([
        loadImg(STATE.files.prodFront),
        loadImg(STATE.files.prodBack)
      ]);

      const canvas = document.createElement('canvas');
      canvas.width = 1920;
      canvas.height = 1080;
      const ctx = canvas.getContext('2d');

      // Fill slate-gray background
      ctx.fillStyle = '#6F7478';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const drawContained = (img, x, y, w, h) => {
        const imgRatio = img.width / img.height;
        const targetRatio = w / h;
        let dw = w;
        let dh = h;
        if (imgRatio > targetRatio) {
          dh = w / imgRatio;
        } else {
          dw = h * imgRatio;
        }
        const dx = x + (w - dw) / 2;
        const dy = y + (h - dh) / 2;
        ctx.drawImage(img, dx, dy, dw, dh);
      };

      // Draw side-by-side
      drawContained(imgFront, 80, 80, 800, 920);
      drawContained(imgBack, 1040, 80, 800, 920);

      const finalDataUrl = canvas.toDataURL('image/png');
      STATE.PRODUCT_SHEET_URL = finalDataUrl;
      mountProductImage(finalDataUrl);
      showToast('Product sheet compiled directly from uploads.');
    } catch (err) {
      console.error(err);
      showToast(`Product sheet compilation failed: ${err.message}`);
    } finally {
      DOM.genProdBtn.disabled = false;
      DOM.prodSpinner.classList.add('hidden');
    }
    return;
  } else if (STATE.prodMode === 'prod-txt') {
    const userText = DOM.prodPromptText.value.trim() || 'Cyber can drink';
    prompt = `A professional commercial design sheet of ${userText}, showing front/back and perspective panels in a 2x2 grid against a neutral showcase studio backdrop. No hands.`;
  } else {
    // Pre-made
    const url = DOM.prodUrlInput.value.trim();
    if (!url) {
      showToast('Please insert a valid Pre-made URL.');
      DOM.genProdBtn.disabled = false;
      DOM.prodSpinner.classList.add('hidden');
      DOM.prodStatusText.textContent = "UNMOUNTED";
      return;
    }
    STATE.PRODUCT_SHEET_URL = url;
    mountProductImage(url);
    showToast('Pre-made product sheet anchored.');
    DOM.genProdBtn.disabled = false;
    DOM.prodSpinner.classList.add('hidden');
    return;
  }

  const refinement = DOM.prodRefinement.value.trim();
  if (refinement && STATE.prodMode !== 'prod-img') {
    prompt += ` [ADDITIONAL REFINEMENTS]: ${refinement}`;
  }

  try {
    const generatedUrl = await generateAssetImage(prompt, fileToUpload);
    STATE.PRODUCT_SHEET_URL = generatedUrl;
    mountProductImage(generatedUrl);
    showToast('Product asset sheet successfully anchored.');
  } catch (err) {
    console.error("Product generation failed:", err);
    showToast(`Generation failed: ${err.message}`);
    DOM.prodStatusText.textContent = "GENERATION FAILED";
    DOM.prodStatusText.className = "text-red-500 uppercase font-bold";
  } finally {
    DOM.genProdBtn.disabled = false;
    DOM.prodSpinner.classList.add('hidden');
  }
}

function mountProductImage(url) {
  DOM.prodPlaceholder.classList.add('hidden');
  DOM.prodLoadedImg.src = url;
  DOM.prodLoadedImg.classList.remove('hidden');
  DOM.prodStatusText.textContent = "ANCHORED & ONLINE";
  DOM.prodStatusText.className = "text-cyber-neonGreen uppercase font-bold";
  DOM.prodCopyUrlBtn.classList.remove('hidden');
  DOM.prodCopyUrlBtn.classList.add('flex');
  DOM.prodDownloadBtn.classList.remove('hidden');
  DOM.prodDownloadBtn.classList.add('flex');
  updateFooterIndicators();
  saveApplicationState();
}

// -------------------------------------------------------------
// TAB 4: PRODUCTION CAMPAIGN COMPILER
// -------------------------------------------------------------
async function compileProductionCampaign() {
  const briefText = DOM.notionBriefInput.value.trim();
  if (!briefText) {
    showToast('Please insert workspace script details to parse.');
    return;
  }

  DOM.compileCampaignBtn.disabled = true;
  DOM.compileSpinner.classList.remove('hidden');
  
  // Parse variables and convert huge base64 strings to short references to avoid token bloat and text pollution
  const charUrl = STATE.CHARACTER_SHEET_URL ? (STATE.CHARACTER_SHEET_URL.startsWith('data:') ? "[Anchored Character Sheet]" : STATE.CHARACTER_SHEET_URL) : null;
  const envUrl = STATE.SET_SHEET_URL ? (STATE.SET_SHEET_URL.startsWith('data:') ? "[Anchored Set Sheet]" : STATE.SET_SHEET_URL) : null;
  const prodUrl = STATE.PRODUCT_SHEET_URL ? (STATE.PRODUCT_SHEET_URL.startsWith('data:') ? "[Anchored Product Sheet]" : STATE.PRODUCT_SHEET_URL) : null;

  // Build the fallback instruction set depending on what variables are active
  let instructionFallback = "";
  if (!charUrl) {
    instructionFallback += " OMIT ALL [BASE ASSETS] character references and character tokens since the user skipped character config.";
  } else {
    instructionFallback += ` Include reference links/tokens pointing to CHARACTER_SHEET: ${charUrl}.`;
  }
  
  if (!envUrl) {
    instructionFallback += " OMIT ALL [BASE ASSETS] environment references and set/location tokens since the user skipped environment config.";
  } else {
    instructionFallback += ` Include reference links/tokens pointing to SET_SHEET: ${envUrl}.`;
  }

  if (!prodUrl) {
    instructionFallback += " OMIT ALL [BASE ASSETS] product references and product layout tokens since the user skipped product design.";
  } else {
    instructionFallback += ` Include reference links/tokens pointing to PRODUCT_SHEET: ${prodUrl}.`;
  }

  // Determine output target layout configurations
  const outputLayout = DOM.outputLayoutSelect ? DOM.outputLayoutSelect.value : 'horizontal';
  let layoutInstruction = "";
  if (outputLayout === 'vertical') {
    layoutInstruction = "Optimize all visual_generation_prompt values to describe narrow, vertical framing layouts tailored for TikTok/Shorts (9:16 aspect ratio, tight vertical tracking, tall framing elements).";
  } else {
    layoutInstruction = "Optimize all visual_generation_prompt values to describe wide, horizontal framing layouts (16:9 aspect ratio, wide landscape composition, horizontal tracking).";
  }

  const audioStripInstruction = "CRITICAL: You must strictly isolate audio generation instructions. Do NOT output any audio instructions, ambient sound cues, sound effects (SFX), scoring notes, musical cues, or background music descriptions inside the voiceover_script or editor_notes fields. All output values must strictly focus on spoken dialogue and character action only.";

  const continuityInstruction = `The generation engine must track visual states sequentially from Scene 1 through the final scene to maintain absolute narrative coherence. 
- Environmental Persistence: If a character is established in a specific state or location in a scene (e.g., sitting at a wooden table in Scene 1), she must remain in that exact state/location in all subsequent scenes unless an explicit action dictates a change (e.g., standing up, walking away).
- Sequential Accumulation: If an action permanently alters the character's appearance in a scene (e.g., in Scene 2 she applies face stripes), that visual change must be explicitly carried over and described in the visual_generation_prompt for all subsequent scenes (e.g., Scenes 3 through 13 must explicitly include the face stripes in the description).
- Prevent Regression: Ensure the character's appearance or environment never reverts to a previous state unless explicitly directed by the source text.`;

  const parserPrompt = `You are a script processing engine parser for movie assets.
Parse the following workspace brief / script table into a structured JSON array of campaign scenes.

[BRIEF / TABLE DATA]:
"${briefText}"

[INSTRUCTIONS ON ASSETS]:
${instructionFallback}

[LAYOUT COMPOSITION]:
${layoutInstruction}

[AUDIO & MUSIC STRIPPING]:
${audioStripInstruction}

[PROGRESSIVE VISUAL CONTINUITY]:
${continuityInstruction}

Output a strictly formatted JSON array containing objects with these exact keys:
- scene_id
- scene_type
- voiceover_script
- editor_notes
- visual_generation_prompt (a fully optimized scene prompt including active asset references like [BASE ASSETS] matching the anchored URLs provided above).

Format the output strictly as raw JSON matching the schema below:
[
  {
    "scene_id": "scene_1",
    "scene_type": "...",
    "voiceover_script": "...",
    "editor_notes": "...",
    "visual_generation_prompt": "..."
  }
]
No markdown packaging. Return ONLY raw JSON array.`;

  if (!STATE.geminiKey) {
    // Simulated parser fallback if keys are missing
    console.warn("No GEMINI_API_KEY found, simulating client-side script compiler parser.");
    setTimeout(() => {
      const simulatedData = simulateScriptParser(briefText, charUrl, envUrl, prodUrl);
      renderTimeline(simulatedData);
      DOM.compileCampaignBtn.disabled = false;
      DOM.compileSpinner.classList.add('hidden');
      showToast('Campaign compiled successfully (simulated fallback).');
    }, 1500);
    return;
  }

  try {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${STATE.geminiKey}`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        contents: [{
          parts: [{ text: parserPrompt }]
        }],
        generationConfig: {
          responseMimeType: "application/json",
          responseSchema: {
            type: "ARRAY",
            items: {
              type: "OBJECT",
              properties: {
                scene_id: { type: "STRING" },
                scene_type: { type: "STRING" },
                voiceover_script: { type: "STRING" },
                editor_notes: { type: "STRING" },
                visual_generation_prompt: { type: "STRING" }
              },
              required: ["scene_id", "scene_type", "voiceover_script", "editor_notes", "visual_generation_prompt"]
            }
          }
        }
      })
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    const textOutput = data.candidates[0].content.parts[0].text;
    
    // Clean potential markdown wrappers
    let cleanJson = textOutput.replace(/```json/g, '').replace(/```/g, '').trim();
    const parsedData = JSON.parse(cleanJson);
    renderTimeline(parsedData);
    showToast('Production timeline campaign compiled!');
  } catch (err) {
    console.error("Compilation failed, falling back to simulated parser:", err);
    const fallbackData = simulateScriptParser(briefText, charUrl, envUrl, prodUrl);
    renderTimeline(fallbackData);
    showToast('Timeline compiled using client-side parser fallback.');
  } finally {
    DOM.compileCampaignBtn.disabled = false;
    DOM.compileSpinner.classList.add('hidden');
  }
}

// Simulated compiler parser backup logic
function simulateScriptParser(brief, char, env, prod) {
  // Regex parsing scenes
  const scenes = [];
  const sceneBlocks = brief.split(/(Scene \d+|SCENE \d+)/i).filter(Boolean);

  let currentId = 1;
  for (let i = 0; i < sceneBlocks.length; i += 2) {
    const header = sceneBlocks[i] || `Scene ${currentId}`;
    const body = sceneBlocks[i + 1] || '';
    
    if (!body.trim()) continue;

    // extract voiceover
    const voMatch = body.match(/voiceover:\s*['"]?([^'"]+)['"]?/i);
    const vo = voMatch ? voMatch[1] : 'Voiceover narration script';

    // extract notes
    const notesMatch = body.match(/editor\s*notes:\s*([^]+)/i);
    const notes = notesMatch ? notesMatch[1].trim() : 'Flicker lights, transition smoothly';

    // Compile custom prompt
    let promptParts = [`Scene depiction of ${header.toLowerCase()}.`];
    if (char) {
      promptParts.push(`Render with 100% features matching character reference [BASE ASSETS: ${char}].`);
    }
    if (env) {
      promptParts.push(`Set location aligned with environment mockup [BASE ASSETS: ${env}].`);
    }
    if (prod) {
      promptParts.push(`Incorporate packaging mockups matching product asset [BASE ASSETS: ${prod}].`);
    }
    
    scenes.push({
      scene_id: header.toLowerCase().replace(' ', '_'),
      scene_type: 'Live-Action Animation Blend',
      voiceover_script: vo,
      editor_notes: notes,
      visual_generation_prompt: promptParts.join(' ')
    });
    currentId++;
  }

  if (scenes.length === 0) {
    // Default mock data if parsing finds nothing
    return [
      {
        scene_id: "scene_1_intro",
        scene_type: "Commercial Opener",
        voiceover_script: "Welcome to the future of clickbait production.",
        editor_notes: "Apply glitch neon text overlays.",
        visual_generation_prompt: `A vibrant cyberpunk setting. ${char ? `Hero matches character sheet: ${char}` : ''} ${env ? `Background aligns with environment concept: ${env}` : ''}`
      }
    ];
  }

  return scenes;
}

// Progressive Scene State Analyzer to track visual states sequentially
function analyzeProgressiveStates(scenes) {
  const activeStates = [];
  
  // Heuristic maps for matching changes in posture or appearance
  const rules = [
    {
      keywords: [/stands? up/i, /standing up/i],
      state: "The character is standing up, not sitting",
      negations: [/sits? down/i, /sitting/i]
    },
    {
      keywords: [/sits? down/i, /sitting/i],
      state: "The character is sitting",
      negations: [/stands? up/i, /standing/i]
    },
    {
      keywords: [/paint.* stripe/i, /put.* stripe/i, /stripe.* face/i, /stripe.* cheek/i],
      state: "with face stripes visible",
      negations: [/wipe.* paint/i, /clean.* face/i]
    }
  ];

  return scenes.map((scene) => {
    const textToSearch = `${scene.voiceover_script} ${scene.editor_notes} ${scene.visual_generation_prompt}`;
    
    // Process matching rules to update active states
    rules.forEach(rule => {
      const matchesKeyword = rule.keywords.some(rx => rx.test(textToSearch));
      if (matchesKeyword) {
        if (rule.negations) {
          rule.negations.forEach(neg => {
            const conflictingRule = rules.find(r => r.keywords.includes(neg));
            if (conflictingRule) {
              const idx = activeStates.indexOf(conflictingRule.state);
              if (idx > -1) activeStates.splice(idx, 1);
            }
          });
        }
        if (rule.state === "The character is standing up, not sitting") {
          const sitIdx = activeStates.indexOf("The character is sitting");
          if (sitIdx > -1) activeStates.splice(sitIdx, 1);
        } else if (rule.state === "The character is sitting") {
          const standIdx = activeStates.indexOf("The character is standing up, not sitting");
          if (standIdx > -1) activeStates.splice(standIdx, 1);
        }
        
        if (!activeStates.includes(rule.state)) {
          activeStates.push(rule.state);
        }
      }
      
      if (rule.negations) {
        const matchesNegation = rule.negations.some(rx => rx.test(textToSearch));
        if (matchesNegation) {
          const idx = activeStates.indexOf(rule.state);
          if (idx > -1) activeStates.splice(idx, 1);
        }
      }
    });

    const updatedScene = { ...scene };
    if (activeStates.length > 0) {
      const stateSuffix = `, ${activeStates.join(', ')}`;
      // Append states inside the prompt text gracefully
      if (!updatedScene.visual_generation_prompt.includes(stateSuffix)) {
        updatedScene.visual_generation_prompt += stateSuffix;
      }
    }
    return updatedScene;
  });
}

// Render Timeline cards to UI
function renderTimeline(rawScenes) {
  const scenes = analyzeProgressiveStates(rawScenes);
  STATE.campaignScenes = scenes;
  DOM.sceneCounter.textContent = `${scenes.length} Scenes Ready`;
  saveApplicationState();

  if (scenes.length === 0) {
    DOM.timelineContainer.innerHTML = '';
    DOM.timelinePlaceholder.classList.remove('hidden');
    return;
  }

  DOM.timelinePlaceholder.classList.add('hidden');
  DOM.timelineContainer.innerHTML = '';

  scenes.forEach((scene, index) => {
    const card = document.createElement('div');
    card.className = "p-5 rounded-lg bg-cyber-lightgray/40 border border-cyber-border/50 hover:border-cyber-accent/40 transition-all duration-200 space-y-4";
    
    // Build active links list for Copy Prompt Bundle and replace inline placeholders
    let resolvedPrompt = scene.visual_generation_prompt;
    if (STATE.CHARACTER_SHEET_URL) {
      resolvedPrompt = resolvedPrompt.replace(/\[?Anchored Character Sheet\]?/gi, STATE.CHARACTER_SHEET_URL)
                                     .replace(/\[?CHARACTER_SHEET\]?/g, STATE.CHARACTER_SHEET_URL);
    }
    if (STATE.SET_SHEET_URL) {
      resolvedPrompt = resolvedPrompt.replace(/\[?Anchored Set Sheet\]?/gi, STATE.SET_SHEET_URL)
                                     .replace(/\[?SET_SHEET\]?/g, STATE.SET_SHEET_URL);
    }
    if (STATE.PRODUCT_SHEET_URL) {
      resolvedPrompt = resolvedPrompt.replace(/\[?Anchored Product Sheet\]?/gi, STATE.PRODUCT_SHEET_URL)
                                     .replace(/\[?PRODUCT_SHEET\]?/g, STATE.PRODUCT_SHEET_URL);
    }

    const linksBundle = [];
    if (STATE.CHARACTER_SHEET_URL) linksBundle.push(`[Character URL: ${STATE.CHARACTER_SHEET_URL}]`);
    if (STATE.SET_SHEET_URL) linksBundle.push(`[Set URL: ${STATE.SET_SHEET_URL}]`);
    if (STATE.PRODUCT_SHEET_URL) linksBundle.push(`[Product URL: ${STATE.PRODUCT_SHEET_URL}]`);
    
    const bundleText = `${resolvedPrompt}\n\nASSETS:\n${linksBundle.join('\n')}`;

    card.innerHTML = `
      <div class="flex items-center justify-between border-b border-cyber-border/40 pb-2">
        <div class="flex items-center gap-2">
          <span class="text-xs font-mono bg-cyber-accent/20 text-cyber-accent px-2 py-0.5 rounded">${scene.scene_id.toUpperCase()}</span>
          <span class="text-[10px] font-mono text-slate-400">${scene.scene_type}</span>
        </div>
        <button class="copy-bundle-btn text-[10px] font-mono bg-cyber-black hover:bg-cyber-lightgray border border-cyber-border text-slate-300 hover:text-white px-2.5 py-1 rounded transition-all flex items-center gap-1">
          <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/></svg>
          <span>Copy Prompt Bundle</span>
        </button>
      </div>

      <div class="space-y-2 text-xs">
        <div>
          <span class="block text-[10px] font-mono text-cyber-neonBlue uppercase tracking-wider">Visual generation prompt</span>
          <p class="text-slate-200 font-mono bg-cyber-black/40 p-2 rounded mt-1 border border-cyber-border/20">${scene.visual_generation_prompt}</p>
        </div>
        <div>
          <span class="block text-[10px] font-mono text-cyber-neonPink uppercase tracking-wider">Voiceover narration</span>
          <p class="text-slate-300 italic p-1 mt-0.5">"${scene.voiceover_script}"</p>
        </div>
        <div>
          <span class="block text-[10px] font-mono text-slate-500 uppercase tracking-wider">Editor notes</span>
          <p class="text-slate-400 mt-0.5">${scene.editor_notes}</p>
        </div>
      </div>
    `;

    // Event listener for copying the prompt bundle
    card.querySelector('.copy-bundle-btn').addEventListener('click', () => {
      copyToClipboard(bundleText, `Scene ${index + 1} Prompt Bundle Copied!`);
    });

    DOM.timelineContainer.appendChild(card);
  });
}

// Export Campaign file JSON utility
function exportCampaignJSON() {
  if (STATE.campaignScenes.length === 0) {
    showToast('Timeline is empty. Compile before exporting.');
    return;
  }

  const exportObj = {
    project: "IN-NO-V8 CLICKBAIT CAMPAIGN",
    compiledAt: new Date().toISOString(),
    assets: {
      character_sheet: STATE.CHARACTER_SHEET_URL,
      set_sheet: STATE.SET_SHEET_URL,
      product_sheet: STATE.PRODUCT_SHEET_URL
    },
    scenes: STATE.campaignScenes
  };

  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportObj, null, 2));
  const downloadAnchor = document.createElement('a');
  downloadAnchor.setAttribute("href", dataStr);
  downloadAnchor.setAttribute("download", `clickbait_campaign_${Date.now()}.json`);
  document.body.appendChild(downloadAnchor);
  downloadAnchor.click();
  downloadAnchor.remove();
  showToast('Campaign JSON file exported successfully.');

  // Push to Supabase if configured
  saveCampaignToSupabase(exportObj);
}

// Export Master Script (ElevenLabs format)
function exportMasterScript() {
  if (STATE.campaignScenes.length === 0) {
    showToast('Timeline is empty. Compile before exporting.');
    return;
  }

  // Extract dialogue lines and separate with three hyphens for speech pause
  const scriptText = STATE.campaignScenes
    .map(scene => scene.voiceover_script || '')
    .filter(line => line.trim() !== '')
    .join('\n\n---\n\n');

  // Trigger file download
  const dataStr = "data:text/plain;charset=utf-8," + encodeURIComponent(scriptText);
  const downloadAnchor = document.createElement('a');
  downloadAnchor.setAttribute("href", dataStr);
  downloadAnchor.setAttribute("download", `campaign_master_voiceover.txt`);
  document.body.appendChild(downloadAnchor);
  downloadAnchor.click();
  downloadAnchor.remove();

  // Also copy to clipboard as convenience
  navigator.clipboard.writeText(scriptText).then(() => {
    showToast('ElevenLabs script downloaded & copied to clipboard!');
  }).catch(() => {
    showToast('ElevenLabs script exported successfully.');
  });
}

// Initialize on Load
window.addEventListener('DOMContentLoaded', init);

// -------------------------------------------------------------
// SUPABASE SECURE HOOK (DISABLED BY DEFAULT)
// -------------------------------------------------------------
/*
import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = 'https://your-project.supabase.co'
const SUPABASE_ANON_KEY = 'your-anon-key'
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

async function saveCampaignToSupabase(campaignData) {
  try {
    const { data, error } = await supabase
      .from('clickbait_campaigns')
      .insert([
        { 
          project_payload: campaignData,
          created_at: new Date()
        }
      ])
    if (error) throw error;
    console.log("Supabase payload saved:", data);
  } catch (error) {
    console.error("Supabase Push Error:", error);
  }
}
*/
function saveCampaignToSupabase(campaignData) {
  // Idle skeleton fallback
  console.log("Supabase Secure Hook is currently disabled. Serverless local mode active.");
}

// LocalStorage State Serialization
function saveApplicationState() {
  const appState = {
    CHARACTER_SHEET_URL: STATE.CHARACTER_SHEET_URL,
    SET_SHEET_URL: STATE.SET_SHEET_URL,
    PRODUCT_SHEET_URL: STATE.PRODUCT_SHEET_URL,
    campaignScenes: STATE.campaignScenes,
    notionBriefText: DOM.notionBriefInput ? DOM.notionBriefInput.value : '',
    charMode: STATE.charMode,
    envMode: STATE.envMode,
    prodMode: STATE.prodMode,
    charRefinement: DOM.charRefinement ? DOM.charRefinement.value : '',
    envRefinement: DOM.envRefinement ? DOM.envRefinement.value : '',
    prodRefinement: DOM.prodRefinement ? DOM.prodRefinement.value : '',
    outputLayout: DOM.outputLayoutSelect ? DOM.outputLayoutSelect.value : 'horizontal'
  };
  localStorage.setItem('clickbait_app_state', JSON.stringify(appState));
}

// LocalStorage State Restoration
function restoreApplicationState() {
  try {
    const stored = localStorage.getItem('clickbait_app_state');
    if (!stored) return;
    const appState = JSON.parse(stored);
    
    // Restore text inputs
    if (DOM.notionBriefInput && appState.notionBriefText) {
      DOM.notionBriefInput.value = appState.notionBriefText;
    }
    if (DOM.charRefinement && appState.charRefinement) {
      DOM.charRefinement.value = appState.charRefinement;
    }
    if (DOM.envRefinement && appState.envRefinement) {
      DOM.envRefinement.value = appState.envRefinement;
    }
    if (DOM.prodRefinement && appState.prodRefinement) {
      DOM.prodRefinement.value = appState.prodRefinement;
    }
    if (DOM.outputLayoutSelect && appState.outputLayout) {
      DOM.outputLayoutSelect.value = appState.outputLayout;
    }

    // Restore modes and programmatically simulate toggle clicks to update layouts and states
    if (appState.charMode) {
      STATE.charMode = appState.charMode;
      const btn = Array.from(DOM.charToggles).find(b => b.getAttribute('data-toggle-mode') === appState.charMode);
      if (btn) btn.click();
    }
    if (appState.envMode) {
      STATE.envMode = appState.envMode;
      const btn = Array.from(DOM.envToggles).find(b => b.getAttribute('data-toggle-mode') === appState.envMode);
      if (btn) btn.click();
    }
    if (appState.prodMode) {
      STATE.prodMode = appState.prodMode;
      const btn = Array.from(DOM.prodToggles).find(b => b.getAttribute('data-toggle-mode') === appState.prodMode);
      if (btn) btn.click();
    }

    // Restore sheet reference URLs
    if (appState.CHARACTER_SHEET_URL) {
      STATE.CHARACTER_SHEET_URL = appState.CHARACTER_SHEET_URL;
      mountCharacterImage(appState.CHARACTER_SHEET_URL);
    }
    if (appState.SET_SHEET_URL) {
      STATE.SET_SHEET_URL = appState.SET_SHEET_URL;
      mountEnvironmentImage(appState.SET_SHEET_URL);
    }
    if (appState.PRODUCT_SHEET_URL) {
      STATE.PRODUCT_SHEET_URL = appState.PRODUCT_SHEET_URL;
      mountProductImage(appState.PRODUCT_SHEET_URL);
    }

    // Restore campaign scenes and compile timeline
    if (appState.campaignScenes && appState.campaignScenes.length > 0) {
      STATE.campaignScenes = appState.campaignScenes;
      renderTimeline(appState.campaignScenes);
    }
  } catch (e) {
    console.error("Failed to restore app state from localStorage:", e);
  }
}
