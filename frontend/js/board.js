const CAT_KEY = "characters/whiskers";
const STORAGE_KEY = "wheres-whiskers-v1";

const appEl = document.getElementById("app");
const tabsEl = document.getElementById("tabs");
const paletteEl = document.getElementById("palette");
const stageEl = document.getElementById("stage");
const wrapEl = document.getElementById("board-wrap");
const boardEl = document.getElementById("board");
const ghostEl = document.getElementById("ghost");
const nameEl = document.getElementById("selection-name");
const hintEl = document.getElementById("hint");

let DATA = null;
let ASSETS = {};
let BOARD_W = 1120;
let MODE = "editor";
let TURN = null;
let token = null;
let state = { room: null, scenes: {} };
let selectedId = null;
let scale = 1;
let sent = false;

function send(type, data) {
    window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type }, data), "*");
}

function setValue(value) {
    value.nonce = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
    send("streamlit:setComponentValue", { value, dataType: "json" });
}

window.addEventListener("message", e => {
    const msg = e.data;
    if (!msg || msg.type !== "streamlit:render") return;
    const args = msg.args || {};
    send("streamlit:setFrameHeight", { height: args.height || 640 });
    if (args.token === token) {
        if (MODE === "viewer") atualizarGatoTelao(args.cat);
        return;
    }
    token = args.token;
    init(args);
});

let ultimoEnvio = 0;
let envioPendente = null;

function gatoAtual() {
    const cat = findItem("cat");
    return cat && { x: r1(cat.x), y: r1(cat.y), w: r1(cat.w), rot: cat.rot, flip: cat.flip, z: cat.z };
}

function enviarMovimento() {
    if (MODE !== "player" || sent) return;
    clearTimeout(envioPendente);
    const falta = 150 - (Date.now() - ultimoEnvio);
    if (falta > 0) {
        envioPendente = setTimeout(enviarMovimento, falta);
        return;
    }
    ultimoEnvio = Date.now();
    setValue({ action: "move", turn: TURN, cat: gatoAtual() });
}

function atualizarGatoTelao(cat) {
    const atual = findItem("cat");
    if (!cat) {
        if (atual) {
            state.scenes[state.room] = items().filter(it => it.id !== "cat");
            renderBoard();
        }
        return;
    }
    if (!atual) {
        items().push({ ...cat, id: "cat", key: CAT_KEY, locked: true });
        renderBoard();
        return;
    }
    Object.assign(atual, cat);
    updateItemEl(atual);
}

send("streamlit:componentReady", { apiVersion: 1 });

function loadState() {
    try {
        const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
        if (saved && saved.scenes) return saved;
    } catch (e) { }
    return { room: DATA.rooms[0].id, scenes: {} };
}

function saveState() {
    if (MODE !== "editor") return;
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (e) { }
}

const room = () => DATA.rooms.find(r => r.id === state.room);
const items = () => (state.scenes[state.room] ||= []);
const boardH = () => Math.round(BOARD_W * room().ratio);
const findItem = id => items().find(it => it.id === id);
const newId = () => Math.random().toString(36).slice(2, 10);
const itemHeight = it => it.w * ASSETS[it.key].ratio;
const maxZ = () => items().reduce((m, it) => Math.max(m, it.z), 0);
const minZ = () => items().reduce((m, it) => Math.min(m, it.z), 0);
const r1 = n => Math.round(n * 10) / 10;

