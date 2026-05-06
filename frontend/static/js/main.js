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
});
