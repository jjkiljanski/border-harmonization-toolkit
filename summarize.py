def summarize_changes(change_list, lang = "pol"):
    for change in change_list:
        if change.type == "v_change":
            change.echo(lang)