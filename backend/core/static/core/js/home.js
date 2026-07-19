// home.js - Versão simplificada
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const icon = document.getElementById('toggle-icon');
    
    if (!sidebar || !icon) return;
    
    // Alterna a classe da sidebar
    sidebar.classList.toggle('closed');

    // Lógica de troca do ícone
    if (sidebar.classList.contains('closed')) {
        icon.classList.remove('fa-arrow-left');
        icon.classList.add('fa-bars'); 
    } else {
        icon.classList.remove('fa-bars');
        icon.classList.add('fa-arrow-left');
    }
}

// Opcional: Garantir que a sidebar comece aberta
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const icon = document.getElementById('toggle-icon');
    
    if (sidebar && !sidebar.classList.contains('closed')) {
        icon.classList.remove('fa-bars');
        icon.classList.add('fa-arrow-left');
    }
});