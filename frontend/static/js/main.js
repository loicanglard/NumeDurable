// TrailMémoire — JavaScript minimal

document.addEventListener('DOMContentLoaded', function () {
    // Gestion des confirmations
    document.querySelectorAll('[data-confirm]').forEach(function (el) {
        el.addEventListener('click', function (e) {
            if (!confirm(el.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

    // Gestion du Thème (Sombre par défaut)
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        const updateToggleButton = (theme) => {
            // Si thème sombre -> on propose le soleil pour passer au clair ? 
            // Non, l'utilisateur demande : ☀️ quand sombre, 🌙 quand clair.
            themeToggle.innerText = theme === 'light' ? '🌙' : '☀️';
        };

        // État initial (déjà posé par le script inline dans base.html)
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
        updateToggleButton(currentTheme);

        themeToggle.addEventListener('click', () => {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            const newTheme = isDark ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateToggleButton(newTheme);
        });
    }

    initGreenITPanel();
});

function initGreenITPanel() {
    const panel = document.getElementById('greenit-panel');
    if (!panel || !window.performance) {
        return;
    }

    const byId = (id) => document.getElementById(id);
    const formatKB = (bytes) => `${(bytes / 1024).toFixed(1)} Ko`;
    const formatMs = (ms) => `${Math.max(0, ms).toFixed(0)} ms`;

    const update = () => {
        const navEntries = performance.getEntriesByType('navigation');
        const nav = navEntries && navEntries.length > 0 ? navEntries[0] : null;
        const resources = performance.getEntriesByType('resource') || [];

        const resourcesTransfer = resources.reduce((sum, entry) => sum + (entry.transferSize || 0), 0);
        const docTransfer = nav ? (nav.transferSize || nav.encodedBodySize || 0) : 0;
        const totalTransfer = resourcesTransfer + docTransfer;

        const requests = resources.length + 1;
        const cached = resources.filter((entry) => (entry.transferSize || 0) === 0).length;
        const cacheRatio = resources.length > 0 ? Math.round((cached / resources.length) * 100) : 0;

        let loadTime = 0;
        if (nav) {
            loadTime = nav.loadEventEnd > 0 ? nav.loadEventEnd - nav.startTime : nav.duration;
        }

        // Approximation Green IT: 1 Mo transfere ~= 0.8 gCO2e cote reseau/data center.
        const totalMB = totalTransfer / (1024 * 1024);
        const estimatedCO2 = totalMB * 0.8;

        const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
        const networkType = connection && connection.effectiveType ? connection.effectiveType : 'inconnu';

        byId('gi-weight').textContent = formatKB(totalTransfer);
        byId('gi-load').textContent = formatMs(loadTime);
        byId('gi-requests').textContent = String(requests);
        byId('gi-cache').textContent = `${cached} (${cacheRatio}%)`;
        byId('gi-co2').textContent = `${estimatedCO2.toFixed(2)} gCO2e`;
        byId('gi-network').textContent = networkType;

        const note = byId('gi-note');
        if (note) {
            const score = getEcoScore(totalTransfer, requests, loadTime);
            note.textContent = `Eco-score local: ${score}. Estimation indicative (navigateur, hors serveur).`;
        }
    };

    if (document.readyState === 'complete') {
        update();
    } else {
        window.addEventListener('load', update, { once: true });
    }
}

function getEcoScore(weightBytes, requests, loadTimeMs) {
    const weightScore = weightBytes < 700 * 1024 ? 1 : (weightBytes < 1300 * 1024 ? 2 : 3);
    const reqScore = requests < 35 ? 1 : (requests < 60 ? 2 : 3);
    const loadScore = loadTimeMs < 1200 ? 1 : (loadTimeMs < 2500 ? 2 : 3);
    const total = weightScore + reqScore + loadScore;
    if (total <= 3) return 'A';
    if (total <= 5) return 'B';
    if (total <= 7) return 'C';
    return 'D';
}
