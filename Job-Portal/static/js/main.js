/* ================================================================
   JOB PORTAL — Main JS
   Handles: mobile nav, flash auto-dismiss, form validation helpers,
   file input previews, confirm dialogs.
================================================================= */

document.addEventListener('DOMContentLoaded', function () {

  /* ---------- Mobile nav toggle ---------- */
  const navToggle = document.querySelector('.nav-toggle');
  const mobileMenu = document.querySelector('.mobile-menu');
  if (navToggle && mobileMenu) {
    navToggle.addEventListener('click', function () {
      mobileMenu.classList.toggle('open');
    });
  }

  /* ---------- Auto-dismiss flash messages ---------- */
  document.querySelectorAll('.alert').forEach(function (alertEl, i) {
    setTimeout(function () {
      alertEl.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      alertEl.style.opacity = '0';
      alertEl.style.transform = 'translateX(30px)';
      setTimeout(function () { alertEl.remove(); }, 400);
    }, 4500 + i * 200);
  });

  /* ---------- File input preview (filename display) ---------- */
  document.querySelectorAll('input[type="file"]').forEach(function (input) {
    const label = input.closest('.file-drop');
    if (!label) return;
    const defaultText = label.querySelector('.file-drop-text')?.textContent;
    input.addEventListener('change', function () {
      const textEl = label.querySelector('.file-drop-text');
      if (input.files && input.files.length > 0 && textEl) {
        textEl.textContent = '📎 ' + input.files[0].name;
      } else if (textEl && defaultText) {
        textEl.textContent = defaultText;
      }
    });
  });

  /* ---------- Confirm before destructive actions ---------- */
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      const message = form.getAttribute('data-confirm') || 'Are you sure?';
      if (!window.confirm(message)) {
        e.preventDefault();
      }
    });
  });

  /* ---------- Password confirm client-side check ---------- */
  const pwForm = document.querySelector('form[data-check-password]');
  if (pwForm) {
    pwForm.addEventListener('submit', function (e) {
      const pw = pwForm.querySelector('input[name="password"]');
      const confirm = pwForm.querySelector('input[name="confirm_password"]');
      if (pw && confirm && pw.value !== confirm.value) {
        e.preventDefault();
        alert('Passwords do not match. Please check and try again.');
      }
    });
  }

  /* ---------- Applicant status dropdown -> auto submit ---------- */
  document.querySelectorAll('.status-select').forEach(function (select) {
    select.addEventListener('change', function () {
      select.closest('form').submit();
    });
  });

  /* ---------- Fade-up reveal on scroll ---------- */
  const revealEls = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && revealEls.length) {
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('fade-up');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });
    revealEls.forEach(function (el) { observer.observe(el); });
  }

  /* ---------- Job search filter auto-submit on select change ---------- */
  document.querySelectorAll('.filter-bar select').forEach(function (sel) {
    sel.addEventListener('change', function () {
      sel.closest('form').submit();
    });
  });
});
