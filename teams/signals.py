def mark_editors(sender, raw, **kwargs):
    if raw:
        return
    team = kwargs['instance']
    from accounts.models import Profile
    Profile.objects.filter(is_editor=False,
                           user__team_memberships__isnull=False)\
                   .update(is_editor=True)

    Profile.objects.filter(is_editor=True,
                           user__team_memberships__isnull=True)\
                   .update(is_editor=False)

def mark_examiners(sender, raw, **kwargs):
    if raw:
        return
    team = kwargs['instance']
    if team.is_examiner:
        from accounts.models import Profile
        Profile.objects.filter(is_examiner=False,
                               user__team_memberships__is_examiner=True)\
                       .update(is_examiner=True)

        Profile.objects.filter(is_examiner=True)\
                       .exclude(user__team_memberships__is_examiner=True)\
                       .update(is_examiner=False)
