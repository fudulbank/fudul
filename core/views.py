from django.shortcuts import render
from accounts.models import Institution

def show_index(request):
    if request.user.is_authenticated():
        institutions = Institution.objects.all()
        context = {'institutions': institutions}
        return render(request, 'index.html', context)
    else:
        return render(request, 'index_unauthenticated.html')
