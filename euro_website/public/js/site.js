(function () {
  const call = (method, args) => {
    if (window.frappe && frappe.call) {
      return frappe.call({ method, args });
    }

    const csrf = (window.frappe && frappe.csrf_token) || window.csrf_token || "";
    return fetch(`/api/method/${method}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Frappe-CSRF-Token": csrf,
      },
      body: JSON.stringify(args || {}),
      credentials: "same-origin",
    }).then((response) => response.json());
  };

  const contactForm = document.getElementById("contact-form");
  if (contactForm) {
    contactForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const status = document.getElementById("contact-status");
      status.textContent = "Sending...";
      const payload = {
        full_name: contactForm.full_name.value,
        email: contactForm.email.value,
        message: contactForm.message.value,
      };

      try {
        const result = await call("euro_website.api.submit_contact", payload);
        const ok = result.message ? result.message.ok : result.ok;
        if (ok) {
          status.textContent = "Thanks. We'll reach out shortly.";
          contactForm.reset();
        } else {
          status.textContent = "Something went wrong. Try again.";
        }
      } catch (error) {
        status.textContent = "Unable to send. Please try later.";
      }
    });
  }

  const signupForm = document.getElementById("signup-form");
  if (signupForm) {
    signupForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const status = document.getElementById("signup-status");
      status.textContent = "Creating account...";
      const payload = {
        full_name: signupForm.full_name.value,
        email: signupForm.email.value,
        password: signupForm.password.value,
        is_trader: signupForm.is_trader.checked ? 1 : 0,
      };

      try {
        const result = await call("euro_website.api.signup_portal_user", payload);
        const ok = result.message ? result.message.ok : result.ok;
        if (ok) {
          status.textContent = "Account created. Please log in.";
          window.location.href = "/login?redirect-to=/portal";
        } else {
          status.textContent = "Unable to create account. Try again.";
        }
      } catch (error) {
        status.textContent = error?.message || "Unable to create account.";
      }
    });
  }

  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const status = document.getElementById("login-status");
      status.textContent = "Signing in...";
      try {
        const response = await fetch("/api/method/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            usr: loginForm.login_email.value,
            pwd: loginForm.login_password.value,
          }),
          credentials: "same-origin",
        });
        const result = await response.json();
        if (result.message === "Logged In" || result.home_page) {
          window.location.href = "/portal";
        } else {
          status.textContent = "Invalid credentials. Try again.";
        }
      } catch (error) {
        status.textContent = "Unable to sign in. Try again.";
      }
    });
  }

  const addButtons = document.querySelectorAll("[data-add-to-cart]");
  addButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const itemCode = button.getAttribute("data-item-code");
      if (!itemCode) return;

      button.disabled = true;
      button.textContent = "Adding...";

      try {
        await call("euro_website.api.update_cart", {
          item_code: itemCode,
          qty: 1,
        });
        button.textContent = "Added to cart";
        setTimeout(() => {
          button.disabled = false;
          button.textContent = "Add to cart";
        }, 1500);
      } catch (error) {
        button.disabled = false;
        button.textContent = "Add to cart";
        alert("Unable to add to cart. Please try again.");
      }
    });
  });

  const galleryMain = document.querySelector("[data-gallery-main]");
  const galleryThumbs = document.querySelectorAll("[data-gallery-thumb]");
  if (galleryMain && galleryThumbs.length) {
    galleryThumbs.forEach((thumb) => {
      thumb.addEventListener("click", () => {
        const img = thumb.getAttribute("data-gallery-thumb");
        if (!img) return;
        galleryMain.style.backgroundImage = `url('${img}')`;
        galleryThumbs.forEach((el) => el.classList.remove("is-active"));
        thumb.classList.add("is-active");
      });
    });
  }
})();
