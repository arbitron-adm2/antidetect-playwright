"""Antidetect preset data models."""

from dataclasses import dataclass, field
from typing import Any
import json


@dataclass
class NavigatorPreset:
    """Navigator fingerprint preset."""

    user_agent: str
    platform: str
    language: str
    languages: list[str]
    hardware_concurrency: int
    device_memory: int
    max_touch_points: int
    vendor: str
    app_version: str
    app_name: str = "Netscape"
    app_code_name: str = "Mozilla"
    product: str = "Gecko"
    product_sub: str = "20030107"
    do_not_track: str | None = None
    webdriver: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "userAgent": self.user_agent,
            "platform": self.platform,
            "language": self.language,
            "languages": self.languages,
            "hardwareConcurrency": self.hardware_concurrency,
            "deviceMemory": self.device_memory,
            "maxTouchPoints": self.max_touch_points,
            "vendor": self.vendor,
            "appVersion": self.app_version,
            "appName": self.app_name,
            "appCodeName": self.app_code_name,
            "product": self.product,
            "productSub": self.product_sub,
            "doNotTrack": self.do_not_track,
            "webdriver": self.webdriver,
        }


@dataclass
class ScreenPreset:
    """Screen fingerprint preset."""

    width: int
    height: int
    avail_width: int
    avail_height: int
    color_depth: int = 24
    pixel_depth: int = 24
    device_pixel_ratio: float = 1.0
    inner_width: int = 0
    inner_height: int = 0
    outer_width: int = 0
    outer_height: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "availWidth": self.avail_width,
            "availHeight": self.avail_height,
            "colorDepth": self.color_depth,
            "pixelDepth": self.pixel_depth,
            "devicePixelRatio": self.device_pixel_ratio,
            "innerWidth": self.inner_width,
            "innerHeight": self.inner_height,
            "outerWidth": self.outer_width,
            "outerHeight": self.outer_height,
        }


@dataclass
class WebGLPreset:
    """WebGL fingerprint preset."""

    vendor: str
    renderer: str
    unmasked_vendor: str
    unmasked_renderer: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor": self.vendor,
            "renderer": self.renderer,
            "unmaskedVendor": self.unmasked_vendor,
            "unmaskedRenderer": self.unmasked_renderer,
        }


@dataclass
class AudioPreset:
    """Audio fingerprint preset."""

    sample_rate: int = 44100
    channel_count: int = 2
    noise_factor: float = 0.0001

    def to_dict(self) -> dict[str, Any]:
        return {
            "sampleRate": self.sample_rate,
            "channelCount": self.channel_count,
            "noiseFactor": self.noise_factor,
        }


@dataclass
class CanvasPreset:
    """Canvas fingerprint preset."""

    noise_r: float = 0.0
    noise_g: float = 0.0
    noise_b: float = 0.0
    noise_a: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "noiseR": self.noise_r,
            "noiseG": self.noise_g,
            "noiseB": self.noise_b,
            "noiseA": self.noise_a,
        }


@dataclass
class WebRTCPreset:
    """WebRTC preset."""

    disabled: bool = True
    public_ip: str | None = None
    local_ip: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "disabled": self.disabled,
            "publicIp": self.public_ip,
            "localIp": self.local_ip,
        }


@dataclass
class TimezonePreset:
    """Timezone preset."""

    timezone_id: str
    offset: int  # minutes from UTC

    def to_dict(self) -> dict[str, Any]:
        return {
            "timezoneId": self.timezone_id,
            "offset": self.offset,
        }


