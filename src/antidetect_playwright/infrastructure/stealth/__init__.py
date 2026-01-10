"""Stealth JavaScript patches for anti-detection."""

WEBDRIVER_PATCH = """
(() => {
    // Remove webdriver property
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true
    });
    
    // Remove automation-related properties from navigator
    delete navigator.__proto__.webdriver;
    
    // Patch navigator.permissions.query for notifications
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
})();
"""

NAVIGATOR_PATCH_TEMPLATE = """
(() => {
    const config = {fingerprint};
    
    // Override navigator properties
    Object.defineProperties(navigator, {
        userAgent: { get: () => config.navigator.userAgent },
        platform: { get: () => config.navigator.platform },
        language: { get: () => config.navigator.language },
        languages: { get: () => Object.freeze(config.navigator.languages) },
        hardwareConcurrency: { get: () => config.navigator.hardwareConcurrency },
        deviceMemory: { get: () => config.navigator.deviceMemory },
        maxTouchPoints: { get: () => config.navigator.maxTouchPoints },
        vendor: { get: () => config.navigator.vendor },
    });
    
    // Override screen properties
    Object.defineProperties(screen, {
        width: { get: () => config.screen.width },
        height: { get: () => config.screen.height },
        availWidth: { get: () => config.screen.availWidth },
        availHeight: { get: () => config.screen.availHeight },
        colorDepth: { get: () => config.screen.colorDepth },
        pixelDepth: { get: () => config.screen.pixelDepth },
    });
    
    // Override window dimensions
    Object.defineProperties(window, {
        innerWidth: { get: () => config.screen.width },
        innerHeight: { get: () => config.screen.height - 100 },
        outerWidth: { get: () => config.screen.width },
        outerHeight: { get: () => config.screen.height },
    });
})();
"""

WEBGL_PATCH_TEMPLATE = """
(() => {
    const config = {fingerprint};
    
    const getParameterProxyHandler = {
        apply: function(target, thisArg, args) {
            const param = args[0];
            
            // UNMASKED_VENDOR_WEBGL
            if (param === 37445) {
                return config.webgl.unmaskedVendor;
            }
            // UNMASKED_RENDERER_WEBGL
            if (param === 37446) {
                return config.webgl.unmaskedRenderer;
            }
            // VENDOR
            if (param === 7936) {
                return config.webgl.vendor;
            }
            // RENDERER
            if (param === 7937) {
                return config.webgl.renderer;
            }
            
            return Reflect.apply(target, thisArg, args);
        }
    };
    
    // Patch WebGL contexts
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(type, ...args) {
        const context = originalGetContext.apply(this, [type, ...args]);
        
        if (context && (type === 'webgl' || type === 'webgl2' || type === 'experimental-webgl')) {
            context.getParameter = new Proxy(context.getParameter, getParameterProxyHandler);
        }
        
        return context;
    };
})();
"""

CANVAS_PATCH_TEMPLATE = """
(() => {
    const config = {fingerprint};
    
    // Add noise to canvas data
    const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
    CanvasRenderingContext2D.prototype.getImageData = function(...args) {
        const imageData = originalGetImageData.apply(this, args);
        
        for (let i = 0; i < imageData.data.length; i += 4) {
            imageData.data[i] = Math.max(0, Math.min(255, 
                imageData.data[i] + Math.round(config.canvas.noiseR * 255)));
            imageData.data[i + 1] = Math.max(0, Math.min(255, 
                imageData.data[i + 1] + Math.round(config.canvas.noiseG * 255)));
            imageData.data[i + 2] = Math.max(0, Math.min(255, 
                imageData.data[i + 2] + Math.round(config.canvas.noiseB * 255)));
        }
        
        return imageData;
    };
    
    // Patch toDataURL
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(...args) {
        const ctx = this.getContext('2d');
        if (ctx) {
            const imageData = ctx.getImageData(0, 0, this.width, this.height);
            ctx.putImageData(imageData, 0, 0);
        }
        return originalToDataURL.apply(this, args);
    };
    
    // Patch toBlob
    const originalToBlob = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = function(callback, ...args) {
        const ctx = this.getContext('2d');
        if (ctx) {
            const imageData = ctx.getImageData(0, 0, this.width, this.height);
            ctx.putImageData(imageData, 0, 0);
        }
        return originalToBlob.apply(this, [callback, ...args]);
    };
})();
"""

