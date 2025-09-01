window.onload = function() {
    
    function applyInitialTheme() {
        const savedTheme = localStorage.getItem('theme');
        const button = document.getElementById('theme-switcher-button');

        if (!button) return; 

        if (savedTheme === 'dark') {
            document.body.classList.add('dark-theme');
            button.innerText = '☀️';
        } else {
            document.body.classList.remove('dark-theme');
            button.innerText = '🌙';
        }
    }

    applyInitialTheme();

    window.dash_clientside = window.dash_clientside || {};
    window.dash_clientside.clientside = {
        toggleTheme: function(n_clicks) {
            if (n_clicks === 0 || n_clicks === undefined) {
                return window.dash_clientside.no_update;
            }

            const isDark = document.body.classList.toggle('dark-theme');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            
            const button = document.getElementById('theme-switcher-button');
            if (button) {
                button.innerText = isDark ? '☀️' : '🌙';
            }

            return ''; 
        }
    };
};