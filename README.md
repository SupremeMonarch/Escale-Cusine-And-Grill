# Escale-Cusine-And-Grill
A website for the restaurant Escale Cuisine and Grill. This project is part of our assignment for the module Web and Mobile application developement at the the University Of Mauritius for the course of Bsc(Hons) Computer Science

## Mobile Menu (jQuery + Flet)

This project now includes a mobile-first menu experience in two forms:

1. jQuery mobile web page in Django:
	- URL: `/menu/mobile/`
	- Data endpoint used by jQuery: `/menu/mobile/data/`
	- Checkout flow: syncs cart to session via `/menu/save_cart/` then opens `/menu/checkout/`
	- Supports cart quantity controls, remove item, and toppings editing for eligible dishes

2. Flet mobile app page:
	- Script: `ECAG_site/apps/menu/flet_mobile_menu.py`
	- Reads data from the same Django endpoint (`/menu/mobile/data/`)
	- Starts checkout via `/menu/mobile/checkout/start/` and opens Django checkout URL
	- Supports persistent cart state and order type across restarts using Flet client storage
	- Supports quantity controls, remove item, and toppings editing for eligible dishes

### Run

1. Start Django server:
	- `cd ECAG_site`
	- `python manage.py runserver`

2. Open the jQuery mobile page:
	- `http://127.0.0.1:8000/menu/mobile/`

3. Run Flet app (new terminal):
	- `cd ECAG_site`
	- `python apps/menu/flet_mobile_menu.py`

Optional custom API URL for Flet:
- `python apps/menu/flet_mobile_menu.py --data-url http://127.0.0.1:8000/menu/mobile/data/`