AUDIO_PATCH_TEMPLATE = """
(() => {
    const config = {fingerprint};
    
    // Patch AudioContext
    const originalCreateAnalyser = AudioContext.prototype.createAnalyser;
    AudioContext.prototype.createAnalyser = function() {
        const analyser = originalCreateAnalyser.apply(this, arguments);
        
        const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;
        analyser.getFloatFrequencyData = function(array) {
            originalGetFloatFrequencyData.apply(this, [array]);
            for (let i = 0; i < array.length; i++) {
                array[i] = array[i] + config.audio.noiseFactor * (Math.random() - 0.5);
            }
        };
        
        return analyser;
    };
    
    // Patch OfflineAudioContext
    if (typeof OfflineAudioContext !== 'undefined') {
        const originalStartRendering = OfflineAudioContext.prototype.startRendering;
        OfflineAudioContext.prototype.startRendering = function() {
            return originalStartRendering.apply(this).then(buffer => {
                const output = buffer.getChannelData(0);
                for (let i = 0; i < output.length; i++) {
                    output[i] = output[i] + config.audio.noiseFactor * (Math.random() - 0.5);
                }
                return buffer;
            });
        };
    }
})();
"""

TIMEZONE_PATCH_TEMPLATE = """
(() => {
    const timezone = '{timezone}';
    
    // Override Intl.DateTimeFormat
    const originalDateTimeFormat = Intl.DateTimeFormat;
    Intl.DateTimeFormat = function(locales, options) {
        options = options || {};
        options.timeZone = timezone;
        return new originalDateTimeFormat(locales, options);
    };
    Object.setPrototypeOf(Intl.DateTimeFormat, originalDateTimeFormat);
    
    // Override Date.prototype.getTimezoneOffset
    const targetOffset = (() => {
        const offsets = {
            'America/New_York': 300,
            'America/Los_Angeles': 480,
            'America/Chicago': 360,
            'Europe/London': 0,
            'Europe/Berlin': -60,
            'Europe/Paris': -60,
            'Asia/Tokyo': -540,
            'Asia/Singapore': -480,
        };
        return offsets[timezone] || 0;
    })();
    
    Date.prototype.getTimezoneOffset = function() {
        return targetOffset;
    };
})();
"""

CLIENT_RECTS_PATCH = """
(() => {
    // Add subtle noise to client rects
    const originalGetClientRects = Element.prototype.getClientRects;
    Element.prototype.getClientRects = function() {
        const rects = originalGetClientRects.apply(this);
        const noise = 0.00001;
        
        return new Proxy(rects, {
            get: function(target, prop) {
                const rect = target[prop];
                if (rect && typeof rect === 'object') {
                    return new Proxy(rect, {
                        get: function(r, p) {
                            const val = r[p];
                            if (typeof val === 'number') {
                                return val + noise * Math.random();
                            }
                            return val;
                        }
                    });
                }
                return rect;
            }
        });
    };
    
    const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
    Element.prototype.getBoundingClientRect = function() {
        const rect = originalGetBoundingClientRect.apply(this);
        const noise = 0.00001;
        
        return new DOMRect(
            rect.x + noise * Math.random(),
            rect.y + noise * Math.random(),
            rect.width + noise * Math.random(),
            rect.height + noise * Math.random()
        );
    };
})();
"""

PLUGINS_PATCH_TEMPLATE = """
(() => {
    const pluginNames = {plugins};
    
    // Create fake plugins array
    const fakePlugins = pluginNames.map((name, index) => ({
        name: name,
        description: name,
        filename: name.toLowerCase().replace(/ /g, '_') + '.dll',
        length: 1,
        item: () => null,
        namedItem: () => null,
    }));
    
    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const arr = Object.create(PluginArray.prototype);
            fakePlugins.forEach((p, i) => {
                arr[i] = p;
            });
            arr.length = fakePlugins.length;
            arr.item = (i) => arr[i];
            arr.namedItem = (name) => fakePlugins.find(p => p.name === name);
            arr.refresh = () => {};
            return arr;
        }
    });
})();
"""

