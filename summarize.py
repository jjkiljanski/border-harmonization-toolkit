def list_json_change_types(changes_json):
    # Takes the district changes read directly from json and print all different change "type" attributes.
    types = [change["type"] for change in changes_json]
    types = set(types)
    print(types)

def summarize_by_d(change_list, lang = "pol"):
    return