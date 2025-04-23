def list_json_change_types(changes_json):
    # Takes the district changes read directly from json and print all different change "type" attributes.
    types = [change["type"] for change in json_changes]
    types = set(types)
    print(types)

def summarize_by_date(change_list, lang = "pol"):
    # Prints all changes ordered by date.
    for change in change_list:
        if change.type == "v_change" or change.type == "d_one_to_many" or change.type == "d_many_to_one":
            change.echo(lang)

def summarize_by_d(change_list, lang = "pol"):
    return