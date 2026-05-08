function switchTab(tabName) {
    const tabs = document.querySelectorAll('.tab-content');
    const buttons = document.querySelectorAll('.tab-button');

    tabs.forEach(tab => {
        tab.classList.remove('active');
    });

    buttons.forEach(btn => {
        btn.classList.remove('border-b-2', 'border-blue-600', 'text-blue-600');
        btn.classList.add('text-gray-600', 'hover:text-gray-900');
    });

    document.getElementById(tabName).classList.add('active');

    const activeBtn = document.querySelector(`[data-tab="${tabName}"]`);
    activeBtn.classList.remove('text-gray-600', 'hover:text-gray-900');
    activeBtn.classList.add('border-b-2', 'border-blue-600', 'text-blue-600');
}

function toggleRuleMode() {
    const mode = document.querySelector('input[name="rule_mode"]:checked').value;
    const fixedWindow = document.getElementById('fixed_window_fields');
    const perDataPoints = document.getElementById('per_data_points_fields');

    if (mode === 'fixed_window') {
        fixedWindow.classList.remove('hidden');
        perDataPoints.classList.add('hidden');
    } else {
        fixedWindow.classList.add('hidden');
        perDataPoints.classList.remove('hidden');
    }
}
