from django.shortcuts import render
from django.http import HttpRequest
from django.db.models import Count, Q
from django.core.paginator import Paginator
from accounts.models import UserProfile
from skills.models import Skill, Category 

# Create your views here.

def browse_view(request : HttpRequest):
    
    query = request.GET.get("q", "").strip()
    offered_id = request.GET.get("offered", "").strip()
    needed_id = request.GET.get("needed", "").strip()
    
    qs = UserProfile.objects.select_related("user").prefetch_related("offered_skills__skill", "needed_skills__skill").all()
        
    if len(query) >= 3:
        qs = qs.filter(user__username__icontains=query)

    # فلتر: users who OFFER a given skill
    if offered_id:
        try:
            offered_id_int = int(offered_id)
            qs = qs.filter(user__offered_skills__skill__id=offered_id_int)
        except ValueError:
            pass

    # فلتر: users who NEED a given skill
    if needed_id:
        try:
            needed_id_int = int(needed_id)
            qs = qs.filter(user__needed_skills__skill__id=needed_id_int)
        except ValueError:
            pass

    qs = qs.distinct()  # مهم لنتجنب التكرار عند الـ joins

    # جلب كل السكِلز عشان نعرضهم في الفيلتر dropdown
    skills = Skill.objects.order_by("skill").all()

    context = {
        "profiles": qs,
        "skills": skills,
        "query": query,
        "selected_offered": offered_id,
        "selected_needed": needed_id,
    }
        
        
    return render(request, 'browse/browse.html', context)
    

# def search_view (request : HttpRequest):
    
#     query = request.GET.get("q", "").strip()
#     results = []
    
#     if len(query) >= 3:
#         results = UserProfile.objects.filter(user__username__icontains=query)
#     return render(request, "browse/browse.html", {"results": results, "query": query})
    
#     # if "search" in request.GET and len(request.GET["search"]) >= 3:
#     #     results = UserProfile.objects.filter(user__username__icontains = request.GET["search"])
#     # else:
#     #     results = []
        
#     # return render(request, "browse/browse.html", {"results": results})
    

