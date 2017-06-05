from django.shortcuts import render

def show_index(request):
    if request.user.is_authenticated():
        return render(request, 'index.html')
    else:
        return render(request, 'index_unauthenticated.html')
