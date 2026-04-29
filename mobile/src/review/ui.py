from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime

import flet as ft

from .models import ReviewItem, ReviewSubmission, build_review_stats
from .service import ApiError, ReviewApiClient


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
NAME_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ'’\-\s]{1,100}$")


def contains_forbidden_content(value: str) -> bool:
	lower = value.lower()
	return bool(re.search(r"<\s*script", lower) or "javascript:" in lower or "<" in value or ">" in value)


class ReviewFeature:
	def __init__(self, page: ft.Page, on_navigate: Callable[[str], None] | None = None):
		self.page = page
		self.on_navigate = on_navigate
		self.client = ReviewApiClient()

		self.selected_sort = "newest"
		self.selected_rating = "all"
		self.reviews: list[ReviewItem] = []
		self.backend_unavailable = False
		self.local_helpful_counts: dict[int, int] = {}
		self.local_helpful_votes: set[int] = set()

		self.reviews_column = ft.Column(spacing=16)
		self.sort_row = ft.Row(spacing=12, scroll=ft.ScrollMode.AUTO)
		self.rating_filter_row = ft.Row(spacing=8, scroll=ft.ScrollMode.AUTO)

		self.rating_value = 4
		self.rating_score_text = ft.Text("4.0", size=26, weight=ft.FontWeight.BOLD, color="#b24700")
		self.rating_input_stars = ft.Row(spacing=3)

		self.name_input = ft.TextField(label="YOUR NAME", hint_text="E.g. Julian Vane", border_radius=14)
		self.email_input = ft.TextField(label="EMAIL ADDRESS", hint_text="julian@cuisine.com", border_radius=14)
		self.title_input = ft.TextField(label="REVIEW TITLE", hint_text="Summarize your visit", border_radius=14)
		self.details_input = ft.TextField(
			label="THE DETAILS",
			hint_text="Tell us about the textures, the service, and the atmosphere...",
			multiline=True,
			min_lines=5,
			max_lines=7,
			max_length=500,
			border_radius=14,
			on_change=self._update_review_length,
		)
		self.review_length_text = ft.Text("0/500", color="#948a78", size=12)

		self.dish_input = ft.TextField(
			label="DISHES YOU ORDERED",
			hint_text="Add a dish (press enter)",
			border_radius=14,
			on_submit=self._handle_add_dish,
		)
		self.dish_chips = ft.Column(spacing=8)
		self.dishes: list[str] = []

		self.date_input = ft.TextField(
			label="DATE OF VISIT",
			hint_text="mm/dd/yyyy",
			border_radius=14,
			read_only=True,
		)

		self.recommend_value = "yes"
		self.recommend_row = ft.Row(spacing=10)
		self.form_feedback_text = ft.Text("", size=13, color="#7a2315")

		self.date_picker = ft.DatePicker(
			first_date=datetime(2020, 1, 1),
			last_date=datetime.now(),
			on_change=self._handle_date_change,
		)
		self.page.overlay.append(self.date_picker)

	def build_list_view(self) -> ft.Control:
		compact = self._is_compact()
		content_width = self._content_width(620)
		self._ensure_reviews_loaded()
		self._refresh_filter_rows()
		self._refresh_reviews_column()

		stats = build_review_stats(self.reviews)
		distribution = self._build_distribution_rows(stats)

		return ft.Container(
			expand=True,
			bgcolor="#f5efe1",
			alignment=ft.Alignment.TOP_CENTER,
			content=ft.Container(
				width=content_width,
				padding=ft.padding.only(left=14, right=14, top=16, bottom=16),
				content=ft.Column(
					scroll=ft.ScrollMode.AUTO,
					spacing=18,
					controls=[
						ft.Container(
							bgcolor="#efe2c9",
							border_radius=30,
							padding=ft.padding.symmetric(horizontal=18, vertical=20),
							content=ft.Column(
								spacing=10,
								horizontal_alignment=ft.CrossAxisAlignment.CENTER,
								controls=[
									ft.Text(f"{stats.average_rating:.1f}", size=54 if compact else 72, weight=ft.FontWeight.BOLD, color="#b24700"),
									self._stars_row(stats.average_int, size=22 if compact else 28),
									ft.Text(
										f"Based on {stats.total_reviews:,} reviews",
										size=14 if compact else 16,
										color="#665f52",
									),
									ft.Container(height=6),
									*distribution,
									ft.Container(height=8),
									self._primary_button("WRITE A REVIEW", lambda e: self._navigate("/review/write")),
								],
							),
						),
						self.sort_row,
						self.rating_filter_row,
						self.reviews_column,
					],
				),
			),
		)

	def build_write_view(self) -> ft.Control:
		compact = self._is_compact()
		tight = self._is_tight()
		content_width = self._content_width(620)
		self._refresh_rating_row()
		self._refresh_dish_chips()
		self._refresh_recommend_toggle()

		rating_content: ft.Control
		if tight:
			rating_content = ft.Column(
				spacing=8,
				horizontal_alignment=ft.CrossAxisAlignment.CENTER,
				controls=[self.rating_input_stars, self.rating_score_text],
			)
		else:
			rating_content = ft.Row(
				alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
				controls=[self.rating_input_stars, self.rating_score_text],
			)

		return ft.Container(
			expand=True,
			bgcolor="#f5efe1",
			alignment=ft.Alignment.TOP_CENTER,
			content=ft.Container(
				width=content_width,
				padding=ft.padding.only(left=14, right=14, top=16, bottom=16),
				content=ft.Column(
					scroll=ft.ScrollMode.AUTO,
					spacing=16,
					controls=[
						ft.Text("Review", size=40 if compact else 58, weight=ft.FontWeight.BOLD, color="#be4f0b"),
						ft.Text("Share Your Experience", size=15 if compact else 17, color="#6c6559"),
						ft.Container(height=8),
						ft.Text("YOUR RATING", size=13, weight=ft.FontWeight.BOLD, color="#be4f0b"),
						ft.Container(
							border_radius=24,
							bgcolor="#ece1cc",
							padding=ft.padding.symmetric(horizontal=20, vertical=14),
							content=rating_content,
						),
						self.name_input,
						self.email_input,
						self.title_input,
						ft.Row(
							alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
							controls=[
								ft.Text("THE DETAILS", size=13, weight=ft.FontWeight.BOLD, color="#6e685e"),
								self.review_length_text,
							],
						),
						self.details_input,
						ft.Text("DISHES YOU ORDERED", size=13, weight=ft.FontWeight.BOLD, color="#6e685e"),
						ft.Row(
							controls=[
								ft.Container(expand=True, content=self.dish_input),
								ft.IconButton(icon=ft.Icons.ADD_CIRCLE_OUTLINE, on_click=self._handle_add_dish),
							],
						),
						self.dish_chips,
						ft.Row(
							controls=[
								ft.Container(expand=True, content=self.date_input),
								ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, on_click=self._open_date_picker),
							],
						),
						ft.Text("RECOMMEND US?", size=13, weight=ft.FontWeight.BOLD, color="#6e685e"),
						self.recommend_row,
						ft.Container(height=10),
						self.form_feedback_text,
						self._primary_button("SUBMIT REVIEW", self._submit_review),
						ft.TextButton("CANCEL & RETURN", on_click=lambda e: self._navigate("/review")),
					],
				),
			),
		)

	def _build_distribution_rows(self, stats) -> list[ft.Control]:
		rows: list[ft.Control] = []
		total = max(stats.total_reviews, 1)
		bar_width = max(120, min(320, self._content_width(620) - 130))

		for rating in [5, 4, 3, 2, 1]:
			count = stats.counts[rating]
			value = count / total
			rows.append(
				ft.Row(
					controls=[
						ft.Container(width=18, content=ft.Text(str(rating), color="#6f6558", weight=ft.FontWeight.W_600)),
						ft.ProgressBar(
							value=value,
							width=bar_width,
							color="#b24700" if rating >= 4 else "#cda17f",
							bgcolor="#dccfb8",
							bar_height=8,
							border_radius=6,
						),
					]
				)
			)
		return rows

	def _refresh_filter_rows(self) -> None:
		sort_options = [
			("newest", "Newest First"),
			("oldest", "Oldest First"),
			("highest", "Highest Rated"),
			("lowest", "Lowest Rated"),
		]
		rating_options = [("all", "All Ratings"), ("5", "5 Star"), ("4", "4 Star"), ("3", "3 Star"), ("2", "2 Star"), ("1", "1 Star")]
		self.sort_row.controls = [self._sort_chip(value, label) for value, label in sort_options]
		self.rating_filter_row.controls = [self._rating_chip(value, label) for value, label in rating_options]
		self._safe_update(self.sort_row)
		self._safe_update(self.rating_filter_row)

	def _sort_chip(self, value: str, label: str) -> ft.Control:
		active = self.selected_sort == value
		return ft.Container(
			border_radius=22,
			bgcolor="#b24700" if active else "#e7dcc7",
			padding=ft.padding.symmetric(horizontal=22, vertical=10),
			content=ft.Text(label, color="white" if active else "#6b655a", weight=ft.FontWeight.W_600),
			on_click=lambda e: self._select_sort(value),
		)

	def _rating_chip(self, value: str, label: str) -> ft.Control:
		active = self.selected_rating == value
		return ft.Container(
			border_radius=22,
			bgcolor="#f2d29a" if active else "#e7dcc7",
			padding=ft.padding.symmetric(horizontal=16, vertical=9),
			content=ft.Row(
				spacing=4,
				controls=[
					ft.Text(label, color="#8a3b0d" if active else "#6b655a", weight=ft.FontWeight.W_600),
					ft.Icon(ft.Icons.STAR, size=14, color="#f2b705") if value != "all" else ft.Container(width=0),
				],
			),
			on_click=lambda e: self._select_rating(value),
		)

	def _select_sort(self, value: str) -> None:
		self.selected_sort = value
		self._refresh_filter_rows()
		self._refresh_reviews_column()

	def _select_rating(self, value: str) -> None:
		self.selected_rating = value
		self._refresh_filter_rows()
		self._refresh_reviews_column()

	def _refresh_reviews_column(self) -> None:
		data = list(self.reviews)
		if self.selected_rating.isdigit():
			rating = int(self.selected_rating)
			data = [review for review in data if review.rating == rating]

		if self.selected_sort == "newest":
			data.sort(key=lambda item: item.submission_date or "", reverse=True)
		elif self.selected_sort == "oldest":
			data.sort(key=lambda item: item.submission_date or "")
		elif self.selected_sort == "highest":
			data.sort(key=lambda item: (item.rating, item.submission_date or ""), reverse=True)
		elif self.selected_sort == "lowest":
			data.sort(key=lambda item: (item.rating, item.submission_date or ""))

		self.reviews_column.controls = [self._review_card(review) for review in data]
		if not data:
			self.reviews_column.controls = [
				ft.Container(
					border_radius=18,
					padding=20,
					bgcolor="#ffffff",
					content=ft.Text("No reviews yet. Be the first to write one.", color="#6d675d"),
				)
			]
		self._safe_update(self.reviews_column)

	def _review_card(self, review: ReviewItem) -> ft.Control:
		compact = self._is_compact()
		display_helpful = self.local_helpful_counts.get(review.review_id, review.helpful_count)
		avatar = (review.user_name[:1] or "U").upper()
		verified_mark = ft.Icon(ft.Icons.VERIFIED, size=16, color="#b24700") if review.is_verified else ft.Container(width=16)

		dish_tags = [
			ft.Container(
				bgcolor="#f0e2cb",
				border_radius=14,
				padding=ft.padding.symmetric(horizontal=10, vertical=4),
				content=ft.Text(dish.upper(), size=12, weight=ft.FontWeight.BOLD, color="#bb5512"),
			)
			for dish in review.dishes
		]

		helpful_disabled = review.review_id in self.local_helpful_votes

		return ft.Container(
			bgcolor="#f8f8f8",
			border_radius=28,
			padding=ft.padding.symmetric(horizontal=12 if compact else 16, vertical=16 if compact else 18),
			content=ft.Column(
				spacing=10,
				controls=[
					ft.Row(
						alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
						vertical_alignment=ft.CrossAxisAlignment.START,
						controls=[
							ft.Container(
								expand=True,
								content=ft.Row(
									spacing=10,
									controls=[
									ft.Container(
										width=46,
										height=46,
										border_radius=23,
										bgcolor="#c06a36",
										alignment=ft.Alignment.CENTER,
										content=ft.Text(avatar, color="white", weight=ft.FontWeight.BOLD),
									),
									ft.Column(
										spacing=0,
										controls=[
											ft.Row(spacing=6, controls=[ft.Text(review.user_name, size=17, weight=ft.FontWeight.BOLD, color="#2f2c2a"), verified_mark]),
											ft.Text(review.submission_label, size=12, color="#8a8276"),
										],
									),
									],
								),
							),
							self._stars_row(review.rating, size=16 if compact else 18),
						],
					),
					ft.Text(review.review_title, size=18 if compact else 20, weight=ft.FontWeight.BOLD, color="#34302a"),
					ft.Text(review.review_text, size=16 if compact else 18, color="#4d4943"),
					self._build_chip_rows(dish_tags, per_row=1 if compact else 2),
					ft.Divider(color="#e8e2d7"),
					ft.Row(
						alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
						controls=[
							ft.TextButton(
								content=ft.Row(
									spacing=6,
									controls=[
										ft.Icon(ft.Icons.THUMB_UP_OFF_ALT, size=18),
										ft.Text(f"HELPFUL ({display_helpful})", size=15, weight=ft.FontWeight.W_600),
									],
								),
								disabled=helpful_disabled,
								on_click=lambda e, rid=review.review_id: self._vote_helpful(rid),
							),
							ft.TextButton(
								content=ft.Row(spacing=6, controls=[ft.Icon(ft.Icons.SHARE, size=18), ft.Text("SHARE", size=15, weight=ft.FontWeight.W_600)]),
								on_click=lambda e: self._show_message("Share action is not wired yet."),
							),
						],
					),
				],
			),
		)

	def _refresh_rating_row(self) -> None:
		compact = self._is_compact()
		tight = self._is_tight()
		self.rating_input_stars.controls = []
		for star in range(1, 6):
			is_filled = star <= self.rating_value
			self.rating_input_stars.controls.append(
				ft.IconButton(
					icon=ft.Icons.STAR if is_filled else ft.Icons.STAR_BORDER,
					selected_icon=ft.Icons.STAR,
					icon_color="#b24700" if is_filled else "#b3a999",
					icon_size=24 if tight else (28 if compact else 36),
					on_click=lambda e, value=star: self._set_rating(value),
				)
			)
		self._safe_update(self.rating_input_stars)

	def _set_rating(self, value: int) -> None:
		self.rating_value = value
		self.rating_score_text.value = f"{value:.1f}"
		self._safe_update(self.rating_score_text)
		self._refresh_rating_row()

	def _handle_add_dish(self, e: ft.ControlEvent) -> None:
		value = (self.dish_input.value or "").strip()
		if not value:
			return
		if contains_forbidden_content(value):
			self._show_message("Please remove HTML or script content from dishes ordered.", is_error=True)
			return
		if len(", ".join([*self.dishes, value])) > 255:
			self._show_message("Dishes ordered must be 255 characters or less.", is_error=True)
			return
		self.dishes.append(value)
		self.dish_input.value = ""
		self._safe_update(self.dish_input)
		self._refresh_dish_chips()

	def _refresh_dish_chips(self) -> None:
		chips: list[ft.Control] = []
		for idx, dish in enumerate(self.dishes):
			chips.append(
				ft.Container(
					bgcolor="#f0e2cb",
					border_radius=16,
					padding=ft.padding.only(left=12, right=6, top=6, bottom=6),
					content=ft.Row(
						spacing=4,
						controls=[
							ft.Text(dish.upper(), size=13, color="#b24700", weight=ft.FontWeight.W_600),
							ft.IconButton(icon=ft.Icons.CLOSE, icon_size=14, on_click=lambda e, i=idx: self._remove_dish(i)),
						],
					),
				)
			)
		self.dish_chips.controls = self._chunk_to_rows(chips, per_row=2)
		self._safe_update(self.dish_chips)

	def _remove_dish(self, index: int) -> None:
		if 0 <= index < len(self.dishes):
			self.dishes.pop(index)
			self._refresh_dish_chips()

	def _update_review_length(self, e: ft.ControlEvent) -> None:
		value = self.details_input.value or ""
		self.review_length_text.value = f"{len(value)}/500"
		self._safe_update(self.review_length_text)

	def _refresh_recommend_toggle(self) -> None:
		self.recommend_row.controls = [
			self._recommend_option("yes", "YES"),
			self._recommend_option("no", "NO"),
		]
		self._safe_update(self.recommend_row)

	def _recommend_option(self, value: str, label: str) -> ft.Control:
		active = self.recommend_value == value
		return ft.Container(
			border_radius=20,
			bgcolor="#b24700" if active else "#efe3cd",
			padding=ft.padding.symmetric(horizontal=28, vertical=10),
			content=ft.Text(label, color="white" if active else "#6c665a", weight=ft.FontWeight.BOLD),
			on_click=lambda e: self._set_recommendation(value),
		)

	def _set_recommendation(self, value: str) -> None:
		self.recommend_value = value
		self._refresh_recommend_toggle()

	def _handle_date_change(self, e: ft.ControlEvent) -> None:
		if self.date_picker.value:
			self.date_input.value = self.date_picker.value.strftime("%m/%d/%Y")
			self._safe_update(self.date_input)

	def _open_date_picker(self, e: ft.ControlEvent) -> None:
		self.date_picker.open = True
		self._safe_update(self.date_picker)

	def _submit_review(self, e: ft.ControlEvent) -> None:
		self.form_feedback_text.value = ""
		self._safe_update(self.form_feedback_text)

		name = (self.name_input.value or "").strip()
		email = (self.email_input.value or "").strip()
		title = (self.title_input.value or "").strip()
		details = (self.details_input.value or "").strip()

		if not name or not email or not title or not details:
			self._set_form_feedback("Please complete all required fields.", is_error=True)
			return

		if not NAME_RE.match(name) or contains_forbidden_content(name):
			self._set_form_feedback("Please enter a valid name using letters, spaces, apostrophes, or hyphens.", is_error=True)
			return

		if not EMAIL_RE.match(email):
			self._set_form_feedback("Please enter a valid email address.", is_error=True)
			return

		if contains_forbidden_content(email) or contains_forbidden_content(title) or contains_forbidden_content(details):
			self._set_form_feedback("Please remove HTML or script content from your review.", is_error=True)
			return

		if len(name) > 100:
			self._set_form_feedback("Name must be 100 characters or less.", is_error=True)
			return

		if len(title) > 100:
			self._set_form_feedback("Review title must be 100 characters or less.", is_error=True)
			return

		if len(", ".join(self.dishes)) > 255:
			self._set_form_feedback("Dishes ordered must be 255 characters or less.", is_error=True)
			return

		if any(contains_forbidden_content(dish) for dish in self.dishes):
			self._set_form_feedback("Please remove HTML or script content from dishes ordered.", is_error=True)
			return

		if len(details) > 500:
			self._set_form_feedback("Review details must be 500 characters or less.", is_error=True)
			return

		visit_iso: str | None = None
		if self.date_input.value.strip():
			try:
				visit_dt = datetime.strptime(self.date_input.value.strip(), "%m/%d/%Y")
				visit_iso = visit_dt.date().isoformat()
			except ValueError:
				self._set_form_feedback("Date of visit must be in mm/dd/yyyy format.", is_error=True)
				return

		payload = ReviewSubmission(
			user_name=name,
			email=email,
			review_title=title,
			review_text=details,
			rating=self.rating_value,
			dishes_ordered=", ".join(self.dishes),
			date_of_visit=visit_iso,
			would_you_recommend=self.recommend_value,
		)

		try:
			self.client.create_review(payload)
		except ApiError as exc:
			if exc.status_code in (401, 403):
				self._set_form_feedback(
					"Submission blocked by backend auth. Set ECAG_API_TOKEN and retry.",
					is_error=True,
				)
				return
			self._set_form_feedback(str(exc), is_error=True)
			return

		self._set_form_feedback("Review submitted successfully.", is_error=False)
		self._show_message("Review submitted successfully.")
		self._reset_form()
		self._ensure_reviews_loaded(force=True)
		self._navigate("/review")

	def _reset_form(self) -> None:
		self.rating_value = 4
		self._refresh_rating_row()
		self.rating_score_text.value = "4.0"
		self.name_input.value = ""
		self.email_input.value = ""
		self.title_input.value = ""
		self.details_input.value = ""
		self.review_length_text.value = "0/500"
		self.dishes = []
		self._refresh_dish_chips()
		self.date_input.value = ""
		self.recommend_value = "yes"
		self.form_feedback_text.value = ""
		self._refresh_recommend_toggle()

	def _ensure_reviews_loaded(self, force: bool = False) -> None:
		if self.reviews and not force:
			return

		try:
			self.reviews = self.client.list_reviews()
			self.backend_unavailable = False
		except ApiError as exc:
			self.backend_unavailable = True
			self._show_message(
				f"Unable to load backend reviews. Showing cached/mobile-only data. {exc}",
				is_error=True,
			)
			if force:
				self.reviews = []

	def _vote_helpful(self, review_id: int) -> None:
		self.local_helpful_votes.add(review_id)
		base_count = self.local_helpful_counts.get(review_id)
		if base_count is None:
			current = next((r.helpful_count for r in self.reviews if r.review_id == review_id), 0)
			self.local_helpful_counts[review_id] = current + 1
		else:
			self.local_helpful_counts[review_id] = base_count + 1

		try:
			helpful_count = self.client.mark_helpful(review_id)
			self.local_helpful_counts[review_id] = helpful_count
		except ApiError:
			self._show_message("Helpful vote saved locally. Backend rejected the request.", is_error=True)

		self._refresh_reviews_column()

	def _stars_row(self, rating: int, size: int) -> ft.Row:
		controls: list[ft.Control] = []
		for idx in range(1, 6):
			controls.append(
				ft.Icon(
					ft.Icons.STAR if idx <= rating else ft.Icons.STAR_BORDER,
					color="#a36500" if idx <= rating else "#cabca8",
					size=size,
				)
			)
		return ft.Row(spacing=1, controls=controls)

	def _primary_button(self, text: str, on_click) -> ft.Control:
		compact = self._is_compact()
		button = ft.ElevatedButton(
			text,
			on_click=on_click,
			style=ft.ButtonStyle(
				bgcolor="#c94f14",
				color="white",
				shape=ft.RoundedRectangleBorder(radius=16),
				padding=ft.padding.symmetric(horizontal=18 if compact else 26, vertical=14 if compact else 16),
			),
		)
		return ft.Container(
			width=max(220, self._content_width(620) - 28),
			content=button,
		)

	def _screen_width(self) -> int:
		width = getattr(self.page, "width", None)
		if isinstance(width, (int, float)) and width > 0:
			return int(width)
		return 390

	def _is_compact(self) -> bool:
		return self._screen_width() <= 430

	def _is_tight(self) -> bool:
		return self._screen_width() <= 360

	def _content_width(self, max_width: int) -> int:
		return max(280, min(max_width, self._screen_width() - 18))

	def _set_form_feedback(self, message: str, is_error: bool) -> None:
		self.form_feedback_text.value = message
		self.form_feedback_text.color = "#7a2315" if is_error else "#2f6c43"
		self._safe_update(self.form_feedback_text)
		self._show_message(message, is_error=is_error)

	def _build_chip_rows(self, chips: list[ft.Control], per_row: int) -> ft.Control:
		return ft.Column(spacing=8, controls=self._chunk_to_rows(chips, per_row=per_row))

	def _chunk_to_rows(self, controls: list[ft.Control], per_row: int) -> list[ft.Row]:
		if not controls:
			return []

		rows: list[ft.Row] = []
		for index in range(0, len(controls), per_row):
			rows.append(ft.Row(spacing=8, controls=controls[index:index + per_row]))
		return rows

	def _show_message(self, message: str, is_error: bool = False) -> None:
		self.page.snack_bar = ft.SnackBar(
			content=ft.Text(message),
			bgcolor="#7a2315" if is_error else "#2f6c43",
		)
		self.page.snack_bar.open = True
		self.page.update()

	def _safe_update(self, control: ft.Control) -> None:
		try:
			self.page.update()
		except RuntimeError:
			# Ignore transient updates while controls are being re-mounted.
			pass

	def _navigate(self, route: str) -> None:
		if self.on_navigate is not None:
			self.on_navigate(route)
		else:
			self.page.go(route)
