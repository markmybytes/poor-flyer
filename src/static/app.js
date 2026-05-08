function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-button').forEach(b => {
        b.classList.remove('border-b-2', 'border-blue-600', 'text-blue-600');
        b.classList.add('text-gray-500');
    });

    document.getElementById(tabName).classList.add('active');

    const btn = document.querySelector(`[data-tab="${tabName}"]`);
    btn.classList.remove('text-gray-500');
    btn.classList.add('border-b-2', 'border-blue-600', 'text-blue-600');
}

function toggleGroup(button) {
    const groupId = button.getAttribute('data-group-id');
    const content = document.getElementById(groupId);
    const icon = button.querySelector('.group-toggle-icon');

    if (content.classList.contains('hidden')) {
        content.classList.remove('hidden');
        icon.textContent = '▼';
    } else {
        content.classList.add('hidden');
        icon.textContent = '▶';
    }
}
