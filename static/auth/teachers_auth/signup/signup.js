// Fill with your Supabase values
const SUPABASE_URL = 'YOUR_SUPABASE_URL';
const SUPABASE_ANON_KEY = 'YOUR_SUPABASE_ANON_KEY';

const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const rulesEl = {
  length: document.getElementById('rule-length'),
  upper: document.getElementById('rule-upper'),
  number: document.getElementById('rule-number'),
  special: document.getElementById('rule-special'),
  match: document.getElementById('rule-match'),
};

function markRule(el, ok) {
  el.classList.toggle('ok', ok);
  el.classList.toggle('bad', !ok);
}

function validatePassword(pw, confirmPw) {
  const hasLen = pw.length >= 8;
  const hasUpper = /[A-Z]/.test(pw);
  const hasNumber = /\d/.test(pw);
  const hasSpecial = /[^A-Za-z0-9]/.test(pw);
  const matches = pw === confirmPw;

  markRule(rulesEl.length, hasLen);
  markRule(rulesEl.upper, hasUpper);
  markRule(rulesEl.number, hasNumber);
  markRule(rulesEl.special, hasSpecial);
  markRule(rulesEl.match, matches);

  return hasLen && hasUpper && hasNumber && hasSpecial && matches;
}

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('teacherSignupForm');
  const firstName = document.getElementById('firstName');
  const lastName = document.getElementById('lastName');
  const title = document.getElementById('title');
  const specialCode = document.getElementById('specialCode');
  const email = document.getElementById('email');
  const password = document.getElementById('password');
  const confirmPassword = document.getElementById('confirmPassword');
  const phone = document.getElementById('phone');
  const googleBtn = document.getElementById('googleBtn');
  const signupBtn = document.getElementById('signupBtn');

  const handleRealtime = () => validatePassword(password.value, confirmPassword.value);
  password.addEventListener('input', handleRealtime);
  confirmPassword.addEventListener('input', handleRealtime);

  // Optional: greet if already logged in
  (async () => {
    const { data: { session } } = await supabase.auth.getSession();
    if (session) {
      window.showMessage?.('success', 'Already logged in.');
    }
  })();

  googleBtn.addEventListener('click', async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.origin, // landing back here for the toast
      },
    });
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    signupBtn.disabled = true;

    if (!validatePassword(password.value, confirmPassword.value)) {
      window.showMessage?.('error', 'Please meet all password requirements.');
      signupBtn.disabled = false;
      return;
    }

    // Supabase sign-up
    const { data, error } = await supabase.auth.signUp({
      email: email.value.trim(),
      password: password.value,
    });

    if (error) {
      window.showMessage?.('error', `Sign-up failed: ${error.message}`);
      signupBtn.disabled = false;
      return;
    }

    const userId = data.user?.id || null;

    // Optionally save profile in Supabase 'teachers' table
    const profile = {
      user_id: userId,
      first_name: firstName.value.trim(),
      last_name: lastName.value.trim(),
      title: title.value,
      special_code: specialCode.value.trim(),
      email: email.value.trim(),
      phone: phone.value.trim(),
    };
    const insertRes = await supabase.from('teachers').insert(profile).select();
    if (insertRes.error) {
      window.showMessage?.('warning', `Profile save warning: ${insertRes.error.message}`);
    }

    // Sync into Django (optional; ignores failure)
    try {
      await fetch('/teachers/register/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile),
      });
    } catch (err) {
      console.warn('Django sync failed:', err);
    }

    // Clear the page and show "Logged in!"
    const main = document.querySelector('main');
    if (main) {
      main.innerHTML = `
        <div class="min-h-[60vh] flex items-center justify-center">
          <div class="flex flex-col items-center gap-3">
            <div class="inline-flex items-center gap-2 rounded-md bg-neutral-900 text-white px-4 py-2">
              <span class="material-symbols-outlined">check_circle</span>
              <span class="font-medium">Logged in!</span>
            </div>
            <p class="text-sm text-neutral-600">Your account has been created successfully.</p>
          </div>
        </div>
      `;
    }

    window.showMessage?.('success', 'Logged in!');
    signupBtn.disabled = false;

    // If you want an auto-redirect, uncomment:
    // setTimeout(() => { window.location.href = '/teachers/dashboard/'; }, 2000);
  });
});