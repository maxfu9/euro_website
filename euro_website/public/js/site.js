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

  const getCart = () => JSON.parse(localStorage.getItem("euro_cart") || "[]");
  const saveCart = (cart) => localStorage.setItem("euro_cart", JSON.stringify(cart));
  const cartTotal = (cart) =>
    cart.reduce((sum, item) => sum + (parseFloat(item.rate) || 0) * (item.qty || 1), 0);

  const renderCart = () => {
    const cart = getCart();
    const count = cart.reduce((sum, item) => sum + (item.qty || 1), 0);
    document.querySelectorAll("[data-cart-count]").forEach((el) => {
      el.textContent = count;
    });

    const cartItems = document.getElementById("cart-items");
    const cartTotalEl = document.getElementById("cart-total");
    if (cartItems) {
      if (!cart.length) {
        cartItems.innerHTML = "<p class='muted'>Your cart is empty.</p>";
      } else {
        cartItems.innerHTML = cart
          .map(
            (item) => `
            <div class="cart-row">
              <div class="cart-thumb" style="background-image: url('${item.image || '/assets/frappe/images/ui/placeholder-image.png'}')"></div>
              <div class="cart-info">
                <div class="cart-name">${item.item_name}</div>
                <div class="cart-meta">${item.qty} × ${item.rate}</div>
                <div class="cart-actions">
                  <button class="btn btn-ghost btn-small" data-cart-minus="${item.item_code}">-</button>
                  <button class="btn btn-ghost btn-small" data-cart-plus="${item.item_code}">+</button>
                  <button class="btn btn-ghost btn-small" data-cart-remove="${item.item_code}">Remove</button>
                </div>
              </div>
            </div>
          `
          )
          .join("");
      }
    }
    if (cartTotalEl) {
      cartTotalEl.textContent = cartTotal(cart).toFixed(2);
    }
  };

  const openCart = () => {
    document.querySelector(".cart-drawer")?.classList.add("is-open");
    document.querySelector(".cart-backdrop")?.classList.add("is-open");
  };

  const closeCart = () => {
    document.querySelector(".cart-drawer")?.classList.remove("is-open");
    document.querySelector(".cart-backdrop")?.classList.remove("is-open");
  };

  document.querySelectorAll("[data-cart-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      renderCart();
      openCart();
    });
  });

  document.querySelectorAll("[data-cart-close]").forEach((button) => {
    button.addEventListener("click", closeCart);
  });

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (target?.dataset?.cartPlus) {
      const cart = getCart();
      const item = cart.find((entry) => entry.item_code === target.dataset.cartPlus);
      if (item) item.qty += 1;
      saveCart(cart);
      renderCart();
    }
    if (target?.dataset?.cartMinus) {
      const cart = getCart();
      const item = cart.find((entry) => entry.item_code === target.dataset.cartMinus);
      if (item) item.qty = Math.max(1, item.qty - 1);
      saveCart(cart);
      renderCart();
    }
    if (target?.dataset?.cartRemove) {
      const cart = getCart().filter((entry) => entry.item_code !== target.dataset.cartRemove);
      saveCart(cart);
      renderCart();
    }
  });

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
    button.addEventListener("click", () => {
      const itemCode = button.getAttribute("data-item-code");
      const itemName = button.getAttribute("data-item-name");
      const itemRoute = button.getAttribute("data-item-route");
      const itemImage = button.getAttribute("data-item-image");
      const itemPrice = button.getAttribute("data-item-price");
      if (!itemCode) return;

      const cart = getCart();
      const existing = cart.find((entry) => entry.item_code === itemCode);
      if (existing) {
        existing.qty += 1;
      } else {
        cart.push({
          item_code: itemCode,
          item_name: itemName || itemCode,
          route: itemRoute || itemCode,
          image: itemImage || "",
          rate: parseFloat(itemPrice) || 0,
          qty: 1,
        });
      }
      saveCart(cart);
      renderCart();
      openCart();
    });
  });

  const addWishlistButtons = document.querySelectorAll("[data-add-to-wishlist]");
  addWishlistButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const itemCode = button.getAttribute("data-item-code");
      const itemName = button.getAttribute("data-item-name");
      const itemRoute = button.getAttribute("data-item-route");
      const itemImage = button.getAttribute("data-item-image");
      if (!itemCode) return;

      const list = JSON.parse(localStorage.getItem("euro_wishlist") || "[]");
      const exists = list.find((entry) => entry.item_code === itemCode);
      if (!exists) {
        list.push({
          item_code: itemCode,
          item_name: itemName || itemCode,
          route: itemRoute || itemCode,
          image: itemImage || "",
        });
        localStorage.setItem("euro_wishlist", JSON.stringify(list));
      }
      button.textContent = "Saved";
    });
  });

  const wishlistGrid = document.getElementById("wishlist-grid");
  if (wishlistGrid) {
    const list = JSON.parse(localStorage.getItem("euro_wishlist") || "[]");
    const empty = document.getElementById("wishlist-empty");
    if (!list.length) {
      if (empty) empty.style.display = "block";
      return;
    }

    wishlistGrid.innerHTML = list
      .map(
        (item) => `\n        <a class="product-card" href="/store/${item.route}">\n          <div class="product-media" style="background-image: url('${item.image || '/assets/frappe/images/ui/placeholder-image.png'}')"></div>\n          <div class="product-body">\n            <div class="product-title">${item.item_name}</div>\n            <div class="product-cta">View details</div>\n          </div>\n        </a>\n      `
      )
      .join("");
  }

  const checkoutSummary = document.getElementById("checkout-summary");
  if (checkoutSummary) {
    const cart = getCart();
    if (!cart.length) {
      checkoutSummary.innerHTML = "<p class='muted'>Your cart is empty.</p>";
    } else {
      checkoutSummary.innerHTML = cart
        .map(
          (item) => `
          <div class="checkout-row">
            <span>${item.item_name}</span>
            <span>${item.qty} × ${item.rate}</span>
          </div>
        `
        )
        .join("");
    }
    const totalEl = document.getElementById("checkout-total");
    if (totalEl) totalEl.textContent = cartTotal(cart).toFixed(2);
  }

  const checkoutForm = document.getElementById("checkout-form");
  if (checkoutForm) {
    checkoutForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const status = document.getElementById("checkout-status");
      const cart = getCart();
      if (!cart.length) {
        status.textContent = "Your cart is empty.";
        return;
      }

      status.textContent = "Placing order...";
      const payload = {
        full_name: checkoutForm.full_name.value,
        email: checkoutForm.email.value,
        phone: checkoutForm.phone.value,
        address_line1: checkoutForm.address_line1.value,
        city: checkoutForm.city.value,
        country: checkoutForm.country.value,
        notes: checkoutForm.notes.value,
        items: cart,
      };

      try {
        const result = await call("euro_website.api.place_order", payload);
        const ok = result.message ? result.message.ok : result.ok;
        if (ok) {
          localStorage.removeItem("euro_cart");
          status.textContent = `Order placed: ${result.message?.sales_order || result.sales_order}`;
          window.location.href = "/portal";
        } else {
          status.textContent = "Unable to place order.";
        }
      } catch (error) {
        status.textContent = "Unable to place order. Please try again.";
      }
    });
  }

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

  renderCart();
})();
