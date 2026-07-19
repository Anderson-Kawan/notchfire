document.addEventListener('DOMContentLoaded', () => {
    configurarPreviewFoto();
    configurarToggleSenha();
});

function configurarPreviewFoto() {
    const input = document.getElementById('foto');
    const preview = document.getElementById('profilePreview');
    if (!input || !preview) return;

    input.addEventListener('change', () => {
        const file = input.files && input.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            preview.src = event.target.result;
        };
        reader.readAsDataURL(file);
    });
}

function configurarToggleSenha() {
    document.querySelectorAll('.toggle-password').forEach((button) => {
        button.addEventListener('click', () => {
            const input = button.closest('.password-input')?.querySelector('input');
            const icon = button.querySelector('i');
            if (!input || !icon) return;

            const showing = input.type === 'text';
            input.type = showing ? 'password' : 'text';
            icon.className = showing ? 'fa-solid fa-eye' : 'fa-solid fa-eye-slash';
            button.title = showing ? 'Mostrar senha' : 'Ocultar senha';
        });
    });
}
