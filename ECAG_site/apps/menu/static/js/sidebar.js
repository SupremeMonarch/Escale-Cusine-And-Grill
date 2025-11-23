// static/js/sidebar.js
(function () {
  // ---- DOM ELEMENTS ----
  const sidebarButton = document.getElementById("sidebar-button");
  const sidebarPanel = document.getElementById("order-sidebar");

  const orderItemsContainer = document.getElementById("order-items");
  const orderCountEl = document.getElementById("order-count");
  const orderDeliveryEl = document.getElementById("order-delivery");
  const orderTotalEl = document.getElementById("order-total");

  const orderTypeWrapper = document.getElementById("order-type-wrapper");
  const orderTypeSlider = document.getElementById("order-type-slider");
  const dineInBtn = document.getElementById("order-type-dinein");
  const pickUpBtn = document.getElementById("order-type-pickup");
  const deliveryBtn = document.getElementById("order-type-delivery");

  // ---- SIDEBAR OPEN/CLOSE ----
  function openSidebar() {
    if (sidebarPanel) sidebarPanel.style.transform = "translateX(0)";
  }

  function closeSidebar() {
    if (sidebarPanel) sidebarPanel.style.transform = "translateX(100%)";
  }

  if (sidebarButton && sidebarPanel) {
    sidebarButton.addEventListener("click", function () {
      const isHidden =
        sidebarPanel.style.transform === "" ||
        sidebarPanel.style.transform === "translateX(100%)";
      if (isHidden) openSidebar();
      else closeSidebar();
    });
  }

  // ---- CART STATE (PERSISTED) ----
  let cart = [];
  try {
    const saved = localStorage.getItem("ecag_cart");
    if (saved) cart = JSON.parse(saved);
  } catch (e) {
    cart = [];
  }

  function saveCart() {
    try {
      localStorage.setItem("ecag_cart", JSON.stringify(cart));
    } catch (e) {}
  }

  // ---- ORDER TYPE STATE ----
  let currentOrderType =
    localStorage.getItem("ecag_order_type") || "dine_in";
  let currentDeliveryFee =
    currentOrderType === "delivery" ? 100 : 0;

  function saveOrderType() {
    try {
      localStorage.setItem("ecag_order_type", currentOrderType);
    } catch (e) {}
  }

  // ---- TOTALS + RENDER ----
  function recalcTotals() {
    const itemsCount = cart.reduce((sum, item) => sum + item.qty, 0);
    const subtotal = cart.reduce(
      (sum, item) => sum + item.qty * item.price,
      0
    );
    const total = subtotal + currentDeliveryFee;

    if (orderCountEl) orderCountEl.textContent = String(itemsCount);
    if (orderDeliveryEl)
      orderDeliveryEl.textContent = String(currentDeliveryFee);
    if (orderTotalEl) orderTotalEl.textContent = String(total);
  }

  function renderCart() {
    if (!orderItemsContainer) {
      recalcTotals();
      return;
    }

    orderItemsContainer.innerHTML = "";

    if (cart.length === 0) {
      const p = document.createElement("p");
      p.textContent = "Your order is empty";
      p.style.color = "#9ca3af";
      p.style.textAlign = "center";
      orderItemsContainer.appendChild(p);
      recalcTotals();
      return;
    }

    cart.forEach((item, index) => {
      const row = document.createElement("div");
      row.style.display = "flex";
      row.style.alignItems = "center";
      row.style.justifyContent = "space-between";
      row.style.padding = "8px 0";
      row.style.borderBottom = "1px solid #f3f4f6";

      const left = document.createElement("div");
      left.style.display = "flex";
      left.style.flexDirection = "column";

      const nameEl = document.createElement("span");
      nameEl.textContent = item.name;
      nameEl.style.fontWeight = "600";
      nameEl.style.fontSize = "14px";

      const priceEl = document.createElement("span");
      priceEl.textContent = "Rs " + item.price;
      priceEl.style.fontSize = "12px";
      priceEl.style.color = "#6b7280";

      left.appendChild(nameEl);
      left.appendChild(priceEl);

      const right = document.createElement("div");
      right.style.display = "flex";
      right.style.alignItems = "center";
      right.style.gap = "4px";

      const minusBtn = document.createElement("button");
      minusBtn.textContent = "-";
      minusBtn.style.padding = "2px 6px";
      minusBtn.style.border = "1px solid #d1d5db";
      minusBtn.style.background = "#fff";
      minusBtn.style.cursor = "pointer";
      minusBtn.onclick = function () {
        if (item.qty > 1) {
          item.qty -= 1;
        } else {
          cart.splice(index, 1);
        }
        saveCart();
        renderCart();
      };

      const qtySpan = document.createElement("span");
      qtySpan.textContent = String(item.qty);
      qtySpan.style.minWidth = "20px";
      qtySpan.style.textAlign = "center";

      const plusBtn = document.createElement("button");
      plusBtn.textContent = "+";
      plusBtn.style.padding = "2px 6px";
      plusBtn.style.border = "1px solid #d1d5db";
      plusBtn.style.background = "#fff";
      plusBtn.style.cursor = "pointer";
      plusBtn.onclick = function () {
        item.qty += 1;
        saveCart();
        renderCart();
      };

      const removeBtn = document.createElement("button");
      removeBtn.textContent = "✕";
      removeBtn.style.border = "none";
      removeBtn.style.background = "transparent";
      removeBtn.style.color = "#ef4444";
      removeBtn.style.cursor = "pointer";
      removeBtn.onclick = function () {
        cart.splice(index, 1);
        saveCart();
        renderCart();
      };

      right.appendChild(minusBtn);
      right.appendChild(qtySpan);
      right.appendChild(plusBtn);
      right.appendChild(removeBtn);

      row.appendChild(left);
      row.appendChild(right);

      orderItemsContainer.appendChild(row);
    });

    recalcTotals();
  }

  // ---- GLOBAL addToCart (still here, just in case) ----
  window.addToCart = function (name, price) {
    const numericPrice = Number(price);
    const existing = cart.find(
      (i) => i.name === name && i.price === numericPrice
    );
    if (existing) {
      existing.qty += 1;
    } else {
      cart.push({ name, price: numericPrice, qty: 1 });
    }
    saveCart();
    renderCart();
    openSidebar();
  };

  // ---- ORDER TYPE SLIDER ----
  function updateOrderTypeSlider(activeIndex) {
    if (!orderTypeWrapper || !orderTypeSlider) return;

    const padding = 4;
    const innerWidth = orderTypeWrapper.clientWidth - padding * 2;
    const segmentWidth = innerWidth / 3;

    orderTypeSlider.style.width = segmentWidth + "px";
    orderTypeSlider.style.left =
      padding + activeIndex * segmentWidth + "px";
  }

  function setOrderType(type) {
    currentOrderType = type;

    [dineInBtn, pickUpBtn, deliveryBtn].forEach((btn) => {
      if (!btn) return;
      btn.style.color = "#000000"; // inactive -> black
    });

    let activeBtn = null;
    let activeIndex = 0;

    if (type === "dine_in") {
      activeBtn = dineInBtn;
      activeIndex = 0;
      currentDeliveryFee = 0;
    } else if (type === "pick_up") {
      activeBtn = pickUpBtn;
      activeIndex = 1;
      currentDeliveryFee = 0;
    } else if (type === "delivery") {
      activeBtn = deliveryBtn;
      activeIndex = 2;
      currentDeliveryFee = 100;
    }

    if (activeBtn) {
      activeBtn.style.color = "#ffffff"; // active -> white
    }

    updateOrderTypeSlider(activeIndex);
    saveOrderType();
    recalcTotals();
  }

  if (dineInBtn) {
    dineInBtn.addEventListener("click", () => setOrderType("dine_in"));
  }
  if (pickUpBtn) {
    pickUpBtn.addEventListener("click", () => setOrderType("pick_up"));
  }
  if (deliveryBtn) {
    deliveryBtn.addEventListener("click", () => setOrderType("delivery"));
  }

  // ---- ATTACH HANDLERS TO "ORDER NOW" BUTTONS ----
  function wireOrderButtons() {
    const buttons = document.querySelectorAll(".order-now-btn");
    buttons.forEach((btn) => {
      btn.addEventListener("click", function () {
        const name = this.dataset.itemName || "Item";
        const priceStr = this.dataset.itemPrice || "0";
        const price = Number(priceStr);
        window.addToCart(name, price);
      });
    });
  }

  // ---- INITIALISE ----
  window.addEventListener("load", () => {
    // restore order type
    if (currentOrderType === "pick_up") {
      setOrderType("pick_up");
    } else if (currentOrderType === "delivery") {
      setOrderType("delivery");
    } else {
      setOrderType("dine_in");
    }

    renderCart();
    wireOrderButtons();
  });

  window.addEventListener("resize", () => {
    const idx =
      currentOrderType === "dine_in"
        ? 0
        : currentOrderType === "pick_up"
        ? 1
        : 2;
    updateOrderTypeSlider(idx);
  });
})();
