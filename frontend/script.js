// ЗАМЕНЯЕМ АБСОЛЮТНЫЙ URL
// const API_BASE = "http://127.0.0.1:5000";

// НА ОТНОСИТЕЛЬНЫЙ ПУТЬ. NGINX БУДЕТ ПЕРЕНАПРАВЛЯТЬ ЭТИ ЗАПРОСЫ
const API_BASE = "/api"; 

// --- THREE.JS SCENE SETUP ---
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById("scene"), antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
camera.position.z = 4.5;

// --- SHADER CODE (GLSL) - без изменений ---
const glsl_noise_functions = `
    vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
    vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
    vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
    vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }
    float snoise(vec3 v) {
        const vec2 C = vec2(1.0/6.0, 1.0/3.0);
        const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
        vec3 i  = floor(v + dot(v, C.yyy));
        vec3 x0 = v - i + dot(i, C.xxx);
        vec3 g = step(x0.yzx, x0.xyz);
        vec3 l = 1.0 - g;
        vec3 i1 = min(g.xyz, l.zxy);
        vec3 i2 = max(g.xyz, l.zxy);
        vec3 x1 = x0 - i1 + C.xxx;
        vec3 x2 = x0 - i2 + C.yyy;
        vec3 x3 = x0 - D.yyy;
        i = mod289(i);
        vec4 p = permute(permute(permute(
                i.z + vec4(0.0, i1.z, i2.z, 1.0))
              + i.y + vec4(0.0, i1.y, i2.y, 1.0))
              + i.x + vec4(0.0, i1.x, i2.x, 1.0));
        float n_ = 0.142857142857;
        vec3  ns = n_ * D.wyz - D.xzx;
        vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
        vec4 x_ = floor(j * ns.z);
        vec4 y_ = floor(j - 7.0 * x_);
        vec4 x = x_ * ns.x + ns.yyyy;
        vec4 y = y_ * ns.x + ns.yyyy;
        vec4 h = 1.0 - abs(x) - abs(y);
        vec4 b0 = vec4(x.xy, y.xy);
        vec4 b1 = vec4(x.zw, y.zw);
        vec4 s0 = floor(b0)*2.0 + 1.0;
        vec4 s1 = floor(b1)*2.0 + 1.0;
        vec4 sh = -step(h, vec4(0.0));
        vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
        vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
        vec3 p0 = vec3(a0.xy,h.x);
        vec3 p1 = vec3(a0.zw,h.y);
        vec3 p2 = vec3(a1.xy,h.z);
        vec3 p3 = vec3(a1.zw,h.w);
        vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
        p0 *= norm.x;
        p1 *= norm.y;
        p2 *= norm.z;
        p3 *= norm.w;
        vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
        m = m * m;
        return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
    }
    float fbm(vec3 p) {
        float value = 0.0;
        float amplitude = 0.5;
        float frequency = 2.0;
        for (int i = 0; i < 5; i++) {
            value += amplitude * snoise(p * frequency);
            amplitude *= 0.5;
            frequency *= 2.0;
        }
        return value;
    }
`;
const sphereVertexShader = `
    uniform float u_time;
    uniform float u_intensity;
    varying vec3 v_normal;
    varying float v_noise;
    ${glsl_noise_functions}
    void main() {
        v_normal = normal;
        vec3 pos = position;
        float displacement = fbm(normal * 1.5 + u_time * 0.2) * u_intensity;
        pos += normal * displacement;
        v_noise = displacement;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
`;
const sphereFragmentShader = `
    uniform vec3 u_color1;
    uniform vec3 u_color2;
    uniform vec3 u_glow_color;
    varying vec3 v_normal;
    varying float v_noise;
    void main() {
        float fresnel = pow(1.0 - abs(dot(v_normal, vec3(0, 0, 1.0))), 2.5);
        float pattern = smoothstep(-0.2, 0.8, v_noise);
        vec3 base_color = mix(u_color1, u_color2, pattern);
        vec3 final_color = base_color + u_glow_color * fresnel;
        gl_FragColor = vec4(final_color, 1.0);
    }
`;

// --- SPHERE CREATION ---
const uniforms = {
    u_time: { value: 0.0 },
    u_intensity: { value: 0.1 },
    u_color1: { value: new THREE.Color("#4a00e0") },
    u_color2: { value: new THREE.Color("#8e2de2") },
    u_glow_color: { value: new THREE.Color("#00ffff") }
};
const sphereGeometry = new THREE.SphereGeometry(2.0, 128, 128);
const sphereMaterial = new THREE.ShaderMaterial({ uniforms, vertexShader: sphereVertexShader, fragmentShader: sphereFragmentShader });
const sphere = new THREE.Mesh(sphereGeometry, sphereMaterial);
scene.add(sphere);

// --- STATE MANAGEMENT & UI ---
let state = "idle";
let mediaRecorder;
let audioChunks = [];
let audio;
let mediaStream = null;

