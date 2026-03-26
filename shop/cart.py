def add_to_cart(request, product_id):
    cart = request.session.get("cart", {})

    if product_id in cart:
        cart[product_id] += 1
    else:
        cart[product_id] = 1

    request.session["cart"] = cart


def remove_from_cart(request, product_id):
    cart = request.session.get("cart", {})

    if product_id in cart:
        del cart[product_id]

    request.session["cart"] = cart