(function () {
  const dataUrl = window.ECAG_MENU_MOBILE_DATA_URL;
  const saveCartUrl = "/menu/save_cart/";
  const checkoutUrl = "/menu/checkout/";
  const statusEl = $("#menu-status");
  const tabsEl = $("#menu-tabs");
  const sectionsEl = $("#menu-sections");
  const cartItemsEl = $("#mobile-cart-items");
  const clearCartBtn = $("#mobile-clear-cart");
  const cartCountEl = $("#cart-count");
  const cartTotalEl = $("#cart-total");
  const checkoutBtn = $("#mobile-checkout-btn");

  const TOPPING_PRICES = {
    Eggs: 25,
    Chicken: 0,
    Shrimps: 30,
    Beef: 15,
    Lamb: 30,
    Mushrooms: 20,
  };
  const MEAT_TOPPINGS = ["Chicken", "Beef", "Lamb"];
  const EXTRA_TOPPINGS = ["Eggs", "Shrimps", "Mushrooms"];

  let cart = [];
  let currentOrderType = localStorage.getItem("ecag_order_type") || "dine_in";

  try {
    cart = JSON.parse(localStorage.getItem("ecag_cart") || "[]");
  } catch (e) {
    cart = [];
  }

  if (!dataUrl) {
    statusEl.text("Missing mobile data URL.");
    return;
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function isToppingEligible(name) {
    const lower = String(name || "").toLowerCase();
    return lower.includes("fried rice") || lower.includes("fried noodles") || lower.includes("magic bowl");
  }

  function normalizeCart() {
    cart = (cart || [])
      .map((item) => {
        if (!item) return null;
        const normalized = {
          item_id: item.item_id || item.id || null,
          id: item.item_id || item.id || null,
          name: item.name || "Item",
          basePrice: Number(item.basePrice != null ? item.basePrice : item.price || 0),
          qty: Math.max(1, Number(item.qty || item.quantity || 1)),
          meatTopping: item.meatTopping || item.meat_topping || "",
          extraToppings: Array.isArray(item.extraToppings)
            ? item.extraToppings
            : Array.isArray(item.extra_toppings)
            ? item.extra_toppings
            : [],
        };
        if (isToppingEligible(normalized.name) && !normalized.meatTopping) {
          normalized.meatTopping = "Chicken";
        }
        return normalized;
      })
      .filter(Boolean);
  }

  function getItemToppingsTotal(item) {
    let total = 0;
    if (item.meatTopping && TOPPING_PRICES[item.meatTopping]) {
      total += TOPPING_PRICES[item.meatTopping];
    }
    if (Array.isArray(item.extraToppings)) {
      total += item.extraToppings.reduce((acc, t) => acc + (TOPPING_PRICES[t] || 0), 0);
    }
    return total;
  }

  function unitPrice(item) {
    return Number(item.basePrice || 0) + getItemToppingsTotal(item);
  }

  function currentDeliveryFee() {
    if (currentOrderType === "delivery") return 100;
    if (currentOrderType === "pick_up") return 50;
    return 0;
  }

  function saveCartLocally() {
    localStorage.setItem("ecag_cart", JSON.stringify(cart));
    localStorage.setItem("ecag_order_type", currentOrderType);
  }

  function recalcCartTotals() {
    const itemsCount = cart.reduce((sum, item) => sum + Number(item.qty || 0), 0);
    const subtotal = cart.reduce((sum, item) => {
      return sum + unitPrice(item) * Number(item.qty || 0);
    }, 0);
    const total = subtotal + currentDeliveryFee();
    cartCountEl.text(itemsCount);
    cartTotalEl.text(total.toFixed(2));
  }

  function setActiveOrderType(type) {
    currentOrderType = type;
    $(".order-type-btn").removeClass("is-active");
    $(`.order-type-btn[data-type='${type}']`).addClass("is-active");
    saveCartLocally();
    renderCartItems();
    recalcCartTotals();
  }

  function setMeat(itemIndex, meat) {
    const item = cart[itemIndex];
    if (!item || !MEAT_TOPPINGS.includes(meat)) return;
    item.meatTopping = meat;
    saveCartLocally();
    renderCartItems();
    recalcCartTotals();
  }

  function toggleExtra(itemIndex, topping) {
    const item = cart[itemIndex];
    if (!item) return;
    if (!Array.isArray(item.extraToppings)) item.extraToppings = [];
    const idx = item.extraToppings.indexOf(topping);
    if (idx === -1) item.extraToppings.push(topping);
    else item.extraToppings.splice(idx, 1);
    saveCartLocally();
    renderCartItems();
    recalcCartTotals();
  }

  function updateQty(itemIndex, delta) {
    const item = cart[itemIndex];
    if (!item) return;
    item.qty += delta;
    if (item.qty <= 0) cart.splice(itemIndex, 1);
    saveCartLocally();
    renderCartItems();
    recalcCartTotals();
  }

  function removeItem(itemIndex) {
    cart.splice(itemIndex, 1);
    saveCartLocally();
    renderCartItems();
    recalcCartTotals();
  }

  function renderCartItems() {
    if (!cart.length) {
      cartItemsEl.html('<p class="mobile-cart-empty">Cart is empty.</p>');
      return;
    }

    const html = cart
      .map((item, index) => {
        const toppingsHtml = isToppingEligible(item.name)
          ? '<div class="mobile-toppings-block">' +
              '<p class="mobile-toppings-label">Meat</p>' +
              '<div class="topping-chip-wrap">' +
              MEAT_TOPPINGS.map((meat) =>
                '<button type="button" class="topping-chip meat-chip ' +
                (item.meatTopping === meat ? "is-selected" : "") +
                '" data-index="' +
                index +
                '" data-meat="' +
                meat +
                '">' +
                escapeHtml(meat) +
                (TOPPING_PRICES[meat] ? ' (+Rs ' + TOPPING_PRICES[meat] + ')' : '') +
                "</button>"
              ).join("") +
              "</div>" +
              '<p class="mobile-toppings-label">Extras</p>' +
              '<div class="topping-chip-wrap">' +
              EXTRA_TOPPINGS.map((top) =>
                '<button type="button" class="topping-chip extra-chip ' +
                (Array.isArray(item.extraToppings) && item.extraToppings.includes(top) ? "is-selected" : "") +
                '" data-index="' +
                index +
                '" data-extra="' +
                top +
                '">' +
                escapeHtml(top) +
                ' (+Rs ' + TOPPING_PRICES[top] + ')' +
                "</button>"
              ).join("") +
              "</div>" +
              "</div>"
          : "";

        return (
          '<article class="mobile-cart-item">' +
          '<div class="mobile-cart-row">' +
          '<div>' +
          '<p class="mobile-cart-item-name">' +
          escapeHtml(item.name) +
          "</p>" +
          '<p class="mobile-cart-item-price">Rs ' +
          unitPrice(item).toFixed(2) +
          " each</p>" +
          "</div>" +
          '<div class="mobile-qty-group">' +
          '<button type="button" class="qty-btn" data-index="' +
          index +
          '" data-step="-1">-</button>' +
          '<span class="qty-value">' +
          item.qty +
          "</span>" +
          '<button type="button" class="qty-btn" data-index="' +
          index +
          '" data-step="1">+</button>' +
          '<button type="button" class="remove-btn" data-index="' +
          index +
          '">Remove</button>' +
          "</div>" +
          "</div>" +
          toppingsHtml +
          "</article>"
        );
      })
      .join("");

    cartItemsEl.html(html);
  }

  function addToCart(item) {
    const itemId = item.item_id;
    const price = Number(item.price || 0);
    const defaultMeat = isToppingEligible(item.name) ? "Chicken" : null;

    const existing = cart.find(
      (x) =>
        (x.item_id || x.id) === itemId &&
        x.name === item.name &&
        Number(x.basePrice || 0) === price &&
        (x.meatTopping || null) === defaultMeat &&
        (!x.extraToppings || x.extraToppings.length === 0)
    );

    if (existing) {
      existing.qty += 1;
    } else {
      cart.push({
        item_id: itemId,
        id: itemId,
        name: item.name,
        basePrice: price,
        qty: 1,
        meatTopping: defaultMeat,
        extraToppings: [],
      });
    }
    saveCartLocally();
    renderCartItems();
    recalcCartTotals();
  }

  function syncCartToSession() {
    const payload = cart.map((it) => ({
      item_id: it.item_id || it.id,
      quantity: it.qty || 1,
      meat_topping: it.meatTopping || "",
      extra_toppings: Array.isArray(it.extraToppings) ? it.extraToppings : [],
    }));

    return fetch(saveCartUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ items: payload, order_type: currentOrderType }),
    });
  }

  function renderCategories(categories) {
    if (!Array.isArray(categories) || !categories.length) {
      statusEl.text("No available menu items.");
      return;
    }

    statusEl.text("Choose a category");

    const tabs = [];
    const sections = [];

    categories.forEach((category, idx) => {
      const categoryName = category.category || "Category";
      const categoryId = "category-" + idx;
      const activeClass = idx === 0 ? " is-active" : "";

      tabs.push(
        '<button class="menu-tab-btn' +
          activeClass +
          '" data-target="' +
          categoryId +
          '">' +
          escapeHtml(categoryName) +
          "</button>"
      );

      const subcategoryBlocks = (category.subcategories || [])
        .map((sub) => {
          const itemCards = (sub.items || [])
            .map((item) => {
              const imagePart = item.image_url
                ? '<img src="' + escapeHtml(item.image_url) + '" alt="' + escapeHtml(item.name) + '">'
                : "<div></div>";

              return (
                '<article class="menu-card">' +
                imagePart +
                '<div class="menu-card-body">' +
                '<div class="menu-row">' +
                '<h3 class="menu-name">' +
                escapeHtml(item.name) +
                "</h3>" +
                '<p class="menu-price">Rs ' +
                escapeHtml(item.price) +
                "</p>" +
                "</div>" +
                '<p class="menu-desc">' +
                escapeHtml(item.desc) +
                "</p>" +
                '<div class="menu-card-actions">' +
                '<button type="button" class="add-cart-btn" data-item-id="' +
                escapeHtml(item.item_id) +
                '" data-item-name="' +
                escapeHtml(item.name) +
                '" data-item-price="' +
                escapeHtml(item.price) +
                '">Add</button>' +
                "</div>" +
                "</div>" +
                "</article>"
              );
            })
            .join("");

          return (
            '<section class="subcategory-block">' +
            '<h2 class="subcategory-title">' +
            escapeHtml(sub.subcategory) +
            "</h2>" +
            itemCards +
            "</section>"
          );
        })
        .join("");

      sections.push(
        '<section id="' +
          categoryId +
          '" class="category-panel" style="display:' +
          (idx === 0 ? "block" : "none") +
          ';">' +
          subcategoryBlocks +
          "</section>"
      );
    });

    tabsEl.html(tabs.join(""));
    sectionsEl.html(sections.join(""));

    tabsEl.on("click", ".menu-tab-btn", function () {
      const target = $(this).data("target");
      $(".menu-tab-btn").removeClass("is-active");
      $(this).addClass("is-active");
      $(".category-panel").hide();
      $("#" + target).show();
    });

    sectionsEl.on("click", ".add-cart-btn", function () {
      const itemId = Number($(this).data("item-id"));
      const name = $(this).data("item-name");
      const price = Number($(this).data("item-price"));
      addToCart({ item_id: itemId, name, price });
      statusEl.text(name + " added to cart");
    });
  }

  cartItemsEl.on("click", ".qty-btn", function () {
    const itemIndex = Number($(this).data("index"));
    const step = Number($(this).data("step"));
    updateQty(itemIndex, step);
  });

  cartItemsEl.on("click", ".remove-btn", function () {
    const itemIndex = Number($(this).data("index"));
    removeItem(itemIndex);
  });

  cartItemsEl.on("click", ".meat-chip", function () {
    const itemIndex = Number($(this).data("index"));
    const meat = $(this).data("meat");
    setMeat(itemIndex, meat);
  });

  cartItemsEl.on("click", ".extra-chip", function () {
    const itemIndex = Number($(this).data("index"));
    const topping = $(this).data("extra");
    toggleExtra(itemIndex, topping);
  });

  clearCartBtn.on("click", function () {
    cart = [];
    saveCartLocally();
    renderCartItems();
    recalcCartTotals();
    statusEl.text("Cart cleared.");
  });

  $(".order-type-btn").on("click", function () {
    setActiveOrderType($(this).data("type"));
  });

  checkoutBtn.on("click", function () {
    if (!cart.length) {
      statusEl.text("Your cart is empty.");
      return;
    }
    statusEl.text("Preparing checkout...");
    syncCartToSession()
      .then(function (res) {
        if (!res.ok) throw new Error("sync failed");
        window.location.href = checkoutUrl;
      })
      .catch(function () {
        statusEl.text("Could not start checkout.");
      });
  });

  normalizeCart();
  setActiveOrderType(currentOrderType);
  renderCartItems();
  recalcCartTotals();

  $.getJSON(dataUrl)
    .done(function (payload) {
      renderCategories(payload.categories || []);
    })
    .fail(function () {
      statusEl.text("Could not load menu data.");
    });
})();
