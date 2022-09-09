def show_name(x):
    return x["name"]


def show_weapon_name(x):
    name = x["name"]
    if x["vehicle"]:
        name += " [%s]" % x["vehicle"]

    if x["alias"] != "None":
        name += " (%s)" % x["alias"]

    name += " - " + x["item_id"]

    return name


def get_defaults(data, key_value_func, selected):
    return filter(lambda x: key_value_func(x) in selected, data)


def get_single_value(coll, default):
    if coll:
        return coll[0]
    else:
        return default


def format_for_dropdown(label_key, value_key, data):
    return list(map(lambda x: {"label": x[label_key], "value": x[value_key]}, data))
