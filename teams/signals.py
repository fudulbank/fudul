def mark_editors(sender, raw, **kwargs):
    if raw:
        return
    team = kwargs['instance']
    for user in team.members.select_related('profile')\
                            .filter(profile__is_editor=False):
        profile = user.profile
        profile.is_editor = True
        profile.save()
