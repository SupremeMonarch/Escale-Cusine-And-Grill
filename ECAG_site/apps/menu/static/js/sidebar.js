// static/js/sidebar.js

document.addEventListener("DOMContentLoaded", () => {
  // ===== SIDEBAR TOGGLE =====
  const sidebarBtn = document.getElementById("sidebar-button");
  const sidebar = document.getElementById("order-sidebar");

  if (sidebarBtn && sidebar) {
    sidebarBtn.addEventListener("click", () => {
      const isHidden =
        sidebar.style.transform === "" ||
        sidebar.style.transform === "translateX(100%)";
      sidebar.style.transform = isHidden ? "translateX(0)" : "translateX(100%)";
    });
  }

  // ===== CART STATE & DOM NODES =====
  const orderItemsContainer = document.getElementById("order-items");
  const countEl = document.getElementById("order-count");
  const deliveryEl = document.getElementById("order-delivery");
  const totalEl = document.getElementById("order-total");

  let cart = JSON.parse(localStorage.getItem("ecag_cart") || "[]");
  let deliveryFee = 0; // only 100 when 'delivery' is active

  // ===== ORDER TYPE BUTTONS & SLIDER =====
  const dineBtn = document.getElementById("order-type-dinein");
  const pickupBtn = document.getElementById("order-type-pickup");
  const deliveryBtn = document.getElementById("order-type-delivery");
  const slider = document.getElementById("order-type-slider");

  const orderButtons = [dineBtn, pickupBtn, deliveryBtn];

  function setOrderType(type) {
    // type is one of "dine_in", "pick_up", "delivery"
    orderButtons.forEach((btn) => {
      if (!btn) return;
      const isActive = btn.dataset.orderType === type;

      // icons use stroke="currentColor", text inherits color – so we just set button color
      btn.style.color = isActive ? "#ffffff" : "#000000";
    });

    // move the orange slider
    if (slider) {
      if (type === "dine_in") {
        slider.style.left = "4px";
      } else if (type === "pick_up") {
        slider.style.left = "calc(33.33% + 4px)";
      } else if (type === "delivery") {
        slider.style.left = "calc(66.66% + 4px)";
      }
    }

    // delivery fee only for Delivery
    deliveryFee = type === "delivery" ? 100 : 0;
    updateSummary();
  }

  if (dineBtn) {
    dineBtn.addEventListener("click", () => setOrderType("dine_in"));
  }
  if (pickupBtn) {
    pickupBtn.addEventListener("click", () => setOrderType("pick_up"));
  }
  if (deliveryBtn) {
    deliveryBtn.addEventListener("click", () => setOrderType("delivery"));
  }

  // default to Dine In when page loads
  setOrderType("dine_in");

  // ===== CART FUNCTIONS =====
  function saveCart() {
    localStorage.setItem("ecag_cart", JSON.stringify(cart));
  }

  function updateSummary() {
    const totalItems = cart.reduce((sum, item) => sum + item.qty, 0);
    const itemsTotal = cart.reduce(
      (sum, item) => sum + item.qty * item.price,
      0
    );
    const grandTotal = itemsTotal + deliveryFee;

    if (countEl) countEl.textContent = String(totalItems);
    if (deliveryEl) deliveryEl.textContent = String(deliveryFee);
    if (totalEl) totalEl.textContent = String(grandTotal);
  }

  function renderCart() {
    if (!orderItemsContainer) return;

    orderItemsContainer.innerHTML = "";

    if (cart.length === 0) {
      orderItemsContainer.innerHTML =
        '<p style="color:#9ca3af;font-size:16px;margin:16px 0;">Your order is empty</p>';
      updateSummary();
      return;
    }

    cart.forEach((item, index) => {
      const row = document.createElement("div");
      row.style.display = "flex";
      row.style.alignItems = "center";
      row.style.justifyContent = "space-between";
      row.style.padding = "8px 0";
      row.style.borderBottom = "1px solid #f3f4f6";

      // left side: name + price
      const left = document.createElement("div");

      const nameEl = document.createElement("div");
      nameEl.textContent = item.name;
      nameEl.style.fontWeight = "600";
      nameEl.style.fontSize = "14px";

      const priceEl = document.createElement("div");
      priceEl.textContent = `Rs ${item.price}`;
      priceEl.style.fontSize = "13px";
      priceEl.style.color = "#f97316";

      left.appendChild(nameEl);
      left.appendChild(priceEl);

      // right side: qty controls + remove
      const right = document.createElement("div");
      right.style.display = "flex";
      right.style.alignItems = "center";
      right.style.gap = "4px";

      const minusBtn = document.createElement("button");
      minusBtn.textContent = "-";
      Object.assign(minusBtn.style, {
        width: "24px",
        height: "24px",
        borderRadius: "9999px",
        border: "1px solid #d1d5db",
        background: "#ffffff",
        cursor: "pointer",
      });

      const qtyEl = document.createElement("span");
      qtyEl.textContent = String(item.qty);
      qtyEl.style.minWidth = "20px";
      qtyEl.style.textAlign = "center";

      const plusBtn = document.createElement("button");
      plusBtn.textContent = "+";
      Object.assign(plusBtn.style, {
        width: "24px",
        height: "24px",
        borderRadius: "9999px",
        border: "1px solid #d1d5db",
        background: "#ffffff",
        cursor: "pointer",
      });

      const removeBtn = document.createElement("button");
      removeBtn.textContent = "✕";
      Object.assign(removeBtn.style, {
        marginLeft: "4px",
        border: "none",
        background: "transparent",
        color: "#ef4444",
        cursor: "pointer",
      });

      minusBtn.addEventListener("click", () => {
        if (cart[index].qty > 1) {
          cart[index].qty -= 1;
        } else {
          cart.splice(index, 1);
        }
        saveCart();
        renderCart();
      });

      plusBtn.addEventListener("click", () => {
        cart[index].qty += 1;
        saveCart();
        renderCart();
      });

      removeBtn.addEventListener("click", () => {
        cart.splice(index, 1);
        saveCart();
        renderCart();
      });

      right.appendChild(minusBtn);
      right.appendChild(qtyEl);
      right.appendChild(plusBtn);
      right.appendChild(removeBtn);

      row.appendChild(left);
      row.appendChild(right);
      orderItemsContainer.appendChild(row);
    });

    updateSummary();
  }

  // ===== ADD TO CART FROM MENU =====
  document.querySelectorAll("[data-add-to-cart]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const name = btn.getAttribute("data-name");
      const price = parseFloat(btn.getAttribute("data-price") || "0");

      if (!name || isNaN(price)) return;

      const existing = cart.find(
        (item) => item.name === name && item.price === price
      );
      if (existing) {
        existing.qty += 1;
      } else {
        cart.push({ name, price, qty: 1 });
      }

      saveCart();
      renderCart();

      // open sidebar whenever an item is added
      if (sidebar) {
        sidebar.style.transform = "translateX(0)";
      }
    });
  });

  // initial render (load cart from localStorage)
  renderCart();
});