const askBtn = document.getElementById("askBtn");
const finishRecBtn = document.getElementById("finishRecBtn");
const sendBtn = document.getElementById("sendBtn");
const cancelBtn = document.getElementById("cancelBtn");
const stopBtn = document.getElementById("stopBtn");
const statusDiv = document.getElementById("status");

function updateUI() {
  statusDiv.textContent = {
    idle: "Нажмите 'Задать вопрос', чтобы начать",
    recording: "Идет запись... Нажмите 'Закончить', когда будете готовы",
    thinking: "Думаю...",
    speaking: "Отвечаю...",
    recorded: "Запись завершена, нажмите 'Отправить'"
  }[state];

  askBtn.classList.toggle("hidden", state !== "idle");
  sendBtn.classList.toggle("hidden", state !== "recorded");
  finishRecBtn.classList.toggle("hidden", state !== "recording");
  cancelBtn.classList.toggle("hidden", !["recording", "recorded"].includes(state));
  stopBtn.classList.toggle("hidden", state !== "speaking");
}

// --- ANIMATION LOGIC ---
const clock = new THREE.Clock();
let targetIntensity = 0.1;
function animate() {
    const elapsedTime = clock.getElapsedTime();
    uniforms.u_time.value = elapsedTime;
    uniforms.u_intensity.value += (targetIntensity - uniforms.u_intensity.value) * 0.05;
    let color1 = new THREE.Color(), color2 = new THREE.Color(), glowColor = new THREE.Color();
    switch (state) {
        case "recording":
            targetIntensity = 0.2;
            color1.set("#FFD700"); color2.set("#FFA500"); glowColor.set("#FFFFFF");
            break;
        case "thinking":
            targetIntensity = 0.25;
            uniforms.u_time.value = elapsedTime * 1.5;
            color1.set("#8A2BE2"); color2.set("#FF00FF"); glowColor.set("#FFFFFF");
            break;
        case "speaking":
            targetIntensity = 0.15 + Math.abs(Math.sin(elapsedTime * 10.0)) * 0.1;
            color1.set("#00BFFF"); color2.set("#1E90FF"); glowColor.set("#AFEEEE");
            break;
        default:
            targetIntensity = 0.1 + Math.sin(elapsedTime * 0.5) * 0.05;
            color1.set("#8A2BE2"); color2.set("#4B0082"); glowColor.set("#00ffff");
            break;
    }
    uniforms.u_color1.value.lerp(color1, 0.1);
    uniforms.u_color2.value.lerp(color2, 0.1);
    uniforms.u_glow_color.value.lerp(glowColor, 0.1);
    renderer.render(scene, camera);
    requestAnimationFrame(animate);
}
animate();
updateUI();

// --- EVENT LISTENERS ---
askBtn.onclick = async () => {
    if (!mediaStream) {
        try {
            mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch (err) {
            statusDiv.textContent = "Ошибка: микрофон не доступен.";
            console.error("Microphone access error:", err);
            return;
        }
    }
    mediaRecorder = new MediaRecorder(mediaStream);
    audioChunks = [];
    mediaRecorder.ondataavailable = event => audioChunks.push(event.data);
    mediaRecorder.onstop = () => {
        if (state === 'recording') {
            state = "recorded";
            updateUI();
        }
    };
    mediaRecorder.start();
    state = "recording";
    updateUI();
    setTimeout(() => { if (mediaRecorder && mediaRecorder.state === 'recording') { mediaRecorder.stop(); } }, 5000);
};

finishRecBtn.onclick = () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
    }
};

sendBtn.onclick = async () => {
    state = "thinking";
    updateUI();
    const formData = new FormData();
    formData.append("audio", new Blob(audioChunks, { type: "audio/webm" }));
    try {
        const sttRes = await fetch(`${API_BASE}/stt`, { method: "POST", body: formData });
        const sttData = await sttRes.json();

        // <<<--- ВОТ ИСПРАВЛЕННАЯ СТРОКА ---
        const chatRes = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: sttData.text }),
        });
        
        const chatData = await chatRes.json();

        const ttsRes = await fetch(`${API_BASE}/tts`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: chatData.answer }),
        });
        const audioBlob = await ttsRes.blob();
        audio = new Audio(URL.createObjectURL(audioBlob));
        state = "speaking";
        updateUI();
        audio.play();
        audio.onended = () => {
            state = "idle";
            updateUI();
        };
    } catch (error) {
        console.error("API Error:", error);
        statusDiv.textContent = "Произошла ошибка";
        state = "idle";
        updateUI();
    }
};

cancelBtn.onclick = () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
    }
    audioChunks = [];
    state = "idle";
    updateUI();
};

stopBtn.onclick = () => {
    if (audio) {
        audio.pause();
        audio.currentTime = 0;
    }
    state = "idle";
    updateUI();
};

window.onresize = () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
};