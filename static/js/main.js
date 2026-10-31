/* Event landing — interactions, validation, submission. */
(function () {
  "use strict";

  /* ---------- Scroll reveal ---------- */
  var revealEls = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
    );
    revealEls.forEach(function (el) { io.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add("is-visible"); });
  }

  /* ---------- Nav background on scroll ---------- */
  var nav = document.getElementById("nav");
  function onScroll() {
    if (window.scrollY > 24) nav.classList.add("is-scrolled");
    else nav.classList.remove("is-scrolled");
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  /* ---------- Form ---------- */
  var form = document.getElementById("reg-form");
  if (!form) return;

  var submitBtn = document.getElementById("submit-btn");
  var success = document.getElementById("success");
  var successReset = document.getElementById("success-reset");

  var EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
  var PHONE_RE = /^\+?[0-9][0-9\s\-()]{6,24}$/;

  function field(name) { return form.querySelector('[data-field="' + name + '"]'); }
  function input(name) { return form.querySelector('[name="' + name + '"]'); }

  function setError(name, message) {
    var el = field(name);
    if (!el) return;
    var err = el.querySelector("[data-error]");
    if (err) err.textContent = message || "";
    el.classList.toggle("is-invalid", !!message);
    if (!message) el.classList.add("is-valid");
  }
  function clearError(name) { setError(name, ""); }

  /* Field-level validators. Return error message or "" */
  var validators = {
    first_name: function (v) { return v.length >= 2 ? "" : "Укажите имя (минимум 2 символа)"; },
    last_name: function (v) { return v.length >= 2 ? "" : "Укажите фамилию (минимум 2 символа)"; },
    company: function (v) { return v.length >= 2 ? "" : "Укажите название компании"; },
    position: function (v) { return v.length >= 2 ? "" : "Укажите должность"; },
    phone: function (v) {
      if (!v) return "Укажите номер телефона";
      return PHONE_RE.test(v) ? "" : "Укажите корректный номер телефона";
    },
    email: function (v) {
      if (!v) return "Укажите электронную почту";
      return EMAIL_RE.test(v) ? "" : "Укажите корректный e-mail";
    },
    consent: function (v) { return v ? "" : "Необходимо согласие на обработку персональных данных"; }
  };

  var REQUIRED = ["first_name", "last_name", "company", "position", "phone", "email"];

  function validateField(name) {
    var value = input(name) ? input(name).value.trim() : "";
    var err = validators[name](value);
    setError(name, err);
    return !err;
  }

  REQUIRED.forEach(function (name) {
    var el = input(name);
    el.addEventListener("blur", function () {
      if (el.value.trim() !== "") validateField(name);
    });
    el.addEventListener("input", function () {
      if (field(name).classList.contains("is-invalid")) validateField(name);
    });
  });

  var consentBox = input("consent");
  consentBox.addEventListener("change", function () {
    if (field("consent").classList.contains("is-invalid") || consentBox.checked) {
      clearError("consent");
    }
  });

  /* Prevent double submit */
  var submitting = false;
  function setSubmitting(on) {
    submitting = on;
    submitBtn.disabled = on;
    submitBtn.classList.toggle("is-loading", on);
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (submitting) return;

    var firstInvalid = null;
    REQUIRED.forEach(function (name) {
      var ok = validateField(name);
      if (!ok && !firstInvalid) firstInvalid = name;
    });
    if (!consentBox.checked) {
      setError("consent", validators.consent(false));
      if (!firstInvalid) firstInvalid = "consent";
    }

    if (firstInvalid) {
      var target = input(firstInvalid) || consentBox;
      target.focus({ preventScroll: false });
      target.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    setSubmitting(true);

    var payload = {
      first_name: input("first_name").value.trim(),
      last_name: input("last_name").value.trim(),
      company: input("company").value.trim(),
      position: input("position").value.trim(),
      phone: input("phone").value.trim(),
      email: input("email").value.trim(),
      comments: input("comments").value.trim(),
      consent: consentBox.checked
    };

    fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(function (res) {
        return res.json().then(function (data) { return { status: res.status, data: data }; });
      })
      .then(function (result) {
        if (result.data.ok) {
          form.hidden = true;
          success.hidden = false;
          success.scrollIntoView({ behavior: "smooth", block: "center" });
          return;
        }
        /* Server-side field errors */
        if (result.data.errors) {
          Object.keys(result.data.errors).forEach(function (name) {
            setError(name, result.data.errors[name]);
          });
          var first = Object.keys(result.data.errors)[0];
          if (first) (input(first) || consentBox).focus();
        } else if (result.data.error) {
          alert(result.data.error);
        }
      })
      .catch(function () {
        alert("Не удалось отправить форму. Проверьте соединение и попробуйте еще раз.");
      })
      .finally(function () { setSubmitting(false); });
  });

  /* Reset to register another guest */
  successReset.addEventListener("click", function () {
    form.reset();
    document.querySelectorAll(".field").forEach(function (el) {
      el.classList.remove("is-invalid", "is-valid");
      var err = el.querySelector("[data-error]");
      if (err) err.textContent = "";
    });
    success.hidden = true;
    form.hidden = false;
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
})();