function init(args) {
    DATA = args.data;
    ASSETS = DATA.assets;
    BOARD_W = DATA.boardWidth;
    MODE = args.mode || "editor";
    TURN = args.turn ?? null;
    appEl.className = MODE;
    selectedId = null;
    sent = false;

    if (MODE === "player") {
        const scene = args.scene;
        const list = scene.items.map(it => ({ ...it, locked: true }));
        state = { room: scene.room, scenes: { [scene.room]: list } };
        const cat = ASSETS[CAT_KEY];
        list.push({
            id: "cat", key: CAT_KEY,
            x: BOARD_W - cat.width * 0.75,
            y: cat.width * cat.ratio * 0.75,
            w: cat.width, rot: 0, flip: false,
            z: maxZ() + 1,
        });
        selectedId = "cat";
    } else if (MODE === "viewer") {
        const scene = args.scene;
        const list = scene.items.map(it => ({ ...it, locked: true }));
        if (args.cat) list.push({ ...args.cat, id: "cat", key: CAT_KEY, locked: true });
        state = { room: scene.room, scenes: { [scene.room]: list } };
    } else {
        state = loadState();
        if (!DATA.rooms.some(r => r.id === state.room)) state.room = DATA.rooms[0].id;
        for (const id in state.scenes) {
            state.scenes[id] = state.scenes[id].filter(it => ASSETS[it.key] && it.key !== CAT_KEY);
        }
    }
    renderAll();
    if (MODE === "player") enviarMovimento();
}

function renderTabs() {
    tabsEl.innerHTML = "";
    for (const r of DATA.rooms) {
        const btn = document.createElement("button");
        btn.className = "tab" + (r.id === state.room ? " active" : "");
        const count = (state.scenes[r.id] || []).length;
        btn.innerHTML = r.label + (count ? `<span class="count">(${count})</span>` : "");
        btn.onclick = () => {
            state.room = r.id;
            selectedId = null;
            saveState();
            renderAll();
        };
        tabsEl.appendChild(btn);
    }
}

function thumb(key) {
    const a = ASSETS[key];
    const el = document.createElement("div");
    el.className = "thumb";
    el.title = "Drag onto the map or click to add";
    el.innerHTML = `<img src="${a.src}" alt=""><span>${a.name}</span>`;
    el.addEventListener("pointerdown", e => startPaletteDrag(e, key));
    return el;
}

function renderPalette() {
    paletteEl.innerHTML = "";
    if (MODE !== "editor") return;
    const sections = [
        ["Furniture", room().palette.filter(k => ASSETS[k].kind === "furniture")],
        ["Objects", room().palette.filter(k => ASSETS[k].kind === "object")],
    ];
    for (const [title, keys] of sections) {
        if (!keys.length) continue;
        const h = document.createElement("h4");
        h.textContent = title;
        const grid = document.createElement("div");
        grid.className = "grid";
        for (const k of keys) grid.appendChild(thumb(k));
        paletteEl.append(h, grid);
    }
}

function renderBoard() {
    const r = room();
    boardEl.style.width = BOARD_W + "px";
    boardEl.style.height = boardH() + "px";
    boardEl.style.backgroundImage = `url(${r.background})`;
    boardEl.innerHTML = "";

    const sorted = [...items()].sort((a, b) => a.z - b.z);
    for (const it of sorted) {
        const el = document.createElement("div");
        el.className = "item" + (it.locked ? " locked" : "") + (it.id === selectedId ? " selected" : "");
        el.dataset.id = it.id;
        el.innerHTML = `<img src="${ASSETS[it.key].src}" alt="">`;
        if (!it.locked) {
            el.innerHTML +=
                `<div class="handle rotate" data-handle="rotate" title="Rotate (Shift snaps 15°)"></div>` +
                `<div class="handle resize" data-handle="resize" title="Resize"></div>`;
            el.addEventListener("pointerdown", e => startItemDrag(e, it.id));
        }
        placeItem(el, it);
        boardEl.appendChild(el);
    }
    fitBoard();
    renderToolbar();
}

function placeItem(el, it) {
    const h = itemHeight(it);
    el.style.left = (it.x - it.w / 2) + "px";
    el.style.top = (it.y - h / 2) + "px";
    el.style.width = it.w + "px";
    el.style.height = h + "px";
    el.style.zIndex = it.z;
    el.style.transform = `rotate(${it.rot}deg)`;
    el.querySelector("img").style.transform = it.flip ? "scaleX(-1)" : "";
}

function updateItemEl(it) {
    const el = boardEl.querySelector(`.item[data-id="${it.id}"]`);
    if (el) placeItem(el, it);
}

