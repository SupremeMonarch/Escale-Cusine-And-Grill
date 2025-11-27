// static/js/sidebar.js
(function () {
  // ---------- TOPPING CONFIG ----------
  const TOPPING_PRICES = {
    Eggs: 25,
    Chicken: 0,
    Shrimps: 30,
    Beef: 15,
    Lamb: 30,
    Mushrooms: 20,
  };

  const MEAT_TOPPINGS = ["Chicken", "Beef", "Lamb"];

  function getOtherToppingsList() {
    return Object.keys(TOPPING_PRICES).filter(
      (t) => !MEAT_TOPPINGS.includes(t)
    );
  }

  function isToppingEligible(name) {
    if (!name) return false;
    const lower = name.toLowerCase();
    return (
      lower.includes("fried rice") ||
      lower.includes("fried noodles") ||
      lower.includes("magic bowl")
    );
  }

  // total for *all* toppings of an item
  function getItemToppingsTotal(item) {
    let total = 0;

    if (item.meatTopping && TOPPING_PRICES[item.meatTopping]) {
      total += TOPPING_PRICES[item.meatTopping];
    }

    if (Array.isArray(item.extraToppings)) {
      total += item.extraToppings.reduce((sum, t) => {
        const price = TOPPING_PRICES[t] || 0;
        return sum + price;
      }, 0);
    }

    return total;
  }

  // ---------- DOM ELEMENTS ----------
  const sidebarButton = document.getElementById("sidebar-button");
  const sidebarPanel = document.getElementById("order-sidebar");

  const orderItemsContainer = document.getElementById("order-items");
  const orderCountEl = document.getElementById("order-count");
  const orderDeliveryEl = document.getElementById("order-delivery");
  const orderTotalEl = document.getElementById("order-total");

  const orderTypeWrapper = () => document.getElementById("order-type-wrapper");
  let dineInBtn = null;
  let pickUpBtn = null;
  let deliveryBtn = null;
  let orderTypeSliderEl = null;
  let orderTypeHoverEl = null;

  function ensureOrderBtns() {
    if (!dineInBtn) dineInBtn = document.getElementById("order-type-dinein");
    if (!pickUpBtn) pickUpBtn = document.getElementById("order-type-pickup");
    if (!deliveryBtn) deliveryBtn = document.getElementById("order-type-delivery");
    if (!orderTypeSliderEl) orderTypeSliderEl = document.getElementById("order-type-slider");
    if (!orderTypeHoverEl) orderTypeHoverEl = document.getElementById("order-type-hover");
  }

  // ---------- SIDEBAR OPEN/CLOSE ----------
  // track state explicitly to avoid relying on inline style comparisons
  let isSidebarOpen = false;

  // ensure both panel and button have matching transition timings (identical)
  try {
    const t = "transform 260ms cubic-bezier(.2,.8,.2,1)";
    if (sidebarPanel) sidebarPanel.style.transition = t;
    if (sidebarButton) sidebarButton.style.transition = t;
  } catch (e) {}

  function openSidebar() {
    // apply transforms in the next animation frame so both animate together
    try {
      if (!sidebarPanel || !sidebarButton) return;
      const w = sidebarPanel.offsetWidth || 400;
      const overlap = 0; // sit exactly on the edge for Firefox

      // ensure starting (closed) state is set before transitioning
      sidebarPanel.style.transform = "translateX(100%)";
      sidebarButton.style.transform = "translateX(0)";

      // force a style flush
      // eslint-disable-next-line no-unused-expressions
      sidebarPanel.offsetWidth;

      // set open transforms together in one animation frame
      requestAnimationFrame(() => {
        sidebarPanel.style.transform = "translateX(0)";
        sidebarButton.style.transform = "translateX(-" + (w - overlap) + "px)";
        isSidebarOpen = true;
      });
    } catch (e) {}
  }

  function closeSidebar() {
    try {
      if (!sidebarPanel || !sidebarButton) return;
      const w = sidebarPanel.offsetWidth || 400;
      const overlap = 0;

      // ensure starting (open) state is set before transitioning
      sidebarPanel.style.transform = "translateX(0)";
      sidebarButton.style.transform = "translateX(-" + (w - overlap) + "px)";

      // force a style flush
      // eslint-disable-next-line no-unused-expressions
      sidebarPanel.offsetWidth;

      // set closed transforms together in one animation frame to keep them synced
      requestAnimationFrame(() => {
        sidebarPanel.style.transform = "translateX(100%)";
        sidebarButton.style.transform = "translateX(0)";
        isSidebarOpen = false;
      });
    } catch (e) {}
  }

  if (sidebarButton && sidebarPanel) {
    sidebarButton.addEventListener("click", function () {
      if (!isSidebarOpen) openSidebar();
      else closeSidebar();
    });
    // ensure initial button transform is reset (button visible at right)
    try {
      sidebarButton.style.transform = "translateX(0)";
      // keep panel closed initially
      sidebarPanel.style.transform = "translateX(100%)";
      isSidebarOpen = false;
    } catch (e) {}
  }

  // Prevent clicks/touches inside the sidebar from bubbling to the document
  try {
    if (sidebarPanel) {
      sidebarPanel.addEventListener('click', function (e) {
        e.stopPropagation();
      });
      sidebarPanel.addEventListener('touchstart', function (e) {
        e.stopPropagation();
      });
    }
  } catch (e) {}

  // close sidebar when clicking outside (click or touch)
  try {
    document.addEventListener("click", function (e) {
      if (!isSidebarOpen) return;
      const t = e.target;
      if (!t) return;
      // if click is inside sidebar, on the toggle button, or on an "Order Now" button, ignore
      if (
        sidebarPanel.contains(t) ||
        sidebarButton.contains(t) ||
        (t.closest && t.closest('.order-now-btn'))
      )
        return;
      closeSidebar();
    });

    // also handle touchstart for mobile/touch devices
    document.addEventListener("touchstart", function (e) {
      if (!isSidebarOpen) return;
      const t = e.target;
      if (!t) return;
      if (
        sidebarPanel.contains(t) ||
        sidebarButton.contains(t) ||
        (t.closest && t.closest('.order-now-btn'))
      )
        return;
      closeSidebar();
    });
  } catch (e) {}

  // add a smooth transition for the toggle button so it animates with the panel
    try {
    // snappier transition using transform so it animates with the sidebar
    if (sidebarButton)
      sidebarButton.style.transition = "transform 220ms cubic-bezier(.2,.8,.2,1)";
  } catch (e) {}

  // ---------- CART STATE (PERSISTED) ----------
  let cart = [];
  try {
    const saved = localStorage.getItem("ecag_cart");
    if (saved) cart = JSON.parse(saved) || [];
  } catch (e) {
    cart = [];
  }

  // migrate old structure -> new {basePrice, meatTopping, extraToppings}
  cart = cart.map((item) => {
    if (!item) return item;

    if (item.basePrice == null && item.price != null) {
      item.basePrice = Number(item.price) || 0;
    }

    if (Array.isArray(item.toppings)) {
      if (!item.meatTopping) {
        const foundMeat = item.toppings.find((t) =>
          MEAT_TOPPINGS.includes(t)
        );
        if (foundMeat) item.meatTopping = foundMeat;
      }
      if (!Array.isArray(item.extraToppings)) {
        item.extraToppings = item.toppings.filter(
          (t) => !MEAT_TOPPINGS.includes(t)
        );
      }
      delete item.toppings;
    }

    if (!Array.isArray(item.extraToppings)) {
      item.extraToppings = [];
    }

    if (typeof item.qty !== "number" || item.qty < 1) {
      item.qty = 1;
    }

    // ensure eligible dishes always have a meat topping
    if (isToppingEligible(item.name) && !item.meatTopping) {
      item.meatTopping = "Chicken";
    }

    return item;
  });

  function saveCart() {
    try {
      localStorage.setItem("ecag_cart", JSON.stringify(cart));
    } catch (e) {}
  }

  // Send the current client-side cart to the server so it can be stored
  // in the user's session. The server exposes a POST endpoint at
  // /menu/save_cart/ that accepts JSON array of items.
  async function syncCartToSession() {
    try {
      // read CSRF token from cookie
      function getCookie(name) {
        const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return v ? v.pop() : '';
      }

      const payload = cart.map((it) => ({
        item_id: it.item_id || it.id || null,
        quantity: it.qty || it.qty === 0 ? it.qty : it.qty || 1,
        meat_topping: it.meatTopping || '',
        extra_toppings: Array.isArray(it.extraToppings) ? it.extraToppings : [],
      }));
      // include current order type for persistence
      const orderType = currentOrderType; // values: dine_in, pick_up, delivery
      const res = await fetch('/menu/save_cart/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ items: payload, order_type: orderType })
      });

      return res.ok;
    } catch (e) {
      return false;
    }
  }

  // ---------- ORDER TYPE STATE ----------
  let currentOrderType =
    localStorage.getItem("ecag_order_type") || "dine_in";
  let currentDeliveryFee =
    currentOrderType === "delivery" ? 100 : currentOrderType === "pick_up" ? 50 : 0;

  function saveOrderType() {
    try {
      localStorage.setItem("ecag_order_type", currentOrderType);
    } catch (e) {}
  }

  // ---------- TOTALS + RENDER ----------
  function recalcTotals() {
    const itemsCount = cart.reduce((sum, item) => sum + item.qty, 0);

    const subtotal = cart.reduce((sum, item) => {
      const perUnitPrice =
        (item.basePrice || 0) + getItemToppingsTotal(item);
      return sum + perUnitPrice * item.qty;
    }, 0);

    const total = subtotal + currentDeliveryFee;

    if (orderCountEl) orderCountEl.textContent = String(itemsCount);
    if (orderDeliveryEl) orderDeliveryEl.textContent = String(currentDeliveryFee);
    // keep fee label in sync even if setOrderType wasn't called (cache, race, etc.)
    try {
      const feeLabelEl = document.getElementById('order-fee-label');
      if (feeLabelEl) {
        if (currentOrderType === 'delivery') feeLabelEl.textContent = 'Delivery';
        else if (currentOrderType === 'pick_up') feeLabelEl.textContent = 'Take Out';
        else feeLabelEl.textContent = 'Dine In';
      }
    } catch (e) {}
    if (orderTotalEl) orderTotalEl.textContent = String(total);
  }

  // 🔸 Radio behaviour: one meat must be active at all times
  function setMeatTopping(itemIndex, toppingName) {
    const item = cart[itemIndex];
    if (!item) return;
    if (!MEAT_TOPPINGS.includes(toppingName)) return;

    // always set, never clear
    item.meatTopping = toppingName;

    saveCart();
    renderCart();
  }

  function toggleExtraTopping(itemIndex, toppingName) {
    const item = cart[itemIndex];
    if (!item) return;
    if (!Array.isArray(item.extraToppings)) {
      item.extraToppings = [];
    }

    const idx = item.extraToppings.indexOf(toppingName);
    if (idx === -1) {
      item.extraToppings.push(toppingName);
    } else {
      item.extraToppings.splice(idx, 1);
    }
    saveCart();
    renderCart();
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

    const otherToppings = getOtherToppingsList();

    cart.forEach((item, index) => {
      const wrapper = document.createElement("div");
      wrapper.style.padding = "10px 0";
      wrapper.style.borderBottom = "1px solid #f3f4f6";

      // ---- main row ----
      const row = document.createElement("div");
      row.style.display = "flex";
      row.style.alignItems = "center";
      row.style.justifyContent = "space-between";
      row.style.gap = "12px";

      const left = document.createElement("div");
      left.style.display = "flex";
      left.style.flexDirection = "column";
      left.style.flex = "1";

      const nameEl = document.createElement("span");
      nameEl.textContent = item.name;
      nameEl.style.fontWeight = "700";
      nameEl.style.fontSize = "16px";
      nameEl.style.color = "#111827";

      const perUnitPrice =
        (item.basePrice || 0) + getItemToppingsTotal(item);

      const priceEl = document.createElement("span");
      priceEl.textContent = "Rs " + perUnitPrice;
      priceEl.style.fontSize = "14px";
      priceEl.style.color = "#f97316";
      priceEl.style.fontWeight = "700";

      left.appendChild(nameEl);
      left.appendChild(priceEl);

      const right = document.createElement("div");
      right.style.display = "flex";
      right.style.alignItems = "center";
      right.style.gap = "8px";

      const minusBtn = document.createElement("button");
      minusBtn.textContent = "-";
      minusBtn.style.padding = "6px 10px";
      minusBtn.style.border = "1px solid #e5e7eb";
      minusBtn.style.background = "#ffffff";
      minusBtn.style.cursor = "pointer";
      minusBtn.style.borderRadius = "8px";
      minusBtn.style.fontWeight = "600";
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
      qtySpan.style.minWidth = "28px";
      qtySpan.style.textAlign = "center";
      qtySpan.style.fontSize = "14px";
      qtySpan.style.fontWeight = "600";

      const plusBtn = document.createElement("button");
      plusBtn.textContent = "+";
      plusBtn.style.padding = "6px 10px";
      plusBtn.style.border = "1px solid #e5e7eb";
      plusBtn.style.background = "#ffffff";
      plusBtn.style.cursor = "pointer";
      plusBtn.style.borderRadius = "8px";
      plusBtn.style.fontWeight = "600";
      plusBtn.onclick = function () {
        item.qty += 1;
        saveCart();
        renderCart();
      };

      const removeBtn = document.createElement("button");
      removeBtn.textContent = "✕";
      removeBtn.style.border = "none";
      removeBtn.style.background = "#fff5f5";
      removeBtn.style.color = "#ef4444";
      removeBtn.style.cursor = "pointer";
      removeBtn.style.padding = "6px 8px";
      removeBtn.style.borderRadius = "8px";
      removeBtn.style.fontWeight = "700";
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

      wrapper.appendChild(row);

      // ---- toppings row (only for eligible dishes) ----
      if (isToppingEligible(item.name)) {
        // ensure a meat is always set on render as well
        if (!item.meatTopping) item.meatTopping = "Chicken";

        const toppingsRow = document.createElement("div");
        toppingsRow.style.marginTop = "8px";
        toppingsRow.style.padding = "8px";
        toppingsRow.style.display = "flex";
        toppingsRow.style.flexDirection = "column";
        toppingsRow.style.gap = "8px";
        toppingsRow.style.background = "#fbfbfd";
        toppingsRow.style.borderRadius = "8px";
        toppingsRow.style.border = "1px solid #f1f5f9";

        // Meat toppings (radio style, NO prices in label)
        const meatLabel = document.createElement("div");
        meatLabel.textContent = "Meat";
        meatLabel.style.fontSize = "12px";
        meatLabel.style.color = "#6b7280";
        toppingsRow.appendChild(meatLabel);

        const meatRow = document.createElement("div");
        meatRow.style.display = "flex";
        meatRow.style.flexWrap = "wrap";
        meatRow.style.gap = "8px";

        MEAT_TOPPINGS.forEach((meatName) => {
          const isSelected = item.meatTopping === meatName;

          const mBtn = document.createElement("button");

          // Write meat name + price except for Chicken
          let label = meatName;
          if (meatName === "Beef") label = "Beef (Rs 15)";
          if (meatName === "Lamb") label = "Lamb (Rs 30)";

          mBtn.textContent = label;

          mBtn.style.fontSize = "13px";
          mBtn.style.padding = "6px 10px";
          mBtn.style.borderRadius = "9999px";
          mBtn.style.border = "1px solid #f97316";
          mBtn.style.cursor = "pointer";
          mBtn.style.background = isSelected
            ? "linear-gradient(to right, #f97316, #ef4444)"
            : "#ffffff";
          mBtn.style.color = isSelected ? "#ffffff" : "#f97316";
          mBtn.style.boxShadow = isSelected ? "0 6px 12px rgba(249,115,22,0.12)" : "none";

          mBtn.onclick = function () {
            setMeatTopping(index, meatName);
          };

          meatRow.appendChild(mBtn);
        });


        toppingsRow.appendChild(meatRow);

        // Extra toppings (multi-select, still show prices)
        const extraLabel = document.createElement("div");
        extraLabel.textContent = "Extras";
        extraLabel.style.fontSize = "12px";
        extraLabel.style.color = "#6b7280";
        toppingsRow.appendChild(extraLabel);

        const extraRow = document.createElement("div");
        extraRow.style.display = "flex";
        extraRow.style.flexWrap = "wrap";
        extraRow.style.gap = "8px";

        otherToppings.forEach((toppingName) => {
          const isSelected =
            Array.isArray(item.extraToppings) &&
            item.extraToppings.indexOf(toppingName) !== -1;

          const tBtn = document.createElement("button");
          tBtn.textContent =
            toppingName + " (Rs " + TOPPING_PRICES[toppingName] + ")";
          tBtn.style.fontSize = "13px";
          tBtn.style.padding = "6px 10px";
          tBtn.style.borderRadius = "9999px";
          tBtn.style.border = isSelected ? "1px solid transparent" : "1px solid #e6a06b";
          tBtn.style.cursor = "pointer";
          tBtn.style.background = isSelected
            ? "linear-gradient(to right, #f97316, #ef4444)"
            : "#fff";
          tBtn.style.color = isSelected ? "#fff" : "#b34718";
          tBtn.style.boxShadow = isSelected ? "0 6px 12px rgba(249,115,22,0.12)" : "none";
          tBtn.style.display = "flex";
          tBtn.style.alignItems = "center";
          tBtn.style.gap = "8px";

          // add a small muted price label for extras
          const priceSpan = document.createElement('span');
          priceSpan.textContent = '(Rs ' + (TOPPING_PRICES[toppingName] || 0) + ')';
          priceSpan.style.fontSize = '11px';
          priceSpan.style.color = isSelected ? '#ffffff' : '#92400e';
          priceSpan.style.opacity = isSelected ? '0.95' : '0.8';
          // append label
          tBtn.textContent = toppingName + ' ';
          tBtn.appendChild(priceSpan);

          tBtn.onclick = function () {
            toggleExtraTopping(index, toppingName);
          };

          extraRow.appendChild(tBtn);
        });

        toppingsRow.appendChild(extraRow);
        wrapper.appendChild(toppingsRow);
      }

      orderItemsContainer.appendChild(wrapper);
    });

    recalcTotals();
  }

  // ---------- GLOBAL addToCart ----------
  function toppingsSignature(item) {
    const meatsig = item.meatTopping || "";
    const extras = Array.isArray(item.extraToppings)
      ? [...item.extraToppings].sort().join(",")
      : "";
    return meatsig + "|" + extras;
  }

  window.addToCart = function (id, name, price) {
    const numericPrice = Number(price) || 0;
    const eligible = isToppingEligible(name);

    const defaultMeat = eligible ? "Chicken" : null;

    const newItem = {
      item_id: id || null,
      id: id || null,
      name: name,
      basePrice: numericPrice,
      qty: 1,
      meatTopping: defaultMeat,
      extraToppings: [],
    };

    const newSig = toppingsSignature(newItem);

    const existing = cart.find(
      (i) =>
        i.name === newItem.name &&
        Number(i.basePrice) === numericPrice &&
        toppingsSignature(i) === newSig
    );

    if (existing) {
      existing.qty += 1;
    } else {
      cart.push(newItem);
    }

    saveCart();
    renderCart();
    openSidebar();
  };

  // ---------- ORDER TYPE SLIDER ----------
  // Reintroduced absolute slider: position using percent-based translateX + small scale overlap
  function updateOrderTypeSlider(activeIndex) {
    ensureOrderBtns();
    if (!orderTypeSliderEl || !orderTypeWrapper()) return;

    const segments = 3;
    const percentPerSeg = 100 / segments; // 33.333...

    // slider width = one segment (percentage)
    orderTypeSliderEl.style.width = percentPerSeg + '%';
    orderTypeSliderEl.style.transformOrigin = 'left center';

    // small scale to overlap the wrapper border and hide hairline gaps
    const scaleX = 1.04;

    // translate by N * 100% of its own width
    orderTypeSliderEl.style.transform = 'translateX(' + activeIndex * 100 + '%) scaleX(' + scaleX + ')';

    // ensure slider covers full height and has pill radius
    try {
      const wrapper = orderTypeWrapper();
      const h = wrapper ? wrapper.clientHeight : 0;
      orderTypeSliderEl.style.top = '0px';
      orderTypeSliderEl.style.bottom = '0px';
      if (h) orderTypeSliderEl.style.borderRadius = Math.round(h / 2) + 'px';
    } catch (e) {}
  }

  // Move hover pill to a given index (0..2) and set visibility
  function showHoverAt(index) {
    ensureOrderBtns();
    if (!orderTypeHoverEl || !orderTypeWrapper()) return;
    // do not show hover for the currently active segment
    const activeIndex = currentOrderType === 'dine_in' ? 0 : currentOrderType === 'pick_up' ? 1 : 2;
    if (index === activeIndex) {
      hideHover();
      return;
    }

    const wrapper = orderTypeWrapper();
    const segments = 3;
    const percentPerSeg = 100 / segments;
    orderTypeHoverEl.style.width = percentPerSeg + '%';
    orderTypeHoverEl.style.transform = 'translateX(' + index * 100 + '%)';
    orderTypeHoverEl.style.opacity = '1';
    // ensure hover pill has same border radius
    try { if (wrapper) orderTypeHoverEl.style.borderRadius = Math.round(wrapper.clientHeight / 2) + 'px'; } catch (e) {}
  }

  function hideHover() {
    if (!orderTypeHoverEl) return;
    // gently hide the hover pill; keep it positioned so it doesn't flash over text
    orderTypeHoverEl.style.opacity = '0';
    // move hover to the active segment so it won't accidentally show over non-active text
    try {
      const activeIndex = currentOrderType === 'dine_in' ? 0 : currentOrderType === 'pick_up' ? 1 : 2;
      orderTypeHoverEl.style.transform = 'translateX(' + activeIndex * 100 + '%)';
    } catch (e) {}
  }

  function setOrderType(type) {
    currentOrderType = type;
    // set button text colors and position slider
    try {
      ensureOrderBtns();
      const all = [dineInBtn, pickUpBtn, deliveryBtn];
      // remove active class from all and reset text color
      all.forEach((b) => {
        if (!b) return;
        b.classList.remove('active');
        b.style.color = '#000000';
      });

      let activeBtn = null;
      let activeIndex = 0;
      if (type === 'dine_in') { activeBtn = dineInBtn; activeIndex = 0; currentDeliveryFee = 0; }
      else if (type === 'pick_up') { activeBtn = pickUpBtn; activeIndex = 1; currentDeliveryFee = 50; }
      else if (type === 'delivery') { activeBtn = deliveryBtn; activeIndex = 2; currentDeliveryFee = 100; }

      // mark the active button with the class so CSS rules (hover:not(.active)) won't affect it
      if (activeBtn) {
        activeBtn.classList.add('active');
        activeBtn.style.color = '#ffffff';
      }

      updateOrderTypeSlider(activeIndex);
    } catch (e) {}

    // Update fee label dynamically
    try {
      const feeLabelEl = document.getElementById('order-fee-label');
      if (feeLabelEl) {
        if (type === 'delivery') feeLabelEl.textContent = 'Delivery';
        else if (type === 'pick_up') feeLabelEl.textContent = 'Take Out';
        else feeLabelEl.textContent = 'Dine In';
      }
    } catch (e) {}

    saveOrderType();
    recalcTotals();
    // live sync order type to server (fire-and-forget)
    try { syncCartToSession(); } catch (e) {}
  }

  // Event listeners for order buttons are attached after DOM load (see INIT)

  // ---------- "ORDER NOW" BUTTON WIRING (if using data- attributes) ----------
  function wireOrderButtons() {
    const buttons = document.querySelectorAll(".order-now-btn");
    buttons.forEach((btn) => {
      btn.addEventListener("click", function () {
          const id = this.dataset.itemId || null;
          const name = this.dataset.itemName || "Item";
          const priceStr = this.dataset.itemPrice || "0";
          const price = Number(priceStr) || 0;
          window.addToCart(id, name, price);
      });
    });
  }

    // Wire the checkout CTA to sync cart then navigate to checkout
    try {
      const checkoutCTA = document.getElementById('checkout-cta');
      if (checkoutCTA) {
        checkoutCTA.addEventListener('click', async function (e) {
          // prevent default navigation while syncing
          e.preventDefault();
          const ok = await syncCartToSession();
          // proceed regardless, but prefer success
          window.location = checkoutCTA.href;
        });
      }
    } catch (e) {}

  // ---------- INIT ----------
  window.addEventListener("load", () => {
    // ensure DOM nodes exist for the order-type buttons
    ensureOrderBtns();

    // attach click handlers on the buttons now that they exist
    try {
      if (dineInBtn) {
        dineInBtn.addEventListener("click", () => setOrderType("dine_in"));
        dineInBtn.addEventListener("mouseenter", () => { if (currentOrderType !== 'dine_in') showHoverAt(0); });
        dineInBtn.addEventListener("mouseleave", hideHover);
      }
      if (pickUpBtn) {
        pickUpBtn.addEventListener("click", () => setOrderType("pick_up"));
        pickUpBtn.addEventListener("mouseenter", () => { if (currentOrderType !== 'pick_up') showHoverAt(1); });
        pickUpBtn.addEventListener("mouseleave", hideHover);
      }
      if (deliveryBtn) {
        deliveryBtn.addEventListener("click", () => setOrderType("delivery"));
        deliveryBtn.addEventListener("mouseenter", () => { if (currentOrderType !== 'delivery') showHoverAt(2); });
        deliveryBtn.addEventListener("mouseleave", hideHover);
      }
    } catch (e) {}

    // set the initial order type (this will toggle the active class)
    if (currentOrderType === "pick_up") setOrderType("pick_up");
    else if (currentOrderType === "delivery") setOrderType("delivery");
    else setOrderType("dine_in");

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
    // reposition hover if visible
    try {
      if (orderTypeHoverEl && orderTypeHoverEl.style.opacity === '1') {
        // find index of hover based on transform translateX; just hide and let mouseenter recompute
        hideHover();
      }
    } catch (e) {}
    // if the sidebar is open, reposition the button smoothly to match new width
    try {
      if (sidebarPanel && sidebarPanel.style.transform === "translateX(0)" && sidebarButton) {
        const w = sidebarPanel.offsetWidth || 400;
        const overlap = 8; // pixels to overlap so button visually attaches
        sidebarButton.style.transform = "translateX(-" + (w - overlap) + "px)";
      }
    } catch (e) {}
  });
})();
