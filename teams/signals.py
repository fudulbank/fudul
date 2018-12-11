def mark_editors(sender, **kwargs):
    team = kwargs['instance']
    for user in team.members.select_related('profile')\
                            .filter(profile__is_editor=False):
        profile = user.profile
        profile.is_editor = True
        profile.save()