function renderToolbar() {
    const it = selectedId && findItem(selectedId);
    nameEl.textContent = it && MODE === "editor" ? ASSETS[it.key].name : "";

    if (MODE === "player") {
        hintEl.textContent = sent
            ? "Resposta enviada! Aguarde o professor."
            : "Arraste o Whiskers até o lugar certo e clique em Enviar.";
        hintEl.style.display = "";
    } else {
        hintEl.textContent = "Monte a cena arrastando os itens e clique em Publicar.";
        hintEl.style.display = it ? "none" : "";
    }

    for (const btn of document.querySelectorAll(".tool[data-action]")) {
        const a = btn.dataset.action;
        const modes = (btn.dataset.modes || "editor").split(" ");
        if (!modes.includes(MODE)) {
            btn.style.display = "none";
            continue;
        }
        if (a === "clear") {
            btn.disabled = !items().length;
            btn.style.display = "";
        } else if (a === "publish") {
            btn.disabled = !items().length;
            btn.style.display = "";
        } else if (a === "submit") {
            btn.disabled = sent;
            btn.style.display = "";
        } else {
            btn.disabled = !it || sent || (a === "duplicate" && it.key === CAT_KEY);
            btn.style.display = it ? "" : "none";
        }
    }
}

function renderAll() {
    renderTabs();
    renderPalette();
    renderBoard();
}

function fitBoard() {
    if (!DATA) return;
    const w = stageEl.clientWidth;
    const h = stageEl.clientHeight;
    if (!w || !h) return;
    scale = Math.min(w / BOARD_W, h / boardH());
    boardEl.style.transform = `scale(${scale})`;
    boardEl.style.setProperty("--inv", 1 / scale);
    wrapEl.style.width = BOARD_W * scale + "px";
    wrapEl.style.height = boardH() * scale + "px";
}

new ResizeObserver(fitBoard).observe(stageEl);

function select(id) {
    selectedId = id;
    for (const el of boardEl.querySelectorAll(".item")) {
        el.classList.toggle("selected", el.dataset.id === id);
    }
    renderToolbar();
}

function commit() {
    saveState();
    if (MODE === "editor") renderTabs();
    renderToolbar();
    enviarMovimento();
}

function addItem(key, x, y) {
    const a = ASSETS[key];
    const jitter = () => (Math.random() - 0.5) * 80;
    const it = {
        id: newId(),
        key,
        x: x !== undefined ? x : BOARD_W / 2 + jitter(),
        y: y !== undefined ? y : boardH() * 0.65 + jitter(),
        w: a.width,
        rot: 0,
        flip: false,
        z: /carpet|rug/i.test(key) ? minZ() - 1 : maxZ() + 1,
    };
    items().push(it);
    selectedId = it.id;
    renderBoard();
    commit();
}

const actions = {
    front(it) { it.z = maxZ() + 1; },
    back(it) { it.z = minZ() - 1; },
    flip(it) { it.flip = !it.flip; },
    duplicate(it) {
        const copy = { ...it, id: newId(), x: it.x + 30, y: it.y + 30, z: maxZ() + 1 };
        items().push(copy);
        selectedId = copy.id;
    },
    remove(it) {
        state.scenes[state.room] = items().filter(o => o.id !== it.id);
        selectedId = null;
    },
};

function flashButton(action, text) {
    const btn = document.querySelector(`.tool[data-action="${action}"]`);
    const original = btn.dataset.label || (btn.dataset.label = btn.textContent);
    btn.textContent = text;
    setTimeout(() => { btn.textContent = original; }, 1800);
}

function publish() {
    const list = items()
        .filter(it => it.key !== CAT_KEY)
        .map(({ id, key, x, y, w, rot, flip, z }) => ({ id, key, x: r1(x), y: r1(y), w: r1(w), rot, flip, z }));
    if (!list.length) return;
    setValue({ action: "publish", scene: { room: state.room, items: list } });
    flashButton("publish", "Publicado!");
}

