from django.shortcuts import render
from accounts.models import Institution
from blocks.models import Category
from accounts import utils
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required


def show_index(request):
    if request.user.is_authenticated():
        user_institution = utils.get_user_institution(request.user)
        user_college = request.user.profile.college
        categories = Category.objects.filter(parent_category__isnull=True,college_limit=user_college)
        if categories.exists():
            for institutions in categories:
                if categories.count() == 1:
                    sub_categories = Category.objects.filter(parent_category=categories)
                    if sub_categories.count() == 1:
                        sub_category = Category.objects.get(parent_category=institutions)
                        HttpResponseRedirect(reverse("blocks:show_category",args=(sub_category.slug,)))
                    else:
                        HttpResponseRedirect(reverse("blocks:show_category",args=(institutions.slug,)))
                else:
                    HttpResponseRedirect(reverse('blocks:list_meta_categories'))

        context = {'categories': categories}

        return render(request, 'index.html', context)
    else:
        return render(request, 'index_unauthenticated.html')
