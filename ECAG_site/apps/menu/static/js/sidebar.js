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

  const orderTypeWrapper = document.getElementById("order-type-wrapper");
  const orderTypeSlider = document.getElementById("order-type-slider");
  const dineInBtn = document.getElementById("order-type-dinein");
  const pickUpBtn = document.getElementById("order-type-pickup");
  const deliveryBtn = document.getElementById("order-type-delivery");

  // ---------- SIDEBAR OPEN/CLOSE ----------
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

  // ---------- ORDER TYPE STATE ----------
  let currentOrderType =
    localStorage.getItem("ecag_order_type") || "dine_in";
  let currentDeliveryFee =
    currentOrderType === "delivery" ? 100 : 0;

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
    if (orderDeliveryEl)
      orderDeliveryEl.textContent = String(currentDeliveryFee);
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
      wrapper.style.padding = "6px 0";
      wrapper.style.borderBottom = "1px solid #f3f4f6";

      // ---- main row ----
      const row = document.createElement("div");
      row.style.display = "flex";
      row.style.alignItems = "center";
      row.style.justifyContent = "space-between";

      const left = document.createElement("div");
      left.style.display = "flex";
      left.style.flexDirection = "column";

      const nameEl = document.createElement("span");
      nameEl.textContent = item.name;
      nameEl.style.fontWeight = "600";
      nameEl.style.fontSize = "14px";

      const perUnitPrice =
        (item.basePrice || 0) + getItemToppingsTotal(item);

      const priceEl = document.createElement("span");
      priceEl.textContent = "Rs " + perUnitPrice;
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

      wrapper.appendChild(row);

      // ---- toppings row (only for eligible dishes) ----
      if (isToppingEligible(item.name)) {
        // ensure a meat is always set on render as well
        if (!item.meatTopping) item.meatTopping = "Chicken";

        const toppingsRow = document.createElement("div");
        toppingsRow.style.marginTop = "4px";
        toppingsRow.style.paddingLeft = "4px";
        toppingsRow.style.display = "flex";
        toppingsRow.style.flexDirection = "column";
        toppingsRow.style.gap = "4px";

        // Meat toppings (radio style, NO prices in label)
        const meatLabel = document.createElement("span");
        meatLabel.textContent = "Meat:";
        meatLabel.style.fontSize = "12px";
        meatLabel.style.color = "#6b7280";
        toppingsRow.appendChild(meatLabel);

        const meatRow = document.createElement("div");
        meatRow.style.display = "flex";
        meatRow.style.flexWrap = "wrap";
        meatRow.style.gap = "6px";

        MEAT_TOPPINGS.forEach((meatName) => {
          const isSelected = item.meatTopping === meatName;

          const mBtn = document.createElement("button");

          // Write meat name + price except for Chicken
          let label = meatName;
          if (meatName === "Beef") label = "Beef (Rs 15)";
          if (meatName === "Lamb") label = "Lamb (Rs 30)";

          mBtn.textContent = label;

          mBtn.style.fontSize = "11px";
          mBtn.style.padding = "2px 6px";
          mBtn.style.borderRadius = "9999px";
          mBtn.style.border = "1px solid #f97316";
          mBtn.style.cursor = "pointer";
          mBtn.style.background = isSelected
            ? "linear-gradient(to right, #f97316, #ef4444)"
            : "#ffffff";
          mBtn.style.color = isSelected ? "#ffffff" : "#f97316";

          mBtn.onclick = function () {
            setMeatTopping(index, meatName);
          };

          meatRow.appendChild(mBtn);
        });


        toppingsRow.appendChild(meatRow);

        // Extra toppings (multi-select, still show prices)
        const extraLabel = document.createElement("span");
        extraLabel.textContent = "Extras:";
        extraLabel.style.fontSize = "12px";
        extraLabel.style.color = "#6b7280";
        toppingsRow.appendChild(extraLabel);

        const extraRow = document.createElement("div");
        extraRow.style.display = "flex";
        extraRow.style.flexWrap = "wrap";
        extraRow.style.gap = "6px";

        otherToppings.forEach((toppingName) => {
          const isSelected =
            Array.isArray(item.extraToppings) &&
            item.extraToppings.indexOf(toppingName) !== -1;

          const tBtn = document.createElement("button");
          tBtn.textContent =
            toppingName + " (Rs " + TOPPING_PRICES[toppingName] + ")";
          tBtn.style.fontSize = "11px";
          tBtn.style.padding = "2px 6px";
          tBtn.style.borderRadius = "9999px";
          tBtn.style.border = "1px solid #f97316";
          tBtn.style.cursor = "pointer";
          tBtn.style.background = isSelected
            ? "linear-gradient(to right, #f97316, #ef4444)"
            : "#ffffff";
          tBtn.style.color = isSelected ? "#ffffff" : "#f97316";

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

  window.addToCart = function (name, price) {
    const numericPrice = Number(price) || 0;
    const eligible = isToppingEligible(name);

    const defaultMeat = eligible ? "Chicken" : null;

    const newItem = {
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

  // ---------- "ORDER NOW" BUTTON WIRING (if using data- attributes) ----------
  function wireOrderButtons() {
    const buttons = document.querySelectorAll(".order-now-btn");
    buttons.forEach((btn) => {
      btn.addEventListener("click", function () {
        const name = this.dataset.itemName || "Item";
        const priceStr = this.dataset.itemPrice || "0";
        const price = Number(priceStr) || 0;
        window.addToCart(name, price);
      });
    });
  }

  // ---------- INIT ----------
  window.addEventListener("load", () => {
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