function submitAnswer() {
    if (sent) return;
    const cat = items().find(it => it.key === CAT_KEY);
    if (!cat) return;
    clearTimeout(envioPendente);
    sent = true;
    cat.locked = true;
    selectedId = null;
    setValue({
        action: "answer",
        turn: TURN,
        cat: { x: r1(cat.x), y: r1(cat.y), w: r1(cat.w), rot: cat.rot, flip: cat.flip, z: cat.z },
    });
    renderBoard();
}

function runAction(name) {
    if (name === "publish") return publish();
    if (name === "submit") return submitAnswer();
    if (name === "clear") {
        if (!items().length || !confirm(`Remove everything from ${room().label}?`)) return;
        state.scenes[state.room] = [];
        selectedId = null;
    } else {
        const it = selectedId && findItem(selectedId);
        if (!it || it.locked) return;
        actions[name](it);
    }
    renderBoard();
    commit();
}

for (const btn of document.querySelectorAll(".tool[data-action]")) {
    btn.addEventListener("click", () => runAction(btn.dataset.action));
}

function boardPoint(e) {
    const rect = boardEl.getBoundingClientRect();
    return { x: (e.clientX - rect.left) / scale, y: (e.clientY - rect.top) / scale };
}

function startPaletteDrag(e, key) {
    e.preventDefault();
    const start = { x: e.clientX, y: e.clientY };
    let dragging = false;
    ghostEl.querySelector("img").src = ASSETS[key].src;

    const move = ev => {
        if (!dragging && Math.hypot(ev.clientX - start.x, ev.clientY - start.y) > 5) {
            dragging = true;
            ghostEl.style.display = "block";
        }
        if (dragging) {
            ghostEl.style.left = ev.clientX + "px";
            ghostEl.style.top = ev.clientY + "px";
        }
    };

    const up = ev => {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", up);
        ghostEl.style.display = "none";
        if (!dragging) return addItem(key);
        const p = boardPoint(ev);
        if (p.x >= 0 && p.y >= 0 && p.x <= BOARD_W && p.y <= boardH()) addItem(key, p.x, p.y);
    };

    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
}

function startItemDrag(e, id) {
    e.preventDefault();
    e.stopPropagation();
    const it = findItem(id);
    if (!it || it.locked) return;
    if (selectedId !== id) select(id);

    const mode = e.target.dataset.handle || "move";
    const p0 = boardPoint(e);
    const orig = { ...it };
    const dist0 = Math.max(Math.hypot(p0.x - it.x, p0.y - it.y), 1);
    let changed = false;

    const move = ev => {
        const p = boardPoint(ev);
        if (mode === "move") {
            it.x = Math.min(Math.max(orig.x + p.x - p0.x, 0), BOARD_W);
            it.y = Math.min(Math.max(orig.y + p.y - p0.y, 0), boardH());
        } else if (mode === "resize") {
            const dist = Math.hypot(p.x - it.x, p.y - it.y);
            it.w = Math.max(20, orig.w * dist / dist0);
        } else if (mode === "rotate") {
            let angle = Math.atan2(p.y - it.y, p.x - it.x) * 180 / Math.PI + 90;
            if (ev.shiftKey) angle = Math.round(angle / 15) * 15;
            it.rot = Math.round(((angle % 360) + 360) % 360);
        }
        changed = true;
        updateItemEl(it);
        enviarMovimento();
    };

    const up = () => {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", up);
        if (changed) commit();
    };

    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
}

boardEl.addEventListener("pointerdown", e => {
    if (e.target === boardEl) select(null);
});

window.addEventListener("keydown", e => {
    const it = selectedId && findItem(selectedId);
    if (!it || it.locked) return;
    const step = e.shiftKey ? 10 : 2;
    const moves = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
    const editor = MODE === "editor";

    if (editor && (e.key === "Delete" || e.key === "Backspace")) {
        runAction("remove");
    } else if (e.key === "Escape") {
        select(null);
    } else if (editor && (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "d") {
        runAction("duplicate");
    } else if (moves[e.key]) {
        it.x += moves[e.key][0];
        it.y += moves[e.key][1];
        updateItemEl(it);
        saveState();
        enviarMovimento();
    } else {
        return;
    }
    e.preventDefault();
});
