(function () {
  const call = (method, args) => {
    if (window.frappe && frappe.call) {
      return frappe.call({ method, args });
    }

    const metaToken = document.querySelector("meta[name='csrf-token']")?.content || "";
    const csrf = (window.frappe && frappe.csrf_token) || window.csrf_token || metaToken || "";
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

  const getUserKey = () => {
    const nav = document.querySelector(".site-nav");
    const user = nav?.dataset?.user || "Guest";
    return user;
  };

  const cartKey = () => `euro_cart:${getUserKey()}`;
  const wishlistKey = () => `euro_wishlist:${getUserKey()}`;

  const migrateLegacyStorage = () => {
    const legacyCart = localStorage.getItem("euro_cart");
    if (legacyCart && !localStorage.getItem(cartKey())) {
      localStorage.setItem(cartKey(), legacyCart);
      localStorage.removeItem("euro_cart");
    }
    const legacyWishlist = localStorage.getItem("euro_wishlist");
    if (legacyWishlist && !localStorage.getItem(wishlistKey())) {
      localStorage.setItem(wishlistKey(), legacyWishlist);
      localStorage.removeItem("euro_wishlist");
    }
  };

  const getCart = () => JSON.parse(localStorage.getItem(cartKey()) || "[]");
  const saveCart = (cart) => localStorage.setItem(cartKey(), JSON.stringify(cart));
  const cartTotal = (cart) =>
    cart.reduce((sum, item) => sum + (parseFloat(item.rate) || 0) * (item.qty || 1), 0);

  const renderCart = () => {
    const cart = getCart();
    const count = cart.reduce((sum, item) => sum + (item.qty || 1), 0);
    document.querySelectorAll("[data-cart-count]").forEach((el) => {
      el.textContent = count;
      el.style.display = count ? "inline-flex" : "none";
    });
    document.querySelectorAll("[data-cart-toggle]").forEach((el) => {
      el.style.display = count ? "inline-flex" : "none";
    });

    const cartItems = document.getElementById("cart-items");
    const cartTotalEl = document.getElementById("cart-total");
    const cartSubtotalEl = document.getElementById("cart-subtotal");
    const cartShippingEl = document.getElementById("cart-shipping");
    const cartCountHeader = document.getElementById("cart-count-header");
    if (cartItems) {
      if (!cart.length) {
        cartItems.innerHTML = "<p class='muted'>Your cart is empty.</p>";
      } else {
        cartItems.innerHTML = cart
          .map(
            (item) => `
            <div class="cart-row">
              <div class="cart-thumb" style="background-image: url('${item.image || '/assets/frappe/images/ui/placeholder-image.png'}')">
                <span class="cart-badge">Sale!</span>
              </div>
              <div class="cart-info">
                <div class="cart-top">
                  <div class="cart-name">${item.item_name}</div>
                  <button class="cart-remove" type="button" data-cart-remove="${item.item_code}">×</button>
                </div>
                <div class="cart-meta">
                  Rs ${(item.rate || 0).toFixed(2)}
                  <span class="cart-savings">You saved 12.5%</span>
                </div>
                <div class="cart-actions">
                  <button class="qty-btn" data-cart-minus="${item.item_code}">−</button>
                  <span class="qty-value">${item.qty || 1}</span>
                  <button class="qty-btn" data-cart-plus="${item.item_code}">+</button>
                </div>
              </div>
            </div>
          `
          )
          .join("");
      }
    }
    if (cartTotalEl) {
      const total = cartTotal(cart);
      cartTotalEl.textContent = `Rs ${total.toFixed(2)}`;
      const subtotalEl = document.getElementById("cart-subtotal");
      if (subtotalEl) {
        const subtotal = total / 0.875;
        subtotalEl.textContent = `Rs ${subtotal.toFixed(2)}`;
      }
      const savingsEl = document.getElementById("cart-savings");
      if (savingsEl) {
        const savings = (total / 0.875) - total;
        savingsEl.textContent = `You saved Rs ${savings.toFixed(2)}`;
      }
    }
    if (cartSubtotalEl) {
      cartSubtotalEl.textContent = cartTotal(cart).toFixed(2);
    }
    if (cartShippingEl) {
      cartShippingEl.textContent = "0";
    }
    const compactTotal = document.getElementById("cart-total-compact");
    if (compactTotal) {
      compactTotal.textContent = `Rs ${cartTotal(cart).toFixed(2)}`;
    }
    if (cartCountHeader) {
      cartCountHeader.textContent = cart.reduce((sum, item) => sum + (item.qty || 1), 0);
    }
  };

  const mergeCartItems = (base, incoming) => {
    const map = new Map(base.map((item) => [item.item_code, { ...item }]));
    incoming.forEach((item) => {
      if (!item.item_code) return;
      const existing = map.get(item.item_code);
      if (existing) {
        existing.qty = (existing.qty || 1) + (item.qty || 1);
      } else {
        map.set(item.item_code, { ...item });
      }
    });
    return Array.from(map.values());
  };

  const refreshCartPrices = async () => {
    if (getUserKey() === "Guest") return;
    const cart = getCart();
    if (!cart.length) return;
    const itemCodes = cart.map((item) => item.item_code).filter(Boolean);
    if (!itemCodes.length) return;
    try {
      const result = await call("euro_website.api.get_item_prices", { item_codes: itemCodes });
      const data = result.message || result;
      const prices = data?.prices || {};
      const updated = cart.map((item) => ({
        ...item,
        rate: prices[item.item_code] != null ? prices[item.item_code] : item.rate,
      }));
      saveCart(updated);
      renderCart();
    } catch (e) {
      // Ignore price refresh errors
    }
  };

  const migrateGuestCart = () => {
    if (getUserKey() === "Guest") return;
    const guestKey = "euro_cart:Guest";
    const guestCart = JSON.parse(localStorage.getItem(guestKey) || "[]");
    if (!guestCart.length) return;
    const current = getCart();
    const merged = mergeCartItems(current, guestCart);
    saveCart(merged);
    localStorage.removeItem(guestKey);
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
    if (target?.dataset?.qtyPlus) {
      const input = document.getElementById(target.dataset.qtyPlus);
      if (input) input.value = Math.max(1, parseInt(input.value || "1", 10) + 1);
    }
    if (target?.dataset?.qtyMinus) {
      const input = document.getElementById(target.dataset.qtyMinus);
      if (input) input.value = Math.max(1, parseInt(input.value || "1", 10) - 1);
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
      const qtyInputId = button.getAttribute("data-qty-input");
      const qtyInput = qtyInputId ? document.getElementById(qtyInputId) : null;
      const qty = Math.max(1, parseInt(qtyInput?.value || "1", 10));
      if (!itemCode) return;

      const cart = getCart();
      const existing = cart.find((entry) => entry.item_code === itemCode);
      if (existing) {
        existing.qty += qty;
      } else {
        cart.push({
          item_code: itemCode,
          item_name: itemName || itemCode,
          route: itemRoute || itemCode,
          image: itemImage || "",
          rate: parseFloat(itemPrice) || 0,
          qty,
        });
      }
      saveCart(cart);
      renderCart();
      openCart();
    });
  });

  const buyButtons = document.querySelectorAll("[data-buy-now]");
  buyButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const itemCode = button.getAttribute("data-item-code");
      const itemName = button.getAttribute("data-item-name");
      const itemRoute = button.getAttribute("data-item-route");
      const itemImage = button.getAttribute("data-item-image");
      const itemPrice = button.getAttribute("data-item-price");
      const qtyInputId = button.getAttribute("data-qty-input");
      const qtyInput = qtyInputId ? document.getElementById(qtyInputId) : null;
      const qty = Math.max(1, parseInt(qtyInput?.value || "1", 10));
      if (!itemCode) return;

      const cart = getCart();
      cart.length = 0;
      cart.push({
        item_code: itemCode,
        item_name: itemName || itemCode,
        route: itemRoute || itemCode,
        image: itemImage || "",
        rate: parseFloat(itemPrice) || 0,
        qty,
      });
      saveCart(cart);
      window.location.href = "/checkout";
    });
  });

  const toggleWishlist = (item, button) => {
    const list = JSON.parse(localStorage.getItem(wishlistKey()) || "[]");
    const exists = list.find((entry) => entry.item_code === item.item_code);
    let updated;
    if (exists) {
      updated = list.filter((entry) => entry.item_code !== item.item_code);
    } else {
      updated = [...list, item];
    }
    localStorage.setItem(wishlistKey(), JSON.stringify(updated));
    if (button) {
      button.classList.toggle("is-active", !exists);
      button.textContent = !exists ? "♥" : "♡";
    }
    wishlistCount();
    renderWishlist();
  };

  const addWishlistButtons = document.querySelectorAll("[data-add-to-wishlist],[data-wishlist-toggle]");
  addWishlistButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const itemCode = button.getAttribute("data-item-code");
      const itemName = button.getAttribute("data-item-name");
      const itemRoute = button.getAttribute("data-item-route");
      const itemImage = button.getAttribute("data-item-image");
      if (!itemCode) return;
      toggleWishlist(
        {
          item_code: itemCode,
          item_name: itemName || itemCode,
          route: itemRoute || itemCode,
          image: itemImage || "",
        },
        button
      );
    });
  });

  const wishlistGrid = document.getElementById("wishlist-grid");
  const renderWishlist = () => {
    if (!wishlistGrid) return;
    const list = JSON.parse(localStorage.getItem(wishlistKey()) || "[]");
    const empty = document.getElementById("wishlist-empty");
    if (!list.length) {
      if (empty) empty.style.display = "block";
      wishlistGrid.innerHTML = "";
      return;
    }
    if (empty) empty.style.display = "none";
    wishlistGrid.innerHTML = list
      .map(
        (item) => `\n        <div class="product-card wishlist-card">\n          <a href="/store/${item.route}">\n            <div class="product-media" style="background-image: url('${item.image || '/assets/frappe/images/ui/placeholder-image.png'}')"></div>\n          </a>\n          <div class="product-body">\n            <div class="product-title">${item.item_name}</div>\n            <div class="product-cta">View details</div>\n            <button class="btn btn-ghost btn-small" type="button" data-wishlist-remove="${item.item_code}">Remove</button>\n          </div>\n        </div>\n      `
      )
      .join("");
  };
  renderWishlist();

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (target?.dataset?.wishlistRemove) {
      const itemCode = target.dataset.wishlistRemove;
      const list = JSON.parse(localStorage.getItem(wishlistKey()) || "[]");
      const updated = list.filter((entry) => entry.item_code !== itemCode);
      localStorage.setItem(wishlistKey(), JSON.stringify(updated));
      wishlistCount();
      renderWishlist();
    }
  });

  const wishlistCount = () => {
    const list = JSON.parse(localStorage.getItem(wishlistKey()) || "[]");
    document.querySelectorAll("[data-wishlist-count]").forEach((el) => {
      el.textContent = list.length;
      el.style.display = list.length ? "inline-flex" : "none";
    });
    document.querySelectorAll(".icon-btn--wish").forEach((el) => {
      el.style.display = list.length ? "inline-flex" : "none";
    });
  };

  document.querySelectorAll("[data-user-menu]").forEach((button) => {
    button.addEventListener("click", () => {
      const wrapper = button.closest(".user-menu");
      wrapper?.classList.toggle("is-open");
    });
  });

  const addressHistoryKey = () => `euro_address_history:${getUserKey()}`;
  const saveAddressHistory = (entry) => {
    const history = JSON.parse(localStorage.getItem(addressHistoryKey()) || "[]");
    const exists = history.find(
      (item) => item.address_line1 === entry.address_line1 && item.city === entry.city
    );
    if (!exists) {
      history.unshift(entry);
      localStorage.setItem(addressHistoryKey(), JSON.stringify(history.slice(0, 5)));
    }
  };

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
    if (totalEl) totalEl.textContent = `Rs ${cartTotal(cart).toFixed(2)}`;
    const savingsEl = document.getElementById("checkout-savings");
    const subtotalEl = document.getElementById("checkout-subtotal");
    if (subtotalEl) {
      const subtotal = cartTotal(cart) / 0.875;
      subtotalEl.textContent = `Rs ${subtotal.toFixed(2)}`;
    }
    if (savingsEl) {
      const savings = (cartTotal(cart) / 0.875) - cartTotal(cart);
      savingsEl.textContent = `You saved Rs ${savings.toFixed(2)}`;
    }
  }

  const checkoutForm = document.getElementById("checkout-form");
  if (checkoutForm) {
    const datalist = document.getElementById("address-history");
    if (datalist) {
      const history = JSON.parse(localStorage.getItem(addressHistoryKey()) || "[]");
      datalist.innerHTML = history
        .map((item) => `<option value="${item.address_line1}">`)
        .join("");
    }

    if (window.frappe && frappe.session && frappe.session.user !== "Guest") {
      call("euro_website.api.get_checkout_profile", {}).then((result) => {
        const data = result.message || result;
        if (!data) return;
        if (data.full_name) checkoutForm.full_name.value = data.full_name;
        if (data.email) checkoutForm.email.value = data.email;
        if (data.phone) checkoutForm.phone.value = data.phone;
        if (data.address_line1) checkoutForm.address_line1.value = data.address_line1;
        if (data.city) checkoutForm.city.value = data.city;
        if (data.country) checkoutForm.country.value = data.country;
      });
    }

    const markError = (input, message) => {
      input.classList.add("input-error");
      input.setAttribute("aria-invalid", "true");
      if (message) input.setAttribute("title", message);
    };

    const clearErrors = () => {
      checkoutForm.querySelectorAll(".input-error").forEach((el) => {
        el.classList.remove("input-error");
        el.removeAttribute("aria-invalid");
      });
    };

    const validateStep = () => {
      clearErrors();
      const status = document.getElementById("checkout-status");
      const email = checkoutForm.email.value.trim();
      const fullName = checkoutForm.full_name.value.trim();
      const addressLine1 = checkoutForm.address_line1.value.trim();
      const city = checkoutForm.city.value.trim();
      const country = checkoutForm.country.value.trim();
      let valid = true;
      if (!fullName) {
        markError(checkoutForm.full_name, "Name required");
        valid = false;
      }
      if (!email || !/^\S+@\S+\.\S+$/.test(email)) {
        markError(checkoutForm.email, "Valid email required");
        valid = false;
      }
      if (!addressLine1) {
        markError(checkoutForm.address_line1, "Address required");
        valid = false;
      }
      if (!city) {
        markError(checkoutForm.city, "City required");
        valid = false;
      }
      if (!country) {
        markError(checkoutForm.country, "Country required");
        valid = false;
      }
      if (!valid) {
        status.textContent = "Please fix the highlighted fields.";
      }
      return valid;
    };

    checkoutForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const status = document.getElementById("checkout-status");
      const cart = getCart();
      if (!cart.length) {
        status.textContent = "Your cart is empty.";
        return;
      }

      if (!validateStep()) {
        return;
      }

      const addressLine1 = checkoutForm.address_line1.value.trim();
      const city = checkoutForm.city.value.trim();
      const country = checkoutForm.country.value.trim();

      status.textContent = "Placing order...";
      const payload = {
        full_name: checkoutForm.full_name.value.trim(),
        email: checkoutForm.email.value.trim(),
        phone: checkoutForm.phone.value,
        address_line1: addressLine1,
        city,
        country,
        notes: checkoutForm.notes.value,
        delivery_method: checkoutForm.delivery_method?.value,
        payment_method: checkoutForm.payment_method.value,
        update_profile: checkoutForm.update_profile?.checked ? 1 : 0,
        update_address: checkoutForm.update_address?.checked ? 1 : 0,
        billing_same: checkoutForm.billing_same?.checked ? 1 : 0,
        items: cart,
      };

      try {
        const result = await call("euro_website.api.place_order", payload);
        const server = result.message || result;
        const ok = server?.ok || server?.sales_order;
        if (ok) {
          const orderId = server?.sales_order;
          saveAddressHistory({ address_line1: addressLine1, city, country });
          localStorage.removeItem(cartKey());
          status.textContent = server.warning
            ? `Order placed: ${orderId}. Note: ${server.warning}`
            : `Order placed: ${orderId}`;
          window.location.href = `/order?order=${encodeURIComponent(orderId)}`;
        } else {
          const serverMsg = server?._server_messages || server?.exc || server?.message;
          status.textContent = serverMsg ? String(serverMsg) : "Unable to place order.";
        }
      } catch (error) {
        status.textContent = error?.message || "Unable to place order. Please try again.";
      }
    });
  }

  const profileForm = document.getElementById("profile-form");
  if (profileForm) {
    call("euro_website.api.get_profile", {}).then((result) => {
      const data = result.message || result;
      if (!data) return;
      profileForm.full_name.value = data.full_name || "";
      profileForm.email.value = data.email || "";
      profileForm.phone.value = data.phone || "";
    });

    profileForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const status = document.getElementById("profile-status");
      status.textContent = "Saving...";
      try {
        const result = await call("euro_website.api.update_profile", {
          full_name: profileForm.full_name.value,
          email: profileForm.email.value,
          phone: profileForm.phone.value,
        });
        const ok = result.message ? result.message.ok : result.ok;
        status.textContent = ok ? "Profile updated." : "Unable to update profile.";
      } catch (error) {
        status.textContent = "Unable to update profile.";
      }
    });
  }

  const addressForm = document.getElementById("address-form");
  if (addressForm) {
    const listEl = document.getElementById("address-list");
    const resetBtn = document.getElementById("address-reset");
    const status = document.getElementById("address-status");

    const loadAddresses = async () => {
      const result = await call("euro_website.api.list_addresses", {});
      const data = result.message || result || [];
      if (!listEl) return;
      listEl.innerHTML = data
        .map(
          (addr) => `
          <div class="address-row">
            <div>
              <div class="row-title">${addr.address_title || addr.name}</div>
              <div class="muted">${addr.address_type || "Shipping"} · ${addr.address_line1}, ${addr.city}, ${addr.country}</div>
              ${addr.is_primary_address || addr.is_shipping_address ? '<span class="badge badge--soft">Default</span>' : ''}
            </div>
            <div class="address-actions">
              <button class="btn btn-ghost btn-small" data-address-edit="${addr.name}">Edit</button>
              <button class="btn btn-ghost btn-small" data-address-delete="${addr.name}">Delete</button>
            </div>
          </div>
        `
        )
        .join("");
    };

    loadAddresses();

    addressForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      status.textContent = "Saving...";
      try {
        const result = await call("euro_website.api.save_address", {
          address_name: addressForm.address_name.value || null,
          address_title: addressForm.address_title.value,
          address_type: addressForm.address_type.value,
          address_line1: addressForm.address_line1.value,
          city: addressForm.city.value,
          country: addressForm.country.value,
          is_default: addressForm.is_default.checked ? 1 : 0,
        });
        const ok = result.message ? result.message.ok : result.ok;
        if (ok) {
          status.textContent = "Address saved.";
          addressForm.reset();
          addressForm.address_name.value = "";
          loadAddresses();
        } else {
          status.textContent = "Unable to save address.";
        }
      } catch (error) {
        status.textContent = "Unable to save address.";
      }
    });

    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        addressForm.reset();
        addressForm.address_name.value = "";
      });
    }

    listEl?.addEventListener("click", async (event) => {
      const target = event.target;
      if (target?.dataset?.addressEdit) {
        const result = await call("euro_website.api.list_addresses", {});
        const data = result.message || result || [];
        const addr = data.find((row) => row.name === target.dataset.addressEdit);
        if (!addr) return;
        addressForm.address_name.value = addr.name;
        addressForm.address_title.value = addr.address_title || "";
        addressForm.address_type.value = addr.address_type || "Shipping";
        addressForm.is_default.checked = (addr.address_type === "Billing" && addr.is_primary_address) ||
          (addr.address_type !== "Billing" && addr.is_shipping_address);
        addressForm.address_line1.value = addr.address_line1 || "";
        addressForm.city.value = addr.city || "";
        addressForm.country.value = addr.country || "";
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
      if (target?.dataset?.addressDelete) {
        status.textContent = "Deleting...";
        await call("euro_website.api.delete_address", { address_name: target.dataset.addressDelete });
        status.textContent = "Address removed.";
        loadAddresses();
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

  migrateLegacyStorage();
  migrateGuestCart();
  refreshCartPrices();
  renderCart();
  wishlistCount();
})();