WEBRTC_PATCH = """
(() => {
    // Disable WebRTC leak
    if (typeof RTCPeerConnection !== 'undefined') {
        const originalRTCPeerConnection = RTCPeerConnection;
        
        RTCPeerConnection = function(...args) {
            const config = args[0] || {};
            
            // Force TURN/STUN to not leak local IP
            config.iceServers = config.iceServers || [];
            config.iceCandidatePoolSize = 0;
            
            const pc = new originalRTCPeerConnection(config);
            
            // Filter ICE candidates
            const originalAddIceCandidate = pc.addIceCandidate.bind(pc);
            pc.addIceCandidate = function(candidate) {
                if (candidate && candidate.candidate) {
                    // Block local IP candidates
                    if (candidate.candidate.includes('typ host')) {
                        return Promise.resolve();
                    }
                }
                return originalAddIceCandidate(candidate);
            };
            
            return pc;
        };
        
        RTCPeerConnection.prototype = originalRTCPeerConnection.prototype;
    }
})();
"""

CHROME_RUNTIME_PATCH = """
(() => {
    // Mock chrome.runtime for headless detection
    window.chrome = window.chrome || {};
    window.chrome.runtime = window.chrome.runtime || {};
    
    window.chrome.runtime.connect = function() {
        return { onMessage: { addListener: function() {} }, postMessage: function() {} };
    };
    window.chrome.runtime.sendMessage = function() {};
    
    // Add chrome.csi
    window.chrome.csi = function() {
        return {
            startE: Date.now(),
            onloadT: Date.now(),
            pageT: Date.now(),
            tran: 15
        };
    };
    
    // Add chrome.loadTimes
    window.chrome.loadTimes = function() {
        return {
            commitLoadTime: Date.now() / 1000,
            connectionInfo: 'h2',
            finishDocumentLoadTime: Date.now() / 1000,
            finishLoadTime: Date.now() / 1000,
            firstPaintAfterLoadTime: 0,
            firstPaintTime: Date.now() / 1000,
            navigationType: 'Other',
            npnNegotiatedProtocol: 'h2',
            requestTime: Date.now() / 1000,
            startLoadTime: Date.now() / 1000,
            wasAlternateProtocolAvailable: false,
            wasFetchedViaSpdy: true,
            wasNpnNegotiated: true
        };
    };
})();
"""

IFRAME_PATCH = """
(() => {
    // Ensure contentWindow matches parent window properties
    const originalContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
    
    Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
        get: function() {
            const win = originalContentWindow.get.call(this);
            if (win) {
                try {
                    // Try to ensure consistent navigator
                    Object.defineProperty(win.navigator, 'webdriver', {
                        get: () => undefined
                    });
                } catch (e) {}
            }
            return win;
        }
    });
})();
"""

HEADLESS_PATCH = """
(() => {
    // Patch headless detection methods
    
    // Override navigator.connection
    if (!navigator.connection) {
        Object.defineProperty(navigator, 'connection', {
            get: () => ({
                effectiveType: '4g',
                rtt: 50,
                downlink: 10,
                saveData: false,
                onchange: null,
            })
        });
    }
    
    // Override window.outerWidth/outerHeight to not be 0
    if (window.outerWidth === 0) {
        Object.defineProperty(window, 'outerWidth', { get: () => window.innerWidth });
    }
    if (window.outerHeight === 0) {
        Object.defineProperty(window, 'outerHeight', { get: () => window.innerHeight + 100 });
    }
    
    // Patch notification permission
    if (Notification.permission === 'denied') {
        Object.defineProperty(Notification, 'permission', { get: () => 'default' });
    }
})();
"""


def generate_stealth_script(fingerprint_data: dict) -> str:
    """Generate complete stealth script from fingerprint data."""
    import json

    fp_json = json.dumps(fingerprint_data)

    scripts = [
        WEBDRIVER_PATCH,
        NAVIGATOR_PATCH_TEMPLATE.replace("{fingerprint}", fp_json),
        WEBGL_PATCH_TEMPLATE.replace("{fingerprint}", fp_json),
        CANVAS_PATCH_TEMPLATE.replace("{fingerprint}", fp_json),
        AUDIO_PATCH_TEMPLATE.replace("{fingerprint}", fp_json),
        TIMEZONE_PATCH_TEMPLATE.replace("{timezone}", fingerprint_data["timezone"]),
        CLIENT_RECTS_PATCH,
        PLUGINS_PATCH_TEMPLATE.replace(
            "{plugins}", json.dumps(fingerprint_data["plugins"])
        ),
        WEBRTC_PATCH,
        CHROME_RUNTIME_PATCH,
        IFRAME_PATCH,
        HEADLESS_PATCH,
    ]

    return "\n".join(scripts)
