from django.shortcuts import render, get_object_or_404
from .models import MenuCategory


def _build_sections(category_name):
    """
    Helper that returns a dict like:
    {
        "CRISPY": <QuerySet of MenuItem>,
        "SALADS": <QuerySet of MenuItem>,
        ...
    }
    for the given top-level MenuCategory.
    """
    category = get_object_or_404(MenuCategory, category=category_name)

    sections = {}
    # Default reverse relation: menusubcategory_set -> menuitem_set
    for sub in category.menusubcategory_set.all():
        items = sub.menuitem_set.filter(is_available=True)
        if items.exists():
            sections[sub.subcategory.upper()] = items

    return sections


def menu_starters(request):
    """
    Starters page (uses menu/menu_starters.html).
    Template expects `sections` and `active`.
    """
    sections = _build_sections("Starters")
    return render(
        request,
        "menu_starters.html",
        {
            "sections": sections,
            "active": "starters",
        },
    )


def menu_main_course(request):
    """
    Main course page (uses menu/menu_main_course.html).
    Template should loop over `sections` similar to starters.
    """
    sections = _build_sections("Main Course")
    return render(
        request,
        "menu_main_course.html",
        {
            "sections": sections,
            "active": "main_course",
        },
    )


def menu_beverages(request):
    """
    Beverages page (uses menu/menu_beverages.html).
    Template already loops over `sections`.
    """
    sections = _build_sections("Beverages")
    return render(
        request,
        "menu_beverages.html",
        {
            "sections": sections,
            "active": "beverages",
        },
    )