@dataclass
class AntidetectPreset:
    """Complete antidetect fingerprint preset."""

    id: str
    name: str
    navigator: NavigatorPreset
    screen: ScreenPreset
    webgl: WebGLPreset
    audio: AudioPreset
    canvas: CanvasPreset
    webrtc: WebRTCPreset
    timezone: TimezonePreset
    fonts: list[str] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)

    # HTTP headers
    accept_language: str = "en-US,en;q=0.9"
    accept_encoding: str = "gzip, deflate, br"
    sec_ch_ua: str = ""
    sec_ch_ua_mobile: str = "?0"
    sec_ch_ua_platform: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "navigator": self.navigator.to_dict(),
            "screen": self.screen.to_dict(),
            "webgl": self.webgl.to_dict(),
            "audio": self.audio.to_dict(),
            "canvas": self.canvas.to_dict(),
            "webrtc": self.webrtc.to_dict(),
            "timezone": self.timezone.to_dict(),
            "fonts": self.fonts,
            "plugins": self.plugins,
            "headers": {
                "Accept-Language": self.accept_language,
                "Accept-Encoding": self.accept_encoding,
                "Sec-Ch-Ua": self.sec_ch_ua,
                "Sec-Ch-Ua-Mobile": self.sec_ch_ua_mobile,
                "Sec-Ch-Ua-Platform": self.sec_ch_ua_platform,
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_playwright_context_options(self) -> dict[str, Any]:
        """Convert to Playwright context options."""
        return {
            "user_agent": self.navigator.user_agent,
            "viewport": {
                "width": self.screen.width,
                "height": self.screen.height - 100,
            },
            "locale": self.navigator.language,
            "timezone_id": self.timezone.timezone_id,
            "color_scheme": "light",
            "extra_http_headers": {
                "Accept-Language": self.accept_language,
            },
        }

    def to_injection_script(self) -> str:
        """Generate JavaScript injection script for fingerprint spoofing."""
        return f"""
(function() {{
    'use strict';
    
    // ========== NATIVE FUNCTION PROTECTION (MUST BE FIRST) ==========
    // Храним оригиналы и подменённые функции
    const spoofedFunctions = new WeakMap();
    const originalFunctionToString = Function.prototype.toString;
    
    // Прокси для toString
    Function.prototype.toString = new Proxy(originalFunctionToString, {{
        apply: function(target, thisArg, args) {{
            // Если функция в нашем списке - возвращаем native string
            if (spoofedFunctions.has(thisArg)) {{
                return spoofedFunctions.get(thisArg);
            }}
            return Reflect.apply(target, thisArg, args);
        }}
    }});
    
    // Регистрируем сам toString как native
    spoofedFunctions.set(Function.prototype.toString, 'function toString() {{ [native code] }}');
    
    // Хелпер для регистрации функций
    const registerNative = (fn, name) => {{
        if (fn) spoofedFunctions.set(fn, `function ${{name || fn.name || ''}}() {{ [native code] }}`);
    }};
    
    // ========== WEBDRIVER COMPLETE ELIMINATION ==========
    // Удаляем с прототипа Navigator
    try {{
        const proto = Object.getPrototypeOf(navigator);
        if (proto.hasOwnProperty('webdriver')) {{
            delete proto.webdriver;
        }}
    }} catch(e) {{}}
    
    // Удаляем с самого navigator
    try {{
        if ('webdriver' in navigator) {{
            delete navigator.webdriver;
        }}
    }} catch(e) {{}}
    const originalIn = Reflect.has;
    
    const propsToDelete = [
        'webdriver', '__webdriver_evaluate', '__selenium_evaluate',
        '__webdriver_script_function', '__webdriver_script_func',
        '__webdriver_script_fn', '__fxdriver_evaluate',
        '__driver_unwrapped', '__webdriver_unwrapped',
        '__driver_evaluate', '__selenium_unwrapped',
        '__fxdriver_unwrapped', '_Selenium_IDE_Recorder',
        '_selenium', 'calledSelenium', '$chrome_asyncScriptInfo',
        '$cdc_asdjflasutopfhvcZLmcfl_', '$chromeDriver', '$webdriver'
    ];
    
    propsToDelete.forEach(prop => {{
        try {{ delete window[prop]; }} catch(e) {{}}
        try {{ delete document[prop]; }} catch(e) {{}}
    }});
    
    // ========== CDP DETECTION ELIMINATION ==========
    const cdcProps = Object.getOwnPropertyNames(window).filter(p => p.includes('cdc_') || p.includes('$cdc'));
    cdcProps.forEach(prop => {{ try {{ delete window[prop]; }} catch(e) {{}} }});
    
    // Очистка document от cdc
    const docCdcProps = Object.getOwnPropertyNames(document).filter(p => p.includes('cdc_') || p.includes('$cdc'));
    docCdcProps.forEach(prop => {{ try {{ delete document[prop]; }} catch(e) {{}} }});
    
    // ========== NAVIGATOR PROPS ==========
    const navigatorProps = {json.dumps(self.navigator.to_dict())};
    
    const navigatorOverrides = {{
        platform: navigatorProps.platform,
        language: navigatorProps.language,
        languages: Object.freeze(navigatorProps.languages),
        hardwareConcurrency: navigatorProps.hardwareConcurrency,
        deviceMemory: navigatorProps.deviceMemory,
        maxTouchPoints: navigatorProps.maxTouchPoints,
        vendor: navigatorProps.vendor,
        appVersion: navigatorProps.appVersion,
        appName: navigatorProps.appName,
        appCodeName: navigatorProps.appCodeName,
        product: navigatorProps.product,
        productSub: navigatorProps.productSub,
        userAgent: navigatorProps.userAgent
    }};
    
    for (const [key, value] of Object.entries(navigatorOverrides)) {{
        try {{
            Object.defineProperty(navigator, key, {{ get: () => value, configurable: true }});
        }} catch(e) {{}}
    }}
    
    // ========== PLUGINS & MIMETYPES ==========
    const createPlugin = (name, filename, desc) => {{
        const p = Object.create(Plugin.prototype);
        Object.defineProperties(p, {{
            name: {{ value: name, enumerable: true }},
            filename: {{ value: filename, enumerable: true }},
            description: {{ value: desc, enumerable: true }},
            length: {{ value: 1, enumerable: true }}
        }});
        return p;
    }};
    
    const mockPlugins = [
        createPlugin('PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
        createPlugin('Chrome PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
        createPlugin('Chromium PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
        createPlugin('Microsoft Edge PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
        createPlugin('WebKit built-in PDF', 'internal-pdf-viewer', 'Portable Document Format')
    ];
    
    const pluginArray = Object.create(PluginArray.prototype);
    mockPlugins.forEach((plugin, i) => {{ pluginArray[i] = plugin; pluginArray[plugin.name] = plugin; }});
    Object.defineProperty(pluginArray, 'length', {{ value: mockPlugins.length }});
    Object.defineProperty(pluginArray, 'item', {{ value: (i) => mockPlugins[i] }});
    Object.defineProperty(pluginArray, 'namedItem', {{ value: (name) => mockPlugins.find(p => p.name === name) }});
    Object.defineProperty(pluginArray, 'refresh', {{ value: () => {{}} }});
    Object.defineProperty(navigator, 'plugins', {{ get: () => pluginArray }});
    
    const mimeTypeArray = Object.create(MimeTypeArray.prototype);
    Object.defineProperty(mimeTypeArray, 'length', {{ value: 2 }});
    Object.defineProperty(navigator, 'mimeTypes', {{ get: () => mimeTypeArray }});
    
    // ========== SCREEN ==========
    const screenProps = {json.dumps(self.screen.to_dict())};
    
    for (const [key, value] of Object.entries({{
        width: screenProps.width, height: screenProps.height,
        availWidth: screenProps.availWidth, availHeight: screenProps.availHeight,
        colorDepth: screenProps.colorDepth, pixelDepth: screenProps.pixelDepth
    }})) {{
        Object.defineProperty(screen, key, {{ get: () => value, configurable: true }});
    }}
    
    Object.defineProperty(window, 'devicePixelRatio', {{ get: () => screenProps.devicePixelRatio }});
    Object.defineProperty(window, 'outerWidth', {{ get: () => screenProps.outerWidth || screenProps.width }});
    Object.defineProperty(window, 'outerHeight', {{ get: () => screenProps.outerHeight || screenProps.height - 100 }});
    Object.defineProperty(window, 'innerWidth', {{ get: () => screenProps.innerWidth || screenProps.width }});
    Object.defineProperty(window, 'innerHeight', {{ get: () => screenProps.innerHeight || screenProps.height - 140 }});
    
    // ========== WEBGL ==========
    const webglProps = {json.dumps(self.webgl.to_dict())};
    
    const getParameterProxyHandler = {{
        apply: function(target, thisArg, args) {{
            const param = args[0];
            if (param === 37445) return webglProps.unmaskedVendor;
            if (param === 37446) return webglProps.unmaskedRenderer;
            if (param === 7936) return webglProps.vendor;
            if (param === 7937) return webglProps.renderer;
            return Reflect.apply(target, thisArg, args);
        }}
    }};
    
    try {{
        WebGLRenderingContext.prototype.getParameter = new Proxy(WebGLRenderingContext.prototype.getParameter, getParameterProxyHandler);
        WebGL2RenderingContext.prototype.getParameter = new Proxy(WebGL2RenderingContext.prototype.getParameter, getParameterProxyHandler);
    }} catch(e) {{}}
    
    // ========== CANVAS NOISE ==========
    const addCanvasNoise = (imageData) => {{
        const d = imageData.data;
        for (let i = 0; i < d.length; i += 4) {{
            d[i] = Math.max(0, Math.min(255, d[i] + ((Math.random() - 0.5) * 2) | 0));
            d[i+1] = Math.max(0, Math.min(255, d[i+1] + ((Math.random() - 0.5) * 2) | 0));
            d[i+2] = Math.max(0, Math.min(255, d[i+2] + ((Math.random() - 0.5) * 2) | 0));
        }}
        return imageData;
    }};
    
    const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
    const patchedGetImageData = function getImageData(...args) {{
        return addCanvasNoise(originalGetImageData.apply(this, args));
    }};
    CanvasRenderingContext2D.prototype.getImageData = patchedGetImageData;
    registerNative(patchedGetImageData, 'getImageData');
    
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    const patchedToDataURL = function toDataURL(...args) {{
        try {{
            const ctx = this.getContext('2d');
            if (ctx && this.width > 0 && this.height > 0) {{
                ctx.putImageData(addCanvasNoise(originalGetImageData.call(ctx, 0, 0, this.width, this.height)), 0, 0);
            }}
        }} catch(e) {{}}
        return originalToDataURL.apply(this, args);
    }};
    HTMLCanvasElement.prototype.toDataURL = patchedToDataURL;
    registerNative(patchedToDataURL, 'toDataURL');
    
    const originalToBlob = HTMLCanvasElement.prototype.toBlob;
    const patchedToBlob = function toBlob(callback, ...args) {{
        try {{
            const ctx = this.getContext('2d');
            if (ctx && this.width > 0 && this.height > 0) {{
                ctx.putImageData(addCanvasNoise(originalGetImageData.call(ctx, 0, 0, this.width, this.height)), 0, 0);
            }}
        }} catch(e) {{}}
        return originalToBlob.call(this, callback, ...args);
    }};
    HTMLCanvasElement.prototype.toBlob = patchedToBlob;
    registerNative(patchedToBlob, 'toBlob');
    
    // ========== AUDIO NOISE ==========
    const audioNoise = {self.audio.noise_factor};
    
    if (window.AudioContext || window.webkitAudioContext) {{
        const AC = window.AudioContext || window.webkitAudioContext;
        const originalGetChannelData = AudioBuffer.prototype.getChannelData;
        const patchedGetChannelData = function getChannelData(channel) {{
            const data = originalGetChannelData.call(this, channel);
            for (let i = 0; i < data.length; i++) {{ data[i] += (Math.random() - 0.5) * audioNoise; }}
            return data;
        }};
        AudioBuffer.prototype.getChannelData = patchedGetChannelData;
        registerNative(patchedGetChannelData, 'getChannelData');
        
        const originalCreateAnalyser = AC.prototype.createAnalyser;
        AC.prototype.createAnalyser = function() {{
            const analyser = originalCreateAnalyser.call(this);
            const originalGetFloatFrequencyData = analyser.getFloatFrequencyData.bind(analyser);
            analyser.getFloatFrequencyData = function(array) {{
                originalGetFloatFrequencyData(array);
                for (let i = 0; i < array.length; i++) {{ array[i] += (Math.random() - 0.5) * audioNoise * 100; }}
            }};
            return analyser;
        }};
    }}
    
    // ========== WEBRTC ==========
    const webrtcProps = {json.dumps(self.webrtc.to_dict())};
    
    if (webrtcProps.disabled) {{
        const rtcHandler = {{
            construct: function(target, args) {{
                const pc = Reflect.construct(target, args);
                pc.createDataChannel = () => null;
                pc.createOffer = () => Promise.reject(new Error('WebRTC disabled'));
                pc.createAnswer = () => Promise.reject(new Error('WebRTC disabled'));
                pc.setLocalDescription = () => Promise.resolve();
                pc.setRemoteDescription = () => Promise.resolve();
                return pc;
            }}
        }};
        if (window.RTCPeerConnection) window.RTCPeerConnection = new Proxy(window.RTCPeerConnection, rtcHandler);
        if (window.webkitRTCPeerConnection) window.webkitRTCPeerConnection = new Proxy(window.webkitRTCPeerConnection, rtcHandler);
    }}
    
    // ========== CHROME RUNTIME ==========
    window.chrome = window.chrome || {{}};
    window.chrome.runtime = window.chrome.runtime || {{}};
    window.chrome.loadTimes = window.chrome.loadTimes || function() {{
        return {{ requestTime: Date.now() / 1000 - Math.random() * 1000, startLoadTime: Date.now() / 1000 - Math.random() * 500, commitLoadTime: Date.now() / 1000 - Math.random() * 300, finishDocumentLoadTime: Date.now() / 1000 - Math.random() * 100, finishLoadTime: Date.now() / 1000, firstPaintTime: Date.now() / 1000 - Math.random() * 50, firstPaintAfterLoadTime: 0, navigationType: 'Other', wasFetchedViaSpdy: false, wasNpnNegotiated: true, npnNegotiatedProtocol: 'h2', wasAlternateProtocolAvailable: false, connectionInfo: 'h2' }};
    }};
    window.chrome.csi = window.chrome.csi || function() {{ return {{ onloadT: Date.now(), pageT: Math.random() * 1000, startE: Date.now() - Math.random() * 2000, tran: 15 }}; }};
    window.chrome.app = window.chrome.app || {{ isInstalled: false, InstallState: {{ DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }}, RunningState: {{ CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' }} }};
    
    // Регистрируем chrome функции как native
    registerNative(window.chrome.loadTimes, 'loadTimes');
    registerNative(window.chrome.csi, 'csi');
    
    // ========== PERMISSIONS API ==========
    const originalQuery = Permissions.prototype.query;
    const patchedQuery = function query(parameters) {{
        if (parameters.name === 'notifications') return Promise.resolve({{ state: Notification.permission, onchange: null }});
        return originalQuery.apply(this, arguments);
    }};
    Permissions.prototype.query = patchedQuery;
    registerNative(patchedQuery, 'query');
    
    // ========== IFRAME PROTECTION ==========
    const originalContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
    Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {{
        get: function() {{
            const win = originalContentWindow.get.call(this);
            if (win) {{ try {{ delete win.navigator.webdriver; Object.defineProperty(win.navigator, 'webdriver', {{ get: () => undefined }}); }} catch(e) {{}} }}
            return win;
        }}
    }});
    
    // ========== BATTERY API ==========
    if (navigator.getBattery) {{
        navigator.getBattery = () => Promise.resolve({{ charging: true, chargingTime: Infinity, dischargingTime: Infinity, level: 1.0, addEventListener: () => {{}}, removeEventListener: () => {{}} }});
    }}
    
}})();
"""
