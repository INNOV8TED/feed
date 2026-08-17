// --- TEMPLATE DEFINITIONS FOR CLIENT DYNAMIC COMPILER ---
        const templateMap = {
            "Studio Pulse Board": `
                <div class="solari-container">
                    <a href="https://feed.in-no-v8.com" target="_blank" class="solari-media-link">
                        <div class="solari-media-window" id="mediaContainer">
                            <div class="solari-media-overlay">Live Capture</div>
                            <div class="solari-media-slot">
                                <div class="solari-reel" id="solariReel">
                                    <img src="/sample.png" alt="Reel Start">
                                </div>
                            </div>
                        </div>
                    </a>
                    <div class="solari-board-side">
                        <div class="solari-board-header">◈ IN-NO-V8 // CREATIVE ARRIVALS</div>
                        <div class="solari-flap-grid" id="solariFlapGrid"></div>
                        <div class="solari-sound-toggle" onclick="toggleMuteSolari()">
                            <svg viewBox="0 0 24 24" id="speakerIcon">
                                <path d="M14,3.23V5.29C16.89,6.15 19,8.83 19,12C19,15.17 16.89,17.85 14,18.71V20.77C18,19.86 21,16.28 21,12C21,7.72 18,4.14 14,3.23M16.5,12C16.5,10.23 15.5,8.71 14,7.97V16.02C15.5,15.29 16.5,13.77 16.5,12M3,9V15H7L12,20V4L7,9H3Z" />
                            </svg>
                        </div>
                    </div>
                </div>
            `,
            "Vault Map & Gallery": `
                <div class="vault-panel-wrapper" style="width: 100%; height: 100%; position: relative; background: #000;">
                    <style>
                        .gallery-toggle-bar {
                            position: absolute;
                            top: 12px;
                            left: 50%;
                            transform: translateX(-50%);
                            z-index: 1000;
                            display: flex;
                            background: rgba(4, 5, 8, 0.85);
                            border: 1px solid rgba(0, 255, 170, 0.25);
                            border-radius: 20px;
                            padding: 2px;
                            backdrop-filter: blur(8px);
                            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.8), 0 0 10px rgba(0, 255, 170, 0.1);
                        }

                        .gallery-toggle-btn {
                            background: transparent;
                            border: none;
                            color: rgba(255, 255, 255, 0.55);
                            font-family: 'Outfit', sans-serif;
                            font-size: 0.7rem;
                            font-weight: 800;
                            padding: 5px 15px;
                            border-radius: 18px;
                            cursor: pointer;
                            text-transform: uppercase;
                            letter-spacing: 1px;
                            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
                        }

                        .gallery-toggle-btn.active {
                            background: var(--accent-green);
                            color: #000;
                            box-shadow: 0 0 12px rgba(0, 255, 170, 0.5);
                            text-shadow: none;
                        }

                        .gallery-toggle-btn:hover:not(.active) {
                            color: var(--accent-green);
                            background: rgba(0, 255, 170, 0.05);
                        }

                        .gallery-hud-overlay {
                            position: absolute;
                            bottom: 12px;
                            left: 12px;
                            right: 12px;
                            display: flex;
                            justify-content: space-between;
                            align-items: flex-end;
                            pointer-events: none;
                            z-index: 10;
                        }

                        .gallery-meta-left {
                            display: flex;
                            flex-direction: column;
                            gap: 6px;
                            background: rgba(4, 6, 10, 0.88);
                            border: 1px solid rgba(0, 255, 170, 0.2);
                            border-radius: 6px;
                            padding: 8px 12px;
                            max-width: 65%;
                            backdrop-filter: blur(8px);
                            pointer-events: auto;
                            box-shadow: 0 10px 30px rgba(0,0,0,0.8);
                        }

                        .gallery-meta-right {
                            display: flex;
                            flex-direction: column;
                            align-items: flex-end;
                            gap: 8px;
                            pointer-events: auto;
                        }

                        .gallery-badge {
                            background: rgba(0, 255, 170, 0.06);
                            border: 1px solid rgba(0, 255, 170, 0.25);
                            color: var(--accent-green);
                            font-size: 8px;
                            padding: 2px 6px;
                            border-radius: 3px;
                            text-transform: uppercase;
                            font-family: 'JetBrains Mono', monospace;
                            font-weight: 800;
                            letter-spacing: 0.5px;
                        }

                        .gallery-score-pill {
                            background: rgba(4, 6, 10, 0.88);
                            border: 1px solid var(--accent-cyan);
                            border-radius: 6px;
                            padding: 5px 10px;
                            font-family: 'JetBrains Mono', monospace;
                            font-size: 0.65rem;
                            color: var(--accent-cyan);
                            backdrop-filter: blur(8px);
                            display: flex;
                            align-items: center;
                            gap: 6px;
                            box-shadow: 0 10px 30px rgba(0,0,0,0.8);
                        }

                        .gallery-controls-hud {
                            display: flex;
                            gap: 6px;
                            background: rgba(4, 6, 10, 0.88);
                            border: 1px solid rgba(255, 255, 255, 0.08);
                            border-radius: 6px;
                            padding: 3px;
                            backdrop-filter: blur(8px);
                            box-shadow: 0 10px 30px rgba(0,0,0,0.8);
                        }

                        .gallery-hud-btn {
                            background: transparent;
                            border: none;
                            color: rgba(255, 255, 255, 0.6);
                            cursor: pointer;
                            transition: all 0.2s;
                            padding: 4px 8px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            border-radius: 4px;
                        }

                        .gallery-hud-btn:hover {
                            color: var(--accent-cyan);
                            background: rgba(0, 255, 255, 0.05);
                        }

                        .gallery-hud-btn.active {
                            color: var(--accent-green);
                        }

                        /* Smooth fade transition */
                        #gallery-media-slot {
                            transition: opacity 0.4s ease-in-out;
                            opacity: 1;
                            width: 100%;
                            height: 100%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            position: relative;
                        }

                        #gallery-media-slot.loading {
                            opacity: 0.1;
                        }
                    </style>

                    <div class="gallery-toggle-bar">
                        <button class="gallery-toggle-btn" id="btn-vault-map" onclick="switchVaultView('map')">◈ Live Map</button>
                        <button class="gallery-toggle-btn active" id="btn-vault-gallery" onclick="switchVaultView('gallery')">◈ Vault Gallery</button>
                    </div>

                    <!-- Map View container -->
                    <div id="vault-map-container" style="width: 100%; height: 100%; display: none; overflow: hidden;">
                        <iframe class="iframe-container" src="/vault/vault_map.html" scrolling="no" style="width: 100%; height: 100%; border: none;"></iframe>
                    </div>

                    <!-- Gallery View container -->
                    <div id="vault-gallery-container" style="width: 100%; height: 100%; display: block; background: #020202; overflow: hidden; position: relative;">
                        <div id="gallery-media-slot">
                            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--accent-green); letter-spacing: 2px;">◈ INGESTING VAULT SEED DATABASES... ◈</div>
                        </div>

                        <!-- Cyber HUD overlay elements -->
                        <div class="gallery-hud-overlay">
                            <div class="gallery-meta-left">
                                <span id="gallery-media-filename" style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #ffffff; letter-spacing: 0.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">shards.json</span>
                                <div id="gallery-media-tags" style="display: flex; flex-wrap: wrap; gap: 4px;"></div>
                            </div>

                            <div class="gallery-meta-right">
                                <div class="gallery-score-pill">
                                    <span style="color: rgba(255,255,255,0.4); font-size: 8px; letter-spacing: 1px;">AESTHETIC</span>
                                    <span id="gallery-media-score" style="font-weight: 800; font-size: 0.75rem; color: #fff; text-shadow: 0 0 8px var(--accent-cyan);">8/10</span>
                                </div>

                                <div class="gallery-controls-hud">
                                    <button class="gallery-hud-btn" onclick="prevVaultMedia()" title="Previous Shard">
                                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M15.41,16.58L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.58Z"/></svg>
                                    </button>
                                    <button class="gallery-hud-btn active" id="btn-gallery-play" onclick="toggleVaultAutoplay()" title="Toggle Autoplay Loop">
                                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" id="galleryPlayIcon"><path d="M12,2C6.48,2 2,6.48 2,12C2,17.52 6.48,22 12,22C17.52,22 22,17.52 22,12C22,6.48 17.52,2 12,2M11,16H9V8H11V16M15,16H13V8H15V16Z"/></svg>
                                    </button>
                                    <button class="gallery-hud-btn" onclick="nextVaultMedia()" title="Next Shard">
                                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z"/></svg>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `,
            "Live Audio Streaming HUD": `
                <div class="music-hud">
                    <div class="music-visualizer-box">
                        <canvas id="visualizer"></canvas>
                        <div class="visualizer-overlay">FREQUENCY DETECTOR // ANALOG AUDIO OSCILLOSCOPE</div>
                    </div>
                    <div class="track-metadata">
                        <div class="track-details">
                            <span class="track-title" id="player-track-name">NO TRACK PLAYING</span>
                            <span class="track-desc" id="player-track-desc">INITIALIZING BROADCAST STREAM...</span>
                        </div>
                    </div>
                    <div class="playback-progress">
                        <span id="player-time-current">0:00</span>
                        <div class="progress-bar-container" onclick="scrubAudio(event)">
                            <div class="progress-bar-fill" id="player-progress-fill"></div>
                        </div>
                        <span id="player-time-total">0:00</span>
                    </div>
                    <div class="media-button-row">
                        <div class="control-btns">
                            <button class="music-btn" onclick="skipAudioTrack(-1)">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M6,18V6H8V18H6M9.5,12L18,6V18L9.5,12Z"/></svg>
                            </button>
                            <button class="music-btn music-btn-play" onclick="togglePlayAudio()">
                                <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" id="playIconSvg"><path d="M8,5.14V19.14L19,12.14L8,5.14Z"/></svg>
                            </button>
                            <button class="music-btn" onclick="skipAudioTrack(1)">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M4,18V6L12.5,12L4,18M14,18V6H16V18H14Z"/></svg>
                            </button>
                            <button class="music-btn" id="loopBtn" onclick="toggleLoopAudio()">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M17,17H7V14L3,18L7,22V19H19V13H17V17M7,7H17V10L21,6L17,2V5H5V11H7V7Z"/></svg>
                            </button>
                        </div>
                        <div class="volume-box">
                            <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="color: rgba(255,255,255,0.4);"><path d="M14,3.23V5.29C16.89,6.15 19,8.83 19,12C19,15.17 16.89,17.85 14,18.71V20.77C18,19.86 21,16.28 21,12C21,7.72 18,4.14 14,3.23M16.5,12C16.5,10.23 15.5,8.71 14,7.97V16.02C15.5,15.29 16.5,13.77 16.5,12M3,9V15H7L12,20V4L7,9H3Z"/></svg>
                            <input type="range" class="volume-slider" min="0" max="1" step="0.05" value="0.7" oninput="setAudioVolume(this.value)">
                        </div>
                    </div>
                </div>
            `,
            "Labs Sandbox Viewport": `
                <div style="width: 100%; height: 100%; position: relative; overflow: hidden; background: #000;">
                    <video id="labs-video-bg" src="https://labs.in-no-v8.com/labloop.mp4" autoplay loop muted playsinline onended="this.play()" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover;"></video>
                    <canvas id="labs-matrix-canvas" style="display:none; position: absolute; top:0; left:0; width: 100%; height: 100%;"></canvas>
                </div>
            `,
            "Labs Sandbox": `
                <div style="width: 100%; height: 100%; position: relative; overflow: hidden; background: #000;">
                    <video src="https://labs.in-no-v8.com/labloop.mp4" autoplay loop muted playsinline onended="this.play()" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover;"></video>
                </div>
            `,
            "INNOV8TV": `
                <div style="width: 100%; height: 100%; display: flex; flex-direction: column; padding: 15px; box-sizing: border-box; font-family: 'Space Mono', monospace; background: rgba(5,5,5,0.6); border: 1px solid var(--border-color);">
                    <iframe src="https://in-no-v8.world/innov8tv/widget.html" style="width: 100%; height: 100%; border: none;"></iframe>
                </div>
            `,
            "Innov8 Profile Slides": `
                <div class="profile-slides-hud">
                    <div class="profile-slide-wrapper">
                        <div class="profile-slides-container" id="profile-slider">
                            <div class="profile-slide" style="background-image: url('https://in-no-v8.com/front/lanna-bg-bw.jpg');">
                                <div class="profile-slide-content">
                                    <div class="profile-slide-tag">LANNA</div>
                                    <div class="profile-slide-title">Lanna Whispers</div>
                                    <div class="profile-slide-desc">Cinematic short film project.</div>
                                    <button class="profile-slide-btn" onclick="window.open('https://www.lannawhispers.com', '_blank')">VIEW PROJECT ↗</button>
                                </div>
                            </div>
                            <div class="profile-slide" style="background-image: url('https://in-no-v8.com/front/port-poster.jpg');">
                                <div class="profile-slide-content">
                                    <div class="profile-slide-tag">CINEMATIC</div>
                                    <div class="profile-slide-title">My Portfolio</div>
                                    <div class="profile-slide-desc">A collection of cinematic works.</div>
                                    <button class="profile-slide-btn" onclick="window.open('https://in-no-v8.com/my-portfolio/', '_blank')">VIEW PORTFOLIO ↗</button>
                                </div>
                            </div>
                            <div class="profile-slide" style="background-image: url('https://in-no-v8.com/front/muay-thai-bg.jpg');">
                                <div class="profile-slide-content">
                                    <div class="profile-slide-tag">VIOLENCE</div>
                                    <div class="profile-slide-title">Muay Thai</div>
                                    <div class="profile-slide-desc">Crispy Violence Instagram.</div>
                                    <button class="profile-slide-btn" onclick="window.open('https://www.instagram.com/crispy.violence', '_blank')">VIEW INSTAGRAM ↗</button>
                                </div>
                            </div>
                            <div class="profile-slide" style="background-image: url('https://in-no-v8.com/front/blue-poster.jpg');">
                                <div class="profile-slide-content">
                                    <div class="profile-slide-tag">SOUNDSCAPE</div>
                                    <div class="profile-slide-title">Blue Chromatic Triangle</div>
                                    <div class="profile-slide-desc">Audio streamer profile.</div>
                                    <button class="profile-slide-btn" onclick="window.open('https://in-no-v8.com/bluechromatictriangle/', '_blank')">LISTEN NOW ↗</button>
                                </div>
                            </div>
                            <div class="profile-slide" style="background-image: url('https://in-no-v8.com/wp-content/uploads/2020/08/facegrow.gif');">
                                <div class="profile-slide-content">
                                    <div class="profile-slide-tag">CREATIVE</div>
                                    <div class="profile-slide-title">About Stephen</div>
                                    <div class="profile-slide-desc">Creative professional profile.</div>
                                    <button class="profile-slide-btn" onclick="window.open('https://in-no-v8.com/about/', '_blank')">READ MORE ↗</button>
                                </div>
                            </div>
                            <div class="profile-slide" style="background-image: url('https://in-no-v8.com/front/hero-poster.jpg');">
                                <div class="profile-slide-content">
                                    <div class="profile-slide-tag">EXPERTISE</div>
                                    <div class="profile-slide-title">Motion Design</div>
                                    <div class="profile-slide-desc">Video work and showreels.</div>
                                    <button class="profile-slide-btn" onclick="window.open('https://in-no-v8.com/video-work-and-showreels/', '_blank')">VIEW REELS ↗</button>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="profile-slides-nav" id="profile-dots"></div>
                </div>
            `
        };

        const fallbackTemplate = `
            <div style="width:100%; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:10px; padding:20px; font-family:'JetBrains Mono', monospace; font-size:0.75rem; color:rgba(255,255,255,0.4);">
                <div style="color: var(--accent-cyan);">◈ CUSTOM CONFIGURED PANEL ◈</div>
                <div style="font-size:0.65rem; color:#888; text-transform:uppercase;">READY FOR CUSTOM COMPONENT INGESTION</div>
            </div>
        `;

        // --- INDUSTRIAL AUDIO ENGINE (CLACKING HARDWARE SHIMS) ---
        let neuralSynced = false;
        const solariClackSound = new Audio('/vault/flap.mp3');
        solariClackSound.preload = 'auto';

        function playSolariClack() {
            if (!neuralSynced || solariClackSound.muted) return;
            solariClackSound.currentTime = 0;
            solariClackSound.play().catch(e => console.warn("Clack seek skip. Hardware occupied."));
        }

        function activateNeuralSync() {
            document.getElementById('neuralSync').style.opacity = '0';
            setTimeout(() => document.getElementById('neuralSync').style.display = 'none', 600);
            
            // Prime sound hardware buffers
            solariClackSound.volume = 0;
            solariClackSound.play().then(() => {
                solariClackSound.pause();
                solariClackSound.currentTime = 0;
                solariClackSound.volume = 1.0;
                console.log("◈ [AUDIO ENGINE] Solari hardware buffers primed.");
            });

            // Initialize visualizer context safely on user gesture
            initAudioVisualizerContext();

            neuralSynced = true;
            
            // Start components
            startSolariEngine();
            loadAudioPlaylist();
        }

        // --- GRID CONFIGURATOR POSITIONING ENGINE ---
        function initWorkspace() {
            let sections = localStorage.getItem('modular_sections');
            if (!sections) {
                const defaults = [
                    { id: "Studio Pulse Board", x: 64, y: 64, width: 698, height: 372 },
                    { id: "Vault Map & Gallery", x: 780, y: 64, width: 402, height: 372 },
                    { id: "Live Audio Streaming HUD", x: 1200, y: 64, width: 594, height: 372 },
                    { id: "Labs Sandbox Viewport", x: 164, y: 460, width: 530, height: 350 },
                    { id: "Innov8 Profile Slides", x: 710, y: 460, width: 714, height: 350 },
                    { id: "INNOV8TV", x: 1444, y: 460, width: 350, height: 350 }
                ];
                localStorage.setItem('modular_sections', JSON.stringify(defaults));
                sections = JSON.stringify(defaults);
            }
            renderWorkspace();
        }

        function renderWorkspace() {
            const desktop = $('#desktop');
            desktop.empty();
            
            const sections = JSON.parse(localStorage.getItem('modular_sections')) || [];
            $('#widget-counter').text(sections.length);
            
            const urlMap = {
                "Studio Pulse Board": "https://feed.in-no-v8.com/",
                "Vault Map & Gallery": "https://in-no-v8.world/vault/",
                "Live Audio Streaming HUD": "https://www.bluechromatictriangle.com/",
                "Labs Sandbox Viewport": "https://labs.in-no-v8.com/",
                "Innov8 Profile Slides": "https://in-no-v8.com/",
                "INNOV8TV": "https://in-no-v8.world/innov8tv/"
            };

            sections.forEach(section => {
                const idSafe = section.id.replace(/\s+/g, '-');
                const contentHtml = templateMap[section.id] || fallbackTemplate;
                const dedicatedUrl = urlMap[section.id];
                
                const titleHtml = dedicatedUrl 
                    ? `<a href="${dedicatedUrl}" target="_blank" class="panel-title-link" title="Open Dedicated Page">${section.id} <span style="font-size: 0.65rem; opacity: 0.6; margin-left: 4px;">[LAUNCH_OUT ->]</span></a>`
                    : section.id;
                
                const sectionClass = dedicatedUrl ? "section external-portal" : "section";
                
                const sectionHtml = `
                    <div id="${idSafe}" 
                         class="${sectionClass}" 
                         data-id="${section.id}"
                         style="left: ${section.x}px; top: ${section.y}px; width: ${section.width}px; height: ${section.height}px;">
                         
                         <!-- Custom drag handle header -->
                         <div class="panel-header">
                             <div class="panel-title">${titleHtml}</div>
                             <div class="panel-drag-pattern"></div>
                             <div class="panel-meta">
                                 <div class="panel-bounds" ${section.id === 'INNOV8TV' ? 'style="display: none;"' : ''}>
                                     [X: <span class="bx">${section.x}</span>, Y: <span class="by">${section.y}</span>, W: <span class="bw">${section.width}</span>, H: <span class="bh">${section.height}</span>]
                                 </div>
                                 <button class="panel-fullscreen" onclick="toggleFullscreen('${idSafe}')" title="Toggle Fullscreen">⛶</button>
                                 <button class="panel-close" onclick="deleteModule('${section.id}')">×</button>
                             </div>
                         </div>

                         <!-- Content body -->
                         <div class="panel-content">
                             ${contentHtml}
                         </div>
                    </div>
                `;
                desktop.append(sectionHtml);
            });
            
            bindGridControls();
            
            // Re-render panels if already running
            if (neuralSynced) {
                const audioHUD = sections.find(s => s.id === "Live Audio Streaming HUD");
                if (audioHUD) {
                    initAudioVisualizerContext();
                    updatePlayPauseState(!audioInstance.paused && audioInstance.src);
                }
                const solariHUD = sections.find(s => s.id === "Studio Pulse Board");
                if (solariHUD) {
                    buildSolariFlaps();
                }
            }
            
            // Initial scale for all lab iframes
            $('.section').each(function() {
                scaleLabsIframe($(this), {width: $(this).width(), height: $(this).height()});
            });
        }

        function scaleLabsIframe(uiElement, uiSize) {
            const iframe = uiElement.find('.labs-iframe-scaler');
            if (iframe.length) {
                const pw = uiSize.width;
                const ph = uiSize.height - 42; // subtract header
                const scaleX = pw / 1920;
                const scaleY = ph / 1080;
                const scale = Math.max(scaleX, scaleY);
                iframe.css('transform', `scale(${scale})`);
            }
        }

        function bindGridControls() {
            if (window.innerWidth <= 768) {
                destroyGridControls();
                return;
            }

            $('.section').off('mousedown.bringToFront').on('mousedown.bringToFront', function() {
                if (!$(this).hasClass('fullscreen')) {
                    const maxZ = Math.max.apply(null, $.map($('.section'), function(e) {
                        return parseInt($(e).css('z-index')) || 100;
                    }));
                    $(this).css('z-index', maxZ + 1);
                }
            });

            $('.section').each(function() {
                const el = $(this);
                
                if (!el.data('ui-draggable') && !el.hasClass('ui-draggable')) {
                    el.draggable({
                        handle: '.panel-header',
                        grid: [12, 12], // snapping matches grid dots
                        containment: '#desktop',
                        stack: '.section',
                        stop: function(event, ui) {
                            const el = $(this);
                            const id = el.data('id');
                            const x = ui.position.left;
                            const y = ui.position.top;
                            
                            el.find('.bx').text(x);
                            el.find('.by').text(y);

                            saveCoordinates(id, { x, y });
                        }
                    });
                } else {
                    try { el.draggable('enable'); } catch(e) {}
                }

                if (!el.data('ui-resizable') && !el.hasClass('ui-resizable')) {
                    el.resizable({
                        grid: [12, 12],
                        handles: 'all',
                        resize: function(event, ui) {
                            const iframe = $(this).find('iframe')[0];
                            if (iframe && iframe.contentWindow) {
                                try {
                                    iframe.contentWindow.dispatchEvent(new Event('resize'));
                                } catch (e) {}
                            }
                            const canvas = $(this).find('canvas')[0];
                            if (canvas) {
                                canvas.width = canvas.offsetWidth;
                                canvas.height = canvas.offsetHeight;
                            }
                        },
                        stop: function(event, ui) {
                            const el = $(this);
                            const id = el.data('id');
                            const width = ui.size.width;
                            const height = ui.size.height;
                            
                            el.find('.bw').text(width);
                            el.find('.bh').text(height);

                            saveCoordinates(id, { width, height });

                            const iframe = el.find('iframe')[0];
                            if (iframe && iframe.contentWindow) {
                                try {
                                    iframe.contentWindow.dispatchEvent(new Event('resize'));
                                } catch (e) {}
                            }
                            const canvas = el.find('canvas')[0];
                            if (canvas) {
                                canvas.width = canvas.offsetWidth;
                                canvas.height = canvas.offsetHeight;
                            }
                        }
                    });
                } else {
                    try { el.resizable('enable'); } catch(e) {}
                }
            });
        }

        function destroyGridControls() {
            $('.section').each(function() {
                const el = $(this);
                if (el.data('ui-draggable') || el.hasClass('ui-draggable')) {
                    try { el.draggable('destroy'); } catch(e) {}
                }
                if (el.data('ui-resizable') || el.hasClass('ui-resizable')) {
                    try { el.resizable('destroy'); } catch(e) {}
                }
            });
        }

        function saveCoordinates(id, coords) {
            const sections = JSON.parse(localStorage.getItem('modular_sections')) || [];
            const index = sections.findIndex(s => s.id === id);
            if (index !== -1) {
                if (coords.x !== undefined) sections[index].x = Number(coords.x);
                if (coords.y !== undefined) sections[index].y = Number(coords.y);
                if (coords.width !== undefined) sections[index].width = Number(coords.width);
                if (coords.height !== undefined) sections[index].height = Number(coords.height);
                localStorage.setItem('modular_sections', JSON.stringify(sections));
                console.log(`◈ Bounds persisted in localStorage for panel "${id}": [X: ${sections[index].x}, Y: ${sections[index].y}, W: ${sections[index].width}, H: ${sections[index].height}]`);
            }
        }

        function toggleFullscreen(idSafe) {
            const el = $(document.getElementById(idSafe));
            if (!el.length) return;

            if (el.hasClass('fullscreen')) {
                el.removeClass('fullscreen');
                el.css({
                    position: 'absolute',
                    top: el.data('fs-top'),
                    left: el.data('fs-left'),
                    width: el.data('fs-width'),
                    height: el.data('fs-height'),
                    zIndex: el.data('fs-zindex') || 100,
                    transition: 'none'
                });
                
                setTimeout(() => el.css('transition', ''), 50);

                el.find('.panel-fullscreen').text('⛶');
                el.draggable('enable');
                el.resizable('enable');
            } else {
                el.data('fs-top', el.css('top'));
                el.data('fs-left', el.css('left'));
                el.data('fs-width', el.css('width'));
                el.data('fs-height', el.css('height'));
                el.data('fs-zindex', el.css('z-index'));

                el.addClass('fullscreen');
                
                const maxZ = Math.max.apply(null, $.map($('.section'), function(e) {
                    return parseInt($(e).css('z-index')) || 100;
                }));
                
                el.css({
                    position: 'fixed',
                    top: '20px',
                    left: '20px',
                    width: 'calc(100vw - 40px)',
                    height: 'calc(100vh - 40px)',
                    zIndex: maxZ + 100,
                    transition: 'all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1)'
                });

                el.find('.panel-fullscreen').text('🗗');
                el.draggable('disable');
                el.resizable('disable');
            }

            setTimeout(() => {
                const iframe = el.find('iframe')[0];
                if (iframe && iframe.contentWindow) {
                    try { iframe.contentWindow.dispatchEvent(new Event('resize')); } catch (e) {}
                }
                const canvas = el.find('canvas')[0];
                if (canvas) {
                    canvas.width = canvas.offsetWidth;
                    canvas.height = canvas.offsetHeight;
                }
            }, 350);
        }

        function resetLayout() {
            if (confirm("Reset desktop configurator coordinates to default factory bounds?")) {
                const defaults = [
                    { id: "Studio Pulse Board", x: 64, y: 64, width: 698, height: 372 },
                    { id: "Vault Map & Gallery", x: 780, y: 64, width: 402, height: 372 },
                    { id: "Live Audio Streaming HUD", x: 1200, y: 64, width: 594, height: 372 },
                    { id: "Labs Sandbox Viewport", x: 164, y: 460, width: 530, height: 350 },
                    { id: "Innov8 Profile Slides", x: 710, y: 460, width: 714, height: 350 },
                    { id: "INNOV8TV", x: 1444, y: 460, width: 350, height: 350 }
                ];
                localStorage.setItem('modular_sections', JSON.stringify(defaults));
                stopVaultAutoplay();
                if (audioInstance) {
                    audioInstance.pause();
                }
                window.location.reload();
            }
        }

        function deleteModule(id) {
            if (confirm(`Permanently dismantle and purge module "${id}"?`)) {
                let sections = JSON.parse(localStorage.getItem('modular_sections')) || [];
                sections = sections.filter(s => s.id !== id);
                localStorage.setItem('modular_sections', JSON.stringify(sections));
                
                // CPU/Battery Optimization: Clean up global intervals when Labs Sandbox is closed
                if (id === "Labs Sandbox" || id === "Labs Sandbox Viewport") {
                    if (window.matrixInterval) clearInterval(window.matrixInterval);
                }
                
                renderWorkspace();
            }
        }

        function openAddModal() {
            const listContainer = $('#modalPresetList');
            listContainer.empty();
            
            const activeSections = JSON.parse(localStorage.getItem('modular_sections')) || [];
            const activeIds = activeSections.map(s => s.id);
            
            const urlMapLocal = {
                "Studio Pulse Board": "https://feed.in-no-v8.com/",
                "Vault Map & Gallery": "https://in-no-v8.world/vault/",
                "Live Audio Streaming HUD": "https://www.bluechromatictriangle.com/",
                "Labs Sandbox Viewport": "https://labs.in-no-v8.com/",
                "Innov8 Profile Slides": "https://in-no-v8.com/"
            };

            for (const [presetId, domain] of Object.entries(urlMapLocal)) {
                const isActive = activeIds.includes(presetId);
                const btnState = isActive ? 'disabled' : '';
                const btnText = isActive ? '◈ ACTIVE' : '+ INGEST';
                
                const itemHtml = `
                    <div class="modal-module-item">
                        <div class="modal-module-info">
                            <div class="modal-module-name">${presetId}</div>
                            <div class="modal-module-domain">${domain}</div>
                        </div>
                        <button class="modal-ingest-btn" onclick="ingestPresetModule('${presetId}')" ${btnState}>${btnText}</button>
                    </div>
                `;
                listContainer.append(itemHtml);
            }
            
            $('#addModal').css('display', 'flex').css('opacity', '1');
            $('.modal-box').css('transform', 'scale(1)');
        }

        function closeAddModal() {
            $('#addModal').css('opacity', '0');
            $('.modal-box').css('transform', 'scale(0.9)');
            setTimeout(() => $('#addModal').css('display', 'none'), 300);
        }

        function ingestPresetModule(id) {
            const sections = JSON.parse(localStorage.getItem('modular_sections')) || [];
            if (sections.some(s => s.id === id)) return;
            
            // Smart layout defaults if ingesting an originally deleted module
            const factoryDefaults = {
                "Studio Pulse Board": { x: 40, y: 100, width: 680, height: 420 },
                "Vault Map & Gallery": { x: 740, y: 100, width: 640, height: 480 },
                "Live Audio Streaming HUD": { x: 40, y: 540, width: 680, height: 320 },
                "Labs Sandbox Viewport": { x: 740, y: 600, width: 640, height: 400 },
                "Innov8 Profile Slides": { x: 1400, y: 100, width: 480, height: 650 },
                "INNOV8TV": { x: 1444, y: 460, width: 350, height: 350 }
            };
            
            const preset = factoryDefaults[id] || { 
                x: Math.round((Math.random() * 200 + 100) / 12) * 12, 
                y: Math.round((Math.random() * 200 + 100) / 12) * 12, 
                width: 480, 
                height: 360 
            };
            
            sections.push({ id: id, x: preset.x, y: preset.y, width: preset.width, height: preset.height });
            localStorage.setItem('modular_sections', JSON.stringify(sections));
            
            closeAddModal();
            renderWorkspace();
        }

        // --- MODULE 1: MECHANICAL SOLARID FLAP ENGINE ---
        // --- MODULE 1: MECHANICAL SOLARID FLAP ENGINE ---
        const CHARS = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789◈:#-.\"/(){},'!?[]@_%&".split("");
        const BOARD_SIZE = 240; // 12 rows x 20 columns
        let solariCurrentText = "".padEnd(BOARD_SIZE, " ");

        function sanitizeChar(c) {
            if (!c) return ' ';
            const u = c.toUpperCase();
            return CHARS.includes(u) ? u : ' ';
        }

        function sanitizeString(str) {
            if (!str) return '';
            return str.split('').map(sanitizeChar).join('');
        }

        function buildSolariFlaps() {
            const grid = document.getElementById('solariFlapGrid');
            if (!grid) return;
            grid.innerHTML = '';
            for (let i = 0; i < BOARD_SIZE; i++) {
                const flap = document.createElement('div');
                const row = Math.floor(i / 20);
                flap.className = 'solari-flap';
                flap.dataset.char = ' ';
                
                if (row === 0) flap.classList.add('accent-row'); 
                if (row >= 1 && row <= 3) flap.classList.add('white-row'); 
                if (row === 4) flap.classList.add('dim-row'); 
                if (row >= 6) flap.classList.add('quote-row'); 
                
                flap.innerHTML = `
                    <div class="top"><span> </span></div>
                    <div class="bottom"><span> </span></div>
                    <div class="leaf">
                        <div class="leaf-front"><span> </span></div>
                        <div class="leaf-back"><span> </span></div>
                    </div>
                `;
                grid.appendChild(flap);
            }
        }

        function animateSolariFlap(element, endChar) {
            const startChar = element.dataset.char || ' ';
            let currentIndex = CHARS.indexOf(startChar);
            if (currentIndex === -1) currentIndex = 0;
            
            const targetChar = sanitizeChar(endChar);
            const targetIndex = CHARS.indexOf(targetChar);
            
            if (element._animTimer) {
                clearTimeout(element._animTimer);
                element._animTimer = null;
            }

            if (targetIndex === -1 || currentIndex === targetIndex) {
                element.querySelector('.bottom span').innerText = targetChar;
                element.querySelector('.top span').innerText = targetChar;
                element.querySelector('.leaf-front span').innerText = targetChar;
                element.querySelector('.leaf-back span').innerText = targetChar;
                element.dataset.char = targetChar;
                element.classList.remove('flipping');
                return;
            }
            
            const animate = () => {
                const char = CHARS[currentIndex];
                const nextIndex = (currentIndex + 1) % CHARS.length;
                const nextChar = CHARS[nextIndex];

                element.querySelector('.top span').innerText = nextChar;
                element.querySelector('.bottom span').innerText = char;
                element.querySelector('.leaf-front span').innerText = char;
                element.querySelector('.leaf-back span').innerText = nextChar;

                element.classList.remove('flipping');
                void element.offsetWidth; 
                element.classList.add('flipping');

                currentIndex = nextIndex;

                element._animTimer = setTimeout(() => {
                    element.querySelector('.bottom span').innerText = nextChar;
                    element.querySelector('.leaf-front span').innerText = nextChar;
                    element.classList.remove('flipping');
                    element.dataset.char = nextChar;
                    
                    if (currentIndex !== targetIndex) {
                        element._animTimer = setTimeout(animate, 2);
                    } else {
                        element._animTimer = null;
                    }
                }, 15);
            };
            
            animate();
        }

        async function spinReel(newUrl) {
            const container = document.getElementById('mediaContainer');
            const reel = document.getElementById('solariReel');
            if (!reel || !container) return;
            
            const h = container.offsetHeight;
            
            for (let i = 0; i < 4; i++) {
                const dummy = document.createElement('img');
                dummy.src = "/vault/sample.png";
                dummy.style.height = h + 'px';
                reel.appendChild(dummy);
            }

            let targetElement;
            const isVideo = newUrl.toLowerCase().endsWith('.mp4');
            if (isVideo) {
                targetElement = document.createElement('video');
                targetElement.src = newUrl;
                targetElement.autoplay = true;
                targetElement.muted = true;
                targetElement.loop = true;
                targetElement.playsInline = true;
            } else {
                targetElement = document.createElement('img');
                targetElement.src = newUrl;
                targetElement.onerror = function() { this.onerror=null; this.src='/sample.png'; };
            }
            targetElement.style.height = h + 'px';
            reel.appendChild(targetElement);

            container.classList.add('spinning');
            const totalItems = reel.children.length;
            reel.style.transform = `translateY(-${(totalItems - 1) * h}px)`;

            setTimeout(() => {
                container.classList.remove('spinning');
                while (reel.children.length > 1) reel.removeChild(reel.firstChild);
                reel.style.transition = 'none';
                reel.style.transform = 'translateY(0)';
                void reel.offsetWidth; 
                reel.style.transition = '';
            }, 3100);
        }

        function toggleMuteSolari() {
            solariClackSound.muted = !solariClackSound.muted;
            const icon = document.getElementById('speakerIcon');
            const trigger = $('.solari-sound-toggle');
            if (solariClackSound.muted) {
                icon.innerHTML = '<path d="M12,4L9.91,6.09L12,8.18V4M14.92,10.12L17.03,8.01C15.93,7.15 14.7,6.48 13.39,6.04V8.19C13.92,8.34 14.44,8.57 14.92,8.88M16.5,12C16.5,10.23 15.5,8.71 14,7.97V16.02C15.5,15.29 16.5,13.77 16.5,12M3,9V15H7L12,20V4L7,9H3Z" />';
                trigger.css('opacity', '0.35');
            } else {
                icon.innerHTML = '<path d="M14,3.23V5.29C16.89,6.15 19,8.83 19,12C19,15.17 16.89,17.85 14,18.71V20.77C18,19.86 21,16.28 21,12C21,7.72 18,4.14 14,3.23M16.5,12C16.5,10.23 15.5,8.71 14,7.97V16.02C15.5,15.29 16.5,13.77 16.5,12M3,9V15H7L12,20V4L7,9H3Z" />';
                trigger.css('opacity', '0.9');
            }
        }

        async function updateSolariBoard(pulse) {
            if (!pulse) return;
            const COLS = 20;
            const ROWS = 12;
            let rows = new Array(ROWS).fill("".padEnd(COLS, " "));
            
            const parts = (pulse.mood_tag || "").split('|');
            const mood = sanitizeString(parts[0] || "ONLINE");
            const subLabel = sanitizeString(parts[1] || "");
            const imageUrl = parts[2] ? parts[2] : '/vault/sample.png';
            const software = sanitizeString(parts[3] || "");
            let rawQuote = parts[4] || "";
            const channel = sanitizeString(parts[5] || "");

            // Ignore raw JSON telemetry payloads in quote
            if (rawQuote.trim().startsWith('{') || rawQuote.includes('"quota"')) {
                rawQuote = subLabel || "STUDIO PULSE SYNCHRONIZED";
            }
            const cleanQuote = sanitizeString(rawQuote || subLabel || "LIVE CAPTURE");

            const projAction = sanitizeString(((pulse.project_name || "") + " " + (pulse.action_label || "")).trim());
            rows[0] = projAction.substring(0, COLS).padEnd(COLS, " ");
            
            const row1Text = channel ? `CHANNEL: ${channel}` : (subLabel || "STATUS: ONLINE");
            rows[1] = row1Text.substring(0, COLS).padEnd(COLS, " ");
            
            const row2Text = software ? `ENGINE: ${software}` : "STUDIO ENGINE: V2";
            rows[2] = row2Text.substring(0, COLS).padEnd(COLS, " ");
            
            rows[3] = "".padEnd(COLS, " ");
            rows[4] = (`MOOD: ${mood}`).substring(0, COLS).padEnd(COLS, " ");
            rows[5] = "".padEnd(COLS, " ");
            
            // Clean word wrapping for quote across rows 6 to 11
            const words = cleanQuote.split(/\s+/).filter(Boolean);
            let r = 6, currentLine = "";
            
            for (let w of words) {
                if (r >= ROWS) break;
                // If a single word is longer than COLS, chunk it
                while (w.length > COLS) {
                    const chunk = w.substring(0, COLS);
                    w = w.substring(COLS);
                    if (currentLine.length > 0) {
                        rows[r] = currentLine.trim().padEnd(COLS, " ");
                        r++;
                        currentLine = "";
                        if (r >= ROWS) break;
                    }
                    rows[r] = chunk.padEnd(COLS, " ");
                    r++;
                    if (r >= ROWS) break;
                }
                if (r >= ROWS) break;
                if (!w) continue;

                if ((currentLine + (currentLine ? " " : "") + w).length > COLS) {
                    rows[r] = currentLine.trim().padEnd(COLS, " ");
                    r++;
                    currentLine = w;
                } else {
                    currentLine += (currentLine ? " " : "") + w;
                }
            }
            if (r < ROWS && currentLine.length > 0) {
                rows[r] = currentLine.trim().padEnd(COLS, " ");
            }

            // Ensure every single row is strictly COLS characters
            for (let i = 0; i < ROWS; i++) {
                rows[i] = (rows[i] || "").substring(0, COLS).padEnd(COLS, " ");
            }

            spinReel(imageUrl);

            const formattedText = rows.join("");
            const flaps = document.querySelectorAll('.solari-flap');

            playSolariClack();

            for (let i = 0; i < BOARD_SIZE; i++) {
                if (formattedText[i] !== solariCurrentText[i]) {
                    const row = Math.floor(i / COLS);
                    const launchDelay = (row / ROWS) * 180;
                    
                    setTimeout(() => {
                        if (flaps[i]) {
                            animateSolariFlap(flaps[i], formattedText[i]);
                        }
                    }, launchDelay);
                }
            }
            solariCurrentText = formattedText;
        }

        let feedSnapshotPool = [];
        let feedSnapshotIndex = 0;

        async function startSolariEngine() {
            buildSolariFlaps();
            try {
                const res = await fetch('https://in-no-v8.world/vault/studio_heartbeat.json?t=' + Date.now());
                const data = await res.json();
                if (data && data.length > 0) {
                    feedSnapshotPool = data.slice(0, 5);
                    solariLoopCycle();
                } else {
                    updateSolariBoard({ project_name: "WORLD", action_label: "CONNECTING...", mood_tag: "OFFLINE|STANDBY|/sample.png|SYSTEM|NO FEED DATA DETECTED|0" });
                }
            } catch(e) {
                console.warn('◈ [PULSE] Local feed snapshot unavailable. Retrying in 10s.', e);
                setTimeout(startSolariEngine, 10000);
            }
        }

        function solariLoopCycle() {
            if (!feedSnapshotPool.length || !neuralSynced) return;
            
            const cycle = () => {
                if (!neuralSynced) return;
                const activePulse = feedSnapshotPool[feedSnapshotIndex];
                updateSolariBoard(activePulse);
                feedSnapshotIndex = (feedSnapshotIndex + 1) % feedSnapshotPool.length;
                setTimeout(cycle, 12000);
            };
            
            cycle();
        }

        // Supabase Real-Time client connection
        try {
            const SUPABASE_URL = "https://dzgyqrnmsnhqaiqthzok.supabase.co";
            const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR6Z3lxcm5tc25ocWFpcXRoem9rIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgyOTQwNzYsImV4cCI6MjA5Mzg3MDA3Nn0.sUWGeR3_Vd1Xm40lRoA0q1nXUjaMK_BbXXv3SBkZ6cY";
            const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
            
            supabaseClient
                .channel('public:studio_heartbeat')
                .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'studio_heartbeat' }, (payload) => {
                    const data = payload.new;
                    if (data.project_name !== '[SYSTEM_STATUS]') {
                        feedSnapshotPool.unshift(data); 
                        updateSolariBoard(data);
                    }
                })
                .subscribe();
        } catch(e) {
            console.warn("Supabase Realtime socket failed to instantiate. Static polling mode active.");
        }

        // --- MODULE 2: DUAL MODE VAULT GALLERY ENGINE ---
        let vaultInventory = [];
        let currentVaultIndex = 0;
        let vaultAutoplayInterval = null;
        let vaultAutoplayActive = true; 

        function switchVaultView(mode) {
            const mapBtn = document.getElementById('btn-vault-map');
            const galleryBtn = document.getElementById('btn-vault-gallery');
            const mapContainer = document.getElementById('vault-map-container');
            const galleryContainer = document.getElementById('vault-gallery-container');

            if (mode === 'map') {
                mapBtn.classList.add('active');
                galleryBtn.classList.remove('active');
                mapContainer.style.display = 'block';
                galleryContainer.style.display = 'none';
                stopVaultAutoplay();
            } else if (mode === 'gallery') {
                galleryBtn.classList.add('active');
                mapBtn.classList.remove('active');
                mapContainer.style.display = 'none';
                galleryContainer.style.display = 'block';
                
                if (vaultInventory.length === 0) {
                    fetchVaultInventory();
                } else {
                    if (vaultAutoplayActive) {
                        startVaultAutoplay();
                    }
                }
            }
        }

        async function fetchVaultInventory() {
            try {
                const res = await fetch('/vault/vault_inventory.json');
                vaultInventory = await res.json();
                if (vaultInventory && vaultInventory.length > 0) {
                    currentVaultIndex = Math.floor(Math.random() * vaultInventory.length);
                    displayVaultMedia(currentVaultIndex);
                    if (vaultAutoplayActive) {
                        startVaultAutoplay();
                    }
                } else {
                    document.getElementById('gallery-media-slot').innerHTML = `
                        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--accent-red); letter-spacing: 2px;">◈ NO SEED MEDIA LOADED ◈</div>
                    `;
                }
            } catch (e) {
                console.error("◈ [VAULT] Failed to load inventory:", e);
                document.getElementById('gallery-media-slot').innerHTML = `
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--accent-red); letter-spacing: 2px;">◈ DATABASE INGESTION ERROR ◈</div>
                `;
            }
        }

        function displayVaultMedia(index) {
            if (index < 0 || index >= vaultInventory.length) return;
            currentVaultIndex = index;
            const item = vaultInventory[index];
            const slot = document.getElementById('gallery-media-slot');

            slot.classList.add('loading');

            setTimeout(() => {
                slot.innerHTML = '';

                if (item.video_preview_url) {
                    const video = document.createElement('video');
                    video.src = item.video_preview_url;
                    video.autoplay = true;
                    video.loop = true;
                    video.muted = true;
                    video.playsInline = true;
                    video.style.width = '100%';
                    video.style.height = '100%';
                    video.style.objectFit = 'cover';
                    slot.appendChild(video);
                } else {
                    const img = document.createElement('img');
                    img.src = item.thumb_url;
                    img.onerror = function() { this.onerror=null; this.src='/sample.png'; };
                    img.style.width = '100%';
                    img.style.height = '100%';
                    img.style.objectFit = 'cover';
                    slot.appendChild(img);
                }

                const filename = item.image_path ? item.image_path.split('/').pop() : (item.filename ? item.filename.split('/').pop().replace('.supplemental-metadata.json', '') : 'shard.json');
                document.getElementById('gallery-media-filename').innerText = filename;

                const score = item.aesthetic_score !== undefined ? item.aesthetic_score : 8;
                document.getElementById('gallery-media-score').innerText = `${score}/10`;

                const tagsContainer = document.getElementById('gallery-media-tags');
                tagsContainer.innerHTML = '';
                if (item.vision_tags && item.vision_tags.length > 0) {
                    item.vision_tags.forEach(tag => {
                        const span = document.createElement('span');
                        span.className = 'gallery-badge';
                        span.innerText = tag.replace(/_/g, ' ');
                        tagsContainer.appendChild(span);
                    });
                } else {
                    const span = document.createElement('span');
                    span.className = 'gallery-badge';
                    span.innerText = 'RAW SEED';
                    tagsContainer.appendChild(span);
                }

                slot.classList.remove('loading');
            }, 400);
        }

        function nextVaultMedia() {
            if (vaultInventory.length === 0) return;
            const nextIndex = Math.floor(Math.random() * vaultInventory.length);
            displayVaultMedia(nextIndex);
            resetVaultAutoplayTimer();
        }

        function prevVaultMedia() {
            if (vaultInventory.length === 0) return;
            const prevIndex = Math.floor(Math.random() * vaultInventory.length);
            displayVaultMedia(prevIndex);
            resetVaultAutoplayTimer();
        }

        function startVaultAutoplay() {
            stopVaultAutoplay();
            vaultAutoplayInterval = setInterval(() => {
                nextVaultMedia();
            }, 8000);
            
            const btn = document.getElementById('btn-gallery-play');
            if (btn) btn.classList.add('active');
            
            const icon = document.getElementById('galleryPlayIcon');
            if (icon) icon.innerHTML = '<path d="M12,2C6.48,2 2,6.48 2,12C2,17.52 6.48,22 12,22C17.52,22 22,17.52 22,12C22,6.48 17.52,2 12,2M11,16H9V8H11V16M15,16H13V8H15V16Z"/>';
        }

        function stopVaultAutoplay() {
            if (vaultAutoplayInterval) {
                clearInterval(vaultAutoplayInterval);
                vaultAutoplayInterval = null;
            }
            
            const btn = document.getElementById('btn-gallery-play');
            if (btn) btn.classList.remove('active');
            
            const icon = document.getElementById('galleryPlayIcon');
            if (icon) icon.innerHTML = '<path d="M12,2C6.48,2 2,6.48 2,12C2,17.52 6.48,22 12,22C17.52,22 22,17.52 22,12C22,6.48 17.52,2 12,2M10,16.5L16,12L10,7.5V16.5Z"/>';
        }

        function toggleVaultAutoplay() {
            vaultAutoplayActive = !vaultAutoplayActive;
            if (vaultAutoplayActive) {
                startVaultAutoplay();
            } else {
                stopVaultAutoplay();
            }
        }

        function resetVaultAutoplayTimer() {
            if (vaultAutoplayActive) {
                startVaultAutoplay();
            }
        }

        // --- MODULE 3: LIVE STREAM MUSIC HUD ENGINE ---
        let playlist = [];
        let currentPlaylistIndex = -1;
        let audioInstance = new Audio();
        audioInstance.crossOrigin = "anonymous";
        let audioContextInst, audioSourceNode, audioAnalyserNode;
        let visualizerCanvas, visualizerCtx;
        let loopAudioActive = false;
        let preloadedAudio = new Audio(); // For smooth buffer priming
        let isFadingAudio = false;

        // --- BCT SIGNATURE DIGITAL SCRAMBLE TEXT EFFECT ---
        function scrambleText(element, finalValue, duration = 1200) {
            const chars = "ABCDEFGHIJKLMN0123456789//--[!]";
            let start = null;
            const step = (timestamp) => {
                if (!start) start = timestamp;
                const progress = timestamp - start;
                const iteration = Math.floor(progress / (duration / finalValue.length));
                let current = "";
                for(let i=0; i<finalValue.length; i++) {
                    if (i < iteration) current += finalValue[i];
                    else current += chars[Math.floor(Math.random() * chars.length)];
                }
                element.innerText = current;
                if (progress < duration) window.requestAnimationFrame(step);
                else element.innerText = finalValue;
            };
            window.requestAnimationFrame(step);
        }

        function loadAudioPlaylist() {
            $.getJSON('/vault/audio_inventory.json', (data) => {
                if (data && data.length > 0) {
                    playlist = data;
                    // Pick a random track to start
                    const randomIdx = Math.floor(Math.random() * playlist.length);
                    loadAudioTrack(randomIdx, false);
                }
            });
        }

        function initAudioVisualizerContext() {
            visualizerCanvas = document.getElementById('visualizer');
            if (!visualizerCanvas) return;
            visualizerCtx = visualizerCanvas.getContext('2d');
            
            visualizerCanvas.width = visualizerCanvas.offsetWidth;
            visualizerCanvas.height = visualizerCanvas.offsetHeight;

            // Trigger overlay scramble on boot
            const overlay = document.querySelector('.visualizer-overlay');
            if (overlay) scrambleText(overlay, "FREQUENCY DETECTOR // ANALOG AUDIO OSCILLOSCOPE");

            audioContextInst = new (window.AudioContext || window.webkitAudioContext)();
            audioAnalyserNode = audioContextInst.createAnalyser();
            audioAnalyserNode.fftSize = 256;

            audioSourceNode = audioContextInst.createMediaElementSource(audioInstance);
            audioSourceNode.connect(audioAnalyserNode);
            audioAnalyserNode.connect(audioContextInst.destination);

            renderFrequencyOscillations();
        }

        function loadAudioTrack(idx, autoPlay = true) {
            idx = parseInt(idx);
            if (idx < 0 || idx >= playlist.length) return;
            
            currentPlaylistIndex = idx;
            const track = playlist[idx];
            
            audioInstance.src = track.url;
            audioInstance.loop = loopAudioActive;
            
            const titleElem = document.getElementById('player-track-name');
            const descElem = document.getElementById('player-track-desc');
            if (titleElem) {
                scrambleText(titleElem, track.name.toUpperCase());
            } else {
                $('#player-track-name').text(track.name.toUpperCase());
            }
            if (descElem) {
                scrambleText(descElem, track.filename.toUpperCase());
            } else {
                $('#player-track-desc').text(track.filename);
            }
            
            // Remove tracks-select value update since it's deleted

            if (autoPlay) {
                audioInstance.play().then(() => {
                    if (audioContextInst && audioContextInst.state === 'suspended') {
                        audioContextInst.resume();
                    }
                    updatePlayPauseState(true);
                }).catch(e => console.error("Audio playback error:", e));
            } else {
                updatePlayPauseState(false);
            }
        }

        audioInstance.ontimeupdate = () => {
            const current = audioInstance.currentTime;
            const total = audioInstance.duration || 0;
            
            if (total > 0) {
                const pct = (current / total) * 100;
                $('#player-progress-fill').css('width', `${pct}%`);
                $('#player-time-current').text(formatTime(current));
                $('#player-time-total').text(formatTime(total));
                
                // Crossfade & Preload logic (Fade out last 2 seconds)
                if (!loopAudioActive && total - current <= 2.0 && !isFadingAudio) {
                    isFadingAudio = true;
                    // Preload the next track invisibly in the background
                    let targetIdx = Math.floor(Math.random() * playlist.length);
                    if (playlist.length > 1 && targetIdx === currentPlaylistIndex) {
                        targetIdx = (targetIdx + 1) % playlist.length;
                    }
                    preloadedAudio.src = playlist[targetIdx].url;
                    preloadedAudio.load();
                    
                    // Smooth volume fade out
                    $(audioInstance).animate({volume: 0}, 1900, 'linear', () => {
                        loadAudioTrack(targetIdx);
                        audioInstance.volume = 1;
                        isFadingAudio = false;
                    });
                }
            }
        };

        audioInstance.onended = () => {
            // Failsafe in case fade logic misses
            if (!loopAudioActive && !isFadingAudio) {
                skipAudioTrack(1);
            }
        };

        function togglePlayAudio() {
            if (currentPlaylistIndex === -1) {
                if (playlist.length > 0) {
                    const randomIdx = Math.floor(Math.random() * playlist.length);
                    loadAudioTrack(randomIdx);
                }
                return;
            }

            if (audioInstance.paused) {
                audioInstance.play();
                updatePlayPauseState(true);
            } else {
                audioInstance.pause();
                updatePlayPauseState(false);
            }
        }

        function updatePlayPauseState(playing) {
            const svg = document.getElementById('playIconSvg');
            if (!svg) return;
            if (playing) {
                svg.innerHTML = '<path d="M14,19H18V5H14M6,19H10V5H6V19Z"/>';
            } else {
                svg.innerHTML = '<path d="M8,5.14V19.14L19,12.14L8,5.14Z"/>';
            }
        }

        function scrubAudio(e) {
            if (!audioInstance.duration) return;
            const rect = e.currentTarget.getBoundingClientRect();
            const pct = (e.clientX - rect.left) / rect.width;
            audioInstance.currentTime = pct * audioInstance.duration;
        }

        function skipAudioTrack(dir) {
            if (playlist.length === 0) return;
            // Pick a random track instead of linear
            let targetIdx = Math.floor(Math.random() * playlist.length);
            // Ensure we don't pick the same track if there are multiple options
            if (playlist.length > 1 && targetIdx === currentPlaylistIndex) {
                targetIdx = (targetIdx + 1) % playlist.length;
            }
            loadAudioTrack(targetIdx);
        }

        function toggleLoopAudio() {
            loopAudioActive = !loopAudioActive;
            audioInstance.loop = loopAudioActive;
            const btn = $('#loopBtn');
            if (loopAudioActive) {
                btn.css('color', '#00f2ff');
                btn.css('filter', 'drop-shadow(0 0 5px #00f2ff)');
            } else {
                btn.css('color', '');
                btn.css('filter', '');
            }
        }

        function setAudioVolume(val) {
            audioInstance.volume = parseFloat(val);
        }

        function formatTime(secs) {
            const mins = Math.floor(secs / 60);
            const remaining = Math.floor(secs % 60);
            return `${mins}:${remaining.toString().padStart(2, '0')}`;
        }

        function renderFrequencyOscillations() {
            if (!visualizerCanvas || !visualizerCtx) return;
            
            const bufferLength = audioAnalyserNode.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            
            const draw = () => {
                // CPU Battery Optimization: Stop animating if canvas is removed from DOM
                if (!document.body.contains(visualizerCanvas)) return;
                
                requestAnimationFrame(draw);
                
                audioAnalyserNode.getByteFrequencyData(dataArray);
                
                const w = visualizerCanvas.width;
                const h = visualizerCanvas.height;
                
                visualizerCtx.fillStyle = 'rgba(0, 0, 0, 0.15)';
                visualizerCtx.fillRect(0, 0, w, h);
                
                const barWidth = (w / bufferLength) * 1.6;
                let barHeight;
                let x = 0;
                
                // Draw diagnostic clinical monitor gridlines
                visualizerCtx.strokeStyle = 'rgba(0, 242, 255, 0.05)';
                visualizerCtx.lineWidth = 1;
                
                // Horizontal gridlines
                for (let ly = 10; ly < h; ly += 12) {
                    visualizerCtx.beginPath();
                    visualizerCtx.moveTo(0, ly);
                    visualizerCtx.lineTo(w, ly);
                    visualizerCtx.stroke();
                }
                
                // Vertical gridlines
                for (let lx = 20; lx < w; lx += 25) {
                    visualizerCtx.beginPath();
                    visualizerCtx.moveTo(lx, 0);
                    visualizerCtx.lineTo(lx, h);
                    visualizerCtx.stroke();
                }

                for (let i = 0; i < bufferLength; i++) {
                    barHeight = dataArray[i] * 0.36;
                    
                    const grad = visualizerCtx.createLinearGradient(0, h, 0, h - barHeight);
                    grad.addColorStop(0, '#001525');
                    grad.addColorStop(0.5, '#006699');
                    grad.addColorStop(1, '#00f2ff');
                    
                    visualizerCtx.fillStyle = grad;
                    
                    visualizerCtx.shadowColor = 'rgba(0, 242, 255, 0.6)';
                    visualizerCtx.shadowBlur = 10;
                    
                    visualizerCtx.fillRect(x, h - barHeight, barWidth - 1, barHeight);
                    
                    visualizerCtx.shadowBlur = 0;
                    
                    x += barWidth + 1;
                }
            };
            
            draw();
        }

        // --- MODULE 4: LABS CONTROLLERS ---
        function switchLabsFeed(feed, btnElement) {
            const video = document.getElementById('labs-video-bg');
            const canvas = document.getElementById('labs-matrix-canvas');
            const label = document.getElementById('labs-feed-label');
            
            $(btnElement).siblings().removeClass('active');
            $(btnElement).addClass('active');
            label.innerText = `[FEED: ${feed}]`;

            if (feed === 'A-CAM') {
                canvas.style.display = 'none';
                video.style.display = 'block';
                video.src = 'https://in-no-v8.world/vault/labloopvert.mp4';
            } else if (feed === 'PROJ ZOOM') {
                canvas.style.display = 'none';
                video.style.display = 'block';
                video.src = 'https://in-no-v8.world/vault/projzoom.mp4';
            } else if (feed === 'MATRIX') {
                video.style.display = 'none';
                canvas.style.display = 'block';
                initLabsMatrixRain();
            }
        }

        window.matrixInterval = null;
        function initLabsMatrixRain() {
            const canvas = document.getElementById('labs-matrix-canvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            canvas.width = canvas.parentElement.offsetWidth;
            canvas.height = canvas.parentElement.offsetHeight;
            
            const chars = '01'.split('');
            const fontSize = 14;
            const columns = Math.floor(canvas.width / fontSize);
            const drops = [];
            for (let x = 0; x < columns; x++) drops[x] = 1;

            if (window.matrixInterval) clearInterval(window.matrixInterval);
            window.matrixInterval = setInterval(() => {
                // CPU Optimization check
                if (!document.body.contains(canvas)) {
                    clearInterval(window.matrixInterval);
                    return;
                }
                ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = 'rgba(0, 255, 170, 0.8)';
                ctx.font = fontSize + 'px "JetBrains Mono"';
                for (let i = 0; i < drops.length; i++) {
                    const text = chars[Math.floor(Math.random() * chars.length)];
                    ctx.fillText(text, i * fontSize, drops[i] * fontSize);
                    if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
                    drops[i]++;
                }
            }, 50);
        }

        function startLabsLogs() {
            setInterval(() => {
                const logsBox = document.getElementById('labs-logs-box');
                if (!logsBox) return;
                const sysTerms = ['MEM_ALLOC', 'CPU_SPIKE', 'SYS_BUS', 'NET_TRAFFIC', 'SEC_OVERRIDE', 'VAULT_SYNC'];
                const randTerm = sysTerms[Math.floor(Math.random() * sysTerms.length)];
                const val = (Math.random() * 100).toFixed(2);
                
                const line = document.createElement('div');
                line.className = 'labs-log-row';
                line.innerText = `◈ [${new Date().toISOString().split('T')[1].substring(0,8)}] ${randTerm} // ${val}%`;
                logsBox.appendChild(line);
                if (logsBox.children.length > 5) {
                    logsBox.removeChild(logsBox.firstChild);
                }
            }, 2000);
        }

        // --- MODULE 5: PROFILE SLIDER CONTROLLERS ---
        let currentProfileSlide = 0;
        const totalProfileSlides = 6;
        let profileAutoplayInterval;

        function updateProfileSlider() {
            const slider = document.getElementById('profile-slider');
            if (!slider) return;
            
            slider.style.transform = `translateX(-${(currentProfileSlide * 100) / totalProfileSlides}%)`;
            
            const dots = document.getElementById('profile-dots');
            if (dots) {
                Array.from(dots.children).forEach((dot, idx) => {
                    dot.style.background = idx === currentProfileSlide ? 'var(--accent-green)' : 'rgba(255,255,255,0.2)';
                    dot.style.transform = idx === currentProfileSlide ? 'scale(1.2)' : 'scale(1)';
                });
            }
            
            const roleTitles = ['LANNA', 'CINEMATIC', 'VIOLENCE', 'SOUNDSCAPE', 'CREATIVE', 'EXPERTISE'];
            scrambleTitle('profile-role-title', roleTitles[currentProfileSlide]);
        }

        function gotoProfileSlide(idx) {
            currentProfileSlide = idx;
            updateProfileSlider();
            resetProfileAutoplay();
        }

        function nextProfileSlide() {
            currentProfileSlide = (currentProfileSlide + 1) % totalProfileSlides;
            updateProfileSlider();
        }

        function startProfileAutoplay() {
            if (profileAutoplayInterval) clearInterval(profileAutoplayInterval);
            profileAutoplayInterval = setInterval(nextProfileSlide, 4500);
        }

        function resetProfileAutoplay() {
            startProfileAutoplay();
        }

        function scrambleTitle(elementId, targetText) {
            const el = document.getElementById(elementId);
            if (!el) return;
            const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*';
            let iter = 0;
            const maxIter = 10;
            const scrambleInt = setInterval(() => {
                let scrambled = '';
                for (let i = 0; i < targetText.length; i++) {
                    if (i < (iter / maxIter) * targetText.length) {
                        scrambled += targetText[i];
                    } else {
                        scrambled += chars[Math.floor(Math.random() * chars.length)];
                    }
                }
                el.innerText = scrambled;
                iter++;
                if (iter > maxIter) clearInterval(scrambleInt);
            }, 30);
        }

        function buildProfileDots() {
            const dots = document.getElementById('profile-dots');
            if (!dots) return;
            dots.innerHTML = '';
            for (let i = 0; i < totalProfileSlides; i++) {
                const dot = document.createElement('div');
                dot.style.width = '6px';
                dot.style.height = '6px';
                dot.style.borderRadius = '50%';
                dot.style.background = 'rgba(255,255,255,0.2)';
                dot.style.cursor = 'pointer';
                dot.style.transition = 'all 0.3s ease';
                dot.onclick = () => gotoProfileSlide(i);
                dots.appendChild(dot);
            }
            updateProfileSlider();

            const sliderContainer = document.getElementById('profile-slider');
            if (sliderContainer && !sliderContainer.dataset.touchInit) {
                sliderContainer.dataset.touchInit = 'true';
                let touchStartX = 0;
                let touchEndX = 0;
                
                sliderContainer.addEventListener('touchstart', e => {
                    touchStartX = e.changedTouches[0].screenX;
                }, {passive: true});
                
                sliderContainer.addEventListener('touchend', e => {
                    touchEndX = e.changedTouches[0].screenX;
                    const threshold = 40;
                    if (touchEndX < touchStartX - threshold) {
                        nextProfileSlide();
                        resetProfileAutoplay();
                    } else if (touchEndX > touchStartX + threshold) {
                        currentProfileSlide = (currentProfileSlide - 1 + totalProfileSlides) % totalProfileSlides;
                        updateProfileSlider();
                        resetProfileAutoplay();
                    }
                }, {passive: true});
            }
        }

        // Auto-init observer loop
        setInterval(() => {
            if (document.getElementById('profile-slider') && document.getElementById('profile-dots') && !document.getElementById('profile-dots').children.length) {
                buildProfileDots();
                startProfileAutoplay();
            }
            if (document.getElementById('labs-logs-box') && document.getElementById('labs-logs-box').children.length === 1 && !document.getElementById('labs-logs-box').hasAttribute('data-init')) {
                document.getElementById('labs-logs-box').setAttribute('data-init', 'true');
                startLabsLogs();
            }
            if (document.getElementById('vault-gallery-container') && vaultInventory.length === 0) {
                switchVaultView('gallery');
            }
        }, 1000);

        // Initialize coordinates layout workspace on boot
        $(function() {
            initWorkspace();
        });

        let isMobileLayout = window.innerWidth <= 768;
        let resizeTimeout;
        window.addEventListener('resize', () => {
            if (visualizerCanvas) {
                visualizerCanvas.width = visualizerCanvas.offsetWidth;
                visualizerCanvas.height = visualizerCanvas.offsetHeight;
            }
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                const mobileNow = window.innerWidth <= 768;
                if (mobileNow !== isMobileLayout) {
                    isMobileLayout = mobileNow;
                    bindGridControls();
                }
            }, 250);
        });

        // --- ABOUT DRAWER LOGIC ---
        function toggleAboutDrawer() {
            const drawer = document.getElementById('about-drawer');
            if (drawer) {
                drawer.classList.toggle('open');
            }
        }

        // Swipe to close logic for the About Drawer
        document.addEventListener('DOMContentLoaded', () => {
            const drawer = document.getElementById('about-drawer');
            if (!drawer) return;

            let touchStartX = 0;
            let touchEndX = 0;

            drawer.addEventListener('touchstart', e => {
                touchStartX = e.changedTouches[0].screenX;
            }, { passive: true });

            drawer.addEventListener('touchend', e => {
                touchEndX = e.changedTouches[0].screenX;
                // If swiped right by more than 50px
                if (touchEndX - touchStartX > 50) {
                    if (drawer.classList.contains('open')) {
                        drawer.classList.remove('open');
                    }
                }
            }, { passive: true });
        });
