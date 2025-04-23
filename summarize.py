def summarize_by_date(change_list, lang = "pol"):
    for change in change_list:
        if change.type == "v_change" or change.type == "d_one_to_many":
            change.echo(lang)

def summarize_by_d(change_list, lang = "pol"):
    return