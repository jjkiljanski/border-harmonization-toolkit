def list_json_change_types(changes_json):
    # Takes the district changes read directly from json and print all different change "type" attributes.
    types = [change["type"] for change in changes_json]
    types = set(types)
    print(types)

def list_change_dates(changes_list, lang = "pol"):
    # Lists all the dates of border changes.
    dates = [change.date for change in changes_list]
    dates = list(set(dates))
    dates.sort()
    if lang == "pol":
        print("Wszystkie daty zmian granic:")
    elif lang == "eng":
        print("All dates of border changes:")
    else:
        raise ValueError("Wrong value for the lang parameter.") 
    for date in dates: print(date)

def summarize_by_date(change_list, lang = "pol"):
    # Prints all changes ordered by date.
    for change in change_list:
        if change.type == "v_change" or change.type == "d_one_to_many" or change.type == "d_many_to_one":
            change.echo(lang)

def summarize_by_d(change_list, lang = "pol"):
    return