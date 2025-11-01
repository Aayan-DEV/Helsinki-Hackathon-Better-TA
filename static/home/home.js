// Enhance the login redirect with JS (anchor href is already set)
document.addEventListener('DOMContentLoaded', () => {
  const loginBtn = document.getElementById('login-btn');
  if (!loginBtn) return;

  loginBtn.addEventListener('click', (e) => {
    // If you prefer to handle via JS only, uncomment below:
    // e.preventDefault();
    // window.location.href = '/auth/login/';

    // With direct anchor, no JS needed; this is here for future hooks.
  });
});