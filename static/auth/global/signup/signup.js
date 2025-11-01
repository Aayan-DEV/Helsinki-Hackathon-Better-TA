document.addEventListener('DOMContentLoaded', () => {
  const roleSelect = document.getElementById('roleSelect');
  const continueBtn = document.getElementById('continueBtn');

  roleSelect.addEventListener('change', () => {
    continueBtn.disabled = !roleSelect.value;
  });

  continueBtn.addEventListener('click', () => {
    const role = roleSelect.value;
    if (role === 'teacher') {
      window.location.href = '/auth/teachers/signup/';
    } else if (role === 'ta' || role === 'student') {
      alert('Sign-up for this role is coming soon.');
    }
  });
